"""
Processing service for video editing pipeline
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

from api.models import ProcessingConfig
from api.services.websocket_manager import WebSocketManager
from orchestration.graph_builder import execute_pipeline
from utils.logger import setup_logger

logger = setup_logger("processing_service")


class ProcessingService:
    """Service for managing video processing pipeline"""
    
    def __init__(self):
        self.active_jobs: Dict[str, bool] = {}
    
    async def initialize(self):
        """Initialize processing service"""
        logger.info("Processing service initialized")
    
    async def cleanup(self):
        """Cleanup on shutdown"""
        logger.info("Processing service cleanup")
    
    async def process_video(
        self,
        project_id: str,
        config: ProcessingConfig,
        websocket_manager: WebSocketManager
    ):
        """
        Process video in background
        
        Args:
            project_id: Project ID
            config: Processing configuration
            websocket_manager: WebSocket manager for updates
        """
        try:
            # Mark as active
            self.active_jobs[project_id] = True
            
            logger.info(f"Starting processing for project: {project_id}")
            
            # Send initial update
            await websocket_manager.send_update(project_id, {
                "type": "started",
                "data": {"message": "Processing started"}
            })
            
            # Get project info
            from utils.project_manager import ProjectManager
            pm = ProjectManager()
            project = pm.db.get_project(project_id)
            
            if not project:
                raise Exception("Project not found")
            
            # Build pipeline config
            pipeline_config = {
                "frame_extraction": {
                    "fps": config.fps,
                    "max_frames": config.max_frames,
                },
                "cursor_detection": {
                    "confidence_threshold": 0.7,
                },
                "vision_analysis": {
                    "sample_rate": config.vision_sample_rate or 5,
                },
                "audio_processing": {}
            }
            
            user_preferences = {
                "narration_style": config.narration_style.value,
                "keep_original_audio": config.keep_original_audio,
                "pacing": "medium"
            }
            
            # Execute pipeline (this runs synchronously)
            # We run it in executor to not block async event loop
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(
                None,
                execute_pipeline,
                project_id,
                project['video_path'],
                pipeline_config,
                user_preferences
            )
            
            # Send completion update
            if final_state.get('status') == 'complete':
                await websocket_manager.send_update(project_id, {
                    "type": "complete",
                    "data": {
                        "video_path": final_state.get('final_video_path'),
                        "processing_time": final_state.get('processing_time'),
                        "total_cost": final_state.get('total_cost_usd')
                    }
                })
                logger.info(f"Processing complete: {project_id}")
            else:
                await websocket_manager.broadcast_error(
                    project_id,
                    "Processing failed: " + ", ".join(final_state.get('errors', []))
                )
                logger.error(f"Processing failed: {project_id}")
            
        except Exception as e:
            logger.error(f"Processing error for {project_id}: {e}", exc_info=True)
            await websocket_manager.broadcast_error(
                project_id,
                str(e)
            )
        finally:
            # Remove from active jobs
            self.active_jobs.pop(project_id, None)
    
    def is_processing(self, project_id: str) -> bool:
        """Check if project is currently processing"""
        return project_id in self.active_jobs
    
    def get_active_jobs_count(self) -> int:
        """Get number of active processing jobs"""
        return len(self.active_jobs)