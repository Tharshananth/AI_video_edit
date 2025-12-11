import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from openai import OpenAI
from config.settings import (
    OPENAI_API_KEY,
    ANALYSIS_MODEL,
    TTS_MODEL,
    TTS_VOICE,
    COST_GPT4O_INPUT,
    COST_GPT4O_OUTPUT,
    COST_TTS
)
from config.prompts import format_script_planner_prompt
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger

class ScriptPlannerAgent:
    """Agent 6: Generates narration script and detailed edit plan"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("script_planner", project_id)
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    def execute(self, event_timeline: Dict, original_transcript: Dict,
                video_metadata: Dict, user_preferences: Optional[Dict] = None,
                config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate narration script and edit plan
        
        Args:
            event_timeline: From Agent 5
            original_transcript: From Agent 4
            video_metadata: Video information
            user_preferences: User preferences for narration style
            config: Optional configuration overrides
            
        Returns:
            Result dictionary with script and edit plan
        """
        self.logger.start("Generating narration script and edit plan")
        start_time = datetime.now()
        
        try:
            # Set defaults
            if not user_preferences:
                user_preferences = {}
            
            user_prefs = {
                "narration_style": user_preferences.get("narration_style", "professional"),
                "keep_original_audio": user_preferences.get("keep_original_audio", False),
                "music": user_preferences.get("music", False),
                "pacing": user_preferences.get("pacing", "medium")
            }
            
            # Build prompt
            prompt = format_script_planner_prompt(
                event_timeline=json.dumps(event_timeline.get("event_timeline", []), indent=2),
                original_transcript=json.dumps(original_transcript.get("transcript", {}), indent=2),
                video_metadata=json.dumps(video_metadata, indent=2),
                user_preferences=json.dumps(user_prefs, indent=2)
            )
            
            # Call LLM
            self.logger.info("Generating script and edit plan with LLM...")
            response = self.client.chat.completions.create(
                model=ANALYSIS_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert video editor and scriptwriter. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,  # Slightly higher for creative script writing
                max_tokens=4000
            )
            
            # Parse response
            content = response.choices[0].message.content
            script_data = self._parse_script_response(content)
            
            # Validate and fix edit plan
            edit_plan = self._validate_edit_plan(script_data.get("edit_plan", {}))
            narration_script = script_data.get("narration_script", {})
            
            # Calculate costs
            script_text = narration_script.get("full_script_text", "")
            tts_cost = len(script_text) * COST_TTS
            
            # Build result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            tokens_used = response.usage.total_tokens
            llm_cost = (
                response.usage.prompt_tokens * COST_GPT4O_INPUT +
                response.usage.completion_tokens * COST_GPT4O_OUTPUT
            )
            
            result = {
                "agent": "script_edit_planner",
                "status": "success",
                "execution_time": execution_time,
                "narration_script": narration_script,
                "edit_plan": edit_plan,
                "tts_config": {
                    "service": "openai",
                    "model": TTS_MODEL,
                    "voice": TTS_VOICE,
                    "speed": 1.0,
                    "estimated_cost_usd": round(tts_cost, 4)
                },
                "api_usage": {
                    "total_tokens": tokens_used,
                    "estimated_cost_usd": round(llm_cost, 4)
                }
            }
            
            # Save results
            self.file_manager.save_json(result, "edit_plan.json", subdir="output")
            self.file_manager.save_text(
                script_text,
                "narration_script.txt",
                subdir="output"
            )
            
            self.logger.success(f"Generated script ({len(script_text)} chars) and edit plan ({len(edit_plan.get('timeline', []))} edits)")
            return result
            
        except Exception as e:
            self.logger.error(f"Script planning failed: {e}", exc_info=True)
            return {
                "agent": "script_edit_planner",
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _parse_script_response(self, content: str) -> Dict:
        """Parse JSON from script planner response"""
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
        
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)
            else:
                self.logger.error(f"❌ No JSON found in script response. Raw content:\n{content[:500]}")
                raise ValueError("Script response did not contain valid JSON")
            
            # Validate required fields
            if not data.get("narration_script"):
                self.logger.warning("Script response missing narration_script field")
            if not data.get("edit_plan"):
                data["edit_plan"] = []
            
            return data
        
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Invalid JSON in script response: {e}")
            self.logger.error(f"Response content (first 500 chars): {content[:500]}")
            raise ValueError(f"JSON parsing error in script planner: {e}")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in script parsing: {e}")
            raise
    def _create_fallback_script(self) -> Dict:
        """Create a basic fallback script if LLM fails"""
        return {
            "narration_script": {
                "style": "professional",
                "total_duration": 0.0,
                "segments": [],
                "full_script_text": "Welcome to this tutorial. Let's walk through the steps."
            },
            "edit_plan": {
                "timeline": [],
                "summary": {
                    "total_cuts": 0,
                    "total_zooms": 0,
                    "total_highlights": 0,
                    "total_effects": 0,
                    "original_duration": 0.0,
                    "final_duration": 0.0,
                    "time_saved": 0.0
                }
            }
        }
    
    def _validate_edit_plan(self, edit_plan: Dict) -> Dict:
        """Validate and fix edit plan structure"""
        if not edit_plan:
            edit_plan = {"timeline": [], "summary": {}}
        
        # Ensure timeline exists
        if "timeline" not in edit_plan:
            edit_plan["timeline"] = []
        
        # Validate each edit action
        validated_timeline = []
        for i, edit in enumerate(edit_plan.get("timeline", [])):
            # Ensure required fields
            if "action" not in edit or "start" not in edit:
                self.logger.warning(f"Skipping invalid edit at index {i}")
                continue
            
            # Ensure params exist
            if "params" not in edit:
                edit["params"] = {}
            
            # Add ID if missing
            if "id" not in edit:
                edit["id"] = i
            
            validated_timeline.append(edit)
        
        # Sort by timestamp
        validated_timeline.sort(key=lambda x: x.get("start", 0))
        
        # Calculate summary
        summary = {
            "total_cuts": sum(1 for e in validated_timeline if e["action"] == "cut"),
            "total_zooms": sum(1 for e in validated_timeline if e["action"] == "zoom"),
            "total_highlights": sum(1 for e in validated_timeline if e["action"] == "highlight"),
            "total_effects": sum(1 for e in validated_timeline if e["action"] == "click_effect"),
            "original_duration": edit_plan.get("summary", {}).get("original_duration", 0.0),
            "final_duration": edit_plan.get("summary", {}).get("final_duration", 0.0),
            "time_saved": edit_plan.get("summary", {}).get("time_saved", 0.0)
        }
        
        return {
            "timeline": validated_timeline,
            "summary": summary
        }