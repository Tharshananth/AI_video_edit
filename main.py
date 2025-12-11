#!/usr/bin/env python3
"""
AI-Powered Screen Recording Editor - Main Entry Point
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from utils.project_manager import ProjectManager
from utils.logger import setup_logger
from config.settings import OPENAI_API_KEY

logger = setup_logger("main")

def check_dependencies():
    """Check if all required dependencies are available"""
    errors = []
    
    # Check FFmpeg
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        if result.returncode != 0:
            errors.append("FFmpeg not found or not working")
    except FileNotFoundError:
        errors.append("FFmpeg not installed. Install with: sudo apt install ffmpeg (Linux) or brew install ffmpeg (Mac)")
    
    # Check OpenAI API key
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not set in .env file")
    
    # Check critical Python packages
    try:
        import cv2
        import openai
        import moviepy
    except ImportError as e:
        errors.append(f"Missing Python package: {e.name}. Run: pip install -r requirements.txt")
    
    if errors:
        logger.error("Dependency check failed:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info("✓ All dependencies OK")
    return True

def process_video(video_path: str, project_id: Optional[str] = None, **kwargs):
    """
    Process a video through the entire pipeline
    
    Args:
        video_path: Path to input video
        project_id: Optional custom project ID
        **kwargs: Additional configuration options
    """
    try:
        logger.info("=" * 60)
        logger.info("AI-POWERED VIDEO EDITOR")
        logger.info("=" * 60)
        
        # Verify video exists
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error(f"Video file not found: {video_path}")
            return False
        
        logger.info(f"Input video: {video_file.name}")
        logger.info(f"File size: {video_file.stat().st_size / (1024*1024):.2f} MB")
        
        # Create project
        pm = ProjectManager()
        project = pm.create_project(str(video_file), user_id=kwargs.get('user_id', 'default'))
        
        if not project:
            logger.error("Failed to create project")
            return False
        
        project_id = project['project_id']
        logger.info(f"Created project: {project_id}")
        
        # Run the full pipeline with LangGraph
        logger.info("\n" + "="*60)
        logger.info("PIPELINE EXECUTION")
        logger.info("="*60)
        
        # Import and execute the pipeline
        from orchestration.graph_builder import process_video as run_pipeline
        
        # Prepare configuration
        config = {
            'fps': kwargs.get('fps'),
            'max_frames': kwargs.get('max_frames'),
            'narration_style': kwargs.get('narration_style', 'professional'),
            'keep_original_audio': kwargs.get('keep_audio', False),
            'pacing': kwargs.get('pacing', 'medium')
        }
        
        # Execute pipeline
        logger.info("⏳ Running AI-powered editing pipeline...")
        result = run_pipeline(project_id, project['video_path'], **config)
        
        if result['status'] != 'complete':
            logger.error(f"Pipeline failed: {', '.join(result['errors'])}")
            return False
        
        logger.info("\n" + "="*60)
        logger.info("✓ PROCESSING COMPLETE!")
        logger.info("="*60)
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Output: projects/{project_id}/output/final_video.mp4")
        
        # Show cost summary
        status = pm.get_project_status(project_id)
        if status:
            cost = status['cost']
            logger.info(f"\nCost Summary:")
            logger.info(f"  Total tokens: {cost['total_tokens']:,}")
            logger.info(f"  Estimated cost: ${cost['total_cost_usd']:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return False

def list_projects(user_id: str = "default"):
    """List all projects"""
    pm = ProjectManager()
    projects = pm.list_user_projects(user_id)
    
    if not projects:
        logger.info("No projects found")
        return
    
    logger.info(f"\nFound {len(projects)} project(s):\n")
    logger.info(f"{'ID':<38} {'Video':<30} {'Status':<15} {'Created':<20}")
    logger.info("-" * 110)
    
    for project in projects:
        logger.info(
            f"{project['project_id']:<38} "
            f"{project['video_name']:<30} "
            f"{project['status']:<15} "
            f"{project['created_at']:<20}"
        )

def show_status(project_id: str):
    """Show detailed project status"""
    pm = ProjectManager()
    status = pm.get_project_status(project_id)
    
    if not status:
        logger.error(f"Project not found: {project_id}")
        return
    
    project = status['project']
    stages = status['stages']
    cost = status['cost']
    disk = status['disk_usage']
    
    logger.info("\n" + "=" * 60)
    logger.info("PROJECT STATUS")
    logger.info("=" * 60)
    logger.info(f"Project ID: {project['project_id']}")
    logger.info(f"Video: {project['video_name']}")
    logger.info(f"Status: {project['status']}")
    logger.info(f"Current Stage: {project['current_stage']}")
    logger.info(f"Duration: {project['duration_seconds']:.1f}s")
    logger.info(f"Resolution: {project['resolution']}")
    
    logger.info(f"\nPipeline Stages ({len(stages)}):")
    for stage in stages:
        status_icon = "✓" if stage['status'] == 'completed' else "✗" if stage['status'] == 'failed' else "⏳"
        logger.info(f"  {status_icon} {stage['stage_name']:<20} {stage['status']:<12} {stage.get('duration_seconds', 0):.2f}s")
    
    logger.info(f"\nCost Summary:")
    logger.info(f"  Total tokens: {cost['total_tokens']:,}")
    logger.info(f"  Total cost: ${cost['total_cost_usd']:.2f}")
    
    logger.info(f"\nDisk Usage:")
    logger.info(f"  Input: {disk['input']:.2f} MB")
    logger.info(f"  Frames: {disk['frames']:.2f} MB")
    logger.info(f"  Output: {disk['output']:.2f} MB")
    logger.info(f"  Total: {disk['total']:.2f} MB")

def delete_project(project_id: str):
    """Delete a project"""
    pm = ProjectManager()
    
    # Confirm deletion
    response = input(f"Delete project {project_id}? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        logger.info("Deletion cancelled")
        return
    
    if pm.delete_project(project_id):
        logger.info(f"✓ Project {project_id} deleted")
    else:
        logger.error(f"Failed to delete project {project_id}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI-Powered Screen Recording Editor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a video
  python main.py process video.mp4
  
  # List all projects
  python main.py list
  
  # Check project status
  python main.py status <project-id>
  
  # Delete a project
  python main.py delete <project-id>
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process a video')
    process_parser.add_argument('video', help='Path to video file')
    process_parser.add_argument('--project-id', help='Custom project ID')
    process_parser.add_argument('--user-id', default='default', help='User ID')
    process_parser.add_argument('--fps', type=float, help='Frame extraction rate')
    process_parser.add_argument('--max-frames', type=int, help='Maximum frames to extract')
    process_parser.add_argument('--narration-style', choices=['professional', 'casual', 'technical'],
                              default='professional', help='Narration style')
    process_parser.add_argument('--keep-audio', action='store_true', help='Keep original audio')
    process_parser.add_argument('--review', action='store_true', help='Enable human review checkpoint')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all projects')
    list_parser.add_argument('--user-id', default='default', help='User ID')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show project status')
    status_parser.add_argument('project_id', help='Project ID')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a project')
    delete_parser.add_argument('project_id', help='Project ID')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Delete old projects')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Delete projects older than N days')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Check dependencies for process command
    if args.command == 'process':
        if not check_dependencies():
            return 1
    
    # Execute command
    try:
        if args.command == 'process':
            success = process_video(
                args.video,
                project_id=args.project_id,
                user_id=args.user_id,
                fps=args.fps,
                max_frames=args.max_frames,
                narration_style=args.narration_style,
                keep_audio=args.keep_audio,
                review=args.review
            )
            return 0 if success else 1
            
        elif args.command == 'list':
            list_projects(args.user_id)
            return 0
            
        elif args.command == 'status':
            show_status(args.project_id)
            return 0
            
        elif args.command == 'delete':
            delete_project(args.project_id)
            return 0
            
        elif args.command == 'cleanup':
            pm = ProjectManager()
            count = pm.cleanup_old_projects(args.days)
            logger.info(f"Cleaned up {count} old projects")
            return 0
            
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())