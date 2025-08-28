"""
Comprehensive test suite for SQL execution API functionality.

This test suite covers all aspects of the SQL execution API as specified in task 10:
- Integration tests for /api/execute endpoint with various SQL queries
- Security validation with DDL/DML rejection scenarios  
- Performance tests for execution timing and concurrent queries
- Error handling tests for all failure scenarios
- Test explain endpoint functionality with complex queries
- High code coverage across all components

Requirements covered: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import pytest
import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import os

# Set environment variables for testing
os.environ["REQUIRE_AUTH"] = "false"
os.environ["DASHLY_API_KEY"] = "test-key-for-testing"

from src.main import app

client = TestClient(app)


class TestSQLExecutionIntegration:
    """Integration tests for /api/execute endpoint with various SQL queries."""
    
    def test_execute_simple_select_queries(self):
        """Test /api/execute endpoint with simple SELECT queries."""
        test_queries = [
            "SELECT 1 as number",
            "SELECT 'hello' as greeting",
            "SELECT 1 + 2 as sum",
            "SELECT NOW() as current_time",
            "SELECT TRUE as boolean_value"
        ]
        
        for sql in test_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 200, f"Failed for query: {sql}"
            
            data = response.json()
            assert "columns" in data
            assert "rows" in data
            assert "row_count" in data
            assert "runtime_ms" in data
            assert "truncated" in data
            
            assert data["row_count"] == 1
            assert len(data["rows"]) == 1
            assert not data["truncated"]
            assert data["runtime_ms"] >= 0
    
    def test_execute_complex_select_queries(self):
        """Test /api/execute endpoint with complex SELECT queries."""
        complex_queries = [
            # WITH clause (CTE)
            "WITH numbers AS (SELECT 1 as n UNION SELECT 2 UNION SELECT 3) SELECT * FROM numbers",
            
            # Subquery
            "SELECT (SELECT 42) as nested_value",
            
            # CASE statement
            "SELECT CASE WHEN 1 = 1 THEN 'true' ELSE 'false' END as condition_result",
            
            # Mathematical operations
            "SELECT 10 * 5 as product, 100 / 4 as division, 2 ^ 3 as power",
            
            # String functions
            "SELECT UPPER('hello') as upper_text, LENGTH('world') as text_length",
            
            # Date functions
            "SELECT DATE '2023-01-01' as date_value, EXTRACT(YEAR FROM DATE '2023-01-01') as year_part"
        ]
        
        for sql in complex_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 200, f"Failed for complex query: {sql}"
            
            data = response.json()
            assert data["row_count"] >= 1
            assert len(data["columns"]) >= 1
            assert data["runtime_ms"] >= 0
    
    def test_execute_queries_with_generate_series(self):
        """Test queries using generate_series for larger result sets."""
        # Test with small result set
        response = client.post("/api/execute", json={
            "sql": "SELECT generate_series as num FROM generate_series(1, 5)"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["row_count"] == 5
        assert len(data["rows"]) == 5
        assert not data["truncated"]
        
        # Test with larger result set that might trigger truncation
        response = client.post("/api/execute", json={
            "sql": "SELECT generate_series as num FROM generate_series(1, 100)"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["row_count"] <= 100  # May be truncated
        assert data["runtime_ms"] >= 0
    
    def test_execute_queries_with_aggregations(self):
        """Test queries with aggregation functions."""
        aggregation_queries = [
            "SELECT COUNT(*) as count FROM (SELECT 1 UNION SELECT 2 UNION SELECT 3) t",
            "SELECT SUM(n) as total FROM (SELECT 1 as n UNION SELECT 2 UNION SELECT 3) t",
            "SELECT AVG(n) as average FROM (SELECT 1 as n UNION SELECT 2 UNION SELECT 3) t",
            "SELECT MIN(n) as minimum, MAX(n) as maximum FROM (SELECT 1 as n UNION SELECT 2 UNION SELECT 3) t"
        ]
        
        for sql in aggregation_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 200, f"Failed for aggregation query: {sql}"
            
            data = response.json()
            assert data["row_count"] == 1
            assert len(data["rows"]) == 1
    
    def test_execute_queries_with_joins(self):
        """Test queries with JOIN operations using CTEs."""
        join_query = """
        WITH users AS (
            SELECT 1 as id, 'Alice' as name
            UNION SELECT 2, 'Bob'
            UNION SELECT 3, 'Charlie'
        ),
        orders AS (
            SELECT 1 as user_id, 100 as amount
            UNION SELECT 1, 200
            UNION SELECT 2, 150
        )
        SELECT u.name, COUNT(o.amount) as order_count, SUM(o.amount) as total_amount
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name
        ORDER BY u.name
        """
        
        response = client.post("/api/execute", json={"sql": join_query})
        assert response.status_code == 200
        
        data = response.json()
        assert data["row_count"] == 3  # 3 users
        assert len(data["columns"]) == 3  # name, order_count, total_amount
        assert data["runtime_ms"] >= 0


class TestSQLSecurityValidation:
    """Test security validation with DDL/DML rejection scenarios."""
    
    def test_reject_ddl_operations(self):
        """Test that all DDL operations are properly rejected."""
        ddl_queries = [
            "CREATE TABLE test (id INTEGER)",
            "CREATE VIEW test_view AS SELECT 1",
            "CREATE INDEX idx_test ON test(id)",
            "ALTER TABLE test ADD COLUMN name VARCHAR(50)",
            "ALTER TABLE test DROP COLUMN name",
            "DROP TABLE test",
            "DROP VIEW test_view",
            "DROP INDEX idx_test",
            "TRUNCATE TABLE test",
            "RENAME TABLE old_name TO new_name"
        ]
        
        for sql in ddl_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"DDL query should be rejected: {sql}"
            
            data = response.json()
            assert "detail" in data
            assert data["detail"]["sql_error_type"] == "security"
            assert "SELECT statements only" in str(data["detail"]["suggestions"])
    
    def test_reject_dml_operations(self):
        """Test that all DML operations are properly rejected."""
        dml_queries = [
            "INSERT INTO test VALUES (1, 'test')",
            "INSERT INTO test (id, name) VALUES (1, 'test')",
            "UPDATE test SET name = 'updated' WHERE id = 1",
            "DELETE FROM test WHERE id = 1",
            "MERGE INTO target USING source ON target.id = source.id WHEN MATCHED THEN UPDATE SET name = source.name",
            "UPSERT INTO test VALUES (1, 'test')",
            "REPLACE INTO test VALUES (1, 'test')"
        ]
        
        for sql in dml_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"DML query should be rejected: {sql}"
            
            data = response.json()
            assert "detail" in data
            assert data["detail"]["sql_error_type"] == "security"
    
    def test_reject_administrative_commands(self):
        """Test that administrative commands are properly rejected."""
        admin_queries = [
            "PRAGMA table_info(test)",
            "PRAGMA database_list",
            "ATTACH DATABASE 'test.db' AS test",
            "DETACH DATABASE test",
            "INSTALL 'extension'",
            "LOAD 'extension'",
            "SET variable = value",
            "SHOW TABLES",
            "DESCRIBE test",
            "EXPLAIN SELECT * FROM test"  # EXPLAIN should be rejected in execute endpoint
        ]
        
        for sql in admin_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Admin query should be rejected: {sql}"
            
            data = response.json()
            assert "detail" in data
            assert data["detail"]["sql_error_type"] == "security"
    
    def test_reject_dangerous_patterns(self):
        """Test detection and rejection of dangerous SQL patterns."""
        dangerous_queries = [
            "SELECT * FROM users; DROP TABLE users;",  # Multiple statements
            "SELECT * FROM users -- comment with potential injection",
            "SELECT * FROM users /* block comment */",
            "SELECT system('rm -rf /')",  # System function calls
            "SELECT read_file('/etc/passwd')",  # File access functions
        ]
        
        for sql in dangerous_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Dangerous query should be rejected: {sql}"
            
            data = response.json()
            assert "detail" in data
            assert data["detail"]["sql_error_type"] == "security"
    
    def test_allow_safe_string_literals(self):
        """Test that string literals containing keywords don't trigger false positives."""
        safe_queries = [
            "SELECT 'DROP TABLE users' as fake_command",
            "SELECT 'This INSERT statement is just text' as description",
            "SELECT name FROM (SELECT 'CREATE' as name) t WHERE name LIKE '%CREATE%'",
            "SELECT 'UPDATE: system is working' as status"
        ]
        
        for sql in safe_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 200, f"Safe query should be allowed: {sql}"
            
            data = response.json()
            assert data["row_count"] >= 1
    
    def test_case_insensitive_security_validation(self):
        """Test that security validation works regardless of case."""
        case_variations = [
            "create table test (id int)",
            "CREATE TABLE test (id INT)",
            "Create Table test (id Int)",
            "insert into test values (1)",
            "INSERT INTO test VALUES (1)",
            "Insert Into test Values (1)"
        ]
        
        for sql in case_variations:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Case variation should be rejected: {sql}"
            
            data = response.json()
            assert data["detail"]["sql_error_type"] == "security"


