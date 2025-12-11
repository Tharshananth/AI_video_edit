from typing import Dict, Any
from datetime import datetime

from agents.agent_1_frame_extractor import FrameExtractorAgent
from agents.agent_2_cursor_detector import CursorDetectorAgent
from agents.agent_3_vision_description import VisionDescriptionAgent
from agents.agent_4_audio_agent import AudioAgent
from agents.agent_5_analysis_agent import AnalysisAgent
from agents.agent_6_script_planner import ScriptPlannerAgent

from orchestration.state_schema import PipelineState, update_state_with_agent_result
from utils.database import Database
from utils.logger import setup_logger

logger = setup_logger("orchestration")
db = Database()

def intake_node(state: PipelineState) -> PipelineState:
    """
    Validate input and prepare for processing
    """
    logger.info(f"Starting pipeline for project: {state['project_id']}")
    
    # Update database
    db.update_project_status(
        state['project_id'],
        status="processing",
        current_stage="intake"
    )
    
    # Log stage start
    db.log_stage(
        state['project_id'],
        "intake",
        "started",
        start_time=datetime.now()
    )
    
    return state

def parallel_fork_node(state: PipelineState) -> PipelineState:
    """
    Fork node: Prepares state for parallel execution
    Just passes state through - the graph handles parallelization
    """
    logger.info("Forking into parallel branches: cursor_detector + audio_agent")
    state['current_stage'] = "parallel_processing"
    return state


def parallel_join_node(state: PipelineState) -> PipelineState:
    """
    Join node: Validate parallel branch results
    """
    logger.info("Joining parallel branches")
    
    # Check results
    has_cursor = state.get('cursor_events') is not None and len(state.get('cursor_events', [])) > 0
    has_audio = state.get('audio_transcript') is not None and state.get('audio_transcript', {}).get('segments')
    has_frames = state.get('frames') is not None and len(state.get('frames', [])) > 0
    
    # Frames are CRITICAL - cannot proceed without them
    if not has_frames:
        logger.error("❌ CRITICAL: No frames available - pipeline cannot proceed")
        state['errors'].append("Frame extraction failed - no frames to analyze")
        state['status'] = 'error'
        return state
    
    # Cursor detection is helpful but not critical
    if not has_cursor:
        logger.warning("⚠️  Cursor detection failed - continuing without cursor data")
        state['warnings'].append("Cursor detection produced no results")
        state['cursor_events'] = []  # Empty list, not None
    
    # Audio is helpful but not critical
    if not has_audio:
        logger.warning("⚠️  Audio processing failed - continuing without audio data")
        state['warnings'].append("Audio processing produced no results")
        state['audio_transcript'] = {"segments": [], "duration": 0}  # Empty structure, not None
        state['silence_segments'] = []
    
    state['current_stage'] = "parallel_complete"
    logger.info("✓ Parallel processing complete")
    
    return state

