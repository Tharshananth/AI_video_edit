# AI-POWERED SCREEN RECORDING EDITOR - COMPLETE PROJECT BUILD

### I need you to build a complete AI-powered screen recording editor system that automatically edits screen recordings by detecting cursor movements, understanding UI interactions, generating narration, and producing a polished final video.

---

## 🎯 PROJECT OVERVIEW

**What this system does:**
Takes a raw screen recording video as input and automatically:
1. Extracts frames from the video
2. Detects cursor position and clicks
3. Understands what UI elements are being interacted with
4. Transcribes any existing audio
5. Analyzes all data to create an event timeline
6. Generates a narration script and detailed edit plan
7. Renders the final edited video with zooms, cuts, highlights, and AI narration

**Technology Stack:**
- **Orchestration:** LangChain + LangGraph
- **Vision Analysis:** GPT-4o Vision API
- **Audio:** OpenAI Whisper API
- **Text-to-Speech:** OpenAI TTS API
- **Cursor Detection:** YOLOv8 (or Roboflow API as alternative)
- **Video Processing:** FFmpeg + MoviePy
- **Storage:** File-based with SQLite for project metadata
- **Language:** Python 3.11+

---

## 🏗️ SYSTEM ARCHITECTURE

### Multi-Agent Pipeline (LangGraph Orchestration)
```
INPUT: raw_video.mp4
    ↓
[Agent 1] Frame Extractor (FFmpeg)
    ↓
    ├─→ [Agent 2] Cursor Detector (YOLOv8) ─────┐
    │                                            │
    └─→ [Agent 4] Audio Agent (Whisper) ────────┤
                                                 │
                                                 ↓
         [Agent 3] Frame Description (GPT-4o Vision)
                                                 ↓
         [Agent 5] Analysis Agent (GPT-4o/Claude)
                                                 ↓
         [Agent 6] Script + Edit Planner (GPT-4o/Claude)
                                                 ↓
         [Render Engine] Execute Edits (FFmpeg + MoviePy)
                                                 ↓
OUTPUT: final_edited_video.mp4
```

---

## 📁 PROJECT STRUCTURE

