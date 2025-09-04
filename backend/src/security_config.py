"""
Centralized security configuration for the Dashly application.
"""

import os
import time
from typing import List, Dict, Any
from dataclasses import dataclass

try:
    from .logging_config import get_logger
except ImportError:
    from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SecurityConfig:
    """Centralized security configuration."""
    
    # File upload security
    MAX_CSV_SIZE_MB: int = 50
    ALLOWED_FILE_EXTENSIONS: List[str] = None
    UPLOAD_SCAN_ENABLED: bool = True
    
    # Input validation
    MAX_QUERY_LENGTH: int = 500
    MAX_SQL_LENGTH: int = 2000
    ENABLE_INPUT_SANITIZATION: bool = True
    
    # Rate limiting
    MAX_REQUESTS_PER_HOUR: int = 500
    MAX_UPLOADS_PER_HOUR: int = 50
    LLM_CALLS_PER_MINUTE: int = 10
    LLM_CALLS_PER_HOUR: int = 100
    LLM_TOKENS_PER_HOUR: int = 50000
    
    # Authentication
    REQUIRE_AUTH: bool = True
    MIN_API_KEY_LENGTH: int = 32
    API_KEY_ROTATION_DAYS: int = 90
    
    # CORS and networking
    ALLOWED_ORIGINS: List[str] = None
    ENABLE_HTTPS_ONLY: bool = False  # Set to True in production
    
    # Logging and monitoring
    LOG_SECURITY_EVENTS: bool = True
    LOG_FAILED_AUTH_ATTEMPTS: bool = True
    ALERT_ON_SUSPICIOUS_ACTIVITY: bool = True
    
    # SQL security
    ALLOW_ONLY_SELECT: bool = True
    ENABLE_SQL_INJECTION_DETECTION: bool = True
    MAX_SQL_COMPLEXITY_SCORE: int = 10
    
    def __post_init__(self):
        """Initialize default values from environment variables."""
        if self.ALLOWED_FILE_EXTENSIONS is None:
            self.ALLOWED_FILE_EXTENSIONS = ['.csv']
        
        if self.ALLOWED_ORIGINS is None:
            origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
            self.ALLOWED_ORIGINS = [origin.strip() for origin in origins_env.split(",")]
        
        # Override with environment variables if set
        self.MAX_REQUESTS_PER_HOUR = int(os.getenv("MAX_REQUESTS_PER_HOUR", self.MAX_REQUESTS_PER_HOUR))
        self.MAX_UPLOADS_PER_HOUR = int(os.getenv("MAX_UPLOADS_PER_HOUR", self.MAX_UPLOADS_PER_HOUR))
        self.REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
        
        # Production environment detection
        is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
        if is_production:
            self.ENABLE_HTTPS_ONLY = True
            self.REQUIRE_AUTH = True
            logger.info("Production environment detected - enhanced security enabled")
    
    def validate_configuration(self) -> List[str]:
        """
        Validate security configuration and return any warnings.
        
        Returns:
            List[str]: List of configuration warnings
        """
        warnings = []
        
        # Check authentication settings
        if not self.REQUIRE_AUTH:
            warnings.append("Authentication is disabled - this should only be used in development")
        
        # Check API key configuration
        api_key = os.getenv("DASHLY_API_KEY")
        if api_key:
            if len(api_key) < self.MIN_API_KEY_LENGTH:
                warnings.append(f"API key is shorter than recommended minimum ({self.MIN_API_KEY_LENGTH} chars)")
            
            # Check for weak keys
            weak_keys = ["demo", "test", "dev", "password", "12345", "admin"]
            if any(weak in api_key.lower() for weak in weak_keys):
                warnings.append("API key appears to contain weak patterns")
        
        # Check CORS settings
        if "*" in self.ALLOWED_ORIGINS:
            warnings.append("CORS allows all origins (*) - this is insecure for production")
        
        # Check HTTPS settings
        if not self.ENABLE_HTTPS_ONLY and os.getenv("ENVIRONMENT") == "production":
            warnings.append("HTTPS enforcement is disabled in production environment")
        
        # Check file upload limits
        if self.MAX_CSV_SIZE_MB > 100:
            warnings.append(f"Large file upload limit ({self.MAX_CSV_SIZE_MB}MB) may impact performance")
        
        # Check rate limiting
        if self.MAX_REQUESTS_PER_HOUR > 10000:
            warnings.append("Very high rate limit may allow abuse")
        
        return warnings
    
    def get_security_headers(self) -> Dict[str, str]:
        """
        Get security headers for HTTP responses.
        
        Returns:
            Dict[str, str]: Security headers to add to responses
        """
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=(), "
                "accelerometer=(), ambient-light-sensor=()"
            )
        }
        
        # Add HSTS header if HTTPS is enforced
        if self.ENABLE_HTTPS_ONLY:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        return headers
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], severity: str = "info"):
        """
        Log security events for monitoring.
        
        Args:
            event_type: Type of security event
            details: Event details
            severity: Event severity (info, warning, error, critical)
        """
        if not self.LOG_SECURITY_EVENTS:
            return
        
        log_entry = {
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "timestamp": time.time()
        }
        
        if severity == "critical":
            logger.critical(f"SECURITY EVENT: {event_type} - {details}")
        elif severity == "error":
            logger.error(f"SECURITY EVENT: {event_type} - {details}")
        elif severity == "warning":
            logger.warning(f"SECURITY EVENT: {event_type} - {details}")
        else:
            logger.info(f"SECURITY EVENT: {event_type} - {details}")
    
    def is_suspicious_activity(self, activity_data: Dict[str, Any]) -> bool:
        """
        Detect suspicious activity patterns.
        
        Args:
            activity_data: Activity data to analyze
            
        Returns:
            bool: True if activity appears suspicious
        """
        if not self.ALERT_ON_SUSPICIOUS_ACTIVITY:
            return False
        
        # Check for rapid successive requests
        if activity_data.get("requests_per_minute", 0) > 60:
            return True
        
        # Check for failed authentication attempts
        if activity_data.get("failed_auth_attempts", 0) > 5:
            return True
        
        # Check for unusual query patterns
        if activity_data.get("blocked_queries", 0) > 3:
            return True
        
        return False


# Global security configuration instance
security_config = SecurityConfig()

# Validate configuration on import
config_warnings = security_config.validate_configuration()
if config_warnings:
    logger.warning(f"Security configuration warnings: {config_warnings}")
else:
    logger.info("Security configuration validated successfully")