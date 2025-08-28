"""
Integration tests for the explain endpoint with actual database.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Set environment variables for testing
os.environ["REQUIRE_AUTH"] = "false"
os.environ["DASHLY_API_KEY"] = "test-key-for-testing"

# Add src directory to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import after setting environment variables
from main import app

client = TestClient(app)


class TestExplainIntegration:
    """Integration tests for explain endpoint with real database."""
    
    def test_explain_simple_query_integration(self):
        """Test explain endpoint with a simple query against actual database."""
        # Use a simple query that should work regardless of table existence
        sql = "SELECT 1 as test_column"
        
        response = client.get(f"/api/execute/explain?sql={sql}")
        
        # Should succeed even if no tables exist
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "execution_plan" in data
        assert "estimated_cost" in data
        assert "estimated_rows" in data
        assert "estimated_runtime_ms" in data
        assert "optimization_suggestions" in data
        
        # Verify data types
        assert isinstance(data["execution_plan"], str)
        assert isinstance(data["estimated_cost"], (int, float))
        assert isinstance(data["estimated_rows"], int)
        assert isinstance(data["estimated_runtime_ms"], (int, float))
        assert isinstance(data["optimization_suggestions"], list)
    
    def test_explain_invalid_sql_integration(self):
        """Test explain endpoint with invalid SQL."""
        sql = "DROP TABLE nonexistent"
        
        response = client.get(f"/api/execute/explain?sql={sql}")
        
        # Should return validation error
        assert response.status_code == 400
        data = response.json()
        
        assert data["detail"]["error"] == "sql_validation_failed"
        assert data["detail"]["sql_error_type"] == "syntax"
    
    def test_explain_complex_query_integration(self):
        """Test explain endpoint with a more complex query."""
        # Use a query with subquery and aggregation
        sql = "SELECT COUNT(*) FROM (SELECT 1 as id UNION SELECT 2 as id) t"
        
        response = client.get(f"/api/execute/explain?sql={sql}")
        
        # Should succeed
        assert response.status_code == 200
        data = response.json()
        
        # Should have execution plan
        assert len(data["execution_plan"]) > 0
        assert data["estimated_rows"] >= 0
        assert data["estimated_cost"] >= 0
        
        # Should have some optimization suggestions or indicate it's well optimized
        assert isinstance(data["optimization_suggestions"], list)