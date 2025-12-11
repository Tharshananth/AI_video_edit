"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ProjectStatusEnum(str, Enum):
    """Project status enumeration"""
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"
    FAILED = "failed"


class NarrationStyle(str, Enum):
    """Narration style options"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"


class ProcessingConfig(BaseModel):
    """Configuration for video processing"""
    fps: Optional[float] = Field(None, ge=0.5, le=10.0)
    max_frames: Optional[int] = Field(None, ge=50, le=1000)
    narration_style: NarrationStyle = NarrationStyle.PROFESSIONAL
    keep_original_audio: bool = False
    vision_sample_rate: Optional[int] = Field(None, ge=1, le=20)
    enable_cursor_detection: bool = True
    enable_audio_analysis: bool = True


class ProjectResponse(BaseModel):
    """Basic project response"""
    project_id: str
    video_name: str
    status: ProjectStatusEnum
    current_stage: str
    created_at: str


class VideoMetadata(BaseModel):
    """Video metadata"""
    duration: float
    file_size_mb: float
    resolution: str
    fps: float
    codec: str


class StageInfo(BaseModel):
    """Information about a processing stage"""
    stage_name: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    error_message: Optional[str]


class ProjectStatus(BaseModel):
    """Detailed project status"""
    project_id: str
    video_name: str
    status: ProjectStatusEnum
    current_stage: str
    progress_percentage: float = 0.0
    video_metadata: Optional[VideoMetadata] = None
    stages: List[StageInfo] = []
    completed_stages: List[str] = []
    created_at: datetime
    processing_start: Optional[datetime] = None
    processing_end: Optional[datetime] = None
    total_processing_time: Optional[float] = None
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    errors: List[str] = []
    warnings: List[str] = []
    output_video_path: Optional[str] = None
    narration_script: Optional[str] = None


class ProjectList(BaseModel):
    """List of projects with pagination"""
    projects: List[ProjectResponse]
    total: int
    limit: int
    offset: int


class CostSummary(BaseModel):
    """Cost breakdown for a project"""
    project_id: str
    total_cost_usd: float
    breakdown: Dict[str, float] = Field(default_factory=dict)
    total_tokens: int = 0


class StatusUpdate(BaseModel):
    """Real-time status update for WebSocket"""
    type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str]
    project_id: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.now)