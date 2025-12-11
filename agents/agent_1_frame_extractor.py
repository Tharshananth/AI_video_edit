import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from config.settings import (
    DEFAULT_FPS, MAX_FRAMES, FRAME_RESOLUTION, 
    FRAME_FORMAT, FRAME_QUALITY
)
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger

class FrameExtractorAgent:
    """Agent 1: Extracts frames from video using FFmpeg"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("frame_extractor", project_id)
    
    def execute(self, video_path: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract frames from video
        
        Args:
            video_path: Path to input video
            config: Configuration dictionary with optional overrides
            
        Returns:
            Result dictionary with frame information
        """
        self.logger.start("Starting frame extraction")
        start_time = datetime.now()
        
        try:
            # Merge config with defaults
            cfg = {
                "fps": DEFAULT_FPS,
                "max_frames": MAX_FRAMES,
                "resolution": FRAME_RESOLUTION,
                "format": FRAME_FORMAT,
                "quality": FRAME_QUALITY
            }
            if config:
                cfg.update(config)
            
            # Get video metadata
            video_metadata = self._get_video_info(video_path)
            if not video_metadata:
                raise Exception("Failed to get video metadata")
            
            video_duration = video_metadata["duration"]
            original_fps = video_metadata["fps"]
            
            # Calculate actual FPS to stay under max_frames
            total_frames_at_fps = int(video_duration * cfg["fps"])
            if total_frames_at_fps > cfg["max_frames"]:
                actual_fps = cfg["max_frames"] / video_duration
                self.logger.info(f"Adjusting FPS from {cfg['fps']} to {actual_fps:.2f} to stay under {cfg['max_frames']} frames")
                cfg["fps"] = actual_fps
            
            # Extract frames
            frames = self._extract_frames(video_path, cfg)
            
            if not frames:
                raise Exception("No frames extracted")
            
            # Build result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = {
                "agent": "frame_extractor",
                "status": "success",
                "execution_time": execution_time,
                "frames": frames,
                "metadata": {
                    "total_frames": len(frames),
                    "video_duration": video_duration,
                    "fps_used": cfg["fps"],
                    "original_resolution": f"{video_metadata['width']}x{video_metadata['height']}",
                    "target_resolution": cfg["resolution"]
                }
            }
            
            # Save result
            self.file_manager.save_json(result, "frames.json")
            
            self.logger.success(f"Extracted {len(frames)} frames")
            return result
            
        except Exception as e:
            self.logger.error(f"Frame extraction failed: {e}", exc_info=True)
            return {
                "agent": "frame_extractor",
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Get video metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"FFprobe failed: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            video_stream = next(
                (s for s in data.get('streams', []) if s['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                return None
            
            return {
                "duration": float(data['format'].get('duration', 0)),
                "width": video_stream['width'],
                "height": video_stream['height'],
                "fps": eval(video_stream.get('r_frame_rate', '30/1'))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get video info: {e}")
            return None
    
    def _extract_frames(self, video_path: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract frames using FFmpeg"""
        try:
            frames_dir = self.file_manager.frames_dir
            output_pattern = frames_dir / f"frame_%04d.{config['format']}"
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f"fps={config['fps']},scale={config['resolution']}",
                '-q:v', str(config['quality']),
                '-f', 'image2',
                str(output_pattern)
            ]
            
            self.logger.info(f"Running FFmpeg: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"FFmpeg failed: {result.stderr}")
                return []
            
            # Get list of extracted frames
            frame_files = sorted(frames_dir.glob(f"frame_*.{config['format']}"))
            
            frames = []
            for idx, frame_file in enumerate(frame_files):
                timestamp = idx / config['fps']
                file_size_kb = frame_file.stat().st_size / 1024
                
                frames.append({
                    "id": idx,
                    "timestamp": round(timestamp, 3),
                    "path": str(frame_file),
                    "resolution": config['resolution'],
                    "file_size_kb": round(file_size_kb, 2)
                })
            
            self.logger.info(f"Extracted {len(frames)} frames to {frames_dir}")
            return frames
            
        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg timeout")
            return []
        except Exception as e:
            self.logger.error(f"Frame extraction error: {e}", exc_info=True)
            return []