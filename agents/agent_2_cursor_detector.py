import cv2
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from config.settings import (
    CURSOR_CONFIDENCE_THRESHOLD,
    CLICK_DETECTION_THRESHOLD,
    HOVER_DETECTION_THRESHOLD,
    CURSOR_MODEL
)
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger

class CursorDetectorAgent:
    """Agent 2: Detects cursor position, clicks, and drags"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("cursor_detector", project_id)
        self.model = None
        
    def execute(self, frames: List[Dict[str, Any]], config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Detect cursor in frames
        
        Args:
            frames: List of frame dictionaries from Agent 1
            config: Optional configuration overrides
            
        Returns:
            Result dictionary with cursor events
        """
        self.logger.start("Starting cursor detection")
        start_time = datetime.now()
        
        try:
            # Merge config with defaults
            cfg = {
                "confidence_threshold": CURSOR_CONFIDENCE_THRESHOLD,
                "model_type": CURSOR_MODEL,
                "detect_clicks": True,
                "detect_drags": True
            }
            if config:
                cfg.update(config)
            
            # Load detection model
            if not self._load_model(cfg["model_type"]):
                raise Exception("Failed to load cursor detection model")
            
            # Process frames
            cursor_events = self._process_frames(frames, cfg)
            
            # Detect actions (clicks, drags, hovers)
            self._detect_actions(cursor_events, cfg)
            
            # Calculate trajectory statistics
            trajectory_stats = self._calculate_trajectory_stats(cursor_events)
            
            # Build result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            frames_with_cursor = sum(1 for e in cursor_events if e["cursor_detected"])
            
            result = {
                "agent": "cursor_detector",
                "status": "success",
                "execution_time": execution_time,
                "cursor_events": cursor_events,
                "trajectory": trajectory_stats,
                "metadata": {
                    "frames_processed": len(frames),
                    "frames_with_cursor": frames_with_cursor,
                    "detection_rate": frames_with_cursor / len(frames) if frames else 0
                }
            }
            
            # Save result
            self.file_manager.save_json(result, "cursor_events.json")
            
            self.logger.success(f"Detected cursor in {frames_with_cursor}/{len(frames)} frames")
            return result
            
        except Exception as e:
            self.logger.error(f"Cursor detection failed: {e}", exc_info=True)
            return {
                "agent": "cursor_detector",
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _load_model(self, model_type: str) -> bool:
        """Load cursor detection model"""
        try:
            if model_type == "yolov8":
                from models.yolo_cursor_detector import YOLOCursorDetector
                self.model = YOLOCursorDetector()
                self.logger.info("Loaded YOLOv8 cursor detector")
                return True
            
            elif model_type == "roboflow":
                try:
                    from roboflow import Roboflow
                    from config.settings import ROBOFLOW_API_KEY
                    
                    if not ROBOFLOW_API_KEY:
                        raise Exception("Roboflow API key not set")
                    
                    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
                    project = rf.workspace().project("cursor-detection")
                    self.model = project.version(1).model
                    self.logger.info("Loaded Roboflow cursor detector")
                    return True
                except ImportError:
                    self.logger.error("Roboflow not installed. Install: pip install roboflow")
                    return False
            
            else:
                # Fallback to template matching
                self.model = "template"
                self.logger.warning("Using fallback template matching for cursor detection")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}", exc_info=True)
            return False
    
    def _process_frames(self, frames: List[Dict], config: Dict) -> List[Dict]:
        """Process each frame to detect cursor"""
        cursor_events = []
        prev_center = None
        
        for frame_data in frames:
            frame_path = frame_data["path"]
            frame_id = frame_data["id"]
            timestamp = frame_data["timestamp"]
            
            # Load frame
            frame = cv2.imread(frame_path)
            if frame is None:
                self.logger.warning(f"Failed to load frame: {frame_path}")
                cursor_events.append({
                    "frame_id": frame_id,
                    "timestamp": timestamp,
                    "cursor_detected": False,
                    "bbox": None,
                    "center": None,
                    "confidence": 0.0,
                    "action": "unknown",
                    "velocity": 0.0
                })
                continue
            
            # Detect cursor
            detection = self._detect_cursor(frame, config["confidence_threshold"])
            
            # Calculate velocity
            velocity = 0.0
            if detection["cursor_detected"] and prev_center:
                curr_center = detection["center"]
                velocity = np.sqrt(
                    (curr_center[0] - prev_center[0])**2 + 
                    (curr_center[1] - prev_center[1])**2
                )
                prev_center = curr_center
            elif detection["cursor_detected"]:
                prev_center = detection["center"]
            
            cursor_events.append({
                "frame_id": frame_id,
                "timestamp": timestamp,
                "cursor_detected": detection["cursor_detected"],
                "bbox": detection["bbox"],
                "center": detection["center"],
                "confidence": detection["confidence"],
                "action": "moving",  # Will be updated in _detect_actions
                "velocity": round(velocity, 2)
            })
        
        return cursor_events
    
    def _detect_cursor(self, frame: np.ndarray, threshold: float) -> Dict:
        """Detect cursor in a single frame"""
        try:
            if self.model == "template":
                # Fallback: Look for cursor-like shapes (white arrow, pointer)
                return self._template_matching_detection(frame, threshold)
            
            elif isinstance(self.model, object) and hasattr(self.model, 'detect'):
                # YOLOv8 or Roboflow
                return self.model.detect(frame, threshold)
            
            else:
                return {
                    "cursor_detected": False,
                    "bbox": None,
                    "center": None,
                    "confidence": 0.0
                }
                
        except Exception as e:
            self.logger.debug(f"Detection error: {e}")
            return {
                "cursor_detected": False,
                "bbox": None,
                "center": None,
                "confidence": 0.0
            }
    
    def _template_matching_detection(self, frame: np.ndarray, threshold: float) -> Dict:
        """Fallback cursor detection using template matching"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Simple heuristic: find bright small regions (potential cursor)
        # This is a very basic fallback - YOLO is much better
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Look for small bright regions
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 1000:  # Cursor-sized region
                x, y, w, h = cv2.boundingRect(contour)
                center = [x + w//2, y + h//2]
                
                return {
                    "cursor_detected": True,
                    "bbox": [x, y, x+w, y+h],
                    "center": center,
                    "confidence": 0.6  # Lower confidence for template matching
                }
        
        return {
            "cursor_detected": False,
            "bbox": None,
            "center": None,
            "confidence": 0.0
        }
    
    def _detect_actions(self, cursor_events: List[Dict], config: Dict):
        """Detect clicks, drags, and hovers from cursor movement"""
        if not config["detect_clicks"]:
            return
        
        for i in range(len(cursor_events)):
            event = cursor_events[i]
            
            if not event["cursor_detected"]:
                event["action"] = "not_visible"
                continue
            
            # Detect hover (low velocity for extended period)
            if event["velocity"] < 5.0:
                hover_duration = self._count_stationary_frames(cursor_events, i)
                if hover_duration >= HOVER_DETECTION_THRESHOLD:
                    event["action"] = "hover"
                    continue
            
            # Detect click (stop + slight movement)
            if self._is_click_pattern(cursor_events, i):
                event["action"] = "click"
                continue
            
            # Detect drag (sustained movement)
            if config["detect_drags"] and self._is_drag_pattern(cursor_events, i):
                event["action"] = "drag"
                continue
            
            # Default: moving
            if event["velocity"] > 5.0:
                event["action"] = "moving"
            else:
                event["action"] = "idle"
    
    def _count_stationary_frames(self, events: List[Dict], index: int) -> float:
        """Count how long cursor stays in similar position"""
        if index >= len(events) - 1:
            return 0.0
        
        current_pos = events[index]["center"]
        if not current_pos:
            return 0.0
        
        duration = 0.0
        for i in range(index + 1, len(events)):
            next_pos = events[i]["center"]
            if not next_pos:
                break
            
            distance = np.sqrt(
                (next_pos[0] - current_pos[0])**2 + 
                (next_pos[1] - current_pos[1])**2
            )
            
            if distance < 10:  # Within 10 pixels
                duration += events[i]["timestamp"] - events[i-1]["timestamp"]
            else:
                break
        
        return duration
    
    def _is_click_pattern(self, events: List[Dict], index: int) -> bool:
        """Detect if pattern matches a click (stop, slight down movement)"""
        if index < 2 or index >= len(events) - 2:
            return False
        
        # Check if cursor was moving before
        if events[index - 1]["velocity"] < 5.0:
            return False
        
        # Check if cursor stopped
        if events[index]["velocity"] > 5.0:
            return False
        
        # Check for slight downward movement after stop
        curr_pos = events[index]["center"]
        next_pos = events[index + 1]["center"]
        
        if not curr_pos or not next_pos:
            return False
        
        # Click typically shows small downward motion
        dy = next_pos[1] - curr_pos[1]
        if 2 < dy < 15:
            return True
        
        return False
    
    def _is_drag_pattern(self, events: List[Dict], index: int) -> bool:
        """Detect if pattern matches a drag (sustained directional movement)"""
        if index < 3 or index >= len(events) - 3:
            return False
        
        # Check for sustained movement in same direction
        velocities = [events[i]["velocity"] for i in range(index-2, index+3)]
        
        # All velocities should be moderate (not too fast, not stopped)
        if all(10 < v < 100 for v in velocities):
            return True
        
        return False
    
    def _calculate_trajectory_stats(self, cursor_events: List[Dict]) -> Dict:
        """Calculate statistics about cursor trajectory"""
        total_movements = sum(1 for e in cursor_events if e.get("velocity", 0) > 5)
        clicks_detected = sum(1 for e in cursor_events if e.get("action") == "click")
        drags_detected = sum(1 for e in cursor_events if e.get("action") == "drag")
        hover_moments = sum(1 for e in cursor_events if e.get("action") == "hover")
        
        return {
            "total_movements": total_movements,
            "clicks_detected": clicks_detected,
            "drags_detected": drags_detected,
            "hover_moments": hover_moments
        }