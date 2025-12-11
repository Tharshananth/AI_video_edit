#!/usr/bin/env python3
"""
Download and prepare ML models for cursor detection
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import MODELS_DIR, YOLO_MODEL_SIZE

def download_yolo_model():
    """Download YOLOv8 model"""
    print("=" * 60)
    print("Downloading YOLOv8 Model")
    print("=" * 60)
    print()
    
    try:
        from ultralytics import YOLO
        
        # Ensure models directory exists
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Download model (YOLO will handle this automatically)
        model_name = f"yolov8{YOLO_MODEL_SIZE}.pt"
        print(f"Downloading {model_name}...")
        
        model = YOLO(model_name)
        
        print(f"✓ Model downloaded successfully")
        print(f"✓ Saved to: {MODELS_DIR}")
        print()
        print("Note: This is a general object detection model.")
        print("For best cursor detection results, consider training a custom model on cursor images.")
        print()
        
        return True
        
    except ImportError:
        print("✗ ultralytics not installed")
        print("Install with: pip install ultralytics")
        return False
        
    except Exception as e:
        print(f"✗ Failed to download model: {e}")
        return False

def verify_installation():
    """Verify model installation"""
    print("=" * 60)
    print("Verifying Installation")
    print("=" * 60)
    print()
    
    try:
        from ultralytics import YOLO
        import torch
        
        # Check PyTorch
        print(f"✓ PyTorch version: {torch.__version__}")
        
        # Check CUDA
        if torch.cuda.is_available():
            print(f"✓ CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("ℹ CUDA not available (will use CPU)")
        
        # Try loading model
        model_name = f"yolov8{YOLO_MODEL_SIZE}.pt"
        model = YOLO(model_name)
        print(f"✓ Successfully loaded {model_name}")
        
        print()
        print("Installation verified successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

def main():
    """Main function"""
    print()
    print("=" * 60)
    print("ML Models Setup")
    print("=" * 60)
    print()
    
    # Download YOLO model
    if not download_yolo_model():
        print()
        print("Failed to download YOLO model.")
        print("The system will fall back to template matching for cursor detection.")
        return 1
    
    # Verify installation
    if not verify_installation():
        print()
        print("Verification failed. Please check the errors above.")
        return 1
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("You can now use the video editor with cursor detection.")
    print("Run: python main.py process your_video.mp4")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())