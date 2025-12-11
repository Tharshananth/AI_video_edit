import base64
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import time

from openai import OpenAI
from config.settings import (
    OPENAI_API_KEY,
    VISION_MODEL,
    FRAME_SAMPLE_RATE,
    VISION_MAX_TOKENS,
    VISION_DETAIL,
    COST_GPT4O_INPUT,
    COST_GPT4O_OUTPUT,
    MAX_RETRIES,
    RETRY_DELAY
)
from config.prompts import format_vision_prompt
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger

class VisionDescriptionAgent:
    """Agent 3: Analyzes frames with GPT-4o Vision to understand UI interactions"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("vision_description", project_id)
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.total_tokens = 0
        
    def execute(self, frames: List[Dict], cursor_events: List[Dict], 
                config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze frames with GPT-4o Vision
        
        Args:
            frames: List of frame dictionaries from Agent 1
            cursor_events: Cursor events from Agent 2
            config: Optional configuration overrides
            
        Returns:
            Result dictionary with frame descriptions
        """
        self.logger.start("Starting vision analysis")
        start_time = datetime.now()
        
        try:
            # Merge config
            cfg = {
                "sample_rate": FRAME_SAMPLE_RATE,
                "model": VISION_MODEL,
                "max_tokens": VISION_MAX_TOKENS,
                "detail": VISION_DETAIL
            }
            if config:
                cfg.update(config)
            
            # Sample frames (analyze every Nth frame to reduce costs)
            frames_to_analyze = self._sample_frames(frames, cursor_events, cfg["sample_rate"])
            
            self.logger.info(f"Analyzing {len(frames_to_analyze)} frames (sampled from {len(frames)})")
            
            # Analyze each frame
            descriptions = []
            for i, frame_data in enumerate(frames_to_analyze):
                self.logger.debug(f"Analyzing frame {i+1}/{len(frames_to_analyze)}")
                
                description = self._analyze_frame(frame_data, cfg)
                if description:
                    descriptions.append(description)
                
                # Rate limiting
                time.sleep(0.5)  # Avoid hitting rate limits
            
            # Build result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            estimated_cost = (
                self.total_tokens * COST_GPT4O_INPUT + 
                len(descriptions) * 200 * COST_GPT4O_OUTPUT  # Estimate output tokens
            )
            
            result = {
                "agent": "frame_description",
                "status": "success",
                "execution_time": execution_time,
                "frames_analyzed": len(descriptions),
                "descriptions": descriptions,
                "api_usage": {
                    "total_tokens": self.total_tokens,
                    "estimated_cost_usd": round(estimated_cost, 4)
                }
            }
            
            # Save result
            self.file_manager.save_json(result, "frame_descriptions.json")
            
            self.logger.success(f"Analyzed {len(descriptions)} frames, cost: ${estimated_cost:.4f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Vision analysis failed: {e}", exc_info=True)
            return {
                "agent": "frame_description",
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _sample_frames(self, frames: List[Dict], cursor_events: List[Dict], 
                      sample_rate: int) -> List[Dict]:
        """Sample frames intelligently"""
        frames_to_analyze = []
        
        # Always include first and last frame
        if frames:
            frames_to_analyze.append(self._prepare_frame_data(frames[0], cursor_events))
        
        # Sample every Nth frame
        for i in range(sample_rate, len(frames) - 1, sample_rate):
            frames_to_analyze.append(self._prepare_frame_data(frames[i], cursor_events))
        
        # Always include last frame
        if len(frames) > 1:
            frames_to_analyze.append(self._prepare_frame_data(frames[-1], cursor_events))
        
        # Add frames where clicks happened
        for event in cursor_events:
            if event.get("action") == "click":
                frame_id = event["frame_id"]
                if frame_id < len(frames):
                    frame_data = self._prepare_frame_data(frames[frame_id], cursor_events)
                    # Only add if not already in list
                    if not any(f["frame_id"] == frame_id for f in frames_to_analyze):
                        frames_to_analyze.append(frame_data)
        
        # Sort by frame_id
        frames_to_analyze.sort(key=lambda x: x["frame_id"])
        
        return frames_to_analyze
    
    def _prepare_frame_data(self, frame: Dict, cursor_events: List[Dict]) -> Dict:
        """Prepare frame data with cursor information"""
        frame_id = frame["id"]
        
        # Find corresponding cursor event
        cursor_position = None
        for event in cursor_events:
            if event["frame_id"] == frame_id and event["cursor_detected"]:
                cursor_position = event["center"]
                break
        
        return {
            "frame_id": frame_id,
            "timestamp": frame["timestamp"],
            "path": frame["path"],
            "cursor_position": cursor_position
        }
    
    def _analyze_frame(self, frame_data: Dict, config: Dict) -> Optional[Dict]:
        """Analyze a single frame with GPT-4o Vision"""
        try:
            # Encode image to base64
            image_path = Path(frame_data["path"])
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Build prompt
            prompt = format_vision_prompt(frame_data["cursor_position"])
            
            # Call API with retries
            for attempt in range(MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model=config["model"],
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": prompt
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_data}",
                                            "detail": config["detail"]
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=config["max_tokens"],
                        temperature=0.3
                    )
                    
                    # Track tokens
                    self.total_tokens += response.usage.total_tokens
                    
                    # Parse response
                    content = response.choices[0].message.content
                    
                    # Try to extract JSON
                    parsed_data = self._parse_vision_response(content)
                    
                    return {
                        "frame_id": frame_data["frame_id"],
                        "timestamp": frame_data["timestamp"],
                        "ui_elements": parsed_data.get("ui_elements", []),
                        "cursor_on": parsed_data.get("cursor_on"),
                        "action": parsed_data.get("action", "unknown"),
                        "page_state": parsed_data.get("page_state", ""),
                        "context": parsed_data.get("context", "")
                    }
                    
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        self.logger.warning(f"API call failed, retrying... ({attempt + 1}/{MAX_RETRIES})")
                        time.sleep(RETRY_DELAY * (attempt + 1))
                    else:
                        raise
            
        except Exception as e:
            self.logger.error(f"Failed to analyze frame {frame_data['frame_id']}: {e}")
            return None
    
    def _parse_vision_response(self, content: str) -> Dict:
        """Parse JSON from vision API response"""
        try:
            # Try to find JSON in response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Validate required fields exist
                if not data.get("ui_elements"):
                    self.logger.warning("Response missing ui_elements field")
                if not data.get("context"):
                    data["context"] = ""
                
                return data
            
            # ✓ FIXED: Fail loudly instead of silently
            self.logger.error(f"❌ No JSON found in vision response. Raw content:\n{content[:500]}")
            raise ValueError("Vision API response did not contain valid JSON")
            
        except json.JSONDecodeError as e:
            # ✓ FIXED: Log the actual content and re-raise
            self.logger.error(f"❌ Failed to parse JSON from vision response: {e}")
            self.logger.error(f"Response content (first 500 chars): {content[:500]}")
            raise ValueError(f"Invalid JSON in vision API response: {e}")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error parsing vision response: {e}")
            raise