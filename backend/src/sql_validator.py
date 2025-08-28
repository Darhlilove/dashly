"""
SQL Query Validator for secure query processing.

Provides comprehensive validation for user-generated SQL queries to prevent
SQL injection and ensure only safe SELECT operations are allowed.
"""

import re
import logging
from typing import List, Set, Optional
from enum import Enum

try:
    from .exceptions import ValidationError
    from .logging_config import get_logger
except ImportError:
    from exceptions import ValidationError
    from logging_config import get_logger

logger = get_logger(__name__)


class QueryType(Enum):
    """Enumeration of allowed query types."""
    SELECT = "SELECT"
    WITH = "WITH"  # Allow CTEs (Common Table Expressions)


class SQLValidator:
    """
    Comprehensive SQL query validator for security and safety.
    
    This validator ensures that only safe, read-only SELECT queries
    are allowed, preventing SQL injection and unauthorized operations.
    """
    
    # Comprehensive list of dangerous SQL keywords and patterns
    DANGEROUS_KEYWORDS = {
        # Data modification
        'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'UPSERT',
        # Schema modification
        'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME',
        # System operations
        'EXEC', 'EXECUTE', 'CALL', 'PROCEDURE', 'FUNCTION',
        # Transaction control
        'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'BEGIN', 'START',
        # Access control
        'GRANT', 'REVOKE', 'DENY',
        # Database operations
        'BACKUP', 'RESTORE', 'ATTACH', 'DETACH',
        # System functions (DuckDB specific)
        'PRAGMA', 'INSTALL', 'LOAD', 'SET',
        # File operations
        'COPY', 'EXPORT', 'IMPORT'
    }
    
    # Dangerous functions that could be used for attacks
    DANGEROUS_FUNCTIONS = {
        'system', 'shell', 'exec', 'eval', 'load_extension',
        'read_file', 'write_file', 'glob', 'list_files'
    }
    
    # Allowed aggregate and window functions
    ALLOWED_FUNCTIONS = {
        # Aggregate functions
        'count', 'sum', 'avg', 'min', 'max', 'stddev', 'variance',
        # String functions
        'length', 'upper', 'lower', 'trim', 'substring', 'concat',
        # Date functions
        'date', 'year', 'month', 'day', 'hour', 'minute', 'second',
        'date_part', 'date_trunc', 'extract',
        # Math functions
        'abs', 'ceil', 'floor', 'round', 'sqrt', 'power', 'log',
        # Window functions
        'row_number', 'rank', 'dense_rank', 'lag', 'lead',
        # Conditional functions
        'case', 'coalesce', 'nullif', 'greatest', 'least'
    }
    
    # Pattern for detecting SQL comments (which could hide malicious code)
    COMMENT_PATTERNS = [
        r'--.*$',           # Single line comments
        r'/\*.*?\*/',       # Multi-line comments
        r'#.*$'             # MySQL-style comments
    ]
    
    # Pattern for detecting string literals (to avoid false positives in content)
    STRING_LITERAL_PATTERN = r"'(?:[^'\\]|\\.)*'"
    
    def __init__(self):
        """Initialize the SQL validator."""
        self.max_query_length = 2000  # Reasonable limit for natural language queries
        self.max_select_columns = 50  # Prevent overly complex queries
        
    def validate_query(self, query: str) -> str:
        """
        Validate and sanitize a SQL query.
        
        Args:
            query: The SQL query to validate
            
        Returns:
            str: The validated and sanitized query
            
        Raises:
            ValidationError: If the query is invalid or unsafe
        """
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        # Basic length check
        if len(query) > self.max_query_length:
            raise ValidationError(f"Query too long (max {self.max_query_length} characters)")
        
        # Normalize the query
        normalized_query = self._normalize_query(query)
        
        # Remove comments (potential attack vector)
        cleaned_query = self._remove_comments(normalized_query)
        
        # Validate query structure
        self._validate_query_structure(cleaned_query)
        
        # Check for dangerous keywords
        self._check_dangerous_keywords(cleaned_query)
        
        # Check for dangerous functions
        self._check_dangerous_functions(cleaned_query)
        
        # Validate SELECT statement structure
        self._validate_select_structure(cleaned_query)
        
        logger.info("SQL query validation passed")
        return cleaned_query.strip()
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize the query for consistent processing.
        
        Args:
            query: Raw query string
            
        Returns:
            str: Normalized query
        """
        # Convert to uppercase for keyword detection (but preserve original case for output)
        # Remove excessive whitespace
        normalized = ' '.join(query.split())
        return normalized
    
    def _remove_comments(self, query: str) -> str:
        """
        Remove SQL comments from the query.
        
        Args:
            query: Query with potential comments
            
        Returns:
            str: Query with comments removed
        """
        cleaned = query
        
        # Remove comments while preserving string literals
        for pattern in self.COMMENT_PATTERNS:
            # This is a simplified approach - in production, you'd want more sophisticated parsing
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
        
        return cleaned
    
    def _validate_query_structure(self, query: str) -> None:
        """
        Validate the overall structure of the query.
        
        Args:
            query: Query to validate
            
        Raises:
            ValidationError: If structure is invalid
        """
        query_upper = query.upper()
        
        # Must start with SELECT or WITH (for CTEs)
        if not (query_upper.strip().startswith('SELECT') or query_upper.strip().startswith('WITH')):
            raise ValidationError("Query must be a SELECT statement or start with WITH clause")
        
        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            raise ValidationError("Unbalanced parentheses in query")
        
        # Check for balanced quotes
        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            raise ValidationError("Unbalanced single quotes in query")
    
    def _check_dangerous_keywords(self, query: str) -> None:
        """
        Check for dangerous SQL keywords.
        
        Args:
            query: Query to check
            
        Raises:
            ValidationError: If dangerous keywords are found
        """
        query_upper = query.upper()
        
        # Remove string literals to avoid false positives
        query_no_strings = re.sub(self.STRING_LITERAL_PATTERN, "''", query_upper)
        
        for keyword in self.DANGEROUS_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, query_no_strings):
                logger.warning(f"Dangerous keyword detected in query: {keyword}")
                raise ValidationError(f"Query contains prohibited keyword: {keyword}")
    
    def _check_dangerous_functions(self, query: str) -> None:
        """
        Check for dangerous function calls.
        
        Args:
            query: Query to check
            
        Raises:
            ValidationError: If dangerous functions are found
        """
        query_upper = query.upper()
        
        # Remove string literals to avoid false positives
        query_no_strings = re.sub(self.STRING_LITERAL_PATTERN, "''", query_upper)
        
        for func in self.DANGEROUS_FUNCTIONS:
            # Look for function call pattern: function_name(
            pattern = r'\b' + re.escape(func.upper()) + r'\s*\('
            if re.search(pattern, query_no_strings):
                logger.warning(f"Dangerous function detected in query: {func}")
                raise ValidationError(f"Query contains prohibited function: {func}")
    
    def _validate_select_structure(self, query: str) -> None:
        """
        Validate the structure of SELECT statements.
        
        Args:
            query: Query to validate
            
        Raises:
            ValidationError: If SELECT structure is invalid
        """
        query_upper = query.upper()
        
        # Count SELECT clauses (should be reasonable)
        select_count = len(re.findall(r'\bSELECT\b', query_upper))
        if select_count > 5:  # Allow some subqueries but not excessive nesting
            raise ValidationError("Query contains too many SELECT statements (max 5)")
        
        # Check for UNION operations (can be used for injection)
        if 'UNION' in query_upper:
            # Allow UNION but validate it's not being used maliciously
            union_pattern = r'\bUNION\s+(ALL\s+)?SELECT\b'
            unions = re.findall(union_pattern, query_upper)
            if len(unions) > 3:  # Reasonable limit
                raise ValidationError("Query contains too many UNION operations")
    
    def extract_table_references(self, query: str) -> Set[str]:
        """
        Extract table names referenced in the query.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Set[str]: Set of table names found in the query
        """
        # This is a simplified implementation
        # In production, you'd want a proper SQL parser
        table_names = set()
        
        # Look for FROM and JOIN clauses
        from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        for pattern in [from_pattern, join_pattern]:
            matches = re.findall(pattern, query, re.IGNORECASE)
            table_names.update(matches)
        
        return table_names


# Global validator instance
sql_validator = SQLValidator()