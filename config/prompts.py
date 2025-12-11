<<<<<<< HEAD
"""
AI prompt templates for video analysis
"""

def format_vision_prompt(cursor_position=None):
    """
    Prompt for GPT-4o Vision to analyze a screen recording frame
    
    Args:
        cursor_position: [x, y] coordinates of cursor (if detected)
        
    Returns:
        Formatted prompt string
    """
    cursor_info = ""
    if cursor_position:
        cursor_info = f"\nThe cursor is located at position [{cursor_position[0]}, {cursor_position[1]}]."
    
    return f"""You are analyzing a screenshot from a screen recording tutorial.{cursor_info}

Your task is to identify and describe:

1. **UI Elements**: List all visible interactive elements (buttons, forms, menus, text fields, checkboxes, etc.)
2. **Cursor Target**: What element is the cursor pointing at or near?
3. **Current Action**: What action appears to be happening? (hovering, clicking, typing, scrolling, selecting)
4. **Page Context**: What type of page/application is this? (login page, dashboard, settings, editor, etc.)
5. **Brief Description**: Concise summary of what's happening in this moment

Return ONLY valid JSON in this exact format:
{{
  "ui_elements": [
    {{"type": "button", "text": "Login", "bbox": [x1, y1, x2, y2], "state": "active"}},
    {{"type": "input", "text": "Email", "bbox": [x1, y1, x2, y2], "state": "filled"}}
  ],
  "cursor_on": "Login button",
  "action": "clicking",
  "page_state": "login_page",
  "context": "User is logging into the application after filling credentials"
}}

Important:
- Be concise but specific
- Focus on user-facing elements
- Describe the current moment, not the entire interface
- Use clear action verbs: clicking, hovering, typing, scrolling, selecting
"""


def format_analysis_prompt(cursor_events, frame_descriptions, transcript, silence_segments, video_metadata):
    """
    Prompt for analyzing all data and creating edit timeline
    
    Args:
        cursor_events: JSON string of cursor events
        frame_descriptions: JSON string of frame descriptions
        transcript: JSON string of transcript
        silence_segments: JSON string of silence segments
        video_metadata: JSON string of video metadata
        
    Returns:
        Formatted prompt string
    """
    return f"""You are a professional video editor analyzing a screen recording to create an edit plan.

VIDEO METADATA:
{video_metadata}

CURSOR EVENTS SUMMARY:
{cursor_events}

VISUAL FRAME ANALYSIS:
{frame_descriptions}

AUDIO TRANSCRIPT:
{transcript}

SILENCE SEGMENTS (potential cuts):
{silence_segments}

YOUR TASK:
Create a comprehensive timeline of important events with editing suggestions.

For each event, identify:
1. **Timestamp**: When it occurs
2. **Event Type**: click, hover, page_load, speech, silence, typing
3. **UI Element**: What was interacted with
4. **Importance**: high (critical action), medium (supporting action), low (boring/repetitive)
5. **Edit Suggestion**: What editing action to apply

EDITING GUIDELINES:
- **Clicks on buttons/links** = HIGH importance → ZOOM in (1.3-1.5x scale)
- **Long silences during loading** (>2s) = LOW importance → CUT completely
- **Page transitions** = MEDIUM importance → ADD smooth crossfade
- **Speech segments** = HIGH importance → MAINTAIN fully, never cut
- **Repetitive actions** (filling forms) = MEDIUM → SPEED UP (1.5x)
- **Hovers without clicks** = LOW importance → MAINTAIN normal speed
- **First time showing UI element** = HIGH → HIGHLIGHT with glow effect

Return ONLY valid JSON in this format:
{{
  "event_timeline": [
    {{
      "id": 0,
      "timestamp": 0.0,
      "end_timestamp": 4.5,
      "type": "speech",
      "element": null,
      "description": "User introduces the tutorial",
      "importance": "high",
      "suggested_edit": {{
        "action": "maintain",
        "params": {{"reason": "introduction"}}
      }}
    }},
    {{
      "id": 1,
      "timestamp": 6.0,
      "end_timestamp": 6.5,
      "type": "click",
      "element": "Login button",
      "description": "User clicks Login button to authenticate",
      "importance": "high",
      "suggested_edit": {{
        "action": "zoom",
        "params": {{
          "target_bbox": [450, 320, 550, 360],
          "zoom_scale": 1.4,
          "duration": 0.5,
          "animation": "ease-in-out"
        }}
      }}
    }},
    {{
      "id": 2,
      "timestamp": 7.0,
      "end_timestamp": 10.5,
      "type": "silence",
      "element": null,
      "description": "Loading screen while authenticating",
      "importance": "low",
      "suggested_edit": {{
        "action": "cut",
        "params": {{"duration": 3.5, "reason": "loading_wait"}}
      }}
    }}
  ]
}}

Focus on creating a smooth, professional tutorial flow. Remove dead time but preserve context.
"""


