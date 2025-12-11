"""
Projects API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from api.models import ProjectStatus, ProjectList
from api.services.project_service import ProjectService

router = APIRouter()
project_service = ProjectService()


@router.get("/{project_id}", response_model=ProjectStatus)
async def get_project_status(project_id: str):
    """Get detailed project status"""
    status = await project_service.get_project_status(project_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Convert to ProjectStatus model
    project = status['project']
    
    return {
        "project_id": project['project_id'],
        "video_name": project['video_name'],
        "status": project['status'],
        "current_stage": project['current_stage'],
        "progress_percentage": 0.0,  # TODO: Calculate from stages
        "video_metadata": {
            "duration": project.get('duration_seconds', 0),
            "file_size_mb": project.get('file_size_mb', 0),
            "resolution": project.get('resolution', ''),
            "fps": 30,
            "codec": "h264"
        },
        "stages": status['stages'],
        "completed_stages": [],
        "created_at": project['created_at'],
        "total_tokens_used": status['cost']['total_tokens'],
        "total_cost_usd": status['cost']['total_cost_usd'],
        "errors": [],
        "warnings": []
    }


@router.get("", response_model=ProjectList)
async def list_projects(
    user_id: Optional[str] = "default",
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List all projects"""
    projects = await project_service.list_projects(
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    # Convert to response model
    project_responses = [
        {
            "project_id": p['project_id'],
            "video_name": p['video_name'],
            "status": p['status'],
            "current_stage": p['current_stage'],
            "created_at": p['created_at']
        }
        for p in projects
    ]
    
    return {
        "projects": project_responses,
        "total": len(project_responses),
        "limit": limit,
        "offset": offset
    }


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    success = await project_service.delete_project(project_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"message": "Project deleted successfully", "project_id": project_id}