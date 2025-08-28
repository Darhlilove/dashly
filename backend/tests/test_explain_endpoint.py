"""
Integration tests for the /api/execute/explain endpoint.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

# Set environment variables for testing
os.environ["REQUIRE_AUTH"] = "false"
os.environ["DASHLY_API_KEY"] = "test-key-for-testing"

# Add src directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import after setting environment variables
from main import app

client = TestClient(app)


class TestExplainEndpoint:
    """Test cases for the /api/execute/explain endpoint."""
    
    def test_explain_endpoint_success(self):
        """Test successful query explanation."""
        # Mock the query explain service to return a successful result
        with patch('main.query_explain_service') as mock_service:
            # Create mock explanation result
            mock_result = Mock()
            mock_result.execution_plan = "SEQUENTIAL_SCAN(sales)"
            mock_result.estimated_cost = 50.0
            mock_result.estimated_rows = 1000
            mock_result.estimated_runtime_ms = 25.5
            mock_result.optimization_suggestions = ["Consider adding WHERE clause"]
            
            mock_service.explain_query.return_value = mock_result
            
            # Make request to explain endpoint
            response = client.get("/api/execute/explain?sql=SELECT * FROM sales")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            assert data["execution_plan"] == "SEQUENTIAL_SCAN(sales)"
            assert data["estimated_cost"] == 50.0
            assert data["estimated_rows"] == 1000
            assert data["estimated_runtime_ms"] == 25.5
            assert data["optimization_suggestions"] == ["Consider adding WHERE clause"]
            
            # Verify service was called with correct SQL
            mock_service.explain_query.assert_called_once_with("SELECT * FROM sales")
    
    def test_explain_endpoint_validation_error(self):
        """Test explain endpoint with validation error."""
        from exceptions import ValidationError
        
        with patch('main.query_explain_service') as mock_service:
            # Mock validation error
            mock_service.explain_query.side_effect = ValidationError("Only SELECT statements allowed")
            
            # Make request with invalid SQL
            response = client.get("/api/execute/explain?sql=DROP TABLE sales")
            
            # Verify error response
            assert response.status_code == 400
            data = response.json()
            
            assert data["detail"]["error"] == "sql_validation_failed"
            assert "Only SELECT statements allowed" in data["detail"]["detail"]
            assert data["detail"]["sql_error_type"] == "syntax"
    
    def test_explain_endpoint_explain_error(self):
        """Test explain endpoint with explain-specific error."""
        from exceptions import QueryExplainError
        
        with patch('main.query_explain_service') as mock_service:
            # Mock explain error
            mock_service.explain_query.side_effect = QueryExplainError("Failed to generate execution plan")
            
            # Make request
            response = client.get("/api/execute/explain?sql=SELECT * FROM nonexistent_table")
            
            # Verify error response
            assert response.status_code == 400
            data = response.json()
            
            assert data["detail"]["error"] == "query_explain_failed"
            assert "Failed to generate execution plan" in data["detail"]["detail"]
            assert data["detail"]["sql_error_type"] == "explain"
    
    def test_explain_endpoint_internal_error(self):
        """Test explain endpoint with unexpected error."""
        with patch('main.query_explain_service') as mock_service:
            # Mock unexpected error
            mock_service.explain_query.side_effect = Exception("Unexpected database error")
            
            # Make request
            response = client.get("/api/execute/explain?sql=SELECT * FROM sales")
            
            # Verify error response
            assert response.status_code == 500
            data = response.json()
            
            assert data["detail"]["error"] == "internal_server_error"
            assert "unexpected error occurred" in data["detail"]["detail"]
            assert data["detail"]["sql_error_type"] == "internal"
    
    def test_explain_endpoint_missing_sql_parameter(self):
        """Test explain endpoint without sql parameter."""
        # Make request without sql parameter
        response = client.get("/api/execute/explain")
        
        # Verify error response
        assert response.status_code == 422  # Validation error for missing parameter
    
    def test_explain_endpoint_empty_sql_parameter(self):
        """Test explain endpoint with empty sql parameter."""
        # Make request with empty sql parameter
        response = client.get("/api/execute/explain?sql=")
        
        # Should still call the service, which will handle validation
        with patch('main.query_explain_service') as mock_service:
            from exceptions import ValidationError
            mock_service.explain_query.side_effect = ValidationError("Query cannot be empty")
            
            response = client.get("/api/execute/explain?sql=")
            
            # Verify error response
            assert response.status_code == 400
    
    def test_explain_endpoint_complex_query(self):
        """Test explain endpoint with complex query."""
        with patch('main.query_explain_service') as mock_service:
            # Create mock result for complex query
            mock_result = Mock()
            mock_result.execution_plan = "HASH_JOIN\n  SEQUENTIAL_SCAN(sales)\n  SEQUENTIAL_SCAN(customers)"
            mock_result.estimated_cost = 250.0
            mock_result.estimated_rows = 5000
            mock_result.estimated_runtime_ms = 125.5
            mock_result.optimization_suggestions = [
                "Consider adding indexes on join columns",
                "Large result set - consider using LIMIT"
            ]
            
            mock_service.explain_query.return_value = mock_result
            
            # Make request with complex query
            complex_sql = "SELECT s.*, c.name FROM sales s JOIN customers c ON s.customer_id = c.id"
            response = client.get(f"/api/execute/explain?sql={complex_sql}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            assert "HASH_JOIN" in data["execution_plan"]
            assert data["estimated_cost"] == 250.0
            assert data["estimated_rows"] == 5000
            assert len(data["optimization_suggestions"]) == 2
            assert "indexes on join columns" in data["optimization_suggestions"][0]
    
    def test_explain_endpoint_performance_monitoring(self):
        """Test that explain endpoint records performance metrics."""
        with patch('main.query_explain_service') as mock_service:
            with patch('main.performance_monitor') as mock_monitor:
                # Setup mocks
                mock_timing_context = Mock()
                mock_timing_context.get_elapsed_ms.return_value = 15.5
                mock_monitor.start_timing.return_value.__enter__.return_value = mock_timing_context
                mock_monitor.start_timing.return_value.__exit__.return_value = None
                
                mock_result = Mock()
                mock_result.execution_plan = "SEQUENTIAL_SCAN(sales)"
                mock_result.estimated_cost = 10.0
                mock_result.estimated_rows = 100
                mock_result.estimated_runtime_ms = 5.0
                mock_result.optimization_suggestions = []
                
                mock_service.explain_query.return_value = mock_result
                
                # Make request
                response = client.get("/api/execute/explain?sql=SELECT * FROM sales LIMIT 10")
                
                # Verify response
                assert response.status_code == 200
                
                # Verify performance monitoring was called
                mock_monitor.start_timing.assert_called_once_with("sql_explain")
                mock_monitor.record_execution.assert_called_once()
                
                # Verify the recorded execution details
                call_args = mock_monitor.record_execution.call_args
                assert call_args[1]["sql"] == "EXPLAIN SELECT * FROM sales LIMIT 10"
                assert call_args[1]["runtime_ms"] == 15.5
                assert call_args[1]["success"] is True
                assert call_args[1]["row_count"] == 0  # EXPLAIN doesn't return data rows
                assert call_args[1]["truncated"] is False