Create this folder structure:
```
video_editor_ai/
├── agents/
│   ├── __init__.py
│   ├── agent_1_frame_extractor.py
│   ├── agent_2_cursor_detector.py
│   ├── agent_3_vision_description.py
│   ├── agent_4_audio_agent.py
│   ├── agent_5_analysis_agent.py
│   └── agent_6_script_planner.py
│
├── orchestration/
│   ├── __init__.py
│   ├── state_schema.py
│   ├── graph_builder.py
│   └── nodes.py
│
├── rendering/
│   ├── __init__.py
│   ├── render_orchestrator.py
│   ├── ffmpeg_processor.py
│   ├── moviepy_processor.py
│   └── effects_generator.py
│
├── models/
│   ├── __init__.py
│   ├── yolo_cursor_detector.py
│   └── download_models.py
│
├── utils/
│   ├── __init__.py
│   ├── project_manager.py
│   ├── file_manager.py
│   └── logger.py
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── prompts.py
│
├── projects/
│   └── (created dynamically for each video)
│
├── database/
│   └── projects.db
│
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 AGENT SPECIFICATIONS

### **AGENT 1: FRAME EXTRACTOR**

**File:** `agents/agent_1_frame_extractor.py`

**Input Format:**
```python
{
    "project_id": str,              # UUID
    "video_path": str,              # /projects/{id}/input/raw_video.mp4
    "config": {
        "fps": 2.5,                 # Frames per second to extract
        "max_frames": 500,
        "resolution": "1280x720",   # Resize frames
        "format": "jpg",
        "quality": 85
    }
}
```

**Processing:**
- Use FFmpeg to extract frames at specified FPS
- Save frames to `/projects/{project_id}/frames/`
- Generate index JSON with timestamps

**Output Format:**
```python
{
    "agent": "frame_extractor",
    "status": "success",
    "execution_time": float,
    "frames": [
        {
            "id": int,
            "timestamp": float,
            "path": str,
            "resolution": str,
            "file_size_kb": int
        }
    ],
    "metadata": {
        "total_frames": int,
        "video_duration": float,
        "fps_used": float,
        "original_resolution": str
    }
}
```

**Saved to:** `/projects/{project_id}/intermediate/frames.json`

---

### **AGENT 2: CURSOR DETECTOR**

**File:** `agents/agent_2_cursor_detector.py`

**Input Format:**
```python
{
    "project_id": str,
    "frames": [                      # From Agent 1 output
        {
            "id": int,
            "timestamp": float,
            "path": str
        }
    ],
    "config": {
        "confidence_threshold": 0.7,
        "model_type": "yolov8",      # or "roboflow"
        "detect_clicks": true,
        "detect_drags": true
    }
}
```

**Processing:**
- Load YOLOv8 model for cursor detection
- Process each frame to detect cursor bounding box
- Analyze cursor trajectory to detect clicks/drags
- Click detection: cursor stops + slight downward movement
- Hover detection: cursor stationary >0.5s

**Output Format:**
```python
{
    "agent": "cursor_detector",
    "status": "success",
    "execution_time": float,
    "cursor_events": [
        {
            "frame_id": int,
            "timestamp": float,
            "cursor_detected": bool,
            "bbox": [x1, y1, x2, y2],
            "center": [x, y],
            "confidence": float,
            "action": str,           # "moving"|"hover"|"click"|"drag"
            "velocity": float
        }
    ],
    "trajectory": {
        "total_movements": int,
        "clicks_detected": int,
        "drags_detected": int,
        "hover_moments": int
    },
    "metadata": {
        "frames_processed": int,
        "frames_with_cursor": int,
        "detection_rate": float
    }
}
```

**Saved to:** `/projects/{project_id}/intermediate/cursor_events.json`

---

### **AGENT 3: FRAME DESCRIPTION (VISION)**

**File:** `agents/agent_3_vision_description.py`

**Input Format:**
```python
{
    "project_id": str,
    "frames_to_analyze": [           # Sampled frames (not all)
        {
            "id": int,
            "timestamp": float,
            "path": str,
            "cursor_position": [x, y] or null
        }
    ],
    "config": {
        "sample_rate": 5,            # Analyze every 5th frame
        "model": "gpt-4o",
        "max_tokens": 300,
        "detail": "high"
    }
}
```

**Processing:**
- Sample frames (every 5th frame to reduce API costs)
- For each frame, call GPT-4o Vision API
- Prompt asks to identify: UI elements, cursor target, action, context
- Parse response into structured JSON

**Prompt Template:**
```
Analyze this screenshot from a screen recording. Describe:

1. What UI elements are visible (buttons, forms, menus, text fields)
2. What the cursor is pointing at (position: [X, Y])
3. What action appears to be happening
4. The overall page/context state

