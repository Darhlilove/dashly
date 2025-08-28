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


class QueryExecutionError(DatabaseError):
    """Exception raised when SQL query execution fails."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 sql_error_type: str = "execution", position: Optional[int] = None,
                 suggestions: Optional[list] = None):
        """
        Initialize query execution error.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
            sql_error_type: Type of SQL error (syntax, security, execution, timeout)
            position: Optional character position where error occurred
            suggestions: Optional list of suggestions to fix the error
        """
        super().__init__(message, error_code)
        self.sql_error_type = sql_error_type
        self.position = position
        self.suggestions = suggestions or []


class SQLSyntaxError(QueryExecutionError):
    """Exception raised when SQL query has syntax errors."""
    
    def __init__(self, message: str, position: Optional[int] = None, 
                 suggestions: Optional[list] = None):
        """
        Initialize SQL syntax error.
        
        Args:
            message: Human-readable error message
            position: Character position where syntax error occurred
            suggestions: Optional list of suggestions to fix the syntax
        """
        super().__init__(
            message, 
            error_code="SQL_SYNTAX_ERROR",
            sql_error_type="syntax",
            position=position,
            suggestions=suggestions or ["Check SQL syntax", "Ensure query is a valid SELECT statement"]
        )


class SQLSecurityError(QueryExecutionError):
    """Exception raised when SQL query violates security rules."""
    
    def __init__(self, message: str, violation_type: str = "security_violation",
                 position: Optional[int] = None, suggestions: Optional[list] = None):
        """
        Initialize SQL security error.
        
        Args:
            message: Human-readable error message
            violation_type: Type of security violation
            position: Optional character position where violation occurred
            suggestions: Optional list of suggestions to fix the violation
        """
        super().__init__(
            message,
            error_code="SQL_SECURITY_ERROR", 
            sql_error_type="security",
            position=position,
            suggestions=suggestions or ["Use SELECT statements only", "Avoid DDL/DML operations"]
        )
        self.violation_type = violation_type


class QueryTimeoutError(QueryExecutionError):
    """Exception raised when SQL query execution times out."""
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None,
                 suggestions: Optional[list] = None):
        """
        Initialize query timeout error.
        
        Args:
            message: Human-readable error message
            timeout_seconds: Timeout value that was exceeded
            suggestions: Optional list of suggestions to fix the timeout
        """
        super().__init__(
            message,
            error_code="QUERY_TIMEOUT_ERROR",
            sql_error_type="timeout",
            suggestions=suggestions or [
                "Simplify the query", 
                "Add more specific WHERE conditions", 
                "Consider using LIMIT clause"
            ]
        )
        self.timeout_seconds = timeout_seconds


class ResultSetTooLargeError(QueryExecutionError):
    """Exception raised when query result set exceeds size limits."""
    
    def __init__(self, message: str, max_rows: Optional[int] = None,
                 actual_rows: Optional[int] = None, suggestions: Optional[list] = None):
        """
        Initialize result set too large error.
        
        Args:
            message: Human-readable error message
            max_rows: Maximum allowed rows
            actual_rows: Actual number of rows that would be returned
            suggestions: Optional list of suggestions to fix the issue
        """
        super().__init__(
            message,
            error_code="RESULT_SET_TOO_LARGE_ERROR",
            sql_error_type="execution",
            suggestions=suggestions or [
                "Add LIMIT clause to reduce result set size",
                "Use more specific WHERE conditions",
                "Consider aggregating data instead of returning raw rows"
            ]
        )
        self.max_rows = max_rows
        self.actual_rows = actual_rows


class QueryExplainError(DatabaseError):
    """Exception raised when query explanation or analysis fails."""
    
    def __init__(self, message: str, error_code: Optional[str] = None,
                 suggestions: Optional[list] = None):
        """
        Initialize query explain error.
        
        Args:
            message: Human-readable error message
            error_code: Optional error code for categorization
            suggestions: Optional list of suggestions
        """
        super().__init__(message, error_code)
        self.suggestions = suggestions or ["Check query syntax", "Ensure query is valid"]


class SQLSchemaError(QueryExecutionError):
    """Exception raised when SQL query references non-existent tables or columns."""
    
    def __init__(self, message: str, missing_object: Optional[str] = None,
                 object_type: str = "table", suggestions: Optional[list] = None):
        """
        Initialize SQL schema error.
        
        Args:
            message: Human-readable error message
            missing_object: Name of the missing table/column
            object_type: Type of missing object (table, column)
            suggestions: Optional list of suggestions to fix the error
        """
        super().__init__(
            message,
            error_code="SQL_SCHEMA_ERROR",
            sql_error_type="schema",
            suggestions=suggestions or [
                f"Check available {object_type}s with /api/schema",
                f"Verify {object_type} name spelling"
            ]
        )
        self.missing_object = missing_object
        self.object_type = object_type


class ConcurrentQueryLimitError(QueryExecutionError):
    """Exception raised when concurrent query limit is exceeded."""
    
    def __init__(self, message: str, max_concurrent: Optional[int] = None,
                 suggestions: Optional[list] = None):
        """
        Initialize concurrent query limit error.
        
        Args:
            message: Human-readable error message
            max_concurrent: Maximum number of concurrent queries allowed
            suggestions: Optional list of suggestions
        """
        super().__init__(
            message,
            error_code="CONCURRENT_QUERY_LIMIT_ERROR",
            sql_error_type="execution",
            suggestions=suggestions or [
                "Wait for other queries to complete",
                "Reduce query complexity to execute faster"
            ]
        )
        self.max_concurrent = max_concurrent