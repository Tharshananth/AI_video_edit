from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from config.settings import OPENAI_API_KEY, TTS_MODEL
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger
from rendering.ffmpeg_processor import FFmpegProcessor
from rendering.moviepy_processor import MoviePyProcessor

class RenderOrchestrator:
    """Orchestrates the complete video rendering process"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("render", project_id)
        self.ffmpeg = FFmpegProcessor(self.file_manager.render_dir)
        try:
            self.moviepy = MoviePyProcessor(self.file_manager.render_dir)
        except ImportError:
            self.logger.warning("MoviePy not available, advanced effects disabled")
            self.moviepy = None
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def execute(self, video_path: str, edit_plan: Dict, 
                narration_script: Dict, tts_config: Dict) -> Dict[str, Any]:
        """
        Execute complete rendering pipeline
        
        Pipeline:
        1. Apply cuts (FFmpeg)
        2. Apply speed changes (FFmpeg)
        3. Apply zoom effects (MoviePy)
        4. Apply highlights (MoviePy)
        5. Apply click effects (MoviePy)
        6. Generate TTS narration (OpenAI)
        7. Replace/mix audio (FFmpeg)
        8. Final encode (FFmpeg)
        
        Args:
            video_path: Original video path
            edit_plan: Edit plan from Agent 6
            narration_script: Narration script from Agent 6
            tts_config: TTS configuration
            
        Returns:
            Result dictionary with final video path
        """
        self.logger.start("Starting video rendering pipeline")
        start_time = datetime.now()
        
        try:
            current_video = video_path
            timeline = edit_plan.get('timeline', [])
            
            # ================================================================
            # STEP 1: Apply Cuts (FFmpeg)
            # ================================================================
            cuts = [e for e in timeline if e['action'] == 'cut']
            
            if cuts:
                self.logger.info(f"Applying {len(cuts)} cuts...")
                segments = self.ffmpeg.cut_segments(video_path, cuts)
                
                if segments:
                    concat_path = self.file_manager.render_dir / "01_video_cut.mp4"
                    if self.ffmpeg.concatenate_segments(segments, concat_path):
                        current_video = str(concat_path)
                        self.logger.info("✓ Cuts applied successfully")
                    else:
                        self.logger.warning("Cut concatenation failed, continuing with original")
            
            # ================================================================
            # STEP 2: Apply Speed Changes (FFmpeg)
            # ================================================================
            speed_changes = [e for e in timeline if e['action'] == 'speed']
            
            if speed_changes:
                self.logger.info(f"Applying {len(speed_changes)} speed changes...")
                speed_path = self.file_manager.render_dir / "02_video_speed.mp4"
                
                # For simplicity, apply first speed change only
                # Full implementation would need segment-based speed changes
                if speed_changes:
                    speed = speed_changes[0].get('params', {}).get('speed_multiplier', 1.0)
                    if self.ffmpeg.change_speed(current_video, speed, speed_path):
                        current_video = str(speed_path)
                        self.logger.info("✓ Speed changes applied")
            
            # ================================================================
            # STEP 3: Apply Zoom Effects (MoviePy)
            # ================================================================
            zooms = [e for e in timeline if e['action'] == 'zoom']
            
            if zooms and self.moviepy:
                self.logger.info(f"Applying {len(zooms)} zoom effects...")
                zoom_path = self.file_manager.render_dir / "03_video_zoom.mp4"
                
                if self.moviepy.apply_zoom_effect(current_video, zooms, zoom_path):
                    current_video = str(zoom_path)
                    self.logger.info("✓ Zoom effects applied")
                else:
                    self.logger.warning("Zoom effects failed, continuing without")
            
            # ================================================================
            # STEP 4: Apply Highlights (MoviePy)
            # ================================================================
            highlights = [e for e in timeline if e['action'] == 'highlight']
            
            if highlights and self.moviepy:
                self.logger.info(f"Applying {len(highlights)} highlights...")
                highlight_path = self.file_manager.render_dir / "04_video_highlight.mp4"
                
                if self.moviepy.apply_highlights(current_video, highlights, highlight_path):
                    current_video = str(highlight_path)
                    self.logger.info("✓ Highlights applied")
                else:
                    self.logger.warning("Highlights failed, continuing without")
            
            # ================================================================
            # STEP 5: Apply Click Effects (MoviePy)
            # ================================================================
            clicks = [e for e in timeline if e['action'] == 'click_effect']
            
            if clicks and self.moviepy:
                self.logger.info(f"Applying {len(clicks)} click effects...")
                click_path = self.file_manager.render_dir / "05_video_clicks.mp4"
                
                if self.moviepy.apply_click_effects(current_video, clicks, click_path):
                    current_video = str(click_path)
                    self.logger.info("✓ Click effects applied")
                else:
                    self.logger.warning("Click effects failed, continuing without")
            
            # ================================================================
            # STEP 6: Generate TTS Narration (OpenAI)
            # ================================================================
            narration_path = None
            script_text = narration_script.get('full_script_text', '')
            
            if script_text:
                self.logger.info("Generating TTS narration...")
                narration_path = self._generate_tts_narration(script_text, tts_config)
                
                if narration_path:
                    self.logger.info("✓ TTS narration generated")
                else:
                    self.logger.warning("TTS generation failed, continuing without narration")
            
            # ================================================================
            # STEP 7: Replace/Mix Audio (FFmpeg)
            # ================================================================
            if narration_path:
                self.logger.info("Replacing audio with narration...")
                audio_path = self.file_manager.render_dir / "06_video_with_audio.mp4"
                
                if self.ffmpeg.replace_audio(current_video, narration_path, audio_path):
                    current_video = str(audio_path)
                    self.logger.info("✓ Audio replaced successfully")
                else:
                    self.logger.warning("Audio replacement failed, continuing with original audio")
            
            # ================================================================
            # STEP 8: Final Encode (FFmpeg)
            # ================================================================
            self.logger.info("Final encoding...")
            final_output = self.file_manager.output_dir / "final_video.mp4"
            
            if self.ffmpeg.final_encode(current_video, final_output):
                self.logger.success(f"Video rendered successfully: {final_output}")
                
                # Cleanup temporary files
                self._cleanup_temp_files()
                
                # Build result
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                return {
                    "status": "success",
                    "video_path": str(final_output),
                    "execution_time": execution_time,
                    "metadata": {
                        "cuts_applied": len(cuts),
                        "zooms_applied": len(zooms),
                        "highlights_applied": len(highlights),
                        "click_effects_applied": len(clicks),
                        "narration_generated": narration_path is not None,
                        "file_size_mb": round(final_output.stat().st_size / (1024 * 1024), 2)
                    }
                }
            else:
                raise Exception("Final encoding failed")
            
        except Exception as e:
            self.logger.error(f"Rendering failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _generate_tts_narration(self, script_text: str, tts_config: Dict) -> Optional[str]:
        """Generate TTS audio from script"""
        try:
            output_path = self.file_manager.render_dir / "narration.mp3"
            
            # Call OpenAI TTS API
            response = self.client.audio.speech.create(
                model=tts_config.get('model', TTS_MODEL),
                voice=tts_config.get('voice', 'alloy'),
                input=script_text,
                speed=tts_config.get('speed', 1.0)
            )
            
            # Save audio
            response.stream_to_file(str(output_path))
            
            self.logger.info(f"Generated TTS narration: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"TTS generation failed: {e}", exc_info=True)
            return None
    
    def _cleanup_temp_files(self):
        """Clean up temporary render files"""
        try:
            temp_patterns = [
                "01_*.mp4", "02_*.mp4", "03_*.mp4",
                "04_*.mp4", "05_*.mp4", "06_*.mp4",
                "segment_*.mp4", "*.txt", "narration.mp3"
            ]
            
            for pattern in temp_patterns:
                for temp_file in self.file_manager.render_dir.glob(pattern):
                    try:
                        temp_file.unlink()
                    except:
                        pass
            
            self.logger.debug("Cleaned up temporary files")
            
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")