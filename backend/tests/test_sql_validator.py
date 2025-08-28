"""
Unit tests for SQL validation component.

Tests cover security rule enforcement, DDL/DML detection, dangerous pattern detection,
and SELECT-only enforcement as specified in requirements 2.1-2.6 and 7.2.
"""

import pytest
from unittest.mock import patch, MagicMock

# Import the SQL validator components
try:
    from backend.src.sql_validator import (
        SQLValidator, 
        ValidationResult, 
        SecurityViolation, 
        ParsedQuery,
        sql_validator
    )
    from backend.src.exceptions import ValidationError
except ImportError:
    from src.sql_validator import (
        SQLValidator, 
        ValidationResult, 
        SecurityViolation, 
        ParsedQuery,
        sql_validator
    )
    from src.exceptions import ValidationError


class TestSQLValidator:
    """Test suite for SQLValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SQLValidator()
    
    # Test Requirement 2.1: Only allow SELECT statements
    def test_valid_select_query(self):
        """Test that valid SELECT queries pass validation."""
        valid_queries = [
            "SELECT * FROM sales",
            "SELECT id, name FROM users WHERE active = 1",
            "SELECT COUNT(*) FROM orders GROUP BY status",
            "SELECT a.name, b.total FROM customers a JOIN orders b ON a.id = b.customer_id",
            "WITH cte AS (SELECT * FROM sales) SELECT * FROM cte"
        ]
        
        for query in valid_queries:
            result = self.validator.validate_query(query)
            assert result.is_valid, f"Query should be valid: {query}"
            assert len(result.errors) == 0, f"No errors expected for: {query}"
            assert self.validator.is_select_only(query), f"Should be SELECT only: {query}"
    
    def test_reject_ddl_statements(self):
        """Test that DDL operations are rejected - Requirement 2.2."""
        ddl_queries = [
            "CREATE TABLE test (id INT)",
            "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
            "DROP TABLE old_data",
            "TRUNCATE TABLE logs",
            "RENAME TABLE old_name TO new_name"
        ]
        
        for query in ddl_queries:
            result = self.validator.validate_query(query)
            assert not result.is_valid, f"DDL query should be invalid: {query}"
            assert not self.validator.is_select_only(query), f"Should not be SELECT only: {query}"
            assert any("SELECT" in error for error in result.errors), f"Should mention SELECT requirement: {query}"
    
    def test_reject_dml_statements(self):
        """Test that DML operations are rejected - Requirement 2.3."""
        dml_queries = [
            "INSERT INTO users (name) VALUES ('test')",
            "UPDATE users SET name = 'updated' WHERE id = 1",
            "DELETE FROM users WHERE id = 1",
            "MERGE INTO target USING source ON target.id = source.id",
            "UPSERT INTO users (id, name) VALUES (1, 'test')"
        ]
        
        for query in dml_queries:
            result = self.validator.validate_query(query)
            assert not result.is_valid, f"DML query should be invalid: {query}"
            assert not self.validator.is_select_only(query), f"Should not be SELECT only: {query}"
            assert any("SELECT" in error for error in result.errors), f"Should mention SELECT requirement: {query}"
    
    def test_reject_administrative_commands(self):
        """Test that administrative commands are rejected - Requirement 2.4."""
        admin_queries = [
            "PRAGMA table_info(users)",
            "ATTACH DATABASE 'test.db' AS test",
            "DETACH DATABASE test",
            "INSTALL 'extension'",
            "LOAD 'extension'",
            "SET variable = value",
            "EXEC sp_help",
            "CALL procedure_name()",
            "GRANT SELECT ON users TO role",
            "REVOKE SELECT ON users FROM role"
        ]
        
        for query in admin_queries:
            result = self.validator.validate_query(query)
            assert not result.is_valid, f"Admin query should be invalid: {query}"
            assert not self.validator.is_select_only(query), f"Should not be SELECT only: {query}"
    
    def test_dangerous_pattern_detection(self):
        """Test detection of dangerous patterns - Requirement 2.6."""
        dangerous_queries = [
            "SELECT * FROM users; DROP TABLE users;",  # Multiple statements
            "SELECT * FROM users -- malicious comment with content",
            "SELECT * FROM users /* block comment */",
            "SELECT * FROM users # hash comment with content",
            "SELECT system('rm -rf /')",  # System function
            "SELECT read_file('/etc/passwd')",  # File access function
        ]
        
        for query in dangerous_queries:
            result = self.validator.validate_query(query)
            violations = self.validator.check_dangerous_patterns(query)
            
            # Should have security violations
            assert len(violations) > 0, f"Should detect dangerous patterns in: {query}"
            assert len(result.security_violations) > 0, f"Should have security violations: {query}"
    
    def test_security_violation_details(self):
        """Test that security violations contain proper details."""
        query = "SELECT * FROM users; DROP TABLE users;"
        violations = self.validator.check_dangerous_patterns(query)
        
        assert len(violations) > 0
        violation = violations[0]
        assert isinstance(violation, SecurityViolation)
        assert violation.violation_type in ["dangerous_pattern", "dangerous_function"]
        assert violation.severity in ["error", "warning"]
        assert violation.description is not None
    
    def test_parse_sql_statement(self):
        """Test SQL statement parsing functionality."""
        query = "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name"
        parsed = self.validator.parse_sql_statement(query)
        
        assert isinstance(parsed, ParsedQuery)
        assert parsed.query_type == "SELECT"
        assert parsed.has_joins == True
        assert parsed.has_aggregations == True
        assert len(parsed.tables) > 0
        assert parsed.complexity_score > 1
    
    def test_extract_table_references(self):
        """Test table reference extraction."""
        queries_and_tables = [
            ("SELECT * FROM users", {"users"}),
            ("SELECT * FROM users u JOIN orders o ON u.id = o.user_id", {"users", "orders"}),
            ("SELECT * FROM sales", {"sales"}),
        ]
        
        for query, expected_tables in queries_and_tables:
            tables = self.validator.extract_table_references(query)
            assert tables == expected_tables, f"Expected {expected_tables}, got {tables} for query: {query}"
    
    def test_query_structure_validation(self):
        """Test query structure validation."""
        invalid_structure_queries = [
            "SELECT * FROM users WHERE (name = 'test'",  # Unbalanced parentheses
            "SELECT * FROM users WHERE name = 'test",    # Unbalanced quotes
            "UPDATE users SET name = 'test'",            # Not a SELECT
        ]
        
        for query in invalid_structure_queries:
            result = self.validator.validate_query(query)
            assert not result.is_valid, f"Should be invalid: {query}"
            assert len(result.errors) > 0, f"Should have errors: {query}"
    
    def test_empty_query_validation(self):
        """Test validation of empty queries."""
        empty_queries = ["", "   "]
        
        for query in empty_queries:
            result = self.validator.validate_query(query)
            assert not result.is_valid
            assert "empty" in result.errors[0].lower()
        
        # Test None separately
        result = self.validator.validate_query(None)
        assert not result.is_valid
        assert "None" in result.errors[0] or "empty" in result.errors[0].lower()
    
    def test_query_length_limits(self):
        """Test query length validation."""
        # Create a very long query
        long_query = "SELECT " + ", ".join([f"col{i}" for i in range(1000)]) + " FROM users"
        
        result = self.validator.validate_query(long_query)
        assert not result.is_valid
        assert any("too long" in error for error in result.errors)
    
    def test_legacy_validation_method(self):
        """Test backward compatibility with legacy validation method."""
        valid_query = "SELECT * FROM users"
        invalid_query = "DROP TABLE users"
        
        # Valid query should return cleaned query
        cleaned = self.validator.validate_query_legacy(valid_query)
        assert isinstance(cleaned, str)
        assert "SELECT" in cleaned.upper()
        
        # Invalid query should raise ValidationError
        with pytest.raises(ValidationError):
            self.validator.validate_query_legacy(invalid_query)
    
    def test_complex_select_queries(self):
        """Test validation of complex but valid SELECT queries."""
        complex_queries = [
            """
            WITH monthly_sales AS (
                SELECT 
                    DATE_TRUNC('month', order_date) as month,
                    SUM(amount) as total_sales
                FROM orders 
                WHERE order_date >= '2023-01-01'
                GROUP BY DATE_TRUNC('month', order_date)
            )
            SELECT 
                month,
                total_sales,
                LAG(total_sales) OVER (ORDER BY month) as prev_month_sales
            FROM monthly_sales
            ORDER BY month
            """,
            """
            SELECT 
                u.name,
                COUNT(DISTINCT o.id) as order_count,
                AVG(o.amount) as avg_order_value,
                CASE 
                    WHEN COUNT(o.id) > 10 THEN 'High Value'
                    WHEN COUNT(o.id) > 5 THEN 'Medium Value'
                    ELSE 'Low Value'
                END as customer_tier
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            WHERE u.active = 1
            GROUP BY u.id, u.name
            HAVING COUNT(o.id) > 0
            ORDER BY avg_order_value DESC
            """
        ]
        
        for query in complex_queries:
            result = self.validator.validate_query(query)
            assert result.is_valid, f"Complex SELECT query should be valid: {query[:100]}..."
            assert result.parsed_query.query_type in ["SELECT", "WITH"]
    
    def test_string_literal_handling(self):
        """Test that string literals don't trigger false positives."""
        queries_with_strings = [
            "SELECT 'DROP TABLE users' as fake_command FROM users",
            "SELECT name FROM users WHERE description = 'INSERT new data'",
            "SELECT * FROM products WHERE name LIKE '%CREATE%'",
        ]
        
        for query in queries_with_strings:
            result = self.validator.validate_query(query)
            assert result.is_valid, f"Query with string literals should be valid: {query}"
    
    def test_case_insensitive_validation(self):
        """Test that validation works regardless of case."""
        queries = [
            "select * from users",
            "Select Name From Users Where Active = 1",
            "SELECT * FROM USERS",
        ]
        
        for query in queries:
            result = self.validator.validate_query(query)
            assert result.is_valid, f"Case should not matter: {query}"
    
    def test_global_validator_instance(self):
        """Test that the global validator instance works correctly."""
        query = "SELECT * FROM users"
        result = sql_validator.validate_query(query)
        assert result.is_valid
        
        # Test legacy method
        cleaned = sql_validator.validate_query_legacy(query)
        assert isinstance(cleaned, str)


