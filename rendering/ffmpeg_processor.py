import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from config.settings import (
    VIDEO_CODEC,
    VIDEO_PRESET,
    VIDEO_BITRATE,
    VIDEO_CRF,
    AUDIO_CODEC,
    AUDIO_BITRATE,
    OUTPUT_FPS
)
from utils.logger import setup_logger

logger = setup_logger("ffmpeg_processor")

class FFmpegProcessor:
    """Handles FFmpeg operations for video editing"""
    
    def __init__(self, render_dir: Path):
        self.render_dir = render_dir
        self.render_dir.mkdir(exist_ok=True)
    
    def cut_segments(self, video_path: str, cuts: List[Dict]) -> List[str]:
        """
        Cut video into segments, removing unwanted parts
        
        Args:
            video_path: Input video path
            cuts: List of cut instructions
            
        Returns:
            List of segment file paths
        """
        segments = []
        
        # Build list of segments to keep
        keep_segments = self._calculate_keep_segments(video_path, cuts)
        
        for i, segment in enumerate(keep_segments):
            output_path = self.render_dir / f"segment_{i:03d}.mp4"
            
            if self._extract_segment(video_path, segment['start'], segment['end'], output_path):
                segments.append(str(output_path))
            else:
                logger.error(f"Failed to extract segment {i}")
        
        logger.info(f"Created {len(segments)} segments from cuts")
        return segments
    
    def _calculate_keep_segments(self, video_path: str, cuts: List[Dict]) -> List[Dict]:
        """Calculate segments to keep (inverse of cuts)"""
        # Get video duration
        duration = self._get_video_duration(video_path)
        
        # Sort cuts by start time
        cuts = sorted(cuts, key=lambda x: x.get('start', 0))
        
        keep_segments = []
        current_time = 0.0
        
        for cut in cuts:
            cut_start = cut.get('start', 0)
            cut_end = cut.get('end', cut_start)
            
            # If there's content before this cut, keep it
            if current_time < cut_start:
                keep_segments.append({
                    'start': current_time,
                    'end': cut_start
                })
            
            # Move past the cut
            current_time = max(current_time, cut_end)
        
        # Keep remaining content
        if current_time < duration:
            keep_segments.append({
                'start': current_time,
                'end': duration
            })
        
        return keep_segments
    
    def _extract_segment(self, video_path: str, start: float, end: float, 
                        output_path: Path) -> bool:
        """Extract a segment from video"""
        try:
            duration = end - start
            
            cmd = [
                'ffmpeg',
                '-y',
                '-ss', str(start),
                '-i', video_path,
                '-t', str(duration),
                '-c:v', VIDEO_CODEC,
                '-preset', VIDEO_PRESET,
                '-crf', str(VIDEO_CRF),
                '-c:a', AUDIO_CODEC,
                '-b:a', AUDIO_BITRATE,
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg segment extraction failed: {result.stderr}")
                return False
            
            return output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed to extract segment: {e}")
            return False
    
    def concatenate_segments(self, segments: List[str], output_path: Path) -> bool:
        """
        Concatenate multiple video segments
        
        Args:
            segments: List of segment file paths
            output_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            # Create concat file
            concat_file = self.render_dir / "concat_list.txt"
            
            with open(concat_file, 'w') as f:
                for segment in segments:
                    f.write(f"file '{segment}'\n")
            
            # Concatenate using FFmpeg
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg concatenation failed: {result.stderr}")
                return False
            
            logger.info(f"Concatenated {len(segments)} segments")
            return output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed to concatenate segments: {e}")
            return False
    
    def change_speed(self, video_path: str, speed: float, output_path: Path) -> bool:
        """
        Change video playback speed
        
        Args:
            video_path: Input video
            speed: Speed multiplier (1.5 = 1.5x faster)
            output_path: Output path
            
        Returns:
            True if successful
        """
        try:
            # Calculate PTS (Presentation TimeStamp) filter
            video_pts = 1.0 / speed
            audio_tempo = speed
            
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-filter_complex',
                f'[0:v]setpts={video_pts}*PTS[v];[0:a]atempo={audio_tempo}[a]',
                '-map', '[v]',
                '-map', '[a]',
                '-c:v', VIDEO_CODEC,
                '-preset', VIDEO_PRESET,
                '-crf', str(VIDEO_CRF),
                '-c:a', AUDIO_CODEC,
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg speed change failed: {result.stderr}")
                return False
            
            return output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed to change speed: {e}")
            return False
    
    def extract_audio(self, video_path: str, output_path: Path) -> bool:
        """Extract audio track from video"""
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Audio extraction failed: {result.stderr}")
                return False
            
            return output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            return False
    
    def replace_audio(self, video_path: str, audio_path: str, output_path: Path) -> bool:
        """
        Replace video audio track
        
        Args:
            video_path: Input video
            audio_path: New audio track
            output_path: Output path
            
        Returns:
            True if successful
        """
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',  # Copy video without re-encoding
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-c:a', AUDIO_CODEC,
                '-b:a', AUDIO_BITRATE,
                '-shortest',  # Match shortest stream
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Audio replacement failed: {result.stderr}")
                return False
            
            return output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed to replace audio: {e}")
            return False
    
    def mix_audio(self, video_path: str, audio_tracks: List[Dict], 
                 output_path: Path) -> bool:
        """
        Mix multiple audio tracks
        
        Args:
            video_path: Input video
            audio_tracks: List of {path, volume} dicts
            output_path: Output path
            
        Returns:
            True if successful
        """
        try:
            # Build filter complex for mixing
            inputs = ['-i', video_path]
            for track in audio_tracks:
                inputs.extend(['-i', track['path']])
            
            # Build amerge filter
            audio_inputs = ''.join([f'[{i+1}:a]' for i in range(len(audio_tracks))])
            filter_complex = f'{audio_inputs}amerge=inputs={len(audio_tracks)}[aout]'
            
            cmd = [
                'ffmpeg',
                '-y',
                *inputs,
                '-filter_complex', filter_complex,
                '-map', '0:v',
                '-map', '[aout]',
                '-c:v', 'copy',
                '-c:a', AUDIO_CODEC,
                '-b:a', AUDIO_BITRATE,
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Audio mixing failed: {result.stderr}")
                return False
            
            return output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed to mix audio: {e}")
            return False
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data['format']['duration'])
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get duration: {e}")
            return 0.0
    
    def final_encode(self, video_path: str, output_path: Path) -> bool:
        """
        Final high-quality encode
        
        Args:
            video_path: Input video
            output_path: Final output path
            
        Returns:
            True if successful
        """
        try:
            cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-c:v', VIDEO_CODEC,
                '-preset', VIDEO_PRESET,
                '-crf', str(VIDEO_CRF),
                '-b:v', VIDEO_BITRATE,
                '-r', str(OUTPUT_FPS),
                '-c:a', AUDIO_CODEC,
                '-b:a', AUDIO_BITRATE,
                '-movflags', '+faststart',  # Enable streaming
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode != 0:
                logger.error(f"Final encode failed: {result.stderr}")
                return False
            
            logger.info(f"Final encode complete: {output_path}")
            return output_path.exists()
            
        except Exception as e:
            logger.error(f"Failed final encode: {e}")
            return False