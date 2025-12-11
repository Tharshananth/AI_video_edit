"""
AI agents for video processing pipeline
"""

from agents.agent_1_frame_extractor import FrameExtractorAgent
from agents.agent_2_cursor_detector import CursorDetectorAgent
from agents.agent_3_vision_description import VisionDescriptionAgent
from agents.agent_4_audio_agent import AudioAgent
from agents.agent_5_analysis_agent import AnalysisAgent
from agents.agent_6_script_planner import ScriptPlannerAgent

__all__ = [
    'FrameExtractorAgent',
    'CursorDetectorAgent',
    'VisionDescriptionAgent',
    'AudioAgent',
    'AnalysisAgent',
    'ScriptPlannerAgent'
]
