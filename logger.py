"""
Centralized logging system for Novatel ProPak6 Navigation Data Toolkit
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
import config


class NavigationLogger:
    """Centralized logger for navigation system"""
    
    _instance: Optional['NavigationLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self):
        """Setup the logging configuration"""
        # Create logger
        self._logger = logging.getLogger('navigation')
        # Always log at DEBUG level, but only write to file based on ENABLE_LOGGING
        self._logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self._logger.handlers:
            return
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(config.LOG_FILE) if os.path.dirname(config.LOG_FILE) else 'logs'
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create file handler with rotation
        log_file = config.LOG_FILE if config.LOG_FILE else 'logs/navigation.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Remove any existing console handlers
        for handler in self._logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                self._logger.removeHandler(handler)
        
        # Remove any existing console handlers from the root logger
        for handler in logging.getLogger().handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                logging.getLogger().removeHandler(handler)
        
        # Disable propagation to prevent messages going to root logger
        self._logger.propagate = False
        
        # Remove any existing console handlers from the root logger
        for handler in logging.getLogger().handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                logging.getLogger().removeHandler(handler)
        
        # Disable propagation to prevent messages going to root logger
        self._logger.propagate = False
        
        # Remove all existing handlers from this logger and root logger
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
            
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                root_logger.removeHandler(handler)
        
        # Disable propagation to prevent messages going to root logger
        self._logger.propagate = False
        
        # Remove all existing handlers from this logger and root logger
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
            
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                root_logger.removeHandler(handler)
        
        # Disable propagation to prevent messages going to root logger
        self._logger.propagate = False
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        # Add handler to logger
        self._logger.addHandler(file_handler)
        
        # Log startup
        self._logger.info("=" * 60)
        self._logger.info("Navigation Logger initialized")
        self._logger.info(f"Log file: {os.path.abspath(log_file)}")
        self._logger.info("=" * 60)
    
    def debug(self, message: str):
        """Log debug message"""
        if config.ENABLE_LOGGING and self._logger:
            self._logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        if config.ENABLE_LOGGING and self._logger:
            self._logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        if self._logger:
            self._logger.warning(message)
    
    def error(self, message: str):
        """Log error message"""
        if self._logger:
            self._logger.error(message)
    
    def critical(self, message: str):
        """Log critical message"""
        if self._logger:
            self._logger.critical(message)
    
    def udp_traffic(self, message: str):
        """Log UDP traffic if enabled"""
        if config.LOG_UDP_TRAFFIC:
            self.debug(f"[UDP] {message}")
    
    def nmea_raw(self, message: str):
        """Log raw NMEA data if enabled"""
        if config.LOG_RAW_NMEA:
            self.debug(f"[NMEA-RAW] {message}")
    
    def nmea_parse(self, message: str):
        """Log NMEA parsing attempts if enabled"""
        if config.LOG_PARSE_ATTEMPTS:
            self.debug(f"[NMEA-PARSE] {message}")
    
    def serial_traffic(self, message: str):
        """Log serial traffic if enabled"""
        if config.LOG_SERIAL_TRAFFIC:
            self.debug(f"[SERIAL] {message}")
    
    def novatel_msg(self, message: str):
        """Log Novatel messages if enabled"""
        if config.LOG_NOVATEL_MESSAGES:
            self.debug(f"[NOVATEL] {message}")
    
    def gdl90_frame(self, message: str):
        """Log GDL-90 frame detection if enabled"""
        if config.LOG_GDL90_FRAMES:
            self.debug(f"[GDL90] {message}")
    
    def deframing(self, message: str):
        """Log deframing process if enabled"""
        if config.LOG_DEFRAMING_PROCESS:
            self.debug(f"[DEFRAME] {message}")
    
    def main_process(self, message: str):
        """Log main process events"""
        self.info(f"[MAIN] {message}")
    
    def hex_data(self, data: bytes, prefix: str = "HEX"):
        """Log hex data for debugging"""
        hex_str = data.hex()
        self.debug(f"[{prefix}] Raw hex ({len(data)} bytes): {hex_str}")
        
        # Also log printable ASCII representation
        ascii_repr = ''.join(chr(b) if 32 <= b <= 126 else f'\\x{b:02x}' for b in data)
        self.debug(f"[{prefix}] ASCII repr: {ascii_repr}")


# Global logger instance
logger = NavigationLogger()


def console_print(message: str, force: bool = False):
    """
    Print to console only for critical system messages and startup/shutdown
    Navigation data display should use the NavigationDisplay class directly
    """
    if force:
        print(message)