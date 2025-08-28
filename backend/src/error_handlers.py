"""
Error handling utilities for consistent error responses and HTTP status codes.

This module provides utilities for converting domain-specific exceptions
to appropriate HTTP responses while maintaining security.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from fastapi import HTTPException

try:
    from .exceptions import (
        DashlyBaseException,
        FileUploadError,
        InvalidFileFormatError,
        FileSizeExceededError,
        FileValidationError,
        DatabaseError,
        DatabaseConnectionError,
        TableNotFoundError,
        InvalidTableNameError,
        CSVIngestionError,
        SchemaExtractionError,
        SecurityError,
        PathTraversalError,
        InvalidPathError,
        ValidationError,
        InvalidParameterError,
        ConfigurationError,
        DemoDataError,
        DemoDataNotFoundError,
        QueryExecutionError,
        SQLSyntaxError,
        SQLSecurityError,
        QueryTimeoutError,
        ResultSetTooLargeError,
        QueryExplainError,
        SQLSchemaError,
        ConcurrentQueryLimitError
    )
    from .logging_config import get_logger
except ImportError:
    from exceptions import (
        DashlyBaseException,
        FileUploadError,
        InvalidFileFormatError,
        FileSizeExceededError,
        FileValidationError,
        DatabaseError,
        DatabaseConnectionError,
        TableNotFoundError,
        InvalidTableNameError,
        CSVIngestionError,
        SchemaExtractionError,
        SecurityError,
        PathTraversalError,
        InvalidPathError,
        ValidationError,
        InvalidParameterError,
        ConfigurationError,
        DemoDataError,
        DemoDataNotFoundError,
        QueryExecutionError,
        SQLSyntaxError,
        SQLSecurityError,
        QueryTimeoutError,
        ResultSetTooLargeError,
        QueryExplainError,
        SQLSchemaError,
        ConcurrentQueryLimitError
    )
    from logging_config import get_logger

logger = get_logger(__name__)


class ErrorHandler:
    """Centralized error handling for the application."""
    
    # Mapping of exception types to HTTP status codes and client-safe messages
    ERROR_MAPPINGS = {
        # File upload errors (4xx - client errors)
        InvalidFileFormatError: (400, "Invalid file format. Please upload a valid CSV file."),
        FileSizeExceededError: (413, "File size exceeds the maximum allowed limit."),
        FileValidationError: (400, "File validation failed. Please check your CSV format."),
        FileUploadError: (400, "File upload failed. Please try again."),
        
        # SQL execution errors (must come before DatabaseError since they inherit from it)
        SQLSyntaxError: (400, "SQL syntax error in query."),
        SQLSecurityError: (400, "SQL query violates security rules."),
        QueryTimeoutError: (408, "Query execution timed out."),
        ResultSetTooLargeError: (400, "Query result set too large."),
        SQLSchemaError: (400, "SQL query references non-existent tables or columns."),
        ConcurrentQueryLimitError: (429, "Too many concurrent queries."),
        QueryExplainError: (400, "Query explanation failed."),
        QueryExecutionError: (400, "Query execution failed."),
        
        # Database errors
        TableNotFoundError: (404, "Requested table not found."),
        InvalidTableNameError: (400, "Invalid table name provided."),
        DatabaseConnectionError: (503, "Database service temporarily unavailable."),
        CSVIngestionError: (500, "Failed to process CSV data."),
        SchemaExtractionError: (500, "Failed to retrieve database schema."),
        DatabaseError: (500, "Database operation failed."),
        
        # Security errors (4xx - client errors, but log as security events)
        PathTraversalError: (403, "Access denied."),
        InvalidPathError: (403, "Invalid file path."),
        SecurityError: (403, "Access denied."),
        
        # Validation errors (4xx - client errors)
        InvalidParameterError: (422, "Invalid request parameters."),
        ValidationError: (422, "Request validation failed."),
        
        # Configuration errors (5xx - server errors)
        ConfigurationError: (500, "Service configuration error."),
        
        # Demo data errors
        DemoDataNotFoundError: (404, "Demo data not available. Please run the demo data generation script."),
        DemoDataError: (500, "Demo data operation failed."),
        
        # Base exception (5xx - server error)
        DashlyBaseException: (500, "Internal server error."),
    }
    
    @classmethod
    def handle_exception(cls, exc: Exception, context: Optional[str] = None) -> HTTPException:
        """
        Convert an exception to an appropriate HTTPException.
        
        Args:
            exc: The exception to handle
            context: Optional context information for logging
            
        Returns:
            HTTPException: Appropriate HTTP exception with status code and message
        """
        # Log the original exception with full details
        context_str = f" (context: {context})" if context else ""
        logger.error(f"Exception occurred{context_str}: {type(exc).__name__}: {str(exc)}")
        
        # Handle SQL security exceptions specially
        if isinstance(exc, SQLSecurityError):
            try:
                from .logging_config import DashlyLogger
            except ImportError:
                from logging_config import DashlyLogger
            DashlyLogger.log_security_event(
                logger, 
                f"SQL_SECURITY_VIOLATION_{exc.violation_type}",
                f"SQL security violation: {str(exc)}{context_str}",
                logging.ERROR
            )
        
        # Handle general security exceptions
        elif isinstance(exc, SecurityError):
            try:
                from .logging_config import DashlyLogger
            except ImportError:
                from logging_config import DashlyLogger
            DashlyLogger.log_security_event(
                logger, 
                type(exc).__name__, 
                f"{str(exc)}{context_str}",
                logging.ERROR
            )
        
        # Handle SQL-specific exceptions with detailed error responses
        if isinstance(exc, QueryExecutionError):
            status_code, base_message = cls.ERROR_MAPPINGS.get(type(exc), (400, "Query execution failed."))
            
            # Create detailed error response for SQL exceptions
            error_detail = cls.create_sql_error_response(
                error=type(exc).__name__.lower().replace('error', '_failed'),
                detail=str(exc),
                sql_error_type=exc.sql_error_type,
                position=getattr(exc, 'position', None),
                suggestions=getattr(exc, 'suggestions', [])
            )
            
            return HTTPException(status_code=status_code, detail=error_detail)
        
        # Find the most specific exception type mapping
        for exc_type, (status_code, message) in cls.ERROR_MAPPINGS.items():
            if isinstance(exc, exc_type):
                return HTTPException(status_code=status_code, detail=message)
        
        # Handle standard Python exceptions
        if isinstance(exc, FileNotFoundError):
            logger.warning(f"File not found{context_str}: {str(exc)}")
            return HTTPException(status_code=404, detail="Requested file not found.")
        
        if isinstance(exc, PermissionError):
            logger.error(f"Permission error{context_str}: {str(exc)}")
            return HTTPException(status_code=403, detail="Access denied.")
        
        if isinstance(exc, ValueError):
            logger.warning(f"Value error{context_str}: {str(exc)}")
            return HTTPException(status_code=400, detail="Invalid input provided.")
        
        if isinstance(exc, OSError):
            logger.error(f"OS error{context_str}: {str(exc)}")
            return HTTPException(status_code=500, detail="System operation failed.")
        
        # Default handling for unexpected exceptions
        logger.error(f"Unexpected exception{context_str}: {type(exc).__name__}: {str(exc)}")
        return HTTPException(status_code=500, detail="Internal server error.")
    
    @classmethod
    def create_error_response(cls, status_code: int, message: str, 
                            error_code: Optional[str] = None,
                            details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            status_code: HTTP status code
            message: Error message
            error_code: Optional error code
            details: Optional additional details
            
        Returns:
            Dict[str, Any]: Standardized error response
        """
        response = {
            "error": True,
            "message": message,
            "status_code": status_code
        }
        
        if error_code:
            response["error_code"] = error_code
        
        if details:
            response["details"] = details
        
        return response
    
    @classmethod
    def create_sql_error_response(cls, error: str, detail: str, sql_error_type: str,
                                position: Optional[int] = None, 
                                suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a SQL-specific error response with detailed context.
        
        Args:
            error: Error type identifier
            detail: Detailed error message
            sql_error_type: Type of SQL error (syntax, security, execution, timeout)
            position: Optional character position where error occurred
            suggestions: Optional list of suggestions to fix the error
            
        Returns:
            Dict[str, Any]: SQL error response matching SQLErrorResponse model
        """
        response = {
            "error": error,
            "detail": detail,
            "sql_error_type": sql_error_type
        }
        
        if position is not None:
            response["position"] = position
        
        if suggestions:
            response["suggestions"] = suggestions
        
        return response
    
    @classmethod
    def log_and_raise_http_exception(cls, status_code: int, detail: str, 
                                   context: Optional[str] = None,
                                   log_level: int = logging.ERROR):
        """
        Log an error and raise an HTTPException.
        
        Args:
            status_code: HTTP status code
            detail: Error detail message
            context: Optional context for logging
            log_level: Logging level to use
        """
        context_str = f" (context: {context})" if context else ""
        logger.log(log_level, f"HTTP {status_code} error{context_str}: {detail}")
        raise HTTPException(status_code=status_code, detail=detail)


def handle_api_exception(func):
    """
    Decorator for API endpoints to handle exceptions consistently.
    
    Usage:
        @handle_api_exception
        async def my_endpoint():
            # endpoint logic
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            # Convert other exceptions to HTTPExceptions
            http_exc = ErrorHandler.handle_exception(e, context=func.__name__)
            raise http_exc
    
    return wrapper


def handle_sync_api_exception(func):
    """
    Decorator for synchronous API endpoints to handle exceptions consistently.
    
    Usage:
        @handle_sync_api_exception
        def my_sync_endpoint():
            # endpoint logic
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            # Convert other exceptions to HTTPExceptions
            http_exc = ErrorHandler.handle_exception(e, context=func.__name__)
            raise http_exc
    
    return wrapper