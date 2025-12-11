"""
Download API routes
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from api.services.project_service import ProjectService

router = APIRouter()
project_service = ProjectService()


@router.get("/{project_id}")
async def download_video(project_id: str):
    """Download processed video"""
    video_path = await project_service.get_video_path(project_id)
    
    if not video_path or not Path(video_path).exists():
        raise HTTPException(
            status_code=404,
            detail="Video not found or processing not complete"
        )
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"edited_{project_id}.mp4"
    )