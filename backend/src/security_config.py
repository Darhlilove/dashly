"""
Security configuration for the database manager.
"""

from typing import List


class SecurityConfig:
    """Security configuration constants and settings."""
    
    # File size limits
    MAX_CSV_SIZE_MB: int = 50  # Reduced from 100MB for security
    
    # Table name constraints
    MAX_TABLE_NAME_LENGTH: int = 32  # Reduced for security
    
    # Directory restrictions
    ALLOWED_DATA_DIR: str = "data"
    
    # Request size limits
    MAX_REQUEST_SIZE_MB: int = 60  # Slightly larger than CSV to account for multipart overhead
    
    # Sensitive field patterns for data sanitization
    SENSITIVE_FIELD_PATTERNS: List[str] = [
        'email', 'phone', 'ssn', 'password', 'token', 'secret', 'key',
        'credit_card', 'cc_number', 'social_security', 'passport',
        'license', 'account_number', 'routing_number', 'pin'
    ]
    
    # Sample data limits
    MAX_SAMPLE_ROWS: int = 5
    MAX_FIELD_LENGTH: int = 100
    
    # Logging configuration
    LOG_SECURITY_EVENTS: bool = True
    LOG_LEVEL: str = "INFO"
    
    @classmethod
    def is_sensitive_field(cls, field_name: str) -> bool:
        """
        Check if a field name suggests sensitive data.
        
        Args:
            field_name: Name of the field to check
            
        Returns:
            bool: True if field appears to contain sensitive data
        """
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in cls.SENSITIVE_FIELD_PATTERNS)