Be concise. Return JSON format:
{
  "ui_elements": [{"type": "button", "text": "...", "bbox": [...]}],
  "cursor_on": "element name",
  "action": "hovering|clicking|typing|etc",
  "page_state": "login_page|dashboard|etc",
  "context": "brief description"
}
```

**Output Format:**
```python
{
    "agent": "frame_description",
    "status": "success",
    "execution_time": float,
    "frames_analyzed": int,
    "descriptions": [
        {
            "frame_id": int,
            "timestamp": float,
            "ui_elements": [
                {
                    "type": str,
                    "text": str,
                    "bbox": [x1, y1, x2, y2],
                    "state": str
                }
            ],
            "cursor_on": str or null,
            "action": str,
            "page_state": str,
            "context": str
        }
    ],
    "api_usage": {
        "total_tokens": int,
        "estimated_cost_usd": float
    }
}
```

**Saved to:** `/projects/{project_id}/intermediate/frame_descriptions.json`

---

### **AGENT 4: AUDIO AGENT**

**File:** `agents/agent_4_audio_agent.py`

**Input Format:**
```python
{
    "project_id": str,
    "video_path": str,
    "config": {
        "model": "whisper-1",
        "language": "en",
        "detect_silences": true,
        "silence_threshold_db": -40,
        "min_silence_duration": 0.5
    }
}
```

**Processing:**
- Extract audio from video using FFmpeg
- Transcribe using OpenAI Whisper API
- Detect silence segments using pydub or librosa
- Analyze speaking pace and pauses

**Output Format:**
```python
{
    "agent": "audio_agent",
    "status": "success",
    "execution_time": float,
    "transcript": {
        "language": str,
        "duration": float,
        "segments": [
            {
                "id": int,
                "start": float,
                "end": float,
                "text": str,
                "words": [
                    {
                        "word": str,
                        "start": float,
                        "end": float
                    }
                ],
                "confidence": float
            }
        ]
    },
    "silence_segments": [
        {
            "start": float,
            "end": float,
            "duration": float,
            "type": str              # "pre_speech"|"pause"|"post_speech"
        }
    ],
    "audio_analysis": {
        "total_speech_duration": float,
        "total_silence_duration": float,
        "speech_to_silence_ratio": float,
        "average_pause_duration": float,
        "longest_silence": float,
        "speaking_pace": str     # "fast"|"normal"|"slow"
    },
    "api_usage": {
        "audio_duration_minutes": float,
        "estimated_cost_usd": float
    }
}
```

**Saved to:** `/projects/{project_id}/intermediate/audio_transcript.json`

---

### **AGENT 5: ANALYSIS AGENT**

**File:** `agents/agent_5_analysis_agent.py`

**Input Format:**
```python
{
    "project_id": str,
    "cursor_events": {...},          # From Agent 2
    "frame_descriptions": {...},     # From Agent 3
    "transcript": {...},             # From Agent 4
    "silence_segments": [...],       # From Agent 4
    "video_metadata": {
        "duration": float,
        "fps": int,
        "resolution": str
    }
}
```

**Processing:**
- Merge all data sources (cursor, vision, audio)
- Understand user actions chronologically
- Identify important moments (clicks, page changes)
- Suggest edit actions (zoom, cut, highlight)
- Create unified event timeline

**Prompt Template:**
```
You are analyzing a screen recording to understand user actions.

INPUT DATA:
- Cursor movements and clicks: {cursor_events}
- Visual frame descriptions: {frame_descriptions}
- Audio transcript: {transcript}
- Silence periods: {silence_segments}

TASK: Create a timeline of important events. For each event:
1. Timestamp
2. Event type (click|hover|page_load|speech|silence)
3. UI element involved
4. Importance level (high|medium|low)
5. Suggested edit action (zoom|highlight|cut|maintain)

EDITING GUIDELINES:
- Clicks = high importance (zoom in)
- Long silences (>2s) during loading = low importance (cut)
- Page transitions = medium importance (smooth transition)
- Speech segments = high importance (maintain)
- Repetitive actions = medium importance (speed up)

Return JSON array of events with suggested edits.
```

**Output Format:**
```python
{
    "agent": "analysis_agent",
    "status": "success",
    "execution_time": float,
    "event_timeline": [
        {
            "id": int,
            "timestamp": float,
            "end_timestamp": float or null,
            "type": str,
            "element": str or null,
            "description": str,
            "importance": str,       # "high"|"medium"|"low"
            "suggested_edit": {
                "action": str,       # "zoom"|"highlight"|"cut"|"maintain"
                "params": dict
            }
        }
    ],
    "insights": {
        "total_clicks": int,
        "total_page_transitions": int,
        "total_silence_duration": float,
        "removable_silence": float,
        "loading_screens": int,
        "suggested_cuts": int,
        "suggested_zooms": int,
        "suggested_highlights": int,
        "original_duration": float,
        "estimated_edited_duration": float
    },
    "api_usage": {
        "total_tokens": int,
        "estimated_cost_usd": float
    }
}
```

**Saved to:** `/projects/{project_id}/intermediate/event_timeline.json`

---

### **AGENT 6: SCRIPT + EDIT PLANNER**

**File:** `agents/agent_6_script_planner.py`

**Input Format:**
```python
{
    "project_id": str,
    "event_timeline": {...},         # From Agent 5
    "original_transcript": {...},    # From Agent 4
    "video_metadata": {...},
    "user_preferences": {
        "narration_style": str,      # "professional"|"casual"|"technical"
        "keep_original_audio": bool,
        "music": bool,
        "pacing": str                # "fast"|"medium"|"slow"
    }
}
```

**Processing:**
- Generate professional narration script
- Create detailed edit instructions with exact parameters
- Output both script and edit plan as structured JSON

**Prompt Template:**
```
You are creating a polished, professional screen recording tutorial.