def format_script_planner_prompt(event_timeline, original_transcript, video_metadata, user_preferences):
    """
    Prompt for generating narration script and detailed edit plan
    
    Args:
        event_timeline: JSON string of event timeline
        original_transcript: JSON string of original transcript
        video_metadata: JSON string of video metadata
        user_preferences: JSON string of user preferences
        
    Returns:
        Formatted prompt string
    """
    return f"""You are a professional scriptwriter and video editor creating a polished tutorial.

EVENT TIMELINE (what happens in the video):
{event_timeline}

ORIGINAL TRANSCRIPT (if any):
{original_transcript}

VIDEO METADATA:
{video_metadata}

USER PREFERENCES:
{user_preferences}

YOUR TASKS:

1. **NARRATION SCRIPT**:
Write clear, engaging narration that:
- Explains each step as it happens
- Uses natural, conversational language
- Matches the pacing (don't rush or drag)
- Provides context for what the viewer sees
- Uses appropriate style: {user_preferences}

2. **DETAILED EDIT PLAN**:
Create precise editing instructions:
- **cuts**: Exact timestamps to remove (silences, loading screens)
- **zooms**: When to zoom in, coordinates, scale, duration
- **highlights**: Visual emphasis on important elements
- **click_effects**: Ripple animations on click moments
- **speed_changes**: Speed up boring parts (form filling)
- **transitions**: Smooth crossfades between page changes

Return ONLY valid JSON in this format:
{{
  "narration_script": {{
    "style": "professional",
    "total_duration": 105.2,
    "segments": [
      {{
        "id": 0,
        "start": 0.0,
        "end": 4.5,
        "text": "Welcome to this tutorial. Today, I'll show you how to log in to the application.",
        "timing_notes": "Speak clearly at medium pace"
      }},
      {{
        "id": 1,
        "start": 4.5,
        "end": 9.0,
        "text": "First, we'll click the Login button to access the system.",
        "timing_notes": "Sync 'click' with the actual click at 6.0s"
      }}
    ],
    "full_script_text": "Welcome to this tutorial. Today, I'll show you how to log in to the application. First, we'll click the Login button..."
  }},
  "edit_plan": {{
    "timeline": [
      {{
        "id": 0,
        "action": "cut",
        "start": 7.0,
        "end": 10.5,
        "params": {{
          "duration": 3.5,
          "reason": "loading_screen"
        }}
      }},
      {{
        "id": 1,
        "action": "zoom",
        "start": 6.0,
        "end": 6.5,
        "params": {{
          "target_bbox": [450, 320, 550, 360],
          "zoom_scale": 1.4,
          "animation": "ease-in-out"
        }}
      }},
      {{
        "id": 2,
        "action": "highlight",
        "start": 6.0,
        "end": 6.3,
        "params": {{
          "bbox": [450, 320, 550, 360],
          "effect": "glow",
          "color": "#4A90E2",
          "intensity": 0.8
        }}
      }},
      {{
        "id": 3,
        "action": "click_effect",
        "start": 6.0,
        "params": {{
          "position": [500, 340],
          "effect_type": "ripple",
          "duration": 0.4
        }}
      }},
      {{
        "id": 4,
        "action": "speed",
        "start": 15.0,
        "end": 20.0,
        "params": {{
          "speed_multiplier": 1.5,
          "reason": "repetitive_form_filling"
        }}
      }}
    ],
    "summary": {{
      "total_cuts": 5,
      "total_zooms": 8,
      "total_highlights": 8,
      "total_effects": 8,
      "original_duration": 120.5,
      "final_duration": 105.2,
      "time_saved": 15.3
    }}
  }}
}}

Make the tutorial feel smooth and professional. Every action should have clear narration.
"""
=======
"""
AI prompt templates for video analysis
"""

