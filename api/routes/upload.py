"""
Upload API routes
"""

from fastapi import APIRouter, File, UploadFile, HTTPException

router = APIRouter()


@router.post("")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file
    
    Note: This is handled by the main /api/v1/process endpoint
    This route exists for compatibility
    """
    if not file.filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Supported: mp4, avi, mov, mkv"
        )
    
    return {
        "message": "Use /api/v1/process endpoint instead",
        "filename": file.filename
    }