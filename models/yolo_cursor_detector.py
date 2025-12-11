import numpy as np
from pathlib import Path
from typing import Dict, Optional
import cv2

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

from config.settings import MODELS_DIR, YOLO_MODEL_SIZE

class YOLOCursorDetector:
    """YOLO-based cursor detector"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize YOLO cursor detector
        
        Args:
            model_path: Path to YOLO model weights (optional)
        """
        if not YOLO_AVAILABLE:
            raise ImportError("ultralytics not installed. Install: pip install ultralytics")
        
        # Use provided model or download default
        if model_path:
            self.model = YOLO(model_path)
        else:
            # Use YOLOv8 nano for speed (can detect pointer-like objects)
            model_file = MODELS_DIR / f"yolov8{YOLO_MODEL_SIZE}.pt"
            
            # YOLO will download automatically if not present
            self.model = YOLO(f"yolov8{YOLO_MODEL_SIZE}.pt")
            
            # Note: For best cursor detection, you'd train a custom YOLO model
            # on cursor images. This uses the pre-trained model which may detect
            # cursor-like objects with limited accuracy.
    
    def detect(self, frame: np.ndarray, confidence_threshold: float = 0.7) -> Dict:
        """
        Detect cursor in frame
        
        Args:
            frame: Input frame (numpy array)
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            Detection dictionary
        """
        try:
            # Run inference
            results = self.model.predict(
                frame,
                conf=confidence_threshold,
                verbose=False,
                device='cpu'  # Use CPU by default (change to 'cuda' if GPU available)
            )
            
            # Since we don't have a cursor-specific model, we'll look for small objects
            # that could be cursors (fallback approach)
            best_detection = self._find_cursor_candidate(results[0], frame.shape)
            
            if best_detection:
                return {
                    "cursor_detected": True,
                    "bbox": best_detection["bbox"],
                    "center": best_detection["center"],
                    "confidence": best_detection["confidence"]
                }
            
            return {
                "cursor_detected": False,
                "bbox": None,
                "center": None,
                "confidence": 0.0
            }
            
        except Exception as e:
            print(f"YOLO detection error: {e}")
            return {
                "cursor_detected": False,
                "bbox": None,
                "center": None,
                "confidence": 0.0
            }
    
    def _find_cursor_candidate(self, result, frame_shape) -> Optional[Dict]:
        """
        Find the most likely cursor from detections
        
        Since we don't have a cursor-specific model, we use heuristics:
        - Small size (cursors are typically small)
        - High contrast area
        - Located in reasonable screen position
        """
        if not result.boxes:
            return None
        
        height, width = frame_shape[:2]
        candidates = []
        
        for box in result.boxes:
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0])
            
            # Calculate size
            w = x2 - x1
            h = y2 - y1
            area = w * h
            
            # Cursor heuristics: small size (100-2000 pixels)
            if 100 < area < 2000:
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                
                candidates.append({
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "center": [center_x, center_y],
                    "confidence": conf,
                    "area": area
                })
        
        # Return the smallest detection (most likely to be cursor)
        if candidates:
            return min(candidates, key=lambda x: x["area"])
        
        return None


class TemplateCursorDetector:
    """
    Fallback cursor detector using template matching and color detection
    
    This is used when YOLO is not available or as a backup method
    """
    
    def __init__(self):
        """Initialize template-based detector"""
        self.templates = self._create_cursor_templates()
    
    def _create_cursor_templates(self):
        """Create basic cursor templates"""
        templates = []
        
        # White arrow cursor (most common)
        arrow = np.zeros((20, 15, 3), dtype=np.uint8)
        pts = np.array([[0, 0], [0, 18], [5, 14], [8, 19], [11, 17], [8, 12], [13, 12]], dtype=np.int32)
        cv2.fillPoly(arrow, [pts], (255, 255, 255))
        templates.append(arrow)
        
        # Black arrow cursor
        arrow_black = arrow.copy()
        cv2.fillPoly(arrow_black, [pts], (0, 0, 0))
        templates.append(arrow_black)
        
        return templates
    
    def detect(self, frame: np.ndarray, confidence_threshold: float = 0.6) -> Dict:
        """
        Detect cursor using template matching
        
        Args:
            frame: Input frame
            confidence_threshold: Minimum confidence
            
        Returns:
            Detection dictionary
        """
        try:
            best_match = None
            best_score = 0
            
            # Try each template
            for template in self.templates:
                result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_match = {
                        "location": max_loc,
                        "template_size": template.shape[:2]
                    }
            
            # Check if match is good enough
            if best_match and best_score > confidence_threshold:
                x, y = best_match["location"]
                h, w = best_match["template_size"]
                
                return {
                    "cursor_detected": True,
                    "bbox": [x, y, x + w, y + h],
                    "center": [x + w // 2, y + h // 2],
                    "confidence": float(best_score)
                }
            
            return {
                "cursor_detected": False,
                "bbox": None,
                "center": None,
                "confidence": 0.0
            }
            
        except Exception as e:
            print(f"Template detection error: {e}")
            return {
                "cursor_detected": False,
                "bbox": None,
                "center": None,
                "confidence": 0.0
            }


# Factory function to get appropriate detector
def get_cursor_detector(use_yolo: bool = True):
    """
    Get cursor detector instance
    
    Args:
        use_yolo: Whether to use YOLO (falls back to template if not available)
        
    Returns:
        Cursor detector instance
    """
    if use_yolo and YOLO_AVAILABLE:
        try:
            return YOLOCursorDetector()
        except Exception as e:
            print(f"Failed to initialize YOLO: {e}, falling back to template matching")
            return TemplateCursorDetector()
    else:
        return TemplateCursorDetector()