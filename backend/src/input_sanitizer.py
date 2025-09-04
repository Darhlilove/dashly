"""
Input sanitization module for security.
Provides comprehensive input validation and sanitization for user queries and LLM inputs.
"""

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

try:
    from .exceptions import ValidationError, SecurityError
    from .logging_config import get_logger
except ImportError:
    from exceptions import ValidationError, SecurityError
    from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    sanitized_input: str
    warnings: List[str]
    blocked_patterns: List[str]
    is_safe: bool


class InputSanitizer:
    """Comprehensive input sanitizer for user queries and LLM inputs."""
    
    # Prompt injection patterns that could manipulate LLM behavior
    PROMPT_INJECTION_PATTERNS = [
        r'ignore\s+previous\s+instructions',
        r'forget\s+everything',
        r'system\s*:',
        r'assistant\s*:',
        r'human\s*:',
        r'user\s*:',
        r'prompt\s*:',
        r'instruction\s*:',
        r'override\s+security',
        r'bypass\s+validation',
        r'execute\s+code',
        r'run\s+command',
        r'</s>',
        r'<\|endoftext\|>',
        r'###\s*instruction',
        r'###\s*system',
        r'role\s*=\s*["\']?(system|assistant)',
        r'content\s*=\s*["\']',
        r'\\n\\n',  # Encoded newlines that could break prompts
        r'\\r\\n',
        r'%0a%0d',  # URL encoded newlines
        r'%0d%0a',
    ]
    
    # SQL injection patterns (additional layer beyond SQL validator)
    SQL_INJECTION_PATTERNS = [
        r'union\s+select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into',
        r'update\s+set',
        r'exec\s*\(',
        r'execute\s*\(',
        r'sp_executesql',
        r'xp_cmdshell',
        r'--\s*\w',  # Comments with content
        r'/\*.*\*/',  # Block comments
        r';\s*\w',    # Multiple statements
        r'0x[0-9a-f]+',  # Hex values
        r'char\s*\(',
        r'ascii\s*\(',
        r'waitfor\s+delay',
        r'benchmark\s*\(',
    ]
    
    # Suspicious characters that could indicate injection attempts
    SUSPICIOUS_CHARS = {
        '\x00', '\x1a', '\x08', '\x09', '\x0a', '\x0d', '\x1b',  # Control chars
        '\u2028', '\u2029',  # Unicode line separators
    }
    
    # Maximum allowed lengths for different input types
    MAX_QUERY_LENGTH = 500
    MAX_SQL_LENGTH = 2000
    
    def __init__(self):
        """Initialize the input sanitizer."""
        self.blocked_count = 0
        logger.info("InputSanitizer initialized")
    
    def sanitize_user_query(self, query: str) -> SanitizationResult:
        """
        Sanitize user natural language query for LLM processing.
        
        Args:
            query: Raw user query
            
        Returns:
            SanitizationResult: Sanitized query with security metadata
        """
        if not query:
            return SanitizationResult(
                sanitized_input="",
                warnings=["Empty query provided"],
                blocked_patterns=[],
                is_safe=False
            )
        
        warnings = []
        blocked_patterns = []
        
        # Length validation
        if len(query) > self.MAX_QUERY_LENGTH:
            warnings.append(f"Query truncated from {len(query)} to {self.MAX_QUERY_LENGTH} characters")
            query = query[:self.MAX_QUERY_LENGTH]
        
        # Remove suspicious control characters
        original_query = query
        query = self._remove_suspicious_chars(query)
        if query != original_query:
            warnings.append("Suspicious control characters removed")
        
        # Check for prompt injection patterns
        injection_patterns = self._detect_prompt_injection(query)
        if injection_patterns:
            blocked_patterns.extend(injection_patterns)
            # Remove or neutralize injection patterns
            query = self._neutralize_injection_patterns(query, injection_patterns)
        
        # Basic SQL injection check (additional layer)
        sql_patterns = self._detect_sql_injection(query)
        if sql_patterns:
            blocked_patterns.extend(sql_patterns)
            warnings.append("Potential SQL injection patterns detected and neutralized")
        
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Final safety check
        is_safe = len(blocked_patterns) == 0 and len(query) > 0
        
        if blocked_patterns:
            self.blocked_count += 1
            logger.warning(f"Blocked patterns in user query: {blocked_patterns}")
        
        return SanitizationResult(
            sanitized_input=query,
            warnings=warnings,
            blocked_patterns=blocked_patterns,
            is_safe=is_safe
        )
    
    def validate_llm_generated_sql(self, sql: str, original_query: str) -> str:
        """
        Validate and sanitize LLM-generated SQL for additional security.
        
        Args:
            sql: LLM-generated SQL query
            original_query: Original user query for context
            
        Returns:
            str: Validated SQL query
            
        Raises:
            SecurityError: If SQL contains security violations
            ValidationError: If SQL is invalid
        """
        if not sql or not sql.strip():
            raise ValidationError("LLM generated empty SQL query")
        
        sql = sql.strip()
        
        # Length validation
        if len(sql) > self.MAX_SQL_LENGTH:
            raise SecurityError(f"Generated SQL exceeds maximum length ({self.MAX_SQL_LENGTH} chars)")
        
        # Must be SELECT only
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith('SELECT'):
            raise SecurityError("LLM must generate SELECT statements only")
        
        # Check for suspicious patterns that might bypass validation
        suspicious_patterns = [
            r'UNION\s+SELECT',
            r'EXEC\s*\(',
            r'EXECUTE\s*\(',
            r'DECLARE\s+@',
            r'--\s*\w',  # Comments with content
            r'/\*.*\*/',  # Block comments
            r';\s*\w',    # Multiple statements
            r'xp_cmdshell',
            r'sp_executesql',
            r'WAITFOR\s+DELAY',
            r'BENCHMARK\s*\(',
            r'SLEEP\s*\(',
            r'pg_sleep\s*\(',
            r'LOAD_FILE\s*\(',
            r'INTO\s+OUTFILE',
            r'INTO\s+DUMPFILE',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, sql_upper):
                logger.error(f"Suspicious SQL pattern detected: {pattern}")
                raise SecurityError(f"Generated SQL contains suspicious pattern: {pattern}")
        
        # Validate that it's querying expected tables
        if not self._validate_table_references(sql):
            raise SecurityError("Generated SQL references unexpected tables")
        
        # Check for excessive complexity that might indicate obfuscation
        complexity_score = self._calculate_sql_complexity(sql)
        if complexity_score > 10:  # Reasonable threshold
            logger.warning(f"High complexity SQL generated (score: {complexity_score})")
            raise SecurityError("Generated SQL is too complex for safety")
        
        logger.info(f"LLM-generated SQL validated successfully: {sql[:100]}...")
        return sql
    
    def _remove_suspicious_chars(self, text: str) -> str:
        """Remove suspicious control characters from input."""
        cleaned = text
        for char in self.SUSPICIOUS_CHARS:
            cleaned = cleaned.replace(char, '')
        return cleaned
    
    def _detect_prompt_injection(self, query: str) -> List[str]:
        """Detect prompt injection patterns in user query."""
        detected = []
        query_lower = query.lower()
        
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                detected.append(pattern)
        
        return detected
    
    def _detect_sql_injection(self, query: str) -> List[str]:
        """Detect SQL injection patterns in user query."""
        detected = []
        query_lower = query.lower()
        
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                detected.append(pattern)
        
        return detected
    
    def _neutralize_injection_patterns(self, query: str, patterns: List[str]) -> str:
        """Neutralize detected injection patterns."""
        neutralized = query
        
        # Replace dangerous patterns with safe alternatives
        replacements = {
            r'ignore\s+previous\s+instructions': 'analyze previous data',
            r'forget\s+everything': 'focus on current data',
            r'system\s*:': 'data system',
            r'assistant\s*:': 'data assistant',
            r'execute\s+code': 'analyze data',
            r'run\s+command': 'run query',
            r'--\s*\w': '',  # Remove comments
            r'/\*.*\*/': '',  # Remove block comments
            r';\s*\w': '',   # Remove additional statements
        }
        
        for pattern, replacement in replacements.items():
            neutralized = re.sub(pattern, replacement, neutralized, flags=re.IGNORECASE)
        
        return neutralized
    
    def _validate_table_references(self, sql: str) -> bool:
        """Validate that SQL only references expected tables."""
        # Extract table names from SQL (simplified)
        table_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        
        tables = []
        for pattern in [table_pattern, join_pattern]:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)
        
        # Expected tables in our system
        expected_tables = {'sales', 'products', 'customers', 'orders', 'demo'}
        
        for table in tables:
            if table.lower() not in expected_tables:
                logger.warning(f"Unexpected table reference: {table}")
                return False
        
        return True
    
    def _calculate_sql_complexity(self, sql: str) -> int:
        """Calculate complexity score for SQL query."""
        score = 0
        sql_upper = sql.upper()
        
        # Count various complexity indicators
        score += len(re.findall(r'\bSELECT\b', sql_upper))  # Subqueries
        score += len(re.findall(r'\bJOIN\b', sql_upper)) * 2  # Joins are complex
        score += len(re.findall(r'\bUNION\b', sql_upper)) * 3  # Unions are very complex
        score += len(re.findall(r'\bCASE\b', sql_upper))  # Case statements
        score += len(re.findall(r'\bWITH\b', sql_upper)) * 2  # CTEs
        score += len(re.findall(r'\bOVER\s*\(', sql_upper)) * 2  # Window functions
        
        # Count nested parentheses levels
        max_nesting = 0
        current_nesting = 0
        for char in sql:
            if char == '(':
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif char == ')':
                current_nesting -= 1
        
        score += max_nesting
        
        return score
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics for monitoring."""
        return {
            "blocked_queries_count": self.blocked_count,
            "sanitizer_active": True,
            "max_query_length": self.MAX_QUERY_LENGTH,
            "max_sql_length": self.MAX_SQL_LENGTH
        }


# Global sanitizer instance
input_sanitizer = InputSanitizer()