def frame_extractor_node(state: PipelineState) -> PipelineState:
    """
    Node: Extract frames from video (Agent 1)
    """
    logger.info("Executing Agent 1: Frame Extractor")
    
    start_time = datetime.now()
    
    try:
        agent = FrameExtractorAgent(state['project_id'])
        result = agent.execute(
            state['video_path'],
            config=state.get('config', {}).get('frame_extraction')
        )
        
        # Update state
        state = update_state_with_agent_result(state, "frame_extractor", result)
        
        # Log to database
        end_time = datetime.now()
        db.log_stage(
            state['project_id'],
            "frame_extraction",
            "completed" if result['status'] == 'success' else "failed",
            start_time=start_time,
            end_time=end_time,
            error_message=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Frame extraction node failed: {e}", exc_info=True)
        state['errors'].append(f"frame_extractor: {str(e)}")
        state['status'] = "error"
    
    return state


def cursor_detector_node(state: PipelineState) -> PipelineState:
    """
    Node: Detect cursor movements (Agent 2)
    """
    logger.info("Executing Agent 2: Cursor Detector")
    
    start_time = datetime.now()
    
    try:
        agent = CursorDetectorAgent(state['project_id'])
        result = agent.execute(
            state.get('frames', []),
            config=state.get('config', {}).get('cursor_detection')
        )
        
        # Update state
        state = update_state_with_agent_result(state, "cursor_detector", result)
        
        # Log to database
        end_time = datetime.now()
        db.log_stage(
            state['project_id'],
            "cursor_detection",
            "completed" if result['status'] == 'success' else "failed",
            start_time=start_time,
            end_time=end_time,
            error_message=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Cursor detection node failed: {e}", exc_info=True)
        state['errors'].append(f"cursor_detector: {str(e)}")
        # Don't fail pipeline - cursor detection is non-critical
        state['warnings'].append("Cursor detection failed, continuing without cursor data")
    
    return state


def audio_agent_node(state: PipelineState) -> PipelineState:
    """
    Node: Extract and analyze audio (Agent 4)
    """
    logger.info("Executing Agent 4: Audio Agent")
    
    start_time = datetime.now()
    
    try:
        agent = AudioAgent(state['project_id'])
        result = agent.execute(
            state['video_path'],
            config=state.get('config', {}).get('audio_processing')
        )
        
        # Update state
        state = update_state_with_agent_result(state, "audio_agent", result)
        
        # Log to database
        end_time = datetime.now()
        db.log_stage(
            state['project_id'],
            "audio_processing",
            "completed" if result['status'] == 'success' else "failed",
            start_time=start_time,
            end_time=end_time,
            cost_usd=result.get('api_usage', {}).get('estimated_cost_usd'),
            error_message=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Audio agent node failed: {e}", exc_info=True)
        state['errors'].append(f"audio_agent: {str(e)}")
        # Don't fail pipeline - can continue without audio
        state['warnings'].append("Audio processing failed, continuing without audio data")
    
    return state


def vision_description_node(state: PipelineState) -> PipelineState:
    """
    Node: Analyze frames with vision AI (Agent 3)
    """
    logger.info("Executing Agent 3: Vision Description")
    
    start_time = datetime.now()
    
    try:
        agent = VisionDescriptionAgent(state['project_id'])
        result = agent.execute(
            state.get('frames', []),
            state.get('cursor_events', []),
            config=state.get('config', {}).get('vision_analysis')
        )
        
        # Update state
        state = update_state_with_agent_result(state, "vision_description", result)
        
        # Log to database
        end_time = datetime.now()
        db.log_stage(
            state['project_id'],
            "vision_analysis",
            "completed" if result['status'] == 'success' else "failed",
            start_time=start_time,
            end_time=end_time,
            tokens_used=result.get('api_usage', {}).get('total_tokens'),
            cost_usd=result.get('api_usage', {}).get('estimated_cost_usd'),
            error_message=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Vision description node failed: {e}", exc_info=True)
        state['errors'].append(f"vision_description: {str(e)}")
        state['status'] = "error"  # Vision is critical
    
    return state


def analysis_agent_node(state: PipelineState) -> PipelineState:
    """
    Node: Analyze all data and create timeline (Agent 5)
    """
    logger.info("Executing Agent 5: Analysis Agent")
    
    start_time = datetime.now()
    
    try:
        agent = AnalysisAgent(state['project_id'])
        
        # Prepare inputs
        cursor_events = {"cursor_events": state.get('cursor_events', [])}
        frame_descriptions = {"descriptions": state.get('frame_descriptions', [])}
        audio_transcript = {"transcript": state.get('audio_transcript', {}), 
                          "silence_segments": state.get('silence_segments', [])}
        
        result = agent.execute(
            cursor_events,
            frame_descriptions,
            audio_transcript,
            state.get('video_metadata', {})
        )
        
        # Update state
        state = update_state_with_agent_result(state, "analysis_agent", result)
        
        # Log to database
        end_time = datetime.now()
        db.log_stage(
            state['project_id'],
            "analysis",
            "completed" if result['status'] == 'success' else "failed",
            start_time=start_time,
            end_time=end_time,
            tokens_used=result.get('api_usage', {}).get('total_tokens'),
            cost_usd=result.get('api_usage', {}).get('estimated_cost_usd'),
            error_message=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Analysis agent node failed: {e}", exc_info=True)
        state['errors'].append(f"analysis_agent: {str(e)}")
        state['status'] = "error"
    
    return state


def script_planner_node(state: PipelineState) -> PipelineState:
    """
    Node: Generate script and edit plan (Agent 6)
    """
    logger.info("Executing Agent 6: Script Planner")
    
    start_time = datetime.now()
    
    try:
        agent = ScriptPlannerAgent(state['project_id'])
        
        # Prepare inputs
        event_timeline = {"event_timeline": state.get('event_timeline', [])}
        audio_transcript = {"transcript": state.get('audio_transcript', {})}
        
        result = agent.execute(
            event_timeline,
            audio_transcript,
            state.get('video_metadata', {}),
            user_preferences=state.get('user_preferences', {})
        )
        
        # Update state
        state = update_state_with_agent_result(state, "script_planner", result)
        
        # Log to database
        end_time = datetime.now()
        db.log_stage(
            state['project_id'],
            "script_planning",
            "completed" if result['status'] == 'success' else "failed",
            start_time=start_time,
            end_time=end_time,
            tokens_used=result.get('api_usage', {}).get('total_tokens'),
            cost_usd=result.get('api_usage', {}).get('estimated_cost_usd'),
            error_message=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Script planner node failed: {e}", exc_info=True)
        state['errors'].append(f"script_planner: {str(e)}")
        state['status'] = "error"
    
    return state


def render_node(state: PipelineState) -> PipelineState:
    """Node: Render final video"""
    logger.info("Executing Render Engine")
    
    start_time = datetime.now()
    
    try:
        from rendering.render_orchestrator import RenderOrchestrator
        
        renderer = RenderOrchestrator(state['project_id'])
        result = renderer.execute(
            state['video_path'],
            state.get('edit_plan', {}),
            state.get('narration_script', {}),
            state.get('tts_config', {})
        )
        
        # Update state
        state = update_state_with_agent_result(state, "render", result)
        
        # Log to database
        end_time = datetime.now()
        db.log_stage(
            state['project_id'],
            "rendering",
            "completed" if result['status'] == 'success' else "failed",
            start_time=start_time,
            end_time=end_time,
            error_message=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Render node failed: {e}", exc_info=True)
        state['errors'].append(f"render: {str(e)}")
        state['status'] = "error"
    
    return state


def output_node(state: PipelineState) -> PipelineState:
    """Final node: Cleanup and finalize"""
    logger.info("Finalizing pipeline")
    
    # Update database with final status
    db.update_project_status(
        state['project_id'],
        status=state['status'],
        current_stage="completed" if state['status'] == 'complete' else "failed"
    )
    
    # Log summary
    logger.info(f"Pipeline completed with status: {state['status']}")
    logger.info(f"Total processing time: {state['processing_time']:.2f}s")
    logger.info(f"Total cost: ${state['total_cost_usd']:.4f}")
    logger.info(f"Completed stages: {', '.join(state['completed_stages'])}")
    
    if state['errors']:
        logger.error(f"Errors: {', '.join(state['errors'])}")
    
    if state['warnings']:
        logger.warning(f"Warnings: {', '.join(state['warnings'])}")
    
    return state