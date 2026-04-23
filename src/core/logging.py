# ComputeHub Core - Logging
# Inherited from OpenPC System timestamp logging pattern

import logging
import sys
from datetime import datetime
from pathlib import Path


class ComputeHubFormatter(logging.Formatter):
    """Custom formatter with timestamp, matching OpenPC System pattern."""
    
    def format(self, record):
        # Use custom timestamp attribute if set, otherwise generate one
        if hasattr(record, 'timestamp'):
            ts = record.timestamp
        else:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        level = record.levelname
        message = record.getMessage()
        return f"[{ts}] [{level}] {message}"


def get_logger(name: str = "computehub", level: str = "INFO", 
               log_file: str = None, fmt: str = None) -> logging.Logger:
    """Get a ComputeHub logger with timestamp formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if not logger.handlers:
        formatter = ComputeHubFormatter(fmt="%(__timestamp)s [%(__levelname)s] %(message)s")
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (optional)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    return logger
