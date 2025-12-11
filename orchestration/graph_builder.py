from langgraph.graph import StateGraph, END
from typing import Dict, Any

from orchestration.state_schema import PipelineState
from orchestration import nodes
from utils.logger import setup_logger

logger = setup_logger("graph_builder")

def should_continue_after_parallel(state: PipelineState) -> str:
    """
    Conditional edge: Check if parallel processing succeeded
    """
    if state.get('status') == 'error':
        logger.error("Pipeline failed during parallel processing")
        return "output"
    
    # Check if we have required data for vision analysis
    if not state.get('frames'):
        logger.error("No frames available for vision analysis")
        state['errors'].append("Frame extraction failed")
        state['status'] = 'error'
        return "output"
    
    return "vision_description"


def should_continue_after_vision(state: PipelineState) -> str:
    """
    Conditional edge: Check if vision analysis succeeded
    """
    if state.get('status') == 'error':
        logger.error("Pipeline failed during vision analysis")
        return "output"
    
    # Vision is critical, must have descriptions
    if not state.get('frame_descriptions'):
        logger.error("No frame descriptions available")
        state['errors'].append("Vision analysis failed")
        state['status'] = 'error'
        return "output"
    
    return "analysis_agent"


def should_render(state: PipelineState) -> str:
    """
    Conditional edge: Check if we should proceed to rendering
    """
    if state.get('status') == 'error':
        logger.error("Pipeline failed before rendering")
        return "output"
    
    # Check if we have edit plan
    if not state.get('edit_plan'):
        logger.warning("No edit plan available, skipping render")
        state['warnings'].append("Edit plan missing, skipping render")
        return "output"
    
    return "render"


