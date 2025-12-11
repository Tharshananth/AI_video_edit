"""
Settings API routes
"""

from fastapi import APIRouter
from config import settings

router = APIRouter()


@router.get("")
async def get_settings():
    """Get current settings (non-sensitive only)"""
    return {
        "frame_extraction": {
            "default_fps": settings.DEFAULT_FPS,
            "max_frames": settings.MAX_FRAMES,
            "resolution": settings.FRAME_RESOLUTION
        },
        "vision_analysis": {
            "sample_rate": settings.FRAME_SAMPLE_RATE,
            "model": settings.VISION_MODEL
        },
        "cursor_detection": {
            "model": settings.CURSOR_MODEL,
            "confidence_threshold": settings.CURSOR_CONFIDENCE_THRESHOLD
        },
        "rendering": {
            "codec": settings.VIDEO_CODEC,
            "preset": settings.VIDEO_PRESET,
            "output_fps": settings.OUTPUT_FPS
        },
        "project_management": {
            "retention_days": settings.PROJECT_RETENTION_DAYS,
            "max_concurrent": settings.MAX_CONCURRENT_PROJECTS
        }
    }