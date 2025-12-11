"""
MoviePy processor for advanced video effects (zoom, highlights, overlays)
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

try:
    from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
    from moviepy.video.fx.all import crop, resize
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

from utils.logger import setup_logger

logger = setup_logger("moviepy_processor")


class MoviePyProcessor:
    """Handles MoviePy operations for advanced video effects"""
    
    def __init__(self, render_dir: Path):
        if not MOVIEPY_AVAILABLE:
            raise ImportError("MoviePy not installed. Install: pip install moviepy")
        
        self.render_dir = render_dir
        self.render_dir.mkdir(exist_ok=True)
    
    def apply_zoom_effect(self, video_path: str, zoom_instructions: List[Dict],
                         output_path: Path) -> bool:
        """
        Apply zoom effects to video
        
        Args:
            video_path: Input video path
            zoom_instructions: List of zoom instructions with timestamps
            output_path: Output path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            clip = VideoFileClip(video_path)
            
            # Sort zoom instructions by timestamp
            zooms = sorted(zoom_instructions, key=lambda x: x.get('start', 0))
            
            # Build list of subclips
            subclips = []
            current_time = 0.0
            
            for zoom in zooms:
                start = zoom.get('start', 0)
                end = zoom.get('end', start + 0.5)
                bbox = zoom.get('params', {}).get('target_bbox', [0, 0, 100, 100])
                scale = zoom.get('params', {}).get('zoom_scale', 1.3)
                
                # Add normal segment before zoom
                if current_time < start:
                    subclips.append(clip.subclip(current_time, start))
                
                # Apply zoom effect
                zoom_clip = self._create_zoom_clip(clip, start, end, bbox, scale)
                subclips.append(zoom_clip)
                
                current_time = end
            
            # Add remaining normal segment
            if current_time < clip.duration:
                subclips.append(clip.subclip(current_time, clip.duration))
            
            # Concatenate all clips
            from moviepy.editor import concatenate_videoclips
            final_clip = concatenate_videoclips(subclips)
            
            # Write output
            final_clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                preset='medium'
            )
            
            # Cleanup
            clip.close()
            final_clip.close()
            
            logger.info(f"Applied {len(zooms)} zoom effects")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply zoom effects: {e}", exc_info=True)
            return False
    
    def _create_zoom_clip(self, clip: VideoFileClip, start: float, end: float,
                         bbox: List[int], scale: float):
        """Create a zoomed clip segment"""
        try:
            # Extract subclip
            subclip = clip.subclip(start, end)
            
            # Get video dimensions
            w, h = clip.size
            
            # Calculate crop region
            x1, y1, x2, y2 = bbox
            crop_w = x2 - x1
            crop_h = y2 - y1
            
            # Ensure crop region is valid
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(x1 + 1, min(x2, w))
            y2 = max(y1 + 1, min(y2, h))
            
            # Apply crop and resize
            cropped = crop(subclip, x1=x1, y1=y1, x2=x2, y2=y2)
            zoomed = resize(cropped, (w, h))
            
            return zoomed
            
        except Exception as e:
            logger.error(f"Failed to create zoom clip: {e}")
            return subclip
    
    def apply_highlights(self, video_path: str, highlight_instructions: List[Dict],
                        output_path: Path) -> bool:
        """
        Apply highlight effects to video
        
        Args:
            video_path: Input video path
            highlight_instructions: List of highlight instructions
            output_path: Output path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            clip = VideoFileClip(video_path)
            
            # Generate highlight overlays
            overlays = []
            for highlight in highlight_instructions:
                start = highlight.get('start', 0)
                end = highlight.get('end', start + 0.3)
                bbox = highlight.get('params', {}).get('bbox', [0, 0, 100, 100])
                color = highlight.get('params', {}).get('color', '#4A90E2')
                
                overlay = self._create_highlight_overlay(
                    clip.size, bbox, color, start, end
                )
                if overlay:
                    overlays.append(overlay)
            
            # Composite video with overlays
            if overlays:
                final_clip = CompositeVideoClip([clip] + overlays)
            else:
                final_clip = clip
            
            # Write output
            final_clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                preset='medium'
            )
            
            # Cleanup
            clip.close()
            final_clip.close()
            
            logger.info(f"Applied {len(overlays)} highlights")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply highlights: {e}", exc_info=True)
            return False
    
    def _create_highlight_overlay(self, video_size: Tuple[int, int],
                                  bbox: List[int], color: str,
                                  start: float, end: float) -> Optional[ImageClip]:
        """Create a highlight glow overlay"""
        try:
            w, h = video_size
            x1, y1, x2, y2 = bbox
            
            # Create transparent image
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Parse color (hex to RGB)
            color_rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            # Draw glow effect (multiple rectangles with decreasing alpha)
            for i in range(5, 0, -1):
                alpha = int(50 / i)
                offset = i * 2
                draw.rectangle(
                    [x1 - offset, y1 - offset, x2 + offset, y2 + offset],
                    outline=(*color_rgb, alpha),
                    width=3
                )
            
            # Convert to numpy array
            img_array = np.array(img)
            
            # Create ImageClip
            overlay = ImageClip(img_array).set_duration(end - start).set_start(start)
            
            return overlay
            
        except Exception as e:
            logger.error(f"Failed to create highlight overlay: {e}")
            return None
    
    def apply_click_effects(self, video_path: str, click_instructions: List[Dict],
                           output_path: Path) -> bool:
        """
        Apply click ripple effects
        
        Args:
            video_path: Input video path
            click_instructions: List of click effect instructions
            output_path: Output path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            clip = VideoFileClip(video_path)
            
            # Generate click effect overlays
            overlays = []
            for click in click_instructions:
                timestamp = click.get('start', 0)
                position = click.get('params', {}).get('position', [100, 100])
                
                overlay = self._create_click_ripple(
                    clip.size, position, timestamp
                )
                if overlay:
                    overlays.append(overlay)
            
            # Composite
            if overlays:
                final_clip = CompositeVideoClip([clip] + overlays)
            else:
                final_clip = clip
            
            # Write output
            final_clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                preset='medium'
            )
            
            # Cleanup
            clip.close()
            final_clip.close()
            
            logger.info(f"Applied {len(overlays)} click effects")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply click effects: {e}", exc_info=True)
            return False
    
    def _create_click_ripple(self, video_size: Tuple[int, int],
                            position: List[int], timestamp: float) -> Optional[ImageClip]:
        """Create a click ripple effect"""
        try:
            w, h = video_size
            x, y = position
            
            # Create ripple animation frames
            frames = []
            duration = 0.4  # 400ms animation
            fps = 30
            num_frames = int(duration * fps)
            
            for frame_idx in range(num_frames):
                img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Calculate ripple radius
                progress = frame_idx / num_frames
                radius = int(30 * progress)
                alpha = int(255 * (1 - progress))
                
                # Draw ripple circle
                draw.ellipse(
                    [x - radius, y - radius, x + radius, y + radius],
                    outline=(255, 255, 255, alpha),
                    width=2
                )
                
                frames.append(np.array(img))
            
            # Create clip from frames
            def make_frame(t):
                frame_idx = int(t * fps)
                if frame_idx >= len(frames):
                    frame_idx = len(frames) - 1
                return frames[frame_idx]
            
            overlay = (ImageClip(make_frame, duration=duration)
                      .set_start(timestamp))
            
            return overlay
            
        except Exception as e:
            logger.error(f"Failed to create click ripple: {e}")
            return None