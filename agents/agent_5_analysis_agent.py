import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from openai import OpenAI
from config.settings import (
    OPENAI_API_KEY,
    ANALYSIS_MODEL,
    COST_GPT4O_INPUT,
    COST_GPT4O_OUTPUT
)
from config.prompts import format_analysis_prompt
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger

class AnalysisAgent:
    """Agent 5: Merges all data and creates timeline with edit suggestions"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("analysis_agent", project_id)
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    def execute(self, cursor_events: Dict, frame_descriptions: Dict,
                audio_transcript: Dict, video_metadata: Dict,
                config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze all data and create event timeline
        
        Args:
            cursor_events: From Agent 2
            frame_descriptions: From Agent 3
            audio_transcript: From Agent 4
            video_metadata: Video information
            config: Optional configuration overrides
            
        Returns:
            Result dictionary with event timeline and edit suggestions
        """
        self.logger.start("Starting comprehensive analysis")
        start_time = datetime.now()
        
        try:
            # Prepare data for LLM
            analysis_data = self._prepare_analysis_data(
                cursor_events,
                frame_descriptions,
                audio_transcript,
                video_metadata
            )
            
            # Build prompt
            prompt = format_analysis_prompt(
                cursor_events=json.dumps(analysis_data["cursor_summary"], indent=2),
                frame_descriptions=json.dumps(analysis_data["vision_summary"], indent=2),
                transcript=json.dumps(analysis_data["transcript_summary"], indent=2),
                silence_segments=json.dumps(analysis_data["silence_summary"], indent=2),
                video_metadata=json.dumps(video_metadata, indent=2)
            )
            
            # Call LLM
            self.logger.info("Calling LLM for analysis...")
            response = self.client.chat.completions.create(
                model=ANALYSIS_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert video editor analyzing screen recordings. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            # Parse response
            content = response.choices[0].message.content
            timeline_data = self._parse_timeline_response(content)
            
            # Calculate insights
            insights = self._calculate_insights(
                timeline_data.get("event_timeline", []),
                video_metadata.get("duration", 0)
            )
            
            # Build result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            tokens_used = response.usage.total_tokens
            estimated_cost = (
                response.usage.prompt_tokens * COST_GPT4O_INPUT +
                response.usage.completion_tokens * COST_GPT4O_OUTPUT
            )
            
            result = {
                "agent": "analysis_agent",
                "status": "success",
                "execution_time": execution_time,
                "event_timeline": timeline_data.get("event_timeline", []),
                "insights": insights,
                "api_usage": {
                    "total_tokens": tokens_used,
                    "estimated_cost_usd": round(estimated_cost, 4)
                }
            }
            
            # Save result
            self.file_manager.save_json(result, "event_timeline.json")
            
            self.logger.success(f"Created timeline with {len(result['event_timeline'])} events")
            return result
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                "agent": "analysis_agent",
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _prepare_analysis_data(self, cursor_events: Dict, frame_descriptions: Dict,
                               audio_transcript: Dict, video_metadata: Dict) -> Dict:
        """Prepare and summarize data for LLM analysis"""
        
        # Summarize cursor events
        cursor_summary = {
            "total_events": len(cursor_events.get("cursor_events", [])),
            "clicks": [],
            "hovers": [],
            "movements": []
        }
        
        for event in cursor_events.get("cursor_events", []):
            if event.get("action") == "click":
                cursor_summary["clicks"].append({
                    "timestamp": event["timestamp"],
                    "position": event.get("center")
                })
            elif event.get("action") == "hover":
                cursor_summary["hovers"].append({
                    "timestamp": event["timestamp"],
                    "position": event.get("center")
                })
        
        # Summarize vision descriptions
        vision_summary = []
        for desc in frame_descriptions.get("descriptions", []):
            vision_summary.append({
                "timestamp": desc["timestamp"],
                "ui_elements": [e.get("type") for e in desc.get("ui_elements", [])],
                "cursor_on": desc.get("cursor_on"),
                "action": desc.get("action"),
                "page_state": desc.get("page_state"),
                "context": desc.get("context", "")[:200]  # Limit context length
            })
        
        # Summarize transcript
        transcript_summary = {
            "has_audio": len(audio_transcript.get("transcript", {}).get("segments", [])) > 0,
            "segments": []
        }
        
        for seg in audio_transcript.get("transcript", {}).get("segments", [])[:20]:  # Limit to 20 segments
            transcript_summary["segments"].append({
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"][:100]  # Limit text length
            })
        
        # Summarize silences
        silence_summary = []
        for silence in audio_transcript.get("silence_segments", []):
            if silence["duration"] > 1.0:  # Only include significant silences
                silence_summary.append({
                    "start": silence["start"],
                    "end": silence["end"],
                    "duration": silence["duration"],
                    "type": silence["type"]
                })
        
        return {
            "cursor_summary": cursor_summary,
            "vision_summary": vision_summary,
            "transcript_summary": transcript_summary,
            "silence_summary": silence_summary
        }
    
    def _parse_timeline_response(self, content: str) -> Dict:
        """Parse JSON from analysis LLM response"""
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
        
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                data = json.loads(json_str)
            
                # Validate required fields
                if not data.get("timeline"):
                    self.logger.warning("Analysis response missing timeline field")
                if not data.get("edit_suggestions"):
                    data["edit_suggestions"] = []
                
                return data
            
            # ✓ FIXED: Fail loudly
            self.logger.error(f"❌ No JSON found in analysis response. Raw content:\n{content[:500]}")
            raise ValueError("Analysis response did not contain valid JSON")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Invalid JSON in analysis response: {e}")
            self.logger.error(f"Response content (first 500 chars): {content[:500]}")
            raise ValueError(f"JSON parsing error in analysis: {e}")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in timeline parsing: {e}")
            raise
    
    def _calculate_insights(self, timeline: List[Dict], total_duration: float) -> Dict:
        """Calculate statistics about the timeline"""
        
        total_clicks = sum(1 for e in timeline if e.get("type") == "click")
        total_page_transitions = sum(1 for e in timeline if e.get("type") == "page_load")
        
        # Count suggested edits
        suggested_cuts = sum(1 for e in timeline 
                           if e.get("suggested_edit", {}).get("action") == "cut")
        suggested_zooms = sum(1 for e in timeline 
                            if e.get("suggested_edit", {}).get("action") == "zoom")
        suggested_highlights = sum(1 for e in timeline 
                                  if e.get("suggested_edit", {}).get("action") == "highlight")
        
        # Calculate silence to remove
        removable_silence = sum(
            e.get("end_timestamp", e.get("timestamp")) - e.get("timestamp")
            for e in timeline
            if e.get("suggested_edit", {}).get("action") == "cut"
        )
        
        # Estimate edited duration
        estimated_edited_duration = total_duration - removable_silence
        
        return {
            "total_clicks": total_clicks,
            "total_page_transitions": total_page_transitions,
            "total_silence_duration": round(removable_silence, 2),
            "removable_silence": round(removable_silence, 2),
            "loading_screens": 0,  # TODO: Detect from vision analysis
            "suggested_cuts": suggested_cuts,
            "suggested_zooms": suggested_zooms,
            "suggested_highlights": suggested_highlights,
            "original_duration": round(total_duration, 2),
            "estimated_edited_duration": round(max(0, estimated_edited_duration), 2)
        }