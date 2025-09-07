"""
Logging configuration and setup for Music Trainer application
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logger(name="music_trainer", level=logging.INFO):
    """
    Setup application logging with both file and console handlers
    
    Args:
        name (str): Logger name
        level: Logging level (default: INFO)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    log_file = log_dir / f"music_trainer_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB max, 5 backups
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name=None):
    """
    Get an existing logger instance
    
    Args:
        name (str): Logger name (default: music_trainer)
    
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name or "music_trainer")
