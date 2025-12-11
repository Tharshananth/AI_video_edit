"""
FastAPI Backend for AI Video Editor
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, List
import uvicorn
import asyncio
from pathlib import Path

from api.models import (
    ProjectCreate, ProjectResponse, ProjectStatus,
    ProcessingConfig, ProjectList, ErrorResponse,
    StatusUpdate, CostSummary
)
from api.services.project_service import ProjectService
from api.services.processing_service import ProcessingService
from api.services.websocket_manager import WebSocketManager
from api.middleware.error_handler import add_error_handlers
from api.routes import projects, upload, download, settings
from utils.logger import setup_logger
from config.settings import PROJECTS_DIR

logger = setup_logger("api")

# Global instances
project_service = ProjectService()
processing_service = ProcessingService()
websocket_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting AI Video Editor API...")
    
    # Ensure directories exist
    PROJECTS_DIR.mkdir(exist_ok=True)
    
    # Initialize services
    await processing_service.initialize()
    
    logger.info("API ready to accept requests")
    
    yield
    
    # Cleanup
    logger.info("Shutting down API...")
    await processing_service.cleanup()


# Create FastAPI app
app = FastAPI(
    title="AI Video Editor API",
    description="Automatically edit screen recordings with AI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handlers
add_error_handlers(app)

# Mount static files
app.mount("/outputs", StaticFiles(directory=str(PROJECTS_DIR)), name="outputs")

# Include routers
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Upload"])
app.include_router(download.router, prefix="/api/v1/download", tags=["Download"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AI Video Editor API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "project_service": "operational",
            "processing_service": "operational",
            "websocket_manager": "operational"
        }
    }


@app.post("/api/v1/process", response_model=ProjectResponse)
async def process_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    fps: Optional[float] = None,
    max_frames: Optional[int] = None,
    narration_style: str = "professional",
    keep_audio: bool = False
):
    """
    Upload and process a video
    
    Args:
        file: Video file to process
        fps: Frame extraction rate (optional)
        max_frames: Maximum frames to extract (optional)
        narration_style: Style of narration (professional/casual/technical)
        keep_audio: Keep original audio
        
    Returns:
        Project information with processing status
    """
    try:
        # Validate file
        if not file.filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            raise HTTPException(status_code=400, detail="Invalid file format. Supported: mp4, avi, mov, mkv")
        
        # Save uploaded file
        logger.info(f"Received video: {file.filename}")
        project = await project_service.create_project_from_upload(file)
        
        # Build config
        config = ProcessingConfig(
            fps=fps,
            max_frames=max_frames,
            narration_style=narration_style,
            keep_original_audio=keep_audio
        )
        
        # Start processing in background
        background_tasks.add_task(
            processing_service.process_video,
            project['project_id'],
            config,
            websocket_manager
        )
        
        logger.info(f"Started processing project: {project['project_id']}")
        
        return ProjectResponse(**project)
        
    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time progress updates
    
    Args:
        websocket: WebSocket connection
        project_id: Project ID to monitor
    """
    await websocket_manager.connect(project_id, websocket)
    
    try:
        # Send initial status
        status = await project_service.get_project_status(project_id)
        if status:
            await websocket_manager.send_update(project_id, {
                "type": "status",
                "data": status
            })
        
        # Keep connection alive
        while True:
            try:
                # Receive keep-alive messages
                data = await websocket.receive_text()
                
                # Handle client messages if needed
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(project_id, websocket)


@app.get("/api/v1/projects/{project_id}/status", response_model=ProjectStatus)
async def get_project_status(project_id: str):
    """
    Get detailed project status
    
    Args:
        project_id: Project ID
        
    Returns:
        Detailed project status
    """
    status = await project_service.get_project_status(project_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectStatus(**status)


@app.get("/api/v1/projects/{project_id}/download")
async def download_video(project_id: str):
    """
    Download processed video
    
    Args:
        project_id: Project ID
        
    Returns:
        Video file
    """
    video_path = await project_service.get_video_path(project_id)
    
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video not found or processing not complete")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"edited_{project_id}.mp4"
    )


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str):
    """
    Delete a project
    
    Args:
        project_id: Project ID
        
    Returns:
        Success message
    """
    success = await project_service.delete_project(project_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"message": "Project deleted successfully", "project_id": project_id}


@app.get("/api/v1/projects", response_model=ProjectList)
async def list_projects(
    user_id: Optional[str] = "default",
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all projects
    
    Args:
        user_id: User ID filter
        status: Status filter (processing/complete/error)
        limit: Maximum results
        offset: Offset for pagination
        
    Returns:
        List of projects
    """
    projects = await project_service.list_projects(
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return ProjectList(
        projects=projects,
        total=len(projects),
        limit=limit,
        offset=offset
    )


@app.get("/api/v1/projects/{project_id}/cost", response_model=CostSummary)
async def get_project_cost(project_id: str):
    """
    Get cost breakdown for a project
    
    Args:
        project_id: Project ID
        
    Returns:
        Cost summary
    """
    cost = await project_service.get_project_cost(project_id)
    
    if not cost:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return CostSummary(**cost)


@app.post("/api/v1/projects/{project_id}/retry")
async def retry_project(project_id: str, background_tasks: BackgroundTasks):
    """
    Retry a failed project
    
    Args:
        project_id: Project ID
        
    Returns:
        Updated project status
    """
    project = await project_service.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project['status'] not in ['error', 'failed']:
        raise HTTPException(status_code=400, detail="Project is not in failed state")
    
    # Reset status
    await project_service.update_project_status(project_id, "processing", "retrying")
    
    # Restart processing
    config = ProcessingConfig()  # Use default config
    background_tasks.add_task(
        processing_service.process_video,
        project_id,
        config,
        websocket_manager
    )
    
    return {"message": "Project retry started", "project_id": project_id}


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )