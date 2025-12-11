import logging
import sys
from pathlib import Path
from datetime import datetime
from config.settings import LOG_LEVEL, LOG_FILE


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logger(name: str = "video_editor_ai") -> logging.Logger:
    """
    Set up logger with both file and console handlers
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = ColoredFormatter(
        '%(levelname)s | %(name)s | %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler without colors
    LOG_FILE.parent.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


class AgentLogger:
    """Logger wrapper for agent-specific logging"""
    
    def __init__(self, agent_name: str, project_id: str = None):
        self.agent_name = agent_name
        self.project_id = project_id
        self.logger = setup_logger(f"agent.{agent_name}")
        self.start_time = None
    
    def start(self, message: str = "Starting agent"):
        """Log agent start"""
        self.start_time = datetime.now()
        prefix = f"[{self.project_id}] " if self.project_id else ""
        self.logger.info(f"{prefix}{message}")
    
    def info(self, message: str):
        """Log info message"""
        prefix = f"[{self.project_id}] " if self.project_id else ""
        self.logger.info(f"{prefix}{message}")
    
    def warning(self, message: str):
        """Log warning message"""
        prefix = f"[{self.project_id}] " if self.project_id else ""
        self.logger.warning(f"{prefix}{message}")
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message"""
        prefix = f"[{self.project_id}] " if self.project_id else ""
        self.logger.error(f"{prefix}{message}", exc_info=exc_info)
    
    def success(self, message: str):
        """Log success message"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            message = f"{message} (completed in {duration:.2f}s)"
        prefix = f"[{self.project_id}] " if self.project_id else ""
        self.logger.info(f"{prefix}✓ {message}")
    
    def debug(self, message: str):
        """Log debug message"""
        prefix = f"[{self.project_id}] " if self.project_id else ""
        self.logger.debug(f"{prefix}{message}")


# Create default logger
default_logger = setup_logger()