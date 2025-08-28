"""
Comprehensive error scenario tests for SQL execution API.

Tests all possible error conditions, edge cases, and error response formats
to ensure robust error handling across the entire system.
"""

import pytest
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
import os

# Set environment variables for testing
os.environ["REQUIRE_AUTH"] = "false"

from src.main import app

client = TestClient(app)


class TestRequestValidationErrors:
    """Test request validation and malformed input handling."""
    
    def test_missing_request_body(self):
        """Test handling of missing request body."""
        response = client.post("/api/execute")
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_empty_request_body(self):
        """Test handling of empty JSON request body."""
        response = client.post("/api/execute", json={})
        assert response.status_code == 422  # Missing required field
    
    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        response = client.post("/api/execute", 
                             data="invalid json content",
                             headers={"Content-Type": "application/json"})
        assert response.status_code == 422
    
    def test_wrong_content_type(self):
        """Test handling of wrong content type."""
        response = client.post("/api/execute", 
                             data="sql=SELECT 1",
                             headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 422
    
    def test_sql_field_wrong_type(self):
        """Test handling of sql field with wrong data type."""
        invalid_requests = [
            {"sql": 123},  # Number instead of string
            {"sql": ["SELECT 1"]},  # Array instead of string
            {"sql": {"query": "SELECT 1"}},  # Object instead of string
            {"sql": True},  # Boolean instead of string
        ]
        
        for request_data in invalid_requests:
            response = client.post("/api/execute", json=request_data)
            assert response.status_code == 422, f"Should reject invalid sql type: {request_data}"
    
    def test_extra_fields_in_request(self):
        """Test handling of extra fields in request."""
        request_with_extra = {
            "sql": "SELECT 1",
            "extra_field": "should_be_ignored",
            "another_field": 123
        }
        
        response = client.post("/api/execute", json=request_with_extra)
        # Should either succeed (ignoring extra fields) or return validation error
        assert response.status_code in [200, 422]
    
    def test_null_sql_field(self):
        """Test handling of null sql field."""
        response = client.post("/api/execute", json={"sql": None})
        assert response.status_code in [400, 422]
    
    def test_very_large_request(self):
        """Test handling of very large request."""
        # Create a very long SQL query
        long_sql = "SELECT " + ", ".join([f"'{i}' as col_{i}" for i in range(1000)])
        
        response = client.post("/api/execute", json={"sql": long_sql})
        # Should either succeed or fail with appropriate error
        assert response.status_code in [200, 400, 413]  # 413 = Payload Too Large


class TestSQLValidationErrors:
    """Test SQL validation error scenarios."""
    
    def test_empty_sql_variations(self):
        """Test various forms of empty SQL."""
        empty_sql_variations = [
            "",
            "   ",
            "\t",
            "\n",
            "\r\n",
            "  \t  \n  ",
        ]
        
        for sql in empty_sql_variations:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Empty SQL should be rejected: {repr(sql)}"
            
            data = response.json()
            assert "detail" in data
            assert data["detail"]["sql_error_type"] in ["syntax", "security"]
    
    def test_sql_injection_attempts(self):
        """Test detection of SQL injection attempts."""
        injection_attempts = [
            "SELECT * FROM users; DROP TABLE users; --",
            "SELECT * FROM users WHERE id = 1 OR 1=1 --",
            "SELECT * FROM users UNION SELECT * FROM passwords",
            "'; DROP TABLE users; --",
            "SELECT * FROM users WHERE name = 'admin'--",
            "SELECT * FROM users /* comment */ WHERE 1=1",
        ]
        
        for sql in injection_attempts:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Injection attempt should be blocked: {sql}"
            
            data = response.json()
            assert data["detail"]["sql_error_type"] == "security"
    
    def test_nested_query_limits(self):
        """Test handling of deeply nested queries."""
        # Create deeply nested subquery
        nested_query = "SELECT 1"
        for i in range(20):  # Very deep nesting
            nested_query = f"SELECT ({nested_query}) as nested_{i}"
        
        response = client.post("/api/execute", json={"sql": nested_query})
        # Should either succeed or fail with complexity limit
        assert response.status_code in [200, 400]
        
        if response.status_code == 400:
            data = response.json()
            assert data["detail"]["sql_error_type"] in ["syntax", "execution"]
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters in SQL."""
        unicode_queries = [
            "SELECT 'héllo wörld' as unicode_text",
            "SELECT '你好世界' as chinese_text",
            "SELECT 'emoji: 🚀🎉' as emoji_text",
            "SELECT 'special: !@#$%^&*()' as special_chars",
            "SELECT 'quotes: \"single\" and ''double''' as quotes",
        ]
        
        for sql in unicode_queries:
            response = client.post("/api/execute", json={"sql": sql})
            # Should handle unicode properly
            assert response.status_code in [200, 400]
            
            if response.status_code == 200:
                data = response.json()
                assert data["row_count"] == 1
    
    def test_case_sensitivity_in_validation(self):
        """Test case sensitivity in SQL validation."""
        case_variations = [
            ("select 1", "SELECT 1"),
            ("Select 1", "SELECT 1"),
            ("create table test (id int)", "CREATE TABLE test (id INT)"),
            ("CREATE table TEST (ID int)", "CREATE TABLE TEST (ID INT)"),
        ]
        
        for lower_case, upper_case in case_variations:
            lower_response = client.post("/api/execute", json={"sql": lower_case})
            upper_response = client.post("/api/execute", json={"sql": upper_case})
            
            # Both should have same validation result
            assert lower_response.status_code == upper_response.status_code, \
                f"Case sensitivity issue: {lower_case} vs {upper_case}"


class TestExecutionErrors:
    """Test SQL execution error scenarios."""
    
    def test_syntax_error_variations(self):
        """Test various syntax error scenarios."""
        syntax_errors = [
            "SELECT * FROM",  # Incomplete FROM
            "SELECT FROM users",  # Missing column list
            "SELECT * users",  # Missing FROM keyword
            "SELECT * FROM users WHERE",  # Incomplete WHERE
            "SELECT * FROM users WHERE (name = 'test'",  # Unbalanced parentheses
            "SELECT * FROM users WHERE name = 'test",  # Unbalanced quotes
            "SELECT * FROM users ORDER",  # Incomplete ORDER BY
            "SELECT * FROM users GROUP",  # Incomplete GROUP BY
            "SELCT * FROM users",  # Typo in SELECT
            "SELECT * FORM users",  # Typo in FROM
        ]
        
        for sql in syntax_errors:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Syntax error should be caught: {sql}"
            
            data = response.json()
            assert data["detail"]["sql_error_type"] in ["syntax", "execution"]
    
    def test_schema_errors(self):
        """Test schema-related error scenarios."""
        schema_errors = [
            "SELECT * FROM nonexistent_table_12345",
            "SELECT nonexistent_column FROM (SELECT 1 as id) t",
            "SELECT id FROM nonexistent_table WHERE name = 'test'",
            "SELECT users.name FROM nonexistent_users users",
            "SELECT * FROM table_that_definitely_does_not_exist",
        ]
        
        for sql in schema_errors:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Schema error should be caught: {sql}"
            
            data = response.json()
            assert data["detail"]["sql_error_type"] == "execution"
    
    def test_type_mismatch_errors(self):
        """Test type mismatch and conversion errors."""
        type_errors = [
            "SELECT 'text' + 123",  # String + number
            "SELECT DATE('invalid-date')",  # Invalid date format
            "SELECT 1 / 0",  # Division by zero
            "SELECT CAST('not-a-number' AS INTEGER)",  # Invalid cast
        ]
        
        for sql in type_errors:
            response = client.post("/api/execute", json={"sql": sql})
            # May succeed (with NULL/error handling) or fail
            assert response.status_code in [200, 400]
            
            if response.status_code == 400:
                data = response.json()
                assert data["detail"]["sql_error_type"] == "execution"
    
    def test_function_errors(self):
        """Test function-related errors."""
        function_errors = [
            "SELECT UNKNOWN_FUNCTION(1)",
            "SELECT LENGTH()",  # Missing argument
            "SELECT SUBSTRING('test', 'invalid')",  # Wrong argument type
            "SELECT DATE_ADD('2023-01-01', 'invalid')",  # Invalid interval
        ]
        
        for sql in function_errors:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Function error should be caught: {sql}"
            
            data = response.json()
            assert data["detail"]["sql_error_type"] == "execution"


class TestResourceLimitErrors:
    """Test resource limit and timeout error scenarios."""
    
    @patch('src.query_executor.QueryExecutor.execute_query')
    def test_timeout_error_simulation(self, mock_execute):
        """Test timeout error handling."""
        from src.exceptions import QueryTimeoutError
        
        mock_execute.side_effect = QueryTimeoutError(
            "Query execution timeout after 30 seconds", 
            timeout_seconds=30
        )
        
        response = client.post("/api/execute", json={"sql": "SELECT * FROM slow_table"})
        assert response.status_code == 408  # Request Timeout
        
        data = response.json()
        assert data["detail"]["sql_error_type"] == "timeout"
        assert "timeout" in data["detail"]["detail"].lower()
        assert "30" in data["detail"]["detail"]  # Should mention timeout duration
    
    @patch('src.query_executor.QueryExecutor.execute_with_limits')
    def test_result_set_too_large_error(self, mock_execute):
        """Test result set size limit error."""
        from src.exceptions import ResultSetTooLargeError
        
        mock_execute.side_effect = ResultSetTooLargeError(
            "Result set exceeds maximum size limit",
            max_rows=10000,
            actual_rows=50000
        )
        
        response = client.post("/api/execute", json={"sql": "SELECT * FROM huge_table"})
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"]["sql_error_type"] == "execution"
        assert "limit" in data["detail"]["detail"].lower()
    
    @patch('src.query_executor.QueryExecutor.execute_query')
    def test_concurrent_limit_error(self, mock_execute):
        """Test concurrent query limit error."""
        from src.exceptions import ConcurrentQueryLimitError
        
        mock_execute.side_effect = ConcurrentQueryLimitError(
            "Too many concurrent queries",
            max_concurrent=5
        )
        
        response = client.post("/api/execute", json={"sql": "SELECT 1"})
        assert response.status_code == 429  # Too Many Requests
        
        data = response.json()
        assert data["detail"]["sql_error_type"] == "execution"
        assert "concurrent" in data["detail"]["detail"].lower()
    
    def test_large_query_handling(self):
        """Test handling of very large queries."""
        # Create a query with many columns
        large_query = "SELECT " + ", ".join([f"{i} as col_{i}" for i in range(500)])
        
        response = client.post("/api/execute", json={"sql": large_query})
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 400, 413]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data["columns"]) == 500
            assert data["row_count"] == 1


class TestErrorResponseFormat:
    """Test error response format consistency."""
    
    def test_error_response_structure(self):
        """Test that all error responses have consistent structure."""
        error_scenarios = [
            ("security", "CREATE TABLE test (id INT)"),
            ("syntax", "SELECT * FROM WHERE"),
            ("execution", "SELECT * FROM nonexistent_table"),
        ]
        
        for error_type, sql in error_scenarios:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400
            
            data = response.json()
            
            # Check top-level structure
            assert "detail" in data
            assert isinstance(data["detail"], dict)
            
            # Check error detail structure
            error_detail = data["detail"]
            required_fields = ["error", "detail", "sql_error_type"]
            
            for field in required_fields:
                assert field in error_detail, f"Missing field {field} in {error_type} error"
            
            # Check field types
            assert isinstance(error_detail["error"], str)
            assert isinstance(error_detail["detail"], str)
            assert isinstance(error_detail["sql_error_type"], str)
            
            # Check optional fields
            if "position" in error_detail:
                assert isinstance(error_detail["position"], (int, type(None)))
            
            if "suggestions" in error_detail:
                assert isinstance(error_detail["suggestions"], list)
                for suggestion in error_detail["suggestions"]:
                    assert isinstance(suggestion, str)
                    assert len(suggestion) > 0
    
    def test_error_message_content(self):
        """Test that error messages are informative."""
        error_scenarios = [
            ("CREATE TABLE test (id INT)", "security", ["SELECT", "only"]),
            ("SELECT * FROM WHERE", "syntax", ["syntax", "error"]),
            ("SELECT * FROM nonexistent_xyz", "execution", ["table", "exist"]),
        ]
        
        for sql, expected_type, expected_keywords in error_scenarios:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400
            
            data = response.json()
            error_detail = data["detail"]
            
            assert error_detail["sql_error_type"] == expected_type
            
            # Error message should contain relevant keywords
            error_text = error_detail["detail"].lower()
            for keyword in expected_keywords:
                assert keyword.lower() in error_text, \
                    f"Error message should contain '{keyword}': {error_text}"
    
    def test_error_suggestions_quality(self):
        """Test that error suggestions are helpful."""
        response = client.post("/api/execute", json={"sql": "CREATE TABLE test (id INT)"})
        assert response.status_code == 400
        
        data = response.json()
        if "suggestions" in data["detail"]:
            suggestions = data["detail"]["suggestions"]
            
            # Should have at least one suggestion
            assert len(suggestions) > 0
            
            # Suggestions should be meaningful
            for suggestion in suggestions:
                assert len(suggestion) > 10  # Not just single words
                assert suggestion[0].isupper()  # Should be properly formatted
    
    def test_error_serialization(self):
        """Test that error responses can be properly serialized."""
        response = client.post("/api/execute", json={"sql": "INVALID SQL"})
        assert response.status_code == 400
        
        # Should be valid JSON
        data = response.json()
        
        # Should be able to serialize back to JSON
        json_str = json.dumps(data)
        parsed_back = json.loads(json_str)
        
        assert parsed_back == data


class TestEdgeCaseErrors:
    """Test edge case error scenarios."""
    
    def test_extremely_long_sql(self):
        """Test handling of extremely long SQL queries."""
        # Create a very long query (beyond reasonable limits)
        long_sql = "SELECT " + " + ".join([f"'{i}'" for i in range(10000)])
        
        response = client.post("/api/execute", json={"sql": long_sql})
        # Should handle gracefully
        assert response.status_code in [200, 400, 413]
    
    def test_deeply_nested_expressions(self):
        """Test handling of deeply nested expressions."""
        # Create deeply nested expression
        nested_expr = "1"
        for i in range(100):
            nested_expr = f"({nested_expr} + 1)"
        
        sql = f"SELECT {nested_expr} as result"
        
        response = client.post("/api/execute", json={"sql": sql})
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_binary_data_in_sql(self):
        """Test handling of binary data in SQL strings."""
        # SQL with binary/non-printable characters
        binary_sql = "SELECT '\x00\x01\x02' as binary_data"
        
        response = client.post("/api/execute", json={"sql": binary_sql})
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_sql_with_null_bytes(self):
        """Test handling of SQL with null bytes."""
        sql_with_null = "SELECT 'test\x00data' as null_byte_data"
        
        response = client.post("/api/execute", json={"sql": sql_with_null})
        # Should handle gracefully
        assert response.status_code in [200, 400]
    
    def test_concurrent_error_scenarios(self):
        """Test error handling under concurrent load."""
        import threading
        
        def execute_error_query(results, index):
            sql = f"SELECT * FROM nonexistent_table_{index}"
            response = client.post("/api/execute", json={"sql": sql})
            results[index] = {
                "status_code": response.status_code,
                "has_error_detail": "detail" in response.json() if response.status_code == 400 else False
            }
        
        results = {}
        threads = []
        
        # Execute multiple error queries concurrently
        for i in range(10):
            thread = threading.Thread(target=execute_error_query, args=(results, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should handle errors consistently
        for i, result in results.items():
            assert result["status_code"] == 400, f"Query {i} should return error"
            assert result["has_error_detail"], f"Query {i} should have error detail"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])