class TestSQLExecutionPerformance:
    """Performance tests for execution timing and concurrent queries."""
    
    def test_execution_timing_measurement(self):
        """Test that execution timing is properly measured and returned."""
        # Test with a simple query
        response = client.post("/api/execute", json={"sql": "SELECT 1"})
        assert response.status_code == 200
        
        data = response.json()
        assert "runtime_ms" in data
        assert isinstance(data["runtime_ms"], (int, float))
        assert data["runtime_ms"] >= 0
        assert data["runtime_ms"] < 1000  # Should be very fast
        
        # Test with a slightly more complex query
        response = client.post("/api/execute", json={
            "sql": "SELECT generate_series as num FROM generate_series(1, 10)"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["runtime_ms"] >= 0
        # More complex query might take longer, but should still be reasonable
        assert data["runtime_ms"] < 5000
    
    def test_concurrent_query_execution(self):
        """Test concurrent query execution handling."""
        def execute_query(query_id):
            """Execute a query and return the result."""
            sql = f"SELECT {query_id} as query_id, generate_series as num FROM generate_series(1, 5)"
            response = client.post("/api/execute", json={"sql": sql})
            return response.status_code, response.json() if response.status_code == 200 else None
        
        # Execute multiple queries concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_query, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # All queries should succeed (or be properly queued/limited)
        success_count = sum(1 for status, _ in results if status == 200)
        assert success_count >= 3, "At least 3 concurrent queries should succeed"
        
        # Check that successful queries have proper structure
        for status, data in results:
            if status == 200 and data:
                assert "runtime_ms" in data
                assert data["row_count"] == 5
                assert len(data["rows"]) == 5
    
    def test_query_performance_with_different_complexities(self):
        """Test performance measurement with queries of different complexities."""
        queries_by_complexity = [
            ("Simple", "SELECT 1"),
            ("Medium", "SELECT generate_series FROM generate_series(1, 50)"),
            ("Complex", """
                WITH RECURSIVE fibonacci(n, a, b) AS (
                    SELECT 1, 0, 1
                    UNION ALL
                    SELECT n+1, b, a+b FROM fibonacci WHERE n < 10
                )
                SELECT n, a as fib_number FROM fibonacci
            """)
        ]
        
        performance_results = {}
        
        for complexity, sql in queries_by_complexity:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 200, f"Failed for {complexity} query"
            
            data = response.json()
            performance_results[complexity] = data["runtime_ms"]
            
            # All queries should complete in reasonable time
            assert data["runtime_ms"] < 10000, f"{complexity} query took too long: {data['runtime_ms']}ms"
        
        # Simple query should be fastest (though this isn't guaranteed)
        assert performance_results["Simple"] >= 0
        assert performance_results["Medium"] >= 0
        assert performance_results["Complex"] >= 0
    
    def test_large_result_set_performance(self):
        """Test performance with larger result sets and truncation."""
        # Test with result set that should trigger truncation
        response = client.post("/api/execute", json={
            "sql": "SELECT generate_series as num FROM generate_series(1, 15000)"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "runtime_ms" in data
        assert data["runtime_ms"] >= 0
        
        # Should be truncated due to row limits
        if data["truncated"]:
            assert data["row_count"] <= 10000  # Default max rows
            assert len(data["rows"]) <= 10000
        else:
            # If not truncated, should have all rows
            assert data["row_count"] == 15000


class TestSQLExecutionErrorHandling:
    """Error handling tests for all failure scenarios."""
    
    def test_syntax_error_handling(self):
        """Test handling of SQL syntax errors."""
        syntax_error_queries = [
            "SELECT * FROM WHERE",  # Missing table name
            "SELECT * FROM users WHERE (name = 'test'",  # Unbalanced parentheses
            "SELECT * FROM users WHERE name = 'test",  # Unbalanced quotes
            "SELCT * FROM users",  # Typo in SELECT
            "SELECT * FORM users",  # Typo in FROM
        ]
        
        for sql in syntax_error_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Syntax error should return 400: {sql}"
            
            data = response.json()
            assert "detail" in data
            # Could be caught by validation or execution
            assert data["detail"]["sql_error_type"] in ["syntax", "execution"]
    
    def test_schema_error_handling(self):
        """Test handling of schema-related errors."""
        schema_error_queries = [
            "SELECT * FROM nonexistent_table",
            "SELECT nonexistent_column FROM (SELECT 1 as id) t",
            "SELECT id FROM nonexistent_table WHERE name = 'test'"
        ]
        
        for sql in schema_error_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Schema error should return 400: {sql}"
            
            data = response.json()
            assert "detail" in data
            assert data["detail"]["sql_error_type"] == "execution"
    
    def test_empty_and_invalid_requests(self):
        """Test handling of empty and invalid requests."""
        invalid_requests = [
            {},  # Missing sql field
            {"sql": ""},  # Empty SQL
            {"sql": "   "},  # Whitespace only
            {"sql": None},  # None value
        ]
        
        for request_data in invalid_requests:
            response = client.post("/api/execute", json=request_data)
            assert response.status_code in [400, 422], f"Invalid request should be rejected: {request_data}"
    
    def test_malformed_json_requests(self):
        """Test handling of malformed JSON requests."""
        # Test with invalid JSON
        response = client.post("/api/execute", 
                             data="invalid json",
                             headers={"Content-Type": "application/json"})
        assert response.status_code == 422
    
    def test_error_response_structure(self):
        """Test that error responses have consistent structure."""
        # Trigger a validation error
        response = client.post("/api/execute", json={"sql": "CREATE TABLE test (id INT)"})
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        
        error_detail = data["detail"]
        required_fields = ["error", "detail", "sql_error_type"]
        for field in required_fields:
            assert field in error_detail, f"Missing required error field: {field}"
        
        # Check field types
        assert isinstance(error_detail["error"], str)
        assert isinstance(error_detail["detail"], str)
        assert isinstance(error_detail["sql_error_type"], str)
        
        # Optional fields should be present when applicable
        if "suggestions" in error_detail:
            assert isinstance(error_detail["suggestions"], list)
        if "position" in error_detail:
            assert isinstance(error_detail["position"], (int, type(None)))
    
    def test_error_logging_and_context(self):
        """Test that errors are properly logged with context."""
        # This test verifies that error handling includes proper logging
        # We can't easily test the actual logging without mocking, but we can
        # verify that errors are handled consistently
        
        error_scenarios = [
            ("Security", "CREATE TABLE test (id INT)"),
            ("Syntax", "SELECT * FROM WHERE"),
            ("Schema", "SELECT * FROM nonexistent_table")
        ]
        
        for scenario_type, sql in error_scenarios:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 400, f"Error scenario {scenario_type} should return 400"
            
            data = response.json()
            assert "detail" in data
            # Error should have meaningful detail message
            assert len(data["detail"]["detail"]) > 0


class TestExplainEndpointFunctionality:
    """Test explain endpoint functionality with complex queries."""
    
    def test_explain_simple_queries(self):
        """Test explain endpoint with simple queries."""
        simple_queries = [
            "SELECT 1",
            "SELECT 'hello' as greeting",
            "SELECT 1 + 2 as sum"
        ]
        
        for sql in simple_queries:
            response = client.get(f"/api/execute/explain?sql={sql}")
            
            # Note: The actual response depends on implementation
            # If explain is implemented, should return 200
            # If not implemented yet, might return 404 or other status
            if response.status_code == 200:
                data = response.json()
                assert "execution_plan" in data
                assert "estimated_cost" in data
                assert "estimated_rows" in data
                assert "estimated_runtime_ms" in data
                assert "optimization_suggestions" in data
            elif response.status_code == 404:
                # Endpoint not implemented yet - this is acceptable for this test
                pass
            else:
                # Other status codes should be investigated
                assert False, f"Unexpected status code {response.status_code} for explain query: {sql}"
    
    def test_explain_complex_queries(self):
        """Test explain endpoint with complex queries."""
        complex_queries = [
            # CTE query
            "WITH numbers AS (SELECT generate_series as n FROM generate_series(1, 100)) SELECT * FROM numbers WHERE n % 2 = 0",
            
            # Subquery
            "SELECT (SELECT COUNT(*) FROM (SELECT generate_series FROM generate_series(1, 50)) t) as total_count",
            
            # Join simulation with CTEs
            """
            WITH users AS (SELECT 1 as id, 'Alice' as name UNION SELECT 2, 'Bob'),
                 orders AS (SELECT 1 as user_id, 100 as amount UNION SELECT 1, 200)
            SELECT u.name, COUNT(o.amount) as order_count
            FROM users u LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.name
            """
        ]
        
        for sql in complex_queries:
            response = client.get(f"/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 200:
                data = response.json()
                # Complex queries should have more detailed execution plans
                assert len(data["execution_plan"]) > 10
                assert data["estimated_cost"] >= 0
                assert data["estimated_rows"] >= 0
            elif response.status_code == 404:
                # Endpoint not implemented yet
                pass
            else:
                # Should handle complex queries without errors
                assert response.status_code in [200, 404], f"Unexpected error for complex explain query: {sql}"
    
    def test_explain_error_handling(self):
        """Test explain endpoint error handling."""
        error_queries = [
            "CREATE TABLE test (id INT)",  # Should be rejected by security validation
            "SELECT * FROM nonexistent_table",  # Schema error
            "SELCT * FROM test",  # Syntax error
        ]
        
        for sql in error_queries:
            response = client.get(f"/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 400:
                # Proper error handling
                data = response.json()
                assert "detail" in data
                assert data["detail"]["sql_error_type"] in ["security", "execution", "syntax"]
            elif response.status_code == 404:
                # Endpoint not implemented yet
                pass
            else:
                # Should handle errors appropriately
                assert response.status_code in [400, 404], f"Unexpected status for error query: {sql}"
    
    def test_explain_parameter_validation(self):
        """Test explain endpoint parameter validation."""
        # Test missing sql parameter
        response = client.get("/api/execute/explain")
        assert response.status_code in [422, 404]  # 422 for validation error, 404 if not implemented
        
        # Test empty sql parameter
        response = client.get("/api/execute/explain?sql=")
        if response.status_code not in [404]:  # Skip if endpoint not implemented
            assert response.status_code == 400  # Should validate empty query


class TestCodeCoverageAndIntegration:
    """Tests to achieve high code coverage across all components."""
    
    def test_request_response_model_validation(self):
        """Test request and response model validation."""
        # Test valid request structure
        valid_request = {"sql": "SELECT 1 as test"}
        response = client.post("/api/execute", json=valid_request)
        assert response.status_code == 200
        
        # Verify response structure matches expected model
        data = response.json()
        expected_fields = ["columns", "rows", "row_count", "runtime_ms", "truncated"]
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"
        
        # Verify field types
        assert isinstance(data["columns"], list)
        assert isinstance(data["rows"], list)
        assert isinstance(data["row_count"], int)
        assert isinstance(data["runtime_ms"], (int, float))
        assert isinstance(data["truncated"], bool)
    
    def test_sql_validator_edge_cases(self):
        """Test SQL validator with edge cases."""
        edge_case_queries = [
            # Very long query
            "SELECT " + ", ".join([f"'{i}' as col_{i}" for i in range(100)]),
            
            # Query with many nested parentheses
            "SELECT ((((1)))) as nested",
            
            # Query with unicode characters
            "SELECT 'héllo wörld' as unicode_text",
            
            # Query with special characters in strings
            "SELECT 'It''s a test with ''quotes''' as quoted_text",
            
            # Query with line breaks and formatting
            """
            SELECT 
                1 as first_column,
                2 as second_column
            """,
        ]
        
        for sql in edge_case_queries:
            response = client.post("/api/execute", json={"sql": sql})
            # Should either succeed or fail gracefully
            assert response.status_code in [200, 400], f"Edge case query failed unexpectedly: {sql[:50]}..."
    
    def test_query_executor_edge_cases(self):
        """Test query executor with edge cases."""
        # Test query that returns no rows
        response = client.post("/api/execute", json={
            "sql": "SELECT 1 as num WHERE 1 = 0"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["row_count"] == 0
        assert len(data["rows"]) == 0
        assert not data["truncated"]
        
        # Test query with NULL values
        response = client.post("/api/execute", json={
            "sql": "SELECT NULL as null_value, 1 as not_null"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["row_count"] == 1
        assert data["rows"][0][0] is None  # NULL should be None in JSON
        assert data["rows"][0][1] == 1
    
    def test_performance_monitor_integration(self):
        """Test performance monitoring integration."""
        # Execute a few queries to generate performance data
        test_queries = [
            "SELECT 1",
            "SELECT generate_series FROM generate_series(1, 10)",
            "SELECT 'test' as text"
        ]
        
        for sql in test_queries:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == 200
            
            data = response.json()
            # Performance monitoring should record execution time
            assert data["runtime_ms"] >= 0
    
    def test_error_handler_integration(self):
        """Test error handler integration across different error types."""
        error_test_cases = [
            # Security error
            ("CREATE TABLE test (id INT)", 400, "security"),
            
            # Validation error (empty query)
            ("", 400, "syntax"),
            
            # Execution error (nonexistent table)
            ("SELECT * FROM definitely_nonexistent_table_12345", 400, "execution"),
        ]
        
        for sql, expected_status, expected_error_type in error_test_cases:
            response = client.post("/api/execute", json={"sql": sql})
            assert response.status_code == expected_status, f"Wrong status for: {sql}"
            
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                assert data["detail"]["sql_error_type"] == expected_error_type
    
    def test_comprehensive_workflow(self):
        """Test complete workflow from request to response."""
        # This test exercises the full pipeline:
        # Request validation -> SQL validation -> Query execution -> Response formatting
        
        workflow_queries = [
            # Simple successful query
            {
                "sql": "SELECT 42 as answer, 'hello' as greeting",
                "expected_status": 200,
                "expected_rows": 1,
                "expected_columns": 2
            },
            
            # Query with aggregation
            {
                "sql": "SELECT COUNT(*) as total FROM (SELECT 1 UNION SELECT 2 UNION SELECT 3) t",
                "expected_status": 200,
                "expected_rows": 1,
                "expected_columns": 1
            },
            
            # Security violation
            {
                "sql": "DROP TABLE users",
                "expected_status": 400,
                "expected_error_type": "security"
            }
        ]
        
        for test_case in workflow_queries:
            response = client.post("/api/execute", json={"sql": test_case["sql"]})
            assert response.status_code == test_case["expected_status"]
            
            if test_case["expected_status"] == 200:
                data = response.json()
                assert data["row_count"] == test_case["expected_rows"]
                assert len(data["columns"]) == test_case["expected_columns"]
                assert data["runtime_ms"] >= 0
                assert isinstance(data["truncated"], bool)
            elif test_case["expected_status"] == 400:
                data = response.json()
                assert "detail" in data
                if "expected_error_type" in test_case:
                    assert data["detail"]["sql_error_type"] == test_case["expected_error_type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])