class TestValidationResult:
    """Test suite for ValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult object creation."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Minor warning"],
            parsed_query=None,
            security_violations=[]
        )
        
        assert result.is_valid == True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.security_violations == []
    
    def test_validation_result_with_violations(self):
        """Test ValidationResult with security violations."""
        violation = SecurityViolation(
            violation_type="test",
            description="Test violation",
            severity="error",
            position=10
        )
        
        result = ValidationResult(
            is_valid=False,
            errors=["Test error"],
            warnings=[],
            security_violations=[violation]
        )
        
        assert not result.is_valid
        assert len(result.security_violations) == 1
        assert result.security_violations[0].violation_type == "test"


class TestSecurityViolation:
    """Test suite for SecurityViolation class."""
    
    def test_security_violation_creation(self):
        """Test SecurityViolation object creation."""
        violation = SecurityViolation(
            violation_type="dangerous_pattern",
            description="Multiple statements detected",
            severity="error",
            position=25
        )
        
        assert violation.violation_type == "dangerous_pattern"
        assert violation.description == "Multiple statements detected"
        assert violation.severity == "error"
        assert violation.position == 25


class TestParsedQuery:
    """Test suite for ParsedQuery class."""
    
    def test_parsed_query_creation(self):
        """Test ParsedQuery object creation."""
        parsed = ParsedQuery(
            query_type="SELECT",
            tables=["users", "orders"],
            columns=["name", "email"],
            has_joins=True,
            has_aggregations=False,
            complexity_score=3
        )
        
        assert parsed.query_type == "SELECT"
        assert len(parsed.tables) == 2
        assert len(parsed.columns) == 2
        assert parsed.has_joins == True
        assert parsed.has_aggregations == False
        assert parsed.complexity_score == 3


# Integration tests with mocked dependencies
class TestSQLValidatorIntegration:
    """Integration tests for SQL validator with mocked dependencies."""
    
    def test_validator_with_mocked_logger(self):
        """Test validator with mocked logger."""
        # The logger is initialized at module level, so we just test that validation works
        validator = SQLValidator()
        
        result = validator.validate_query("SELECT * FROM users")
        assert result.is_valid
    
    def test_validator_error_handling(self):
        """Test validator handles unexpected errors gracefully."""
        validator = SQLValidator()
        
        # Test with malformed input that might cause parsing errors
        malformed_queries = [
            "SELECT * FROM users WHERE (((",
            "SELECT * FROM users WHERE name = 'test' AND ((id = 1) OR (id = 2) AND",
        ]
        
        for query in malformed_queries:
            result = validator.validate_query(query)
            # Should not raise exception, should return invalid result
            assert not result.is_valid
            assert len(result.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__])