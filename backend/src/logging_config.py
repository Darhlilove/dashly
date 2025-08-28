"""
Logging configuration for the Dashly application.

Provides centralized logging setup with security-aware logging practices.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from .security_config import SecurityConfig
except ImportError:
    from security_config import SecurityConfig


class SecurityAwareFormatter(logging.Formatter):
    """Custom formatter that sanitizes sensitive information from log messages."""
    
    SENSITIVE_PATTERNS = [
        'password', 'token', 'secret', 'key', 'api_key', 'auth',
        'credit_card', 'ssn', 'social_security', 'email', 'phone'
    ]
    
    def format(self, record):
        """Format log record while sanitizing sensitive information."""
        # Get the original formatted message
        formatted = super().format(record)
        
        # Sanitize sensitive information
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.lower() in formatted.lower():
                # Replace potential sensitive values with [REDACTED]
                import re
                # Pattern to match key=value or key: value patterns
                sensitive_pattern = rf'({pattern}[=:\s]+)[^\s,\]}}]+' 
                formatted = re.sub(sensitive_pattern, r'\1[REDACTED]', formatted, flags=re.IGNORECASE)
        
        return formatted


class DashlyLogger:
    """Centralized logger configuration for the Dashly application."""
    
    _loggers = {}
    _configured = False
    
    @classmethod
    def setup_logging(cls, log_level: Optional[str] = None, log_file: Optional[str] = None):
        """
        Set up application-wide logging configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path
        """
        if cls._configured:
            return
        
        # Use security config defaults if not provided
        log_level = log_level or SecurityConfig.LOG_LEVEL
        
        # Create logs directory if logging to file
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = SecurityAwareFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            try:
                # Use rotating file handler to prevent log files from growing too large
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=10 * 1024 * 1024,  # 10MB
                    backupCount=5
                )
                file_handler.setLevel(getattr(logging, log_level.upper()))
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except (OSError, PermissionError) as e:
                # If we can't write to log file, just log to console
                root_logger.warning(f"Could not set up file logging: {e}")
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for the specified name.
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            logging.Logger: Configured logger instance
        """
        if not cls._configured:
            cls.setup_logging()
        
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def log_security_event(cls, logger: logging.Logger, event_type: str, details: str, 
                          level: int = logging.WARNING):
        """
        Log security-related events with consistent formatting.
        
        Args:
            logger: Logger instance to use
            event_type: Type of security event (e.g., 'PATH_TRAVERSAL', 'INVALID_FILE')
            details: Event details
            level: Logging level
        """
        if SecurityConfig.LOG_SECURITY_EVENTS:
            logger.log(level, f"SECURITY_EVENT: {event_type} - {details}")
    
    @classmethod
    def log_api_request(cls, logger: logging.Logger, method: str, path: str, 
                       status_code: int, duration_ms: Optional[float] = None):
        """
        Log API request with consistent formatting.
        
        Args:
            logger: Logger instance to use
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
        """
        duration_str = f" ({duration_ms:.2f}ms)" if duration_ms else ""
        logger.info(f"API_REQUEST: {method} {path} -> {status_code}{duration_str}")
    
    @classmethod
    def log_database_operation(cls, logger: logging.Logger, operation: str, 
                              table_name: Optional[str] = None, success: bool = True,
                              error_details: Optional[str] = None):
        """
        Log database operations with consistent formatting.
        
        Args:
            logger: Logger instance to use
            operation: Database operation (e.g., 'INGEST_CSV', 'GET_SCHEMA')
            table_name: Optional table name
            success: Whether operation was successful
            error_details: Error details if operation failed
        """
        table_str = f" (table: {table_name})" if table_name else ""
        status = "SUCCESS" if success else "FAILED"
        
        if success:
            logger.info(f"DB_OPERATION: {operation}{table_str} - {status}")
        else:
            error_str = f" - {error_details}" if error_details else ""
            logger.error(f"DB_OPERATION: {operation}{table_str} - {status}{error_str}")


# Initialize logging on module import
DashlyLogger.setup_logging()

# Convenience function for getting loggers
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return DashlyLogger.get_logger(name)