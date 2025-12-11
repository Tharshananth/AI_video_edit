import subprocess
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from openai import OpenAI
from pydub import AudioSegment
from pydub.silence import detect_silence

from config.settings import (
    OPENAI_API_KEY,
    WHISPER_MODEL,
    WHISPER_LANGUAGE,
    SILENCE_THRESHOLD_DB,
    MIN_SILENCE_DURATION,
    COST_WHISPER
)
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger

class AudioAgent:
    """Agent 4: Transcribes audio and detects silence segments"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("audio_agent", project_id)
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
    def execute(self, video_path: str, config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Extract and analyze audio from video
        
        Args:
            video_path: Path to input video
            config: Optional configuration overrides
            
        Returns:
            Result dictionary with transcription and silence analysis
        """
        self.logger.start("Starting audio analysis")
        start_time = datetime.now()
        
        try:
            # Merge config
            cfg = {
                "model": WHISPER_MODEL,
                "language": WHISPER_LANGUAGE,
                "detect_silences": True,
                "silence_threshold_db": SILENCE_THRESHOLD_DB,
                "min_silence_duration": MIN_SILENCE_DURATION
            }
            if config:
                cfg.update(config)
            
            # Extract audio from video
            audio_path = self._extract_audio(video_path)
            if not audio_path:
                raise Exception("Failed to extract audio from video")
            
            # Check if audio exists
            audio = AudioSegment.from_file(audio_path)
            audio_duration = len(audio) / 1000.0  # Convert to seconds
            
            if audio_duration < 0.1:
                self.logger.warning("No audio detected in video")
                return self._create_empty_result(start_time)
            
            # Transcribe audio
            transcript = self._transcribe_audio(audio_path, cfg)
            
            # Detect silence segments
            silence_segments = []
            audio_analysis = {}
            
            if cfg["detect_silences"]:
                silence_segments = self._detect_silence_segments(
                    audio_path, 
                    cfg["silence_threshold_db"],
                    cfg["min_silence_duration"]
                )
                audio_analysis = self._analyze_audio(transcript, silence_segments, audio_duration)
            
            # Build result
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            estimated_cost = (audio_duration / 60.0) * COST_WHISPER
            
            result = {
                "agent": "audio_agent",
                "status": "success",
                "execution_time": execution_time,
                "transcript": transcript,
                "silence_segments": silence_segments,
                "audio_analysis": audio_analysis,
                "api_usage": {
                    "audio_duration_minutes": round(audio_duration / 60.0, 2),
                    "estimated_cost_usd": round(estimated_cost, 4)
                }
            }
            
            # Save result
            self.file_manager.save_json(result, "audio_transcript.json")
            
            self.logger.success(f"Transcribed {audio_duration:.1f}s audio, cost: ${estimated_cost:.4f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Audio analysis failed: {e}", exc_info=True)
            return {
                "agent": "audio_agent",
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio track from video using FFmpeg"""
        try:
            output_path = self.file_manager.intermediate_dir / "audio.wav"
            
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # WAV format
                '-ar', '16000',  # 16kHz sample rate (good for speech)
                '-ac', '1',  # Mono
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                self.logger.error(f"FFmpeg failed: {result.stderr}")
                return None
            
            if not output_path.exists():
                return None
            
            self.logger.info(f"Extracted audio to {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"Audio extraction failed: {e}")
            return None
    
    def _transcribe_audio(self, audio_path: str, config: Dict) -> Dict:
        """Transcribe audio using OpenAI Whisper"""
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=config["model"],
                    file=audio_file,
                    language=config["language"],
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"]
                )
            
            # Parse response
            transcript = {
                "language": response.language,
                "duration": response.duration,
                "segments": []
            }
            
            # Add segments
            for segment in response.segments:
                segment_data = {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "words": []
                }
                
                # Add word-level timestamps if available
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        segment_data["words"].append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end
                        })
                
                transcript["segments"].append(segment_data)
            
            self.logger.info(f"Transcribed {len(transcript['segments'])} segments")
            return transcript
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            return {
                "language": config["language"],
                "duration": 0.0,
                "segments": []
            }
    
    def _detect_silence_segments(self, audio_path: str, threshold_db: int, 
                                min_duration: float) -> List[Dict]:
        """Detect silence segments in audio"""
        try:
            audio = AudioSegment.from_file(audio_path)
            
            # Detect silence (returns list of [start_ms, end_ms])
            silences = detect_silence(
                audio,
                min_silence_len=int(min_duration * 1000),  # Convert to ms
                silence_thresh=threshold_db
            )
            
            silence_segments = []
            total_duration = len(audio) / 1000.0
            
            for i, (start_ms, end_ms) in enumerate(silences):
                start_s = start_ms / 1000.0
                end_s = end_ms / 1000.0
                duration = end_s - start_s
                
                # Classify silence type
                if start_s < 1.0:
                    silence_type = "pre_speech"
                elif end_s > total_duration - 1.0:
                    silence_type = "post_speech"
                else:
                    silence_type = "pause"
                
                silence_segments.append({
                    "start": round(start_s, 3),
                    "end": round(end_s, 3),
                    "duration": round(duration, 3),
                    "type": silence_type
                })
            
            self.logger.info(f"Detected {len(silence_segments)} silence segments")
            return silence_segments
            
        except Exception as e:
            self.logger.error(f"Silence detection failed: {e}")
            return []
    
    def _analyze_audio(self, transcript: Dict, silence_segments: List[Dict], 
                      total_duration: float) -> Dict:
        """Analyze audio characteristics"""
        # Calculate speech duration
        speech_duration = 0.0
        for segment in transcript.get("segments", []):
            speech_duration += segment["end"] - segment["start"]
        
        # Calculate silence duration
        silence_duration = sum(s["duration"] for s in silence_segments)
        
        # Calculate ratios
        speech_to_silence_ratio = (
            speech_duration / silence_duration if silence_duration > 0 else float('inf')
        )
        
        # Calculate average pause
        pauses = [s for s in silence_segments if s["type"] == "pause"]
        avg_pause = (
            sum(p["duration"] for p in pauses) / len(pauses) if pauses else 0.0
        )
        
        # Find longest silence
        longest_silence = max([s["duration"] for s in silence_segments]) if silence_segments else 0.0
        
        # Determine speaking pace
        if transcript.get("segments"):
            words = sum(len(seg.get("words", [])) for seg in transcript["segments"])
            wpm = (words / speech_duration * 60) if speech_duration > 0 else 0
            
            if wpm < 100:
                pace = "slow"
            elif wpm > 160:
                pace = "fast"
            else:
                pace = "normal"
        else:
            pace = "unknown"
        
        return {
            "total_speech_duration": round(speech_duration, 2),
            "total_silence_duration": round(silence_duration, 2),
            "speech_to_silence_ratio": round(speech_to_silence_ratio, 2),
            "average_pause_duration": round(avg_pause, 2),
            "longest_silence": round(longest_silence, 2),
            "speaking_pace": pace
        }
    
    def _create_empty_result(self, start_time: datetime) -> Dict:
        """Create result for video with no audio"""
        return {
            "agent": "audio_agent",
            "status": "success",
            "execution_time": (datetime.now() - start_time).total_seconds(),
            "transcript": {
                "language": "none",
                "duration": 0.0,
                "segments": []
            },
            "silence_segments": [],
            "audio_analysis": {
                "total_speech_duration": 0.0,
                "total_silence_duration": 0.0,
                "speech_to_silence_ratio": 0.0,
                "average_pause_duration": 0.0,
                "longest_silence": 0.0,
                "speaking_pace": "none"
            },
            "api_usage": {
                "audio_duration_minutes": 0.0,
                "estimated_cost_usd": 0.0
            }
        }