INPUT: Event timeline with user actions: {event_timeline}

YOUR TASKS:

1. NARRATION SCRIPT:
   - Write clear, engaging narration that explains each step
   - Use natural, conversational language
   - Include timing markers [PAUSE X.Xs] for silence
   - Sync with visual actions
   - Style: {narration_style}

2. EDIT PLAN:
   - Specify exact timestamps for all edits
   - Cuts: Remove silence, loading screens
   - Zooms: Focus on clicks, important UI elements
   - Highlights: Visual emphasis on key moments
   - Speed changes: Speed up boring parts
   - Transitions: Smooth crossfades

Return two JSON objects:
1. narration_script with timed segments
2. edit_plan with detailed instructions
```

**Output Format:**
```python
{
    "agent": "script_edit_planner",
    "status": "success",
    "execution_time": float,
    
    "narration_script": {
        "style": str,
        "total_duration": float,
        "segments": [
            {
                "id": int,
                "start": float,
                "end": float,
                "text": str,
                "timing_notes": str
            }
        ],
        "full_script_text": str
    },
    
    "edit_plan": {
        "timeline": [
            {
                "id": int,
                "action": str,       # "cut"|"zoom"|"highlight"|"speed"|etc
                "start": float or "timestamp",
                "end": float or null,
                "params": {
                    # Varies by action type
                    # For cut: keep_duration, reason
                    # For zoom: target_bbox, zoom_scale, animation
                    # For highlight: bbox, effect, color, intensity
                    # For click_effect: position, effect_type, duration
                }
            }
        ],
        "summary": {
            "total_cuts": int,
            "total_zooms": int,
            "total_highlights": int,
            "total_effects": int,
            "original_duration": float,
            "final_duration": float,
            "time_saved": float
        }
    },
    
    "tts_config": {
        "service": "openai",
        "model": "tts-1-hd",
        "voice": str,
        "speed": float,
        "estimated_cost_usd": float
    },
    
    "api_usage": {
        "total_tokens": int,
        "estimated_cost_usd": float
    }
}
```

**Saved to:**
- `/projects/{project_id}/output/narration_script.txt`
- `/projects/{project_id}/output/edit_plan.json`

---

## 🔗 LANGGRAPH STATE SCHEMA

**File:** `orchestration/state_schema.py`
```python
from typing import TypedDict, List, Dict, Optional

class PipelineState(TypedDict):
    # Project metadata
    project_id: str
    video_path: str
    output_dir: str
    status: str                      # "processing"|"complete"|"error"
    current_stage: str
    
    # Agent 1 outputs
    frames: Optional[List[Dict]]
    
    # Agent 2 outputs
    cursor_events: Optional[List[Dict]]
    
    # Agent 3 outputs
    frame_descriptions: Optional[List[Dict]]
    
    # Agent 4 outputs
    audio_transcript: Optional[Dict]
    silence_segments: Optional[List[Dict]]
    
    # Agent 5 outputs
    event_timeline: Optional[List[Dict]]
    
    # Agent 6 outputs
    narration_script: Optional[Dict]
    edit_plan: Optional[Dict]
    
    # Final output
    final_video_path: Optional[str]
    processing_time: float
    errors: List[str]
```

---

## 🔄 LANGGRAPH FLOW DEFINITION

**File:** `orchestration/graph_builder.py`

**Graph Structure:**
```
START
  ↓
intake_node (validate input)
  ↓
frame_extractor_node (Agent 1)
  ↓
parallel_fork_node
  ├→ cursor_detector_node (Agent 2)
  └→ audio_agent_node (Agent 4)
  ↓
conditional_node (check if cursor detected)
  ↓
vision_description_node (Agent 3)
  ↓
analysis_agent_node (Agent 5)
  ↓
script_planner_node (Agent 6)
  ↓
[OPTIONAL] human_review_checkpoint
  ↓
render_node (Execute edits)
  ↓
output_node (Save results)
  ↓
