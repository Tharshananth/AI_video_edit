"""
Project management - orchestrates project lifecycle
"""

import uuid
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from utils.database import Database
from utils.file_manager import ProjectFileManager
from utils.logger import setup_logger

logger = setup_logger("project_manager")


class ProjectManager:
    """High-level project management"""
    
    def __init__(self):
        self.db = Database()
    
    def create_project(self, video_path: str, user_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Create a new project from a video file
        
        Args:
            video_path: Path to input video
            user_id: User identifier
            
        Returns:
            Project dictionary or None if failed
        """
        try:
            # Generate project ID
            project_id = str(uuid.uuid4())
            
            # Create file structure
            file_manager = ProjectFileManager(project_id)
            if not file_manager.create_structure():
                raise Exception("Failed to create project structure")
            
            # Copy video to input directory
            video_file = Path(video_path)
            if not video_file.exists():
                raise FileNotFoundError(f"Video not found: {video_path}")
            
            destination = file_manager.input_dir / video_file.name
            shutil.copy2(video_path, destination)
            
            # Get video metadata
            import subprocess
            import json
            
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(destination)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                probe_data = json.loads(result.stdout)
                video_stream = next(
                    (s for s in probe_data.get('streams', []) if s['codec_type'] == 'video'),
                    None
                )
                
                duration = float(probe_data['format'].get('duration', 0))
                file_size_mb = float(probe_data['format'].get('size', 0)) / (1024 * 1024)
                resolution = f"{video_stream['width']}x{video_stream['height']}" if video_stream else "unknown"
            else:
                duration = 0.0
                file_size_mb = video_file.stat().st_size / (1024 * 1024)
                resolution = "unknown"
            
            # Create database entry
            project_data = {
                'project_id': project_id,
                'user_id': user_id,
                'video_name': video_file.name,
                'video_path': str(destination),
                'status': 'created',
                'current_stage': 'initialized',
                'duration_seconds': duration,
                'file_size_mb': file_size_mb,
                'resolution': resolution
            }
            
            if not self.db.create_project(project_data):
                raise Exception("Failed to create database entry")
            
            # Save metadata
            file_manager.save_metadata({
                'project_id': project_id,
                'video_name': video_file.name,
                'created_at': datetime.now().isoformat(),
                'user_id': user_id
            })
            
            logger.info(f"Created project: {project_id} ({video_file.name})")
            return project_data
            
        except Exception as e:
            logger.error(f"Failed to create project: {e}", exc_info=True)
            # Cleanup on failure
            try:
                if 'file_manager' in locals():
                    file_manager.delete_project()
            except:
                pass
            return None
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        return self.db.get_project(project_id)
    
    def list_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """List all projects for a user"""
        return self.db.list_projects(user_id=user_id)
    
    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed project status including stages and costs
        
        Returns:
            Dictionary with project, stages, cost, and disk usage
        """
        project = self.db.get_project(project_id)
        if not project:
            return None
        
        stages = self.db.get_project_stages(project_id)
        cost = self.db.get_project_cost_summary(project_id)
        
        file_manager = ProjectFileManager(project_id)
        disk_usage = file_manager.get_disk_usage()
        
        return {
            'project': project,
            'stages': stages,
            'cost': cost,
            'disk_usage': disk_usage
        }
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete project completely (files + database)
        
        Args:
            project_id: Project ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete files
            file_manager = ProjectFileManager(project_id)
            file_manager.delete_project()
            
            # Delete database entries
            self.db.delete_project(project_id)
            
            logger.info(f"Deleted project: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete project: {e}", exc_info=True)
            return False
    
    def cleanup_old_projects(self, days: int = 30) -> int:
        """
        Delete projects older than specified days
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of projects deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            projects = self.db.list_projects()
            
            count = 0
            for project in projects:
                created_at = datetime.fromisoformat(project['created_at'])
                
                if created_at < cutoff_date:
                    if self.delete_project(project['project_id']):
                        count += 1
            
            logger.info(f"Cleaned up {count} old projects")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old projects: {e}", exc_info=True)
            return 0
    
    def save_checkpoint(self, project_id: str, state: Dict[str, Any]) -> bool:
        """
        Save pipeline state checkpoint
        
        Args:
            project_id: Project ID
            state: Pipeline state dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_manager = ProjectFileManager(project_id)
            return file_manager.save_json(state, "pipeline_state.json", subdir="state")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}", exc_info=True)
            return False
    
    def load_checkpoint(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Load pipeline state checkpoint
        
        Args:
            project_id: Project ID
            
        Returns:
            Pipeline state or None if not found
        """
        try:
            file_manager = ProjectFileManager(project_id)
            return file_manager.load_json("pipeline_state.json", subdir="state")
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}", exc_info=True)
            return None