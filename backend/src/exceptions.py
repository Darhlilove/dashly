"""
Custom exception classes for domain-specific errors.

This module defines custom exceptions that provide better error categorization
and handling throughout the application.
"""

from typing import Optional


class DashlyBaseException(Exception):
    """Base exception class for all Dashly-specific errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        """
        Initialize base exception.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__


class FileUploadError(DashlyBaseException):
    """Exception raised for file upload related errors."""
    pass


class InvalidFileFormatError(FileUploadError):
    """Exception raised when uploaded file format is invalid."""
    pass


class FileSizeExceededError(FileUploadError):
    """Exception raised when uploaded file exceeds size limits."""
    pass


class FileValidationError(FileUploadError):
    """Exception raised when file content validation fails."""
    pass


class DatabaseError(DashlyBaseException):
    """Exception raised for database operation errors."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass


class TableNotFoundError(DatabaseError):
    """Exception raised when requested table doesn't exist."""
    pass


class InvalidTableNameError(DatabaseError):
    """Exception raised when table name is invalid."""
    pass


class CSVIngestionError(DatabaseError):
    """Exception raised when CSV ingestion into database fails."""
    pass


class SchemaExtractionError(DatabaseError):
    """Exception raised when database schema extraction fails."""
    pass


class SecurityError(DashlyBaseException):
    """Exception raised for security-related violations."""
    pass


class PathTraversalError(SecurityError):
    """Exception raised when path traversal attempt is detected."""
    pass


class InvalidPathError(SecurityError):
    """Exception raised when file path is invalid or outside allowed directories."""
    pass


class ValidationError(DashlyBaseException):
    """Exception raised for input validation errors."""
    pass


class InvalidParameterError(ValidationError):
    """Exception raised when request parameters are invalid."""
    pass


class ConfigurationError(DashlyBaseException):
    """Exception raised for configuration-related errors."""
    pass


class DemoDataError(DashlyBaseException):
    """Exception raised for demo data related errors."""
    pass


class DemoDataNotFoundError(DemoDataError):
    """Exception raised when demo data is not available."""
    pass