def format_vision_prompt(cursor_position=None):
    """
    Prompt for GPT-4o Vision to analyze a screen recording frame
    
    Args:
        cursor_position: [x, y] coordinates of cursor (if detected)
        
    Returns:
        Formatted prompt string
    """
    cursor_info = ""
    if cursor_position:
        cursor_info = f"\nThe cursor is located at position [{cursor_position[0]}, {cursor_position[1]}]."
    
    return f"""You are analyzing a screenshot from a screen recording tutorial.{cursor_info}

Your task is to identify and describe:

1. **UI Elements**: List all visible interactive elements (buttons, forms, menus, text fields, checkboxes, etc.)
2. **Cursor Target**: What element is the cursor pointing at or near?
3. **Current Action**: What action appears to be happening? (hovering, clicking, typing, scrolling, selecting)
4. **Page Context**: What type of page/application is this? (login page, dashboard, settings, editor, etc.)
5. **Brief Description**: Concise summary of what's happening in this moment

Return ONLY valid JSON in this exact format:
{{
  "ui_elements": [
    {{"type": "button", "text": "Login", "bbox": [x1, y1, x2, y2], "state": "active"}},
    {{"type": "input", "text": "Email", "bbox": [x1, y1, x2, y2], "state": "filled"}}
  ],
  "cursor_on": "Login button",
  "action": "clicking",
  "page_state": "login_page",
  "context": "User is logging into the application after filling credentials"
}}

Important:
- Be concise but specific
- Focus on user-facing elements
- Describe the current moment, not the entire interface
- Use clear action verbs: clicking, hovering, typing, scrolling, selecting
"""


def format_analysis_prompt(cursor_events, frame_descriptions, transcript, silence_segments, video_metadata):
    """
    Prompt for analyzing all data and creating edit timeline
    
    Args:
        cursor_events: JSON string of cursor events
        frame_descriptions: JSON string of frame descriptions
        transcript: JSON string of transcript
        silence_segments: JSON string of silence segments
        video_metadata: JSON string of video metadata
        
    Returns:
        Formatted prompt string
    """
    return f"""You are a professional video editor analyzing a screen recording to create an edit plan.

VIDEO METADATA:
{video_metadata}

CURSOR EVENTS SUMMARY:
{cursor_events}

VISUAL FRAME ANALYSIS:
{frame_descriptions}

AUDIO TRANSCRIPT:
{transcript}

SILENCE SEGMENTS (potential cuts):
{silence_segments}

YOUR TASK:
Create a comprehensive timeline of important events with editing suggestions.

For each event, identify:
1. **Timestamp**: When it occurs
2. **Event Type**: click, hover, page_load, speech, silence, typing
3. **UI Element**: What was interacted with
4. **Importance**: high (critical action), medium (supporting action), low (boring/repetitive)
5. **Edit Suggestion**: What editing action to apply

EDITING GUIDELINES:
- **Clicks on buttons/links** = HIGH importance → ZOOM in (1.3-1.5x scale)
- **Long silences during loading** (>2s) = LOW importance → CUT completely
- **Page transitions** = MEDIUM importance → ADD smooth crossfade
- **Speech segments** = HIGH importance → MAINTAIN fully, never cut
- **Repetitive actions** (filling forms) = MEDIUM → SPEED UP (1.5x)
- **Hovers without clicks** = LOW importance → MAINTAIN normal speed
- **First time showing UI element** = HIGH → HIGHLIGHT with glow effect

Return ONLY valid JSON in this format:
{{
  "event_timeline": [
    {{
      "id": 0,
      "timestamp": 0.0,
      "end_timestamp": 4.5,
      "type": "speech",
      "element": null,
      "description": "User introduces the tutorial",
      "importance": "high",
      "suggested_edit": {{
        "action": "maintain",
        "params": {{"reason": "introduction"}}
      }}
    }},
    {{
      "id": 1,
      "timestamp": 6.0,
      "end_timestamp": 6.5,
      "type": "click",
      "element": "Login button",
      "description": "User clicks Login button to authenticate",
      "importance": "high",
      "suggested_edit": {{
        "action": "zoom",
        "params": {{
          "target_bbox": [450, 320, 550, 360],
          "zoom_scale": 1.4,
          "duration": 0.5,
          "animation": "ease-in-out"
        }}
      }}
    }},
    {{
      "id": 2,
      "timestamp": 7.0,
      "end_timestamp": 10.5,
      "type": "silence",
      "element": null,
      "description": "Loading screen while authenticating",
      "importance": "low",
      "suggested_edit": {{
        "action": "cut",
        "params": {{"duration": 3.5, "reason": "loading_wait"}}
      }}
    }}
  ]
}}

Focus on creating a smooth, professional tutorial flow. Remove dead time but preserve context.
"""