def build_pipeline_graph() -> StateGraph:
    """
    Build the LangGraph workflow for video editing pipeline
    
    Pipeline Flow:
    1. Intake (validate input)
    2. Frame Extraction
    3. Parallel Fork → Cursor Detection + Audio Processing (TRUE PARALLEL)
    4. Parallel Join (wait for both)
    5. Vision Description
    6. Analysis (merge all data)
    7. Script Planning
    8. Rendering
    9. Output (finalize)
    
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(PipelineState)
    
    # Add nodes
    workflow.add_node("intake", nodes.intake_node)
    workflow.add_node("frame_extractor", nodes.frame_extractor_node)
    workflow.add_node("parallel_fork", nodes.parallel_fork_node)  # NEW
    workflow.add_node("cursor_detector", nodes.cursor_detector_node)
    workflow.add_node("audio_agent", nodes.audio_agent_node)
    workflow.add_node("parallel_join", nodes.parallel_join_node)  # NEW
    workflow.add_node("vision_description", nodes.vision_description_node)
    workflow.add_node("analysis_agent", nodes.analysis_agent_node)
    workflow.add_node("script_planner", nodes.script_planner_node)
    workflow.add_node("render", nodes.render_node)
    workflow.add_node("output", nodes.output_node)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    # Sequential flow
    workflow.add_edge("intake", "frame_extractor")
    workflow.add_edge("frame_extractor", "parallel_fork")
    
    # TRUE PARALLEL: Fork into two branches
    workflow.add_conditional_edges(
        "parallel_fork",
        lambda state: "parallel",  # Always return "parallel"
        {
            "parallel": ["cursor_detector", "audio_agent"]  # Both run simultaneously
        }
    )
    
    # Join: Both must complete before continuing
    workflow.add_edge("cursor_detector", "parallel_join")
    workflow.add_edge("audio_agent", "parallel_join")
    
    # After join, proceed to vision
    workflow.add_conditional_edges(
        "parallel_join",
        should_continue_after_parallel,
        {
            "vision_description": "vision_description",
            "output": "output"
        }
    )
    
    # After vision, proceed to analysis
    workflow.add_conditional_edges(
        "vision_description",
        should_continue_after_vision,
        {
            "analysis_agent": "analysis_agent",
            "output": "output"
        }
    )
    
    # Sequential: analysis -> script planning
    workflow.add_edge("analysis_agent", "script_planner")
    
    # Conditional: render only if edit plan exists
    workflow.add_conditional_edges(
        "script_planner",
        should_render,
        {
            "render": "render",
            "output": "output"
        }
    )
    
    # Final output
    workflow.add_edge("render", "output")
    workflow.add_edge("output", END)
    
    # Compile graph
    app = workflow.compile()
    
    logger.info("Pipeline graph built successfully with TRUE parallel execution")
    return app


def should_continue_after_parallel(state: PipelineState) -> str:
    """Check if parallel processing succeeded - DO NOT MODIFY STATE"""
    if state.get('status') == 'error':
        logger.error("Pipeline failed during parallel processing")
        return "output"
    
    # ❌ REMOVE: state['errors'].append(...) - Don't mutate state here
    # ❌ REMOVE: state['status'] = 'error' - Don't mutate state here
    
    # Only check, don't modify
    if not state.get('frames'):
        logger.error("No frames available for vision analysis")
        return "output"  # Route to output node instead
    
    return "vision_description"


def should_continue_after_vision(state: PipelineState) -> str:
    """Check if vision analysis succeeded - DO NOT MODIFY STATE"""
    if state.get('status') == 'error':
        return "output"
    
    if not state.get('frame_descriptions'):
        logger.error("No frame descriptions available")
        return "output"  # Just route, don't modify
    
    return "analysis_agent"


def should_render(state: PipelineState) -> str:
    """Check if we should proceed to rendering - DO NOT MODIFY STATE"""
    if state.get('status') == 'error':
        return "output"
    
    if not state.get('edit_plan'):
        logger.warning("No edit plan available, skipping render")
        return "output"
    
    return "render"
def execute_pipeline(project_id: str, video_path: str, 
                     config: Dict[str, Any] = None,
                     user_preferences: Dict[str, Any] = None) -> PipelineState:
    """
    Execute the complete pipeline
    
    Args:
        project_id: Project identifier
        video_path: Path to input video
        config: Optional configuration overrides
        user_preferences: Optional user preferences
        
    Returns:
        Final pipeline state
    """
    from orchestration.state_schema import create_initial_state
    
    logger.info(f"Starting pipeline execution for project {project_id}")
    
    # Create initial state
    initial_state = create_initial_state(
        project_id=project_id,
        video_path=video_path,
        config=config,
        user_preferences=user_preferences
    )
    
    # Build and execute graph
    app = build_pipeline_graph()
    
    try:
        # Run the workflow
        final_state = app.invoke(initial_state)
        
        logger.info("Pipeline execution completed")
        return final_state
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        initial_state['status'] = 'error'
        initial_state['errors'].append(f"Pipeline execution error: {str(e)}")
        return initial_state


# Convenience function for simple execution
def process_video(project_id: str, video_path: str, **kwargs) -> Dict[str, Any]:
    """
    Simple interface to process a video
    
    Args:
        project_id: Project ID
        video_path: Path to video
        **kwargs: Additional config options
        
    Returns:
        Processing result dictionary
    """
    config = {
        "frame_extraction": {
            "fps": kwargs.get('fps'),
            "max_frames": kwargs.get('max_frames'),
        },
        "cursor_detection": {},
        "vision_analysis": {
            "sample_rate": kwargs.get('vision_sample_rate'),
        },
        "audio_processing": {}
    }
    
    user_preferences = {
        "narration_style": kwargs.get('narration_style', 'professional'),
        "keep_original_audio": kwargs.get('keep_original_audio', False),
        "music": kwargs.get('music', False),
        "pacing": kwargs.get('pacing', 'medium')
    }
    
    # Execute pipeline
    final_state = execute_pipeline(
        project_id=project_id,
        video_path=video_path,
        config=config,
        user_preferences=user_preferences
    )
    
    # Return summary
    return {
        "status": final_state.get('status'),
        "project_id": project_id,
        "output_video": final_state.get('final_video_path'),
        "processing_time": final_state.get('processing_time'),
        "total_cost": final_state.get('total_cost_usd'),
        "errors": final_state.get('errors', []),
        "warnings": final_state.get('warnings', []),
        "completed_stages": final_state.get('completed_stages', [])
    }