END
```

**Conditional Edges:**
1. After parallel_fork: If no cursor detected → skip some zoom features
2. After script_planner: If user_review enabled → go to checkpoint
3. Any agent failure → retry 3x → on failure → error_node

---

## 🎬 RENDERING SYSTEM

**File:** `rendering/render_orchestrator.py`

**Input:** `edit_plan.json` from Agent 6

**Process:**
1. Read edit_plan.json
2. Sort all edits by timestamp
3. Execute edits in order:
   - **Cuts:** Use FFmpeg to extract segments
   - **Speed changes:** FFmpeg setpts filter
   - **Zooms:** MoviePy crop + scale with animation
   - **Click effects:** Generate ripple using Pillow, composite with MoviePy
   - **Highlights:** Generate glow mask, composite with MoviePy
   - **Text overlays:** MoviePy TextClip
4. Concatenate all segments
5. Replace/mix audio with TTS narration
6. Final encoding with FFmpeg (H.264)

**Tool Selection:**
- FFmpeg → Cuts, speed, audio, final encoding
- MoviePy → Zooms, effects, compositing
- Pillow → Generate effect graphics (ripples, glows)

**Output:** `/projects/{project_id}/output/final_video.mp4`

---

## 💾 PROJECT MANAGEMENT

**File:** `utils/project_manager.py`

**Functions:**
- `create_project(video_file)` → Generate UUID, create folder structure
- `get_project_status(project_id)` → Return current processing stage
- `list_user_projects(user_id)` → Return all projects
- `delete_project(project_id)` → Clean up all files
- `save_checkpoint(project_id, state)` → Save LangGraph state to disk

**Folder Structure per Project:**
```
/projects/{project_id}/
├── input/
│   └── raw_video.mp4
├── frames/
│   ├── frame_0001.jpg
│   └── ...
├── intermediate/
│   ├── frames.json
│   ├── cursor_events.json
│   ├── frame_descriptions.json
│   ├── audio_transcript.json
│   └── event_timeline.json
├── output/
│   ├── narration_script.txt
│   ├── edit_plan.json
│   └── final_video.mp4
├── render/
│   └── (temporary files during rendering)
├── state/
│   └── pipeline_state.json
└── metadata.json
```

---

## 🗄️ DATABASE SCHEMA

**File:** SQLite at `database/projects.db`

**Table: projects**
```sql
CREATE TABLE projects (
    project_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(50),
    video_name VARCHAR(255),
    video_path TEXT,
    status VARCHAR(20),
    current_stage VARCHAR(50),
    upload_time TIMESTAMP,
    processing_start TIMESTAMP,
    processing_end TIMESTAMP,
    duration_seconds FLOAT,
    file_size_mb FLOAT,
    resolution VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: pipeline_stages**
```sql
CREATE TABLE pipeline_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id VARCHAR(36),
    stage_name VARCHAR(50),
    status VARCHAR(20),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds FLOAT,
    tokens_used INT,
    cost_usd DECIMAL(10,4),
    error_message TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);
```

---

## ⚙️ CONFIGURATION

**File:** `config/settings.py`
```python
# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Configuration
VISION_MODEL = "gpt-4o"
ANALYSIS_MODEL = "gpt-4o"  # or "claude-sonnet-4"
TTS_MODEL = "tts-1-hd"
TTS_VOICE = "alloy"

# Frame Extraction
DEFAULT_FPS = 2.5
MAX_FRAMES = 500
FRAME_RESOLUTION = "1280x720"

# Vision API
FRAME_SAMPLE_RATE = 5  # Analyze every 5th frame
VISION_MAX_TOKENS = 300

# Cursor Detection
CURSOR_CONFIDENCE_THRESHOLD = 0.7
CURSOR_MODEL = "yolov8"  # or "roboflow"

# Audio Processing
WHISPER_MODEL = "whisper-1"
SILENCE_THRESHOLD_DB = -40
MIN_SILENCE_DURATION = 0.5

# Rendering
VIDEO_CODEC = "libx264"
VIDEO_BITRATE = "8000k"
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"

# Project Management
PROJECT_RETENTION_DAYS = 30
MAX_CONCURRENT_PROJECTS = 3
```

**File:** `.env.example`
```
OPENAI_API_KEY=your_key_here
ROBOFLOW_API_KEY=your_key_here (optional)
```

---
