"""
WebSocket connection manager for real-time updates
"""

from fastapi import WebSocket
from typing import Dict, List, Any
import json
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger("websocket_manager")


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Map project_id -> list of active websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, project_id: str, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection
        
        Args:
            project_id: Project ID to monitor
            websocket: WebSocket connection
        """
        await websocket.accept()
        
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        
        self.active_connections[project_id].append(websocket)
        logger.info(f"WebSocket connected for project {project_id}")
    
    def disconnect(self, project_id: str, websocket: WebSocket):
        """
        Remove a WebSocket connection
        
        Args:
            project_id: Project ID
            websocket: WebSocket connection
        """
        if project_id in self.active_connections:
            try:
                self.active_connections[project_id].remove(websocket)
                
                # Remove project key if no more connections
                if not self.active_connections[project_id]:
                    del self.active_connections[project_id]
                
                logger.info(f"WebSocket disconnected for project {project_id}")
            except ValueError:
                pass
    
    async def send_update(self, project_id: str, data: Dict[str, Any]):
        """
        Send update to all connected clients for a project
        
        Args:
            project_id: Project ID
            data: Update data to send
        """
        if project_id not in self.active_connections:
            return
        
        # Add timestamp
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        # Prepare message
        message = json.dumps(data)
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.active_connections[project_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.disconnect(project_id, websocket)
    
    async def broadcast_progress(
        self,
        project_id: str,
        stage: str,
        progress: float,
        message: str = ""
    ):
        """
        Broadcast progress update
        
        Args:
            project_id: Project ID
            stage: Current stage
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        await self.send_update(project_id, {
            "type": "progress",
            "data": {
                "stage": stage,
                "progress": progress,
                "message": message
            }
        })
    
    async def broadcast_stage_complete(
        self,
        project_id: str,
        stage: str,
        duration: float,
        tokens_used: int = 0,
        cost_usd: float = 0.0
    ):
        """
        Broadcast stage completion
        
        Args:
            project_id: Project ID
            stage: Completed stage name
            duration: Stage duration in seconds
            tokens_used: Tokens used
            cost_usd: Cost in USD
        """
        await self.send_update(project_id, {
            "type": "stage_complete",
            "data": {
                "stage": stage,
                "duration": duration,
                "tokens_used": tokens_used,
                "cost_usd": cost_usd
            }
        })
    
    async def broadcast_error(
        self,
        project_id: str,
        error: str,
        stage: str = ""
    ):
        """
        Broadcast error message
        
        Args:
            project_id: Project ID
            error: Error message
            stage: Stage where error occurred
        """
        await self.send_update(project_id, {
            "type": "error",
            "data": {
                "error": error,
                "stage": stage
            }
        })
    
    def get_connection_count(self, project_id: str) -> int:
        """Get number of active connections for a project"""
        return len(self.active_connections.get(project_id, []))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())