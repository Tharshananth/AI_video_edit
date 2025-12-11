<<<<<<< HEAD
"""
Configuration settings for AI Video Editor
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# PROJECT PATHS
# ============================================================================
BASE_DIR = Path(__file__).parent.parent
PROJECTS_DIR = BASE_DIR / "projects"
MODELS_DIR = BASE_DIR / "models"
DATABASE_DIR = BASE_DIR / "database"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
PROJECTS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
DATABASE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# API KEYS
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", None)

# Validate critical keys
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in .env file")

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
VISION_MODEL = "gpt-4o"
ANALYSIS_MODEL = "gpt-4o"
WHISPER_MODEL = "whisper-1"
TTS_MODEL = "tts-1-hd"
TTS_VOICE = "alloy"  # alloy, echo, fable, onyx, nova, shimmer

# ============================================================================
# FRAME EXTRACTION SETTINGS
# ============================================================================
DEFAULT_FPS = 2.5  # Extract 2.5 frames per second
MAX_FRAMES = 500   # Maximum frames to extract (cost control)
FRAME_RESOLUTION = "1280x720"  # Downscale for faster processing
FRAME_FORMAT = "jpg"
FRAME_QUALITY = 85  # JPEG quality (1-100)

# ============================================================================
# VISION API SETTINGS
# ============================================================================
FRAME_SAMPLE_RATE = 5  # Analyze every 5th frame (cost optimization)
VISION_MAX_TOKENS = 300
VISION_DETAIL = "high"  # "low" or "high"

# ============================================================================
# CURSOR DETECTION SETTINGS
# ============================================================================
CURSOR_MODEL = "yolov8"  # "yolov8" or "template"
YOLO_MODEL_SIZE = "n"    # n (nano), s (small), m (medium), l (large)
CURSOR_CONFIDENCE_THRESHOLD = 0.7
CLICK_DETECTION_THRESHOLD = 5.0   # Velocity threshold for clicks
HOVER_DETECTION_THRESHOLD = 0.5   # Seconds of stationary cursor

# ============================================================================
# AUDIO PROCESSING SETTINGS
# ============================================================================
WHISPER_LANGUAGE = "en"
SILENCE_THRESHOLD_DB = -40    # dB level considered silence
MIN_SILENCE_DURATION = 0.5    # Minimum silence duration to detect (seconds)

# ============================================================================
# VIDEO RENDERING SETTINGS
# ============================================================================
VIDEO_CODEC = "libx264"
VIDEO_PRESET = "medium"  # ultrafast, fast, medium, slow, veryslow
VIDEO_CRF = 23           # Quality (0-51, lower = better, 23 = good)
VIDEO_BITRATE = "8000k"
OUTPUT_FPS = 30

AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"

# ============================================================================
# API COST ESTIMATES (USD per unit)
# ============================================================================
# GPT-4o Vision (per 1M tokens)
COST_GPT4O_INPUT = 2.50 / 1_000_000
COST_GPT4O_OUTPUT = 10.00 / 1_000_000

# Whisper (per minute)
COST_WHISPER = 0.006

# TTS (per 1M characters)
COST_TTS = 15.00 / 1_000_000

# ============================================================================
# DATABASE SETTINGS
# ============================================================================
DATABASE_PATH = DATABASE_DIR / "projects.db"

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================
PROJECT_RETENTION_DAYS = 30  # Auto-delete projects older than this
MAX_CONCURRENT_PROJECTS = 3  # Limit concurrent processing

# ============================================================================
# RETRY & TIMEOUT SETTINGS
# ============================================================================
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = LOGS_DIR / "video_editor.log"

# ============================================================================
# FEATURE FLAGS
# ============================================================================
ENABLE_CURSOR_DETECTION = True
ENABLE_AUDIO_ANALYSIS = True
ENABLE_VISION_ANALYSIS = True
ENABLE_RENDERING = True

# ============================================================================
# DEVELOPMENT MODE
# ============================================================================
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

if DEBUG_MODE:
    print("⚠️  DEBUG MODE ENABLED")
    FRAME_SAMPLE_RATE = 10  # Analyze fewer frames in debug
    MAX_FRAMES = 100
=======
"""
Configuration settings for AI Video Editor
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# PROJECT PATHS
# ============================================================================
BASE_DIR = Path(__file__).parent.parent
PROJECTS_DIR = BASE_DIR / "projects"
MODELS_DIR = BASE_DIR / "models"
DATABASE_DIR = BASE_DIR / "database"
LOGS_DIR = BASE_DIR / "logs"

