<<<<<<< HEAD
"""
File management utilities for project directories
Handles creation, deletion, and organization of project files
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from config.settings import PROJECTS_DIR
from utils.logger import setup_logger

logger = setup_logger("file_manager")


class ProjectFileManager:
    """Manages file structure for a video editing project"""
    
    def __init__(self, project_id: str):
        """
        Initialize file manager for a project
        
        Args:
            project_id: Unique project identifier
        """
        self.project_id = project_id
        self.project_dir = PROJECTS_DIR / project_id
        
        # Define subdirectories
        self.input_dir = self.project_dir / "input"
        self.frames_dir = self.project_dir / "frames"
        self.intermediate_dir = self.project_dir / "intermediate"
        self.output_dir = self.project_dir / "output"
        self.render_dir = self.project_dir / "render"
        self.state_dir = self.project_dir / "state"
        
        # Metadata file
        self.metadata_file = self.project_dir / "metadata.json"
    
    # ========================================================================
    # DIRECTORY OPERATIONS
    # ========================================================================
    
    def create_structure(self) -> bool:
        """
        Create complete directory structure for project
        
        Returns:
            True if successful, False otherwise
        """
        try:
            directories = [
                self.project_dir,
                self.input_dir,
                self.frames_dir,
                self.intermediate_dir,
                self.output_dir,
                self.render_dir,
                self.state_dir
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Created project structure: {self.project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create project structure: {e}", exc_info=True)
            return False
    
    def exists(self) -> bool:
        """
        Check if project directory exists
        
        Returns:
            True if exists, False otherwise
        """
        return self.project_dir.exists()
    
    def delete_project(self) -> bool:
        """
        Delete entire project directory and all contents
        
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
    
    # ========================================================================
    # FILE OPERATIONS
    # ========================================================================
    
    def save_json(self, data: Dict[str, Any], filename: str, 
                  subdir: str = "intermediate") -> bool:
        """
        Save data as JSON file
        
        Args:
            data: Dictionary to save
            filename: Name of JSON file
            subdir: Subdirectory (intermediate, output, state)
            
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
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Save JSON
            file_path = target_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved JSON: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save JSON {filename}: {e}", exc_info=True)
            return False
    
    def load_json(self, filename: str, subdir: str = "intermediate") -> Optional[Dict[str, Any]]:
        """
        Load JSON file
        
        Args:
            filename: Name of JSON file
            subdir: Subdirectory to load from
            
        Returns:
            Dictionary or None if failed
        """
        try:
            # Get source directory
            if subdir == "intermediate":
                source_dir = self.intermediate_dir
            elif subdir == "output":
                source_dir = self.output_dir
            elif subdir == "state":
                source_dir = self.state_dir
            else:
                source_dir = self.project_dir / subdir
            
            file_path = source_dir / filename
            
            if not file_path.exists():
                logger.warning(f"JSON file not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
            
        except Exception as e:
            logger.error(f"Failed to load JSON {filename}: {e}", exc_info=True)
            return None
    
    def save_text(self, text: str, filename: str, subdir: str = "output") -> bool:
        """
        Save text to file
        
        Args:
            text: Text content
            filename: Name of text file
            subdir: Subdirectory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get target directory
            if subdir == "output":
                target_dir = self.output_dir
            elif subdir == "intermediate":
                target_dir = self.intermediate_dir
            else:
                target_dir = self.project_dir / subdir
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = target_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.debug(f"Saved text file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save text {filename}: {e}", exc_info=True)
            return False
    
    def load_text(self, filename: str, subdir: str = "output") -> Optional[str]:
        """
        Load text from file
        
        Args:
            filename: Name of text file
            subdir: Subdirectory
            
        Returns:
            Text content or None if failed
        """
        try:
            if subdir == "output":
                source_dir = self.output_dir
            elif subdir == "intermediate":
                source_dir = self.intermediate_dir
            else:
                source_dir = self.project_dir / subdir
            
            file_path = source_dir / filename
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
            
        except Exception as e:
            logger.error(f"Failed to load text {filename}: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # METADATA OPERATIONS
    # ========================================================================
    
    def save_metadata(self, metadata: Dict[str, Any]) -> bool:
        """
        Save project metadata
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add timestamp
            metadata['last_updated'] = datetime.now().isoformat()
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved metadata: {self.metadata_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}", exc_info=True)
            return False
    
    def load_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Load project metadata
        
        Returns:
            Metadata dictionary or None if not found
        """
        try:
            if not self.metadata_file.exists():
                return None
            
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
            
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}", exc_info=True)
            return None
    
    def update_metadata(self, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in metadata
        
        Args:
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing metadata
            metadata = self.load_metadata() or {}
            
            # Update fields
            metadata.update(updates)
            
            # Save
            return self.save_metadata(metadata)
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # FILE LISTING
    # ========================================================================
    
    def list_files(self, subdir: str = "frames", 
                   pattern: str = "*") -> List[Path]:
        """
        List files in a subdirectory
        
        Args:
            subdir: Subdirectory name
            pattern: Glob pattern for filtering
            
        Returns:
            List of file paths
        """
        try:
            if subdir == "frames":
                target_dir = self.frames_dir
            elif subdir == "intermediate":
                target_dir = self.intermediate_dir
            elif subdir == "output":
                target_dir = self.output_dir
            elif subdir == "render":
                target_dir = self.render_dir
            else:
                target_dir = self.project_dir / subdir
            
            if not target_dir.exists():
                return []
            
            return sorted(target_dir.glob(pattern))
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}", exc_info=True)
            return []
    
    def get_file_count(self, subdir: str = "frames") -> int:
        """
        Get number of files in subdirectory
        
        Args:
            subdir: Subdirectory name
            
        Returns:
            Number of files
        """
        return len(self.list_files(subdir))
    
    # ========================================================================
    # DISK USAGE
    # ========================================================================
    
    def get_disk_usage(self) -> Dict[str, float]:
        """
        Calculate disk usage for project
        
        Returns:
            Dictionary with sizes in MB for each subdirectory
        """
        try:
            def get_dir_size(directory: Path) -> float:
                """Get size of directory in MB"""
                if not directory.exists():
                    return 0.0
                
                total_size = 0
                for item in directory.rglob('*'):
                    if item.is_file():
                        total_size += item.stat().st_size
                
                return total_size / (1024 * 1024)  # Convert to MB
            
            usage = {
                'input': get_dir_size(self.input_dir),
                'frames': get_dir_size(self.frames_dir),
                'intermediate': get_dir_size(self.intermediate_dir),
                'output': get_dir_size(self.output_dir),
                'render': get_dir_size(self.render_dir),
                'state': get_dir_size(self.state_dir)
            }
            
            usage['total'] = sum(usage.values())
            
            # Round to 2 decimal places
            usage = {k: round(v, 2) for k, v in usage.items()}
            
            return usage
            
        except Exception as e:
            logger.error(f"Failed to calculate disk usage: {e}", exc_info=True)
            return {
                'input': 0.0, 'frames': 0.0, 'intermediate': 0.0,
                'output': 0.0, 'render': 0.0, 'state': 0.0, 'total': 0.0
            }
    
    # ========================================================================
    # CLEANUP OPERATIONS
    # ========================================================================
    
    def cleanup_frames(self) -> bool:
        """
        Delete extracted frames to save space
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.frames_dir.exists():
                shutil.rmtree(self.frames_dir)
                self.frames_dir.mkdir(exist_ok=True)
                logger.info(f"Cleaned up frames: {self.project_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup frames: {e}", exc_info=True)
            return False
    
    def cleanup_render_temps(self) -> bool:
        """
        Delete temporary render files
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.render_dir.exists():
                # Delete all files but keep directory
                for item in self.render_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                
                logger.info(f"Cleaned up render temps: {self.project_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup render temps: {e}", exc_info=True)
            return False
    
    def cleanup_intermediate(self) -> bool:
        """
        Delete intermediate processing files
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.intermediate_dir.exists():
                shutil.rmtree(self.intermediate_dir)
                self.intermediate_dir.mkdir(exist_ok=True)
                logger.info(f"Cleaned up intermediate files: {self.project_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup intermediate files: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_video_path(self) -> Optional[str]:
        """
        Get path to input video
        
        Returns:
            Path to video file or None if not found
        """
        videos = list(self.input_dir.glob("*.mp4"))
        videos.extend(self.input_dir.glob("*.avi"))
        videos.extend(self.input_dir.glob("*.mov"))
        videos.extend(self.input_dir.glob("*.mkv"))
        
        if videos:
            return str(videos[0])
        return None
    
    def get_final_video_path(self) -> Optional[str]:
        """
        Get path to final edited video
        
        Returns:
            Path to final video or None if not found
        """
        final_video = self.output_dir / "final_video.mp4"
        if final_video.exists():
            return str(final_video)
        return None
    
    def get_project_summary(self) -> Dict[str, Any]:
        """
        Get summary of project file structure
        
        Returns:
            Summary dictionary
        """
        return {
            "project_id": self.project_id,
            "exists": self.exists(),
            "metadata": self.load_metadata(),
            "disk_usage": self.get_disk_usage(),
            "file_counts": {
                "frames": self.get_file_count("frames"),
                "intermediate": self.get_file_count("intermediate"),
                "output": self.get_file_count("output")
            },
            "input_video": self.get_video_path(),
            "final_video": self.get_final_video_path()
        }
    
    def export_project_data(self, export_path: Path) -> bool:
        """
        Export all project data to a directory
        
        Args:
            export_path: Destination path for export
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_path.mkdir(parents=True, exist_ok=True)
            
            # Copy output directory
            if self.output_dir.exists():
                output_export = export_path / "output"
                shutil.copytree(self.output_dir, output_export, dirs_exist_ok=True)
            
            # Copy metadata
            if self.metadata_file.exists():
                shutil.copy2(self.metadata_file, export_path / "metadata.json")
            
            # Copy intermediate results (optional)
            if self.intermediate_dir.exists():
                intermediate_export = export_path / "intermediate"
                shutil.copytree(self.intermediate_dir, intermediate_export, dirs_exist_ok=True)
            
            logger.info(f"Exported project data to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export project data: {e}", exc_info=True)
            return False


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_all_projects() -> List[str]:
    """
    Get list of all project IDs
    
    Returns:
        List of project IDs
    """
    try:
        PROJECTS_DIR.mkdir(exist_ok=True)
        return [d.name for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        return []


def cleanup_empty_projects() -> int:
    """
    Delete empty project directories
    
    Returns:
        Number of projects cleaned up
    """
    count = 0
    try:
        for project_dir in PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                # Check if directory is empty or only has empty subdirs
                has_files = any(item.is_file() for item in project_dir.rglob('*'))
                
                if not has_files:
                    shutil.rmtree(project_dir)
                    count += 1
                    logger.info(f"Cleaned up empty project: {project_dir.name}")
        
        return count
        
    except Exception as e:
        logger.error(f"Failed to cleanup empty projects: {e}")
        return count
=======
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
>>>>>>> d4e3c4e (update)
