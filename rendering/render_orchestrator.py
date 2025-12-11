from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from config.settings import OPENAI_API_KEY, TTS_MODEL
from utils.file_manager import ProjectFileManager
from utils.logger import AgentLogger
from rendering.ffmpeg_processor import FFmpegProcessor

class RenderOrchestrator:
    """Orchestrates the video rendering process"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.file_manager = ProjectFileManager(project_id)
        self.logger = AgentLogger("render", project_id)
        self.ffmpeg = FFmpegProcessor(self.file_manager.render_dir)
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def execute(self, video_path: str, edit_plan: Dict, 
                narration_script: Dict, tts_config: Dict) -> Dict[str, Any]:
        """
        Execute rendering pipeline
        
        Args:
            video_path: Original video path
            edit_plan: Edit plan from Agent 6
            narration_script: Narration script from Agent 6
            tts_config: TTS configuration
            
        Returns:
            Result dictionary with final video path
        """
        self.logger.start("Starting video rendering")
        start_time = datetime.now()
        
        try:
            # Step 1: Apply cuts (if any)
            current_video = video_path
            cuts = [e for e in edit_plan.get('timeline', []) if e['action'] == 'cut']
            
            if cuts:
                self.logger.info(f"Applying {len(cuts)} cuts...")
                segments = self.ffmpeg.cut_segments(video_path, cuts)
                
                if segments:
                    concat_path = self.file_manager.render_dir / "video_cut.mp4"
                    if self.ffmpeg.concatenate_segments(segments, concat_path):
                        current_video = str(concat_path)
                        self.logger.info("Cuts applied successfully")
            
            # Step 2: Generate TTS narration
            narration_path = None
            if narration_script.get('full_script_text'):
                self.logger.info("Generating TTS narration...")
                narration_path = self._generate_tts_narration(
                    narration_script.get('full_script_text'),
                    tts_config
                )
            
            # Step 3: Replace/mix audio
            if narration_path:
                self.logger.info("Replacing audio with narration...")
                audio_replaced_path = self.file_manager.render_dir / "video_with_narration.mp4"
                
                if self.ffmpeg.replace_audio(current_video, narration_path, audio_replaced_path):
                    current_video = str(audio_replaced_path)
                    self.logger.info("Audio replaced successfully")
            
            # Step 4: Final encode
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
                        "narration_generated": narration_path is not None,
                        "file_size_mb": final_output.stat().st_size / (1024 * 1024)
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
            self.logger.error(f"TTS generation failed: {e}")
            return None
    
    def _cleanup_temp_files(self):
        """Clean up temporary render files"""
        try:
            import shutil
            temp_files = list(self.file_manager.render_dir.glob("*.mp4"))
            temp_files.extend(self.file_manager.render_dir.glob("*.mp3"))
            temp_files.extend(self.file_manager.render_dir.glob("*.txt"))
            
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except:
                    pass
            
            self.logger.debug("Cleaned up temporary files")
            
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")