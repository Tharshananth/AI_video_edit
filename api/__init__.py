"""
FastAPI Backend for AI Video Editor
"""

from api.main import app
from api.models import (
    ProcessingConfig,
    ProjectResponse,
    ProjectStatus,
    ProjectStatusEnum,
    NarrationStyle,
    ProcessingStage,
    StatusUpdate,
    ErrorResponse,
    CostSummary
)

__all__ = [
    'app',
    'ProcessingConfig',
    'ProjectResponse',
    'ProjectStatus',
    'ProjectStatusEnum',
    'NarrationStyle',
    'StatusUpdate',
    'ErrorResponse',
    'CostSummary'
]

__version__ = "1.0.0"