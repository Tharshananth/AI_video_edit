"""
Project service for managing video editing projects
"""

import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import UploadFile
from utils.project_manager import ProjectManager
from utils.logger import setup_logger

logger = setup_logger("project_service")


class ProjectService:
    """Service layer for project management"""
    
    def __init__(self):
        self.project_manager = ProjectManager()
    
    async def create_project_from_upload(self, file: UploadFile) -> Dict[str, Any]:
        """
        Create project from uploaded video file
        
        Args:
            file: Uploaded video file
            
        Returns:
            Project information dictionary
        """
        try:
            # Save uploaded file temporarily
            temp_path = Path(f"/tmp/{file.filename}")
            
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Create project
            project = self.project_manager.create_project(
                str(temp_path),
                user_id="api_user"
            )
            
            # Clean up temp file
            temp_path.unlink()
            
            if not project:
                raise Exception("Failed to create project")
            
            return project
            
        except Exception as e:
            logger.error(f"Failed to create project from upload: {e}", exc_info=True)
            raise
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        return self.project_manager.db.get_project(project_id)
    
    async def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed project status"""
        return self.project_manager.get_project_status(project_id)
    
    async def list_projects(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List projects with filters"""
        projects = self.project_manager.list_user_projects(user_id or "api_user")
        
        # Apply status filter
        if status:
            projects = [p for p in projects if p.get('status') == status]
        
        # Apply pagination
        return projects[offset:offset + limit]
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        return self.project_manager.delete_project(project_id)
    
    async def get_video_path(self, project_id: str) -> Optional[str]:
        """Get path to final rendered video"""
        from utils.file_manager import ProjectFileManager
        
        file_manager = ProjectFileManager(project_id)
        return file_manager.get_final_video_path()
    
    async def get_project_cost(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get cost breakdown for project"""
        cost_summary = self.project_manager.db.get_project_cost_summary(project_id)
        
        if not cost_summary:
            return None
        
        # Get stage-by-stage breakdown
        stages = self.project_manager.db.get_project_stages(project_id)
        
        breakdown = {}
        for stage in stages:
            stage_name = stage.get('stage_name', 'unknown')
            cost = stage.get('cost_usd', 0.0)
            if cost > 0:
                breakdown[stage_name] = cost
        
        return {
            "project_id": project_id,
            "total_cost_usd": cost_summary['total_cost_usd'],
            "breakdown": breakdown,
            "total_tokens": cost_summary['total_tokens']
        }
    
    async def update_project_status(
        self,
        project_id: str,
        status: str,
        current_stage: Optional[str] = None
    ) -> bool:
        """Update project status"""
        return self.project_manager.db.update_project_status(
            project_id,
            status,
            current_stage
        )