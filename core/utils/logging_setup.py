"""Logging setup for Scrappy applications"""
import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from termcolor import colored

def setup_logging(name, log_level=None, log_file=None):
    """
    Set up a logger with console and optional file handlers
    
    Args:
        name (str): Logger name
        log_level (str, optional): Log level (DEBUG, INFO, etc.)
        log_file (str, optional): Path to log file
        
    Returns:
        logging.Logger: Configured logger
    """
    # Default log level from environment or INFO
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with colored output
    console_handler = ColoredConsoleHandler()
    console_handler.setLevel(numeric_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

class ColoredConsoleHandler(logging.StreamHandler):
    """Console handler with colored output based on log level"""
    
    # Define colors for different log levels
    COLORS = {
        logging.DEBUG: 'blue',
        logging.INFO: 'green',
        logging.WARNING: 'yellow',
        logging.ERROR: 'red',
        logging.CRITICAL: 'red',
    }
    
    def __init__(self, stream=None):
        super().__init__(stream or sys.stdout)
    
    def emit(self, record):
        try:
            # Get color for this log level
            color = self.COLORS.get(record.levelno, 'white')
            
            # Color the levelname only
            record.levelname = colored(record.levelname, color)
            
            super().emit(record)
        except Exception:
            self.handleError(record)