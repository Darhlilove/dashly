"""
Integration tests for SQL validator with existing models and components.
"""

import pytest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sql_validator import sql_validator, ValidationResult, SecurityViolation, ParsedQuery
from exceptions import ValidationError


class TestSQLValidatorIntegration:
    """Integration tests for SQL validator with existing components."""
    
    def test_validator_with_existing_models(self):
        """Test that validator works with existing model structure."""
        # Test valid query
        result = sql_validator.validate_query("SELECT * FROM sales")
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        
        # Test invalid query
        result = sql_validator.validate_query("DROP TABLE sales")
        assert isinstance(result, ValidationResult)
        assert not result.is_valid
        assert len(result.errors) > 0
        assert len(result.security_violations) > 0
    
    def test_legacy_compatibility(self):
        """Test backward compatibility with existing code."""
        # Valid query should return string
        cleaned = sql_validator.validate_query_legacy("SELECT * FROM sales")
        assert isinstance(cleaned, str)
        assert "SELECT" in cleaned.upper()
        
        # Invalid query should raise ValidationError
        with pytest.raises(ValidationError):
            sql_validator.validate_query_legacy("DROP TABLE sales")
    
    def test_security_violations_structure(self):
        """Test that security violations have the expected structure."""
        result = sql_validator.validate_query("SELECT * FROM users; DROP TABLE users;")
        
        assert not result.is_valid
        assert len(result.security_violations) > 0
        
        violation = result.security_violations[0]
        assert isinstance(violation, SecurityViolation)
        assert hasattr(violation, 'violation_type')
        assert hasattr(violation, 'description')
        assert hasattr(violation, 'severity')
        assert hasattr(violation, 'position')
    
    def test_parsed_query_structure(self):
        """Test that parsed query has the expected structure."""
        result = sql_validator.validate_query("SELECT name, COUNT(*) FROM users GROUP BY name")
        
        assert result.is_valid
        assert result.parsed_query is not None
        
        parsed = result.parsed_query
        assert isinstance(parsed, ParsedQuery)
        assert hasattr(parsed, 'query_type')
        assert hasattr(parsed, 'tables')
        assert hasattr(parsed, 'columns')
        assert hasattr(parsed, 'has_joins')
        assert hasattr(parsed, 'has_aggregations')
        assert hasattr(parsed, 'complexity_score')
        
        assert parsed.query_type == "SELECT"
        assert parsed.has_aggregations == True
    
    def test_requirements_coverage(self):
        """Test that all requirements are covered by the validator."""
        
        # Requirement 2.1: Only allow SELECT statements
        valid_selects = [
            "SELECT * FROM users",
            "SELECT name FROM users WHERE active = 1",
            "WITH cte AS (SELECT * FROM users) SELECT * FROM cte"
        ]
        
        for query in valid_selects:
            result = sql_validator.validate_query(query)
            assert result.is_valid, f"Valid SELECT should pass: {query}"
            assert sql_validator.is_select_only(query), f"Should be SELECT only: {query}"
        
        # Requirement 2.2: Reject DDL operations
        ddl_queries = ["CREATE TABLE test (id INT)", "ALTER TABLE users ADD COLUMN email VARCHAR(255)", "DROP TABLE users"]
        
        for query in ddl_queries:
            result = sql_validator.validate_query(query)
            assert not result.is_valid, f"DDL should be rejected: {query}"
            assert not sql_validator.is_select_only(query), f"DDL should not be SELECT only: {query}"
        
        # Requirement 2.3: Reject DML operations
        dml_queries = ["INSERT INTO users (name) VALUES ('test')", "UPDATE users SET name = 'test'", "DELETE FROM users"]
        
        for query in dml_queries:
            result = sql_validator.validate_query(query)
            assert not result.is_valid, f"DML should be rejected: {query}"
            assert not sql_validator.is_select_only(query), f"DML should not be SELECT only: {query}"
        
        # Requirement 2.4: Reject administrative commands
        admin_queries = ["PRAGMA table_info(users)", "ATTACH DATABASE 'test.db'", "INSTALL 'extension'"]
        
        for query in admin_queries:
            result = sql_validator.validate_query(query)
            assert not result.is_valid, f"Admin command should be rejected: {query}"
            assert not sql_validator.is_select_only(query), f"Admin should not be SELECT only: {query}"
        
        # Requirement 2.6: Detect dangerous patterns
        dangerous_queries = [
            "SELECT * FROM users; DROP TABLE users;",
            "SELECT * FROM users -- malicious comment",
            "SELECT system('rm -rf /')"
        ]
        
        for query in dangerous_queries:
            result = sql_validator.validate_query(query)
            violations = sql_validator.check_dangerous_patterns(query)
            assert len(violations) > 0, f"Should detect dangerous patterns in: {query}"
    
    def test_error_handling_robustness(self):
        """Test that validator handles edge cases gracefully."""
        edge_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            None,  # None value
            "SELECT" * 1000,  # Very long query
            "SELECT * FROM users WHERE (((",  # Malformed query
        ]
        
        for query in edge_cases:
            try:
                result = sql_validator.validate_query(query)
                # Should always return a ValidationResult, never raise
                assert isinstance(result, ValidationResult)
                if query is None or not str(query).strip():
                    assert not result.is_valid
                    assert len(result.errors) > 0
            except Exception as e:
                pytest.fail(f"Validator should not raise exception for: {query}, got: {e}")


if __name__ == "__main__":
    pytest.main([__file__])