def format_script_planner_prompt(event_timeline, original_transcript, video_metadata, user_preferences):
    """
    Prompt for generating narration script and detailed edit plan
    
    Args:
        event_timeline: JSON string of event timeline
        original_transcript: JSON string of original transcript
        video_metadata: JSON string of video metadata
        user_preferences: JSON string of user preferences
        
    Returns:
        Formatted prompt string
    """
    return f"""You are a professional scriptwriter and video editor creating a polished tutorial.

EVENT TIMELINE (what happens in the video):
{event_timeline}

ORIGINAL TRANSCRIPT (if any):
{original_transcript}

VIDEO METADATA:
{video_metadata}

USER PREFERENCES:
{user_preferences}

YOUR TASKS:

1. **NARRATION SCRIPT**:
Write clear, engaging narration that:
- Explains each step as it happens
- Uses natural, conversational language
- Matches the pacing (don't rush or drag)
- Provides context for what the viewer sees
- Uses appropriate style: {user_preferences}

2. **DETAILED EDIT PLAN**:
Create precise editing instructions:
- **cuts**: Exact timestamps to remove (silences, loading screens)
- **zooms**: When to zoom in, coordinates, scale, duration
- **highlights**: Visual emphasis on important elements
- **click_effects**: Ripple animations on click moments
- **speed_changes**: Speed up boring parts (form filling)
- **transitions**: Smooth crossfades between page changes

Return ONLY valid JSON in this format:
{{
  "narration_script": {{
    "style": "professional",
    "total_duration": 105.2,
    "segments": [
      {{
        "id": 0,
        "start": 0.0,
        "end": 4.5,
        "text": "Welcome to this tutorial. Today, I'll show you how to log in to the application.",
        "timing_notes": "Speak clearly at medium pace"
      }},
      {{
        "id": 1,
        "start": 4.5,
        "end": 9.0,
        "text": "First, we'll click the Login button to access the system.",
        "timing_notes": "Sync 'click' with the actual click at 6.0s"
      }}
    ],
    "full_script_text": "Welcome to this tutorial. Today, I'll show you how to log in to the application. First, we'll click the Login button..."
  }},
  "edit_plan": {{
    "timeline": [
      {{
        "id": 0,
        "action": "cut",
        "start": 7.0,
        "end": 10.5,
        "params": {{
          "duration": 3.5,
          "reason": "loading_screen"
        }}
      }},
      {{
        "id": 1,
        "action": "zoom",
        "start": 6.0,
        "end": 6.5,
        "params": {{
          "target_bbox": [450, 320, 550, 360],
          "zoom_scale": 1.4,
          "animation": "ease-in-out"
        }}
      }},
      {{
        "id": 2,
        "action": "highlight",
        "start": 6.0,
        "end": 6.3,
        "params": {{
          "bbox": [450, 320, 550, 360],
          "effect": "glow",
          "color": "#4A90E2",
          "intensity": 0.8
        }}
      }},
      {{
        "id": 3,
        "action": "click_effect",
        "start": 6.0,
        "params": {{
          "position": [500, 340],
          "effect_type": "ripple",
          "duration": 0.4
        }}
      }},
      {{
        "id": 4,
        "action": "speed",
        "start": 15.0,
        "end": 20.0,
        "params": {{
          "speed_multiplier": 1.5,
          "reason": "repetitive_form_filling"
        }}
      }}
    ],
    "summary": {{
      "total_cuts": 5,
      "total_zooms": 8,
      "total_highlights": 8,
      "total_effects": 8,
      "original_duration": 120.5,
      "final_duration": 105.2,
      "time_saved": 15.3
    }}
  }}
}}

Make the tutorial feel smooth and professional. Every action should have clear narration.
"""
>>>>>>> d4e3c4e (update)
