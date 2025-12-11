"""
Project file management - handles folder structure and file operations
"""

import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from config.settings import PROJECTS_DIR
from utils.logger import setup_logger

logger = setup_logger("file_manager")


class ProjectFileManager:
    """Manages files and folders for a video editing project"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = PROJECTS_DIR / project_id
        
        # Define directory structure
        self.input_dir = self.project_dir / "input"
        self.frames_dir = self.project_dir / "frames"
        self.intermediate_dir = self.project_dir / "intermediate"
        self.output_dir = self.project_dir / "output"
        self.render_dir = self.project_dir / "render"
        self.state_dir = self.project_dir / "state"
    
    def create_structure(self) -> bool:
        """
        Create complete project folder structure
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create all directories
            self.project_dir.mkdir(parents=True, exist_ok=True)
            self.input_dir.mkdir(exist_ok=True)
            self.frames_dir.mkdir(exist_ok=True)
            self.intermediate_dir.mkdir(exist_ok=True)
            self.output_dir.mkdir(exist_ok=True)
            self.render_dir.mkdir(exist_ok=True)
            self.state_dir.mkdir(exist_ok=True)
            
            logger.info(f"Created project structure: {self.project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create project structure: {e}", exc_info=True)
            return False
    
    def save_json(self, data: Dict[str, Any], filename: str, 
                  subdir: str = "intermediate") -> bool:
        """
        Save data as JSON file
        
        Args:
            data: Dictionary to save
            filename: Filename (e.g., "frames.json")
            subdir: Subdirectory ("intermediate", "output", "state")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get target directory
            if subdir == "intermediate":
                target_dir = self.intermediate_dir
            elif subdir == "output":
                target_dir = self.output_dir
            elif subdir == "state":
                target_dir = self.state_dir
            else:
                target_dir = self.project_dir / subdir
            
            target_dir.mkdir(exist_ok=True)
            file_path = target_dir / filename
            
            # Save with pretty formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved JSON: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}", exc_info=True)
            return False
    
    def load_json(self, filename: str, subdir: str = "intermediate") -> Optional[Dict[str, Any]]:
        """
        Load JSON file
        
        Args:
            filename: Filename to load
            subdir: Subdirectory to load from
            
        Returns:
            Dictionary if successful, None otherwise
        """
        try:
            if subdir == "intermediate":
                target_dir = self.intermediate_dir
            elif subdir == "output":
                target_dir = self.output_dir
            elif subdir == "state":
                target_dir = self.state_dir
            else:
                target_dir = self.project_dir / subdir
            
            file_path = target_dir / filename
            
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"Loaded JSON: {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load JSON: {e}", exc_info=True)
            return None
    
    def save_text(self, text: str, filename: str, subdir: str = "output") -> bool:
        """
        Save text file
        
        Args:
            text: Text content to save
            filename: Filename (e.g., "script.txt")
            subdir: Subdirectory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if subdir == "output":
                target_dir = self.output_dir
            elif subdir == "intermediate":
                target_dir = self.intermediate_dir
            else:
                target_dir = self.project_dir / subdir
            
            target_dir.mkdir(exist_ok=True)
            file_path = target_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.debug(f"Saved text: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save text: {e}", exc_info=True)
            return False
    
    def save_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Save project metadata"""
        return self.save_json(metadata, "metadata.json", subdir="")
    
    def load_metadata(self) -> Optional[Dict[str, Any]]:
        """Load project metadata"""
        return self.load_json("metadata.json", subdir="")
    
    def get_disk_usage(self) -> Dict[str, float]:
        """
        Calculate disk usage for project
        
        Returns:
            Dictionary with sizes in MB for each directory
        """
        def get_dir_size(directory: Path) -> float:
            """Get directory size in MB"""
            try:
                total = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
                return total / (1024 * 1024)  # Convert to MB
            except:
                return 0.0
        
        return {
            "input": get_dir_size(self.input_dir),
            "frames": get_dir_size(self.frames_dir),
            "intermediate": get_dir_size(self.intermediate_dir),
            "output": get_dir_size(self.output_dir),
            "render": get_dir_size(self.render_dir),
            "state": get_dir_size(self.state_dir),
            "total": get_dir_size(self.project_dir)
        }
    
    def delete_project(self) -> bool:
        """
        Delete entire project directory
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.project_dir.exists():
                shutil.rmtree(self.project_dir)
                logger.info(f"Deleted project directory: {self.project_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete project: {e}", exc_info=True)
            return False
    
    def cleanup_temp_files(self) -> bool:
        """
        Clean up temporary files (frames, render)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete frames
            if self.frames_dir.exists():
                for file in self.frames_dir.glob('*'):
                    file.unlink()
                logger.debug(f"Cleaned up frames: {self.project_id}")
            
            # Delete render temp files
            if self.render_dir.exists():
                for file in self.render_dir.glob('*'):
                    file.unlink()
                logger.debug(f"Cleaned up render files: {self.project_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}", exc_info=True)
            return False
    
    def get_video_path(self) -> Optional[str]:
        """Get path to input video"""
        try:
            videos = list(self.input_dir.glob('*.mp4'))
            videos.extend(self.input_dir.glob('*.avi'))
            videos.extend(self.input_dir.glob('*.mov'))
            videos.extend(self.input_dir.glob('*.mkv'))
            
            if videos:
                return str(videos[0])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get video path: {e}", exc_info=True)
            return None
    
    def get_final_video_path(self) -> Optional[str]:
        """Get path to final rendered video"""
        final_video = self.output_dir / "final_video.mp4"
        if final_video.exists():
            return str(final_video)
        return None
