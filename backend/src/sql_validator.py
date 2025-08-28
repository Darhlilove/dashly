"""
SQL Query Validator for secure query processing.

Provides comprehensive validation for user-generated SQL queries to prevent
SQL injection and ensure only safe SELECT operations are allowed.
"""

import re
import logging
from typing import List, Set, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

try:
    from .exceptions import ValidationError, SQLSyntaxError, SQLSecurityError
    from .logging_config import get_logger
except ImportError:
    from exceptions import ValidationError, SQLSyntaxError, SQLSecurityError
    from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SecurityViolation:
    """Represents a security violation found during SQL validation."""
    violation_type: str
    description: str
    severity: str  # "error", "warning"
    position: Optional[int] = None


@dataclass
class ParsedQuery:
    """Represents a parsed SQL query with metadata."""
    query_type: str  # "SELECT", "INSERT", etc.
    tables: List[str]
    columns: List[str]
    has_joins: bool
    has_aggregations: bool
    complexity_score: int


@dataclass
class ValidationResult:
    """Result of SQL query validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    parsed_query: Optional[ParsedQuery] = None
    security_violations: List[SecurityViolation] = None
    
    def __post_init__(self):
        if self.security_violations is None:
            self.security_violations = []


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
    
    # DDL (Data Definition Language) operations - Requirements 2.2
    DDL_KEYWORDS = {
        'CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME'
    }
    
    # DML (Data Manipulation Language) operations - Requirements 2.3
    DML_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'MERGE', 'UPSERT'
    }
    
    # Administrative commands - Requirements 2.4
    ADMIN_KEYWORDS = {
        'PRAGMA', 'ATTACH', 'DETACH', 'INSTALL', 'LOAD', 'SET',
        'EXEC', 'EXECUTE', 'CALL', 'PROCEDURE', 'FUNCTION',
        'COMMIT', 'ROLLBACK', 'SAVEPOINT', 'BEGIN', 'START',
        'GRANT', 'REVOKE', 'DENY', 'BACKUP', 'RESTORE'
    }
    
    # All dangerous keywords combined
    DANGEROUS_KEYWORDS = DDL_KEYWORDS | DML_KEYWORDS | ADMIN_KEYWORDS
    
    # Dangerous functions that could be used for attacks
    DANGEROUS_FUNCTIONS = {
        'system', 'shell', 'exec', 'eval', 'load_extension',
        'read_file', 'write_file', 'glob', 'list_files'
    }
    
    # Potentially dangerous patterns - Requirements 2.6
    DANGEROUS_PATTERNS = [
        r';.*\w',           # Multiple statements
        r'--.*\w',          # Comments with content after
        r'/\*.*\*/',        # Block comments
        r'#.*\w',           # Hash comments with content
        r'\bxp_cmdshell\b', # SQL Server command execution
        r'\bsp_executesql\b', # SQL Server dynamic SQL
        r'\\\w+',           # Backslash escapes
    ]
    
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
        
    def validate_query(self, query: str) -> ValidationResult:
        """
        Validate a SQL query and return detailed validation results.
        
        Args:
            query: The SQL query to validate
            
        Returns:
            ValidationResult: Detailed validation results
        """
        errors = []
        warnings = []
        security_violations = []
        parsed_query = None
        
        # Handle None input
        if query is None:
            errors.append("Query cannot be None")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                security_violations=security_violations
            )
        
        if not query or not query.strip():
            errors.append("Query cannot be empty")
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                security_violations=security_violations
            )
        
        try:
            # Basic length check
            if len(query) > self.max_query_length:
                errors.append(f"Query too long (max {self.max_query_length} characters)")
            
            # Normalize the query
            normalized_query = self._normalize_query(query)
            
            # Check for basic syntax errors with position tracking
            syntax_errors = self._check_syntax_errors(query)
            for syntax_error in syntax_errors:
                errors.append(syntax_error.description)
                security_violations.append(syntax_error)
            
            # Parse the query to extract metadata
            parsed_query = self.parse_sql_statement(normalized_query)
            
            # Check if it's SELECT only - Requirements 2.1
            if not self.is_select_only(normalized_query):
                violation_pos = self._find_non_select_position(normalized_query)
                errors.append("Only SELECT statements are allowed")
                security_violations.append(SecurityViolation(
                    violation_type="non_select_statement",
                    description="Query contains non-SELECT operations",
                    severity="error",
                    position=violation_pos
                ))
            
            # Check for dangerous patterns - Requirements 2.6
            pattern_violations = self.check_dangerous_patterns(normalized_query)
            security_violations.extend(pattern_violations)
            
            # Add pattern violation errors
            for violation in pattern_violations:
                if violation.severity == "error":
                    errors.append(violation.description)
                else:
                    warnings.append(violation.description)
            
            # Additional structural validation
            structure_errors = self._validate_query_structure(normalized_query)
            errors.extend(structure_errors)
            
        except Exception as e:
            errors.append(f"Query parsing failed: {str(e)}")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info("SQL query validation passed")
        else:
            logger.warning(f"SQL query validation failed: {errors}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            parsed_query=parsed_query,
            security_violations=security_violations
        )
    
    def is_select_only(self, sql: str) -> bool:
        """
        Check if the SQL query contains only SELECT statements.
        
        Args:
            sql: SQL query to check
            
        Returns:
            bool: True if query contains only SELECT statements
        """
        sql_upper = sql.upper().strip()
        
        # Remove string literals to avoid false positives
        sql_no_strings = re.sub(self.STRING_LITERAL_PATTERN, "''", sql_upper)
        
        # Check for DDL operations
        for keyword in self.DDL_KEYWORDS:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sql_no_strings):
                return False
        
        # Check for DML operations
        for keyword in self.DML_KEYWORDS:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sql_no_strings):
                return False
        
        # Check for administrative commands
        for keyword in self.ADMIN_KEYWORDS:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, sql_no_strings):
                return False
        
        # Must start with SELECT or WITH (for CTEs)
        return sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')
    
    def check_dangerous_patterns(self, sql: str) -> List[SecurityViolation]:
        """
        Check for dangerous SQL patterns.
        
        Args:
            sql: SQL query to check
            
        Returns:
            List[SecurityViolation]: List of security violations found
        """
        violations = []
        sql_upper = sql.upper()
        
        # Remove string literals to avoid false positives
        sql_no_strings = re.sub(self.STRING_LITERAL_PATTERN, "''", sql_upper)
        
        # Check each dangerous pattern
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.finditer(pattern, sql_no_strings, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                violations.append(SecurityViolation(
                    violation_type="dangerous_pattern",
                    description=f"Dangerous pattern detected: {match.group()}",
                    severity="error",
                    position=match.start()
                ))
        
        # Check for dangerous functions
        for func in self.DANGEROUS_FUNCTIONS:
            pattern = r'\b' + re.escape(func.upper()) + r'\s*\('
            matches = re.finditer(pattern, sql_no_strings)
            for match in matches:
                violations.append(SecurityViolation(
                    violation_type="dangerous_function",
                    description=f"Dangerous function detected: {func}",
                    severity="error",
                    position=match.start()
                ))
        
        return violations
    
    def parse_sql_statement(self, sql: str) -> ParsedQuery:
        """
        Parse SQL statement to extract metadata.
        
        Args:
            sql: SQL query to parse
            
        Returns:
            ParsedQuery: Parsed query metadata
        """
        sql_upper = sql.upper()
        
        # Determine query type
        query_type = "UNKNOWN"
        if sql_upper.strip().startswith('SELECT'):
            query_type = "SELECT"
        elif sql_upper.strip().startswith('WITH'):
            query_type = "WITH"
        
        # Extract table references
        tables = list(self.extract_table_references(sql))
        
        # Extract column references (simplified)
        columns = self._extract_column_references(sql)
        
        # Check for joins
        has_joins = bool(re.search(r'\b(INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN|JOIN)\b', sql_upper))
        
        # Check for aggregations
        has_aggregations = bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX|GROUP\s+BY)\b', sql_upper))
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(sql, has_joins, has_aggregations)
        
        return ParsedQuery(
            query_type=query_type,
            tables=tables,
            columns=columns,
            has_joins=has_joins,
            has_aggregations=has_aggregations,
            complexity_score=complexity_score
        )
    
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
    
    def _validate_query_structure(self, query: str) -> List[str]:
        """
        Validate the overall structure of the query.
        
        Args:
            query: Query to validate
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        query_upper = query.upper()
        
        # Must start with SELECT or WITH (for CTEs)
        if not (query_upper.strip().startswith('SELECT') or query_upper.strip().startswith('WITH')):
            errors.append("Query must be a SELECT statement or start with WITH clause")
        
        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            errors.append("Unbalanced parentheses in query")
        
        # Check for balanced quotes
        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            errors.append("Unbalanced single quotes in query")
        
        return errors
    
    def _extract_column_references(self, sql: str) -> List[str]:
        """
        Extract column references from the SQL query (simplified implementation).
        
        Args:
            sql: SQL query to analyze
            
        Returns:
            List[str]: List of column names found in the query
        """
        columns = []
        
        # This is a simplified implementation
        # Look for SELECT clause columns
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # Split by comma and clean up
            column_parts = [col.strip() for col in select_clause.split(',')]
            for col in column_parts:
                # Remove aliases and functions, extract base column name
                col_clean = re.sub(r'\s+AS\s+\w+', '', col, flags=re.IGNORECASE)
                col_clean = re.sub(r'\w+\s*\(.*?\)', '', col_clean)  # Remove functions
                col_clean = col_clean.strip()
                if col_clean and col_clean != '*':
                    columns.append(col_clean)
        
        return columns
    
    def _calculate_complexity_score(self, sql: str, has_joins: bool, has_aggregations: bool) -> int:
        """
        Calculate a complexity score for the SQL query.
        
        Args:
            sql: SQL query
            has_joins: Whether query has joins
            has_aggregations: Whether query has aggregations
            
        Returns:
            int: Complexity score (higher = more complex)
        """
        score = 1  # Base score
        
        # Add points for various complexity factors
        if has_joins:
            score += 2
        if has_aggregations:
            score += 2
        
        # Count subqueries
        subquery_count = len(re.findall(r'\bSELECT\b', sql.upper())) - 1
        score += subquery_count
        
        # Count UNION operations
        union_count = len(re.findall(r'\bUNION\b', sql.upper()))
        score += union_count
        
        # Count window functions
        window_count = len(re.findall(r'\bOVER\s*\(', sql.upper()))
        score += window_count
        
        return score
    
    def _check_syntax_errors(self, query: str) -> List[SecurityViolation]:
        """
        Check for basic syntax errors with position tracking.
        
        Args:
            query: SQL query to check
            
        Returns:
            List[SecurityViolation]: List of syntax violations found
        """
        violations = []
        
        # Check for unbalanced parentheses
        paren_count = 0
        for i, char in enumerate(query):
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count < 0:
                    violations.append(SecurityViolation(
                        violation_type="syntax_error",
                        description="Unmatched closing parenthesis",
                        severity="error",
                        position=i
                    ))
                    break
        
        if paren_count > 0:
            # Find position of last unmatched opening parenthesis
            paren_count = 0
            last_open_pos = 0
            for i, char in enumerate(query):
                if char == '(':
                    paren_count += 1
                    last_open_pos = i
                elif char == ')':
                    paren_count -= 1
            
            violations.append(SecurityViolation(
                violation_type="syntax_error",
                description="Unmatched opening parenthesis",
                severity="error",
                position=last_open_pos
            ))
        
        # Check for unbalanced quotes
        in_single_quote = False
        escape_next = False
        for i, char in enumerate(query):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == "'" and not escape_next:
                in_single_quote = not in_single_quote
        
        if in_single_quote:
            # Find position of last unmatched quote
            last_quote_pos = query.rfind("'")
            violations.append(SecurityViolation(
                violation_type="syntax_error",
                description="Unmatched single quote",
                severity="error",
                position=last_quote_pos
            ))
        
        # Check for common SQL syntax patterns that indicate errors
        common_errors = [
            (r'\bSELECT\s*,', "SELECT statement cannot start with comma"),
            (r',\s*FROM\b', "Comma before FROM clause"),
            (r'\bWHERE\s*AND\b', "WHERE clause cannot start with AND"),
            (r'\bWHERE\s*OR\b', "WHERE clause cannot start with OR"),
            (r'\bORDER\s+BY\s*,', "ORDER BY cannot start with comma"),
            (r'\bGROUP\s+BY\s*,', "GROUP BY cannot start with comma"),
        ]
        
        for pattern, description in common_errors:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                violations.append(SecurityViolation(
                    violation_type="syntax_error",
                    description=description,
                    severity="error",
                    position=match.start()
                ))
        
        return violations
    
    def _find_non_select_position(self, query: str) -> Optional[int]:
        """
        Find the position of the first non-SELECT statement keyword.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Optional[int]: Position of the violation, or None if not found
        """
        query_upper = query.upper()
        
        # Remove string literals to avoid false positives
        query_no_strings = re.sub(self.STRING_LITERAL_PATTERN, "''", query_upper)
        
        # Check for dangerous keywords and return position of first match
        all_dangerous = self.DDL_KEYWORDS | self.DML_KEYWORDS | self.ADMIN_KEYWORDS
        
        for keyword in all_dangerous:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            match = re.search(pattern, query_no_strings)
            if match:
                return match.start()
        
        return None
    
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
    
    def validate_query_legacy(self, query: str) -> str:
        """
        Legacy method for backward compatibility.
        Validates query and returns cleaned query string or raises ValidationError.
        
        Args:
            query: The SQL query to validate
            
        Returns:
            str: The validated and sanitized query
            
        Raises:
            ValidationError: If the query is invalid or unsafe
        """
        result = self.validate_query(query)
        
        if not result.is_valid:
            # Raise the first error found
            error_msg = result.errors[0] if result.errors else "Query validation failed"
            raise ValidationError(error_msg)
        
        # Return the normalized query
        return self._normalize_query(query).strip()


# Global validator instance
sql_validator = SQLValidator()