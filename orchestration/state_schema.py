from typing import TypedDict, List, Dict, Optional, Any

class PipelineState(TypedDict, total=False):
    """
    State schema for the video editing pipeline
    
    This state is passed between all agents in the LangGraph workflow
    """
    
    # Project metadata
    project_id: str
    video_path: str
    output_dir: str
    status: str  # "processing" | "complete" | "error"
    current_stage: str
    
    # Configuration
    config: Dict[str, Any]
    user_preferences: Dict[str, Any]
    
    # Video metadata
    video_metadata: Dict[str, Any]
    
    # Agent 1 outputs (Frame Extractor)
    frames: Optional[List[Dict[str, Any]]]
    frames_metadata: Optional[Dict[str, Any]]
    
    # Agent 2 outputs (Cursor Detector)
    cursor_events: Optional[List[Dict[str, Any]]]
    cursor_trajectory: Optional[Dict[str, Any]]
    cursor_metadata: Optional[Dict[str, Any]]
    
    # Agent 3 outputs (Vision Description)
    frame_descriptions: Optional[List[Dict[str, Any]]]
    vision_metadata: Optional[Dict[str, Any]]
    
    # Agent 4 outputs (Audio Agent)
    audio_transcript: Optional[Dict[str, Any]]
    silence_segments: Optional[List[Dict[str, Any]]]
    audio_analysis: Optional[Dict[str, Any]]
    audio_metadata: Optional[Dict[str, Any]]
    
    # Agent 5 outputs (Analysis Agent)
    event_timeline: Optional[List[Dict[str, Any]]]
    insights: Optional[Dict[str, Any]]
    analysis_metadata: Optional[Dict[str, Any]]
    
    # Agent 6 outputs (Script Planner)
    narration_script: Optional[Dict[str, Any]]
    edit_plan: Optional[Dict[str, Any]]
    tts_config: Optional[Dict[str, Any]]
    script_metadata: Optional[Dict[str, Any]]
    
    # Rendering outputs
    final_video_path: Optional[str]
    render_metadata: Optional[Dict[str, Any]]
    
    # Pipeline tracking
    processing_time: float
    errors: List[str]
    warnings: List[str]
    completed_stages: List[str]
    
    # API usage tracking
    total_tokens_used: int
    total_cost_usd: float


def create_initial_state(project_id: str, video_path: str, 
                         config: Optional[Dict] = None,
                         user_preferences: Optional[Dict] = None) -> PipelineState:
    """
    Create initial pipeline state
    
    Args:
        project_id: Project identifier
        video_path: Path to input video
        config: Optional configuration overrides
        user_preferences: Optional user preferences
        
    Returns:
        Initial state dictionary
    """
    return PipelineState(
        project_id=project_id,
        video_path=video_path,
        output_dir=f"projects/{project_id}/output",
        status="processing",
        current_stage="initialized",
        config=config or {},
        user_preferences=user_preferences or {},
        video_metadata={},
        frames=None,
        frames_metadata=None,
        cursor_events=None,
        cursor_trajectory=None,
        cursor_metadata=None,
        frame_descriptions=None,
        vision_metadata=None,
        audio_transcript=None,
        silence_segments=None,
        audio_analysis=None,
        audio_metadata=None,
        event_timeline=None,
        insights=None,
        analysis_metadata=None,
        narration_script=None,
        edit_plan=None,
        tts_config=None,
        script_metadata=None,
        final_video_path=None,
        render_metadata=None,
        processing_time=0.0,
        errors=[],
        warnings=[],
        completed_stages=[],
        total_tokens_used=0,
        total_cost_usd=0.0
    )


def update_state_with_agent_result(state: PipelineState, 
                                   agent_name: str,
                                   result: Dict[str, Any]) -> PipelineState:
    """
    Update state with agent execution result
    
    Args:
        state: Current pipeline state
        agent_name: Name of the agent
        result: Agent execution result
        
    Returns:
        Updated state
    """
    # Update status
    if result.get("status") == "failed":
        state["errors"].append(f"{agent_name}: {result.get('error', 'Unknown error')}")
        state["status"] = "error"
        return state
    
    # Mark stage as completed
    state["completed_stages"].append(agent_name)
    state["current_stage"] = agent_name
    
    # Update agent-specific outputs
    if agent_name == "frame_extractor":
        state["frames"] = result.get("frames")
        state["frames_metadata"] = result.get("metadata")
        state["video_metadata"] = result.get("metadata", {})
    
    elif agent_name == "cursor_detector":
        state["cursor_events"] = result.get("cursor_events")
        state["cursor_trajectory"] = result.get("trajectory")
        state["cursor_metadata"] = result.get("metadata")
    
    elif agent_name == "vision_description":
        state["frame_descriptions"] = result.get("descriptions")
        state["vision_metadata"] = result.get("api_usage")
        
        # Track API usage
        tokens = result.get("api_usage", {}).get("total_tokens", 0)
        cost = result.get("api_usage", {}).get("estimated_cost_usd", 0.0)
        state["total_tokens_used"] += tokens
        state["total_cost_usd"] += cost
    
    elif agent_name == "audio_agent":
        state["audio_transcript"] = result.get("transcript")
        state["silence_segments"] = result.get("silence_segments")
        state["audio_analysis"] = result.get("audio_analysis")
        state["audio_metadata"] = result.get("api_usage")
        
        # Track API usage
        cost = result.get("api_usage", {}).get("estimated_cost_usd", 0.0)
        state["total_cost_usd"] += cost
    
    elif agent_name == "analysis_agent":
        state["event_timeline"] = result.get("event_timeline")
        state["insights"] = result.get("insights")
        state["analysis_metadata"] = result.get("api_usage")
        
        # Track API usage
        tokens = result.get("api_usage", {}).get("total_tokens", 0)
        cost = result.get("api_usage", {}).get("estimated_cost_usd", 0.0)
        state["total_tokens_used"] += tokens
        state["total_cost_usd"] += cost
    
    elif agent_name == "script_planner":
        state["narration_script"] = result.get("narration_script")
        state["edit_plan"] = result.get("edit_plan")
        state["tts_config"] = result.get("tts_config")
        state["script_metadata"] = result.get("api_usage")
        
        # Track API usage
        tokens = result.get("api_usage", {}).get("total_tokens", 0)
        cost = result.get("api_usage", {}).get("estimated_cost_usd", 0.0)
        tts_cost = result.get("tts_config", {}).get("estimated_cost_usd", 0.0)
        state["total_tokens_used"] += tokens
        state["total_cost_usd"] += cost + tts_cost
    
    elif agent_name == "render":
        state["final_video_path"] = result.get("video_path")
        state["render_metadata"] = result.get("metadata")
        state["status"] = "complete"
    
    # Update processing time
    state["processing_time"] += result.get("execution_time", 0.0)
    
    return state