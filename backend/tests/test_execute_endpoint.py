"""
Tests for the SQL execution endpoint.
"""

import pytest
from fastapi.testclient import TestClient
import os

# Set environment variable for testing
os.environ["REQUIRE_AUTH"] = "false"

from src.main import app

client = TestClient(app)


class TestExecuteEndpoint:
    """Test cases for the /api/execute endpoint."""
    
    def test_execute_endpoint_exists(self):
        """Test that the execute endpoint exists and accepts POST requests."""
        # Test with invalid JSON to check endpoint exists
        response = client.post("/api/execute", json={})
        # Should return 422 for validation error, not 404
        assert response.status_code == 422
    
    def test_execute_valid_select_query(self):
        """Test executing a valid SELECT query."""
        request_data = {
            "sql": "SELECT 1 as test_column"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "columns" in data
        assert "rows" in data
        assert "row_count" in data
        assert "runtime_ms" in data
        assert "truncated" in data
        
        # Verify the actual result
        assert data["columns"] == ["test_column"]
        assert data["rows"] == [[1]]
        assert data["row_count"] == 1
        assert data["truncated"] is False
        assert isinstance(data["runtime_ms"], (int, float))
        assert data["runtime_ms"] >= 0
    
    def test_execute_missing_sql_field(self):
        """Test that missing sql field returns validation error."""
        response = client.post("/api/execute", json={})
        assert response.status_code == 422
    
    def test_execute_empty_sql_query(self):
        """Test that empty SQL query returns validation error."""
        request_data = {
            "sql": ""
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "sqlsyntax_failed"
        assert data["detail"]["sql_error_type"] == "syntax"
    
    def test_execute_ddl_query_rejected(self):
        """Test that DDL queries are rejected."""
        request_data = {
            "sql": "CREATE TABLE test (id INTEGER)"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "sqlsecurity_failed"
        assert data["detail"]["sql_error_type"] == "security"
        assert "SELECT statements only" in str(data["detail"]["suggestions"])
    
    def test_execute_dml_query_rejected(self):
        """Test that DML queries are rejected."""
        request_data = {
            "sql": "INSERT INTO test VALUES (1)"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "sqlsecurity_failed"
        assert data["detail"]["sql_error_type"] == "security"
    
    def test_execute_admin_query_rejected(self):
        """Test that administrative queries are rejected."""
        request_data = {
            "sql": "PRAGMA table_info(test)"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "sqlsecurity_failed"
        assert data["detail"]["sql_error_type"] == "security"
    
    def test_execute_complex_select_query(self):
        """Test executing a more complex SELECT query."""
        request_data = {
            "sql": "SELECT 'test' as name, 42 as value, 3.14 as pi"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["columns"] == ["name", "value", "pi"]
        assert data["rows"] == [["test", 42, 3.14]]
        assert data["row_count"] == 1
        assert data["truncated"] is False
    
    def test_execute_query_with_limit(self):
        """Test executing a query with LIMIT clause."""
        request_data = {
            "sql": "SELECT generate_series as num FROM generate_series(1, 5) LIMIT 3"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["columns"] == ["num"]
        assert len(data["rows"]) == 3
        assert data["row_count"] == 3
        assert data["rows"] == [[1], [2], [3]]
    
    def test_execute_invalid_table_reference(self):
        """Test that invalid table references return appropriate errors."""
        request_data = {
            "sql": "SELECT * FROM nonexistent_table"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "sqlschema_failed"
        assert data["detail"]["sql_error_type"] == "schema"
    
    def test_execute_syntax_error(self):
        """Test that syntax errors are handled properly."""
        request_data = {
            "sql": "SELECT * FROM WHERE"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "detail" in data
        # Could be validation or execution error depending on parser
        assert data["detail"]["error"] in ["sqlsyntax_failed", "queryexecution_failed"]
    
    def test_execute_response_format(self):
        """Test that the response format matches the expected schema."""
        request_data = {
            "sql": "SELECT 1 as id, 'test' as name"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify all required fields are present
        required_fields = ["columns", "rows", "row_count", "runtime_ms", "truncated"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify field types
        assert isinstance(data["columns"], list)
        assert isinstance(data["rows"], list)
        assert isinstance(data["row_count"], int)
        assert isinstance(data["runtime_ms"], (int, float))
        assert isinstance(data["truncated"], bool)
        
        # Verify data consistency
        assert len(data["rows"]) == data["row_count"]
        if data["rows"]:
            assert len(data["rows"][0]) == len(data["columns"])
    
    def test_execute_performance_monitoring(self):
        """Test that performance monitoring is working."""
        request_data = {
            "sql": "SELECT 1"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Runtime should be measured and positive
        assert data["runtime_ms"] >= 0
        # For a simple query, runtime should be reasonable (less than 1 second)
        assert data["runtime_ms"] < 1000
    
    def test_execute_with_cte(self):
        """Test that WITH clauses (CTEs) are allowed."""
        request_data = {
            "sql": "WITH test_cte AS (SELECT 1 as id) SELECT * FROM test_cte"
        }
        
        response = client.post("/api/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["columns"] == ["id"]
        assert data["rows"] == [[1]]
        assert data["row_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])