# Create directories
PROJECTS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
DATABASE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# API KEYS
# ============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", None)

# Validate critical keys
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in .env file")

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================
VISION_MODEL = "gpt-4o"
ANALYSIS_MODEL = "gpt-4o"
WHISPER_MODEL = "whisper-1"
TTS_MODEL = "tts-1-hd"
TTS_VOICE = "alloy"  # alloy, echo, fable, onyx, nova, shimmer

# ============================================================================
# FRAME EXTRACTION SETTINGS
# ============================================================================
DEFAULT_FPS = 2.5  # Extract 2.5 frames per second
MAX_FRAMES = 500   # Maximum frames to extract (cost control)
FRAME_RESOLUTION = "1280x720"  # Downscale for faster processing
FRAME_FORMAT = "jpg"
FRAME_QUALITY = 85  # JPEG quality (1-100)

# ============================================================================
# VISION API SETTINGS
# ============================================================================
FRAME_SAMPLE_RATE = 5  # Analyze every 5th frame (cost optimization)
VISION_MAX_TOKENS = 300
VISION_DETAIL = "high"  # "low" or "high"

# ============================================================================
# CURSOR DETECTION SETTINGS
# ============================================================================
CURSOR_MODEL = "yolov8"  # "yolov8" or "template"
YOLO_MODEL_SIZE = "n"    # n (nano), s (small), m (medium), l (large)
CURSOR_CONFIDENCE_THRESHOLD = 0.7
CLICK_DETECTION_THRESHOLD = 5.0   # Velocity threshold for clicks
HOVER_DETECTION_THRESHOLD = 0.5   # Seconds of stationary cursor

# ============================================================================
# AUDIO PROCESSING SETTINGS
# ============================================================================
WHISPER_LANGUAGE = "en"
SILENCE_THRESHOLD_DB = -40    # dB level considered silence
MIN_SILENCE_DURATION = 0.5    # Minimum silence duration to detect (seconds)

# ============================================================================
# VIDEO RENDERING SETTINGS
# ============================================================================
VIDEO_CODEC = "libx264"
VIDEO_PRESET = "medium"  # ultrafast, fast, medium, slow, veryslow
VIDEO_CRF = 23           # Quality (0-51, lower = better, 23 = good)
VIDEO_BITRATE = "8000k"
OUTPUT_FPS = 30

AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"

# ============================================================================
# API COST ESTIMATES (USD per unit)
# ============================================================================
# GPT-4o Vision (per 1M tokens)
COST_GPT4O_INPUT = 2.50 / 1_000_000
COST_GPT4O_OUTPUT = 10.00 / 1_000_000

# Whisper (per minute)
COST_WHISPER = 0.006

# TTS (per 1M characters)
COST_TTS = 15.00 / 1_000_000

# ============================================================================
# DATABASE SETTINGS
# ============================================================================
DATABASE_PATH = DATABASE_DIR / "projects.db"

# ============================================================================
# PROJECT MANAGEMENT
# ============================================================================
PROJECT_RETENTION_DAYS = 30  # Auto-delete projects older than this
MAX_CONCURRENT_PROJECTS = 3  # Limit concurrent processing

# ============================================================================
# RETRY & TIMEOUT SETTINGS
# ============================================================================
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = LOGS_DIR / "video_editor.log"

# ============================================================================
# FEATURE FLAGS
# ============================================================================
ENABLE_CURSOR_DETECTION = True
ENABLE_AUDIO_ANALYSIS = True
ENABLE_VISION_ANALYSIS = True
ENABLE_RENDERING = True

# ============================================================================
# DEVELOPMENT MODE
# ============================================================================
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

if DEBUG_MODE:
    print("⚠️  DEBUG MODE ENABLED")
    FRAME_SAMPLE_RATE = 10  # Analyze fewer frames in debug
    MAX_FRAMES = 100
>>>>>>> d4e3c4e (update)
