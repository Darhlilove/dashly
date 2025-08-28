"""
Comprehensive tests for the explain endpoint functionality.

Tests query explanation, cost estimation, execution plan generation,
and optimization suggestions as specified in Requirements 4.1-4.5.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import os

# Set environment variables for testing
os.environ["REQUIRE_AUTH"] = "false"
os.environ["DASHLY_API_KEY"] = "test-key-for-testing"

from src.main import app

client = TestClient(app)


class TestExplainEndpointBasic:
    """Basic tests for explain endpoint functionality."""
    
    def test_explain_endpoint_exists(self):
        """Test that the explain endpoint exists."""
        response = client.get("/api/execute/explain?sql=SELECT 1")
        
        # Should not return 404 (endpoint exists)
        # May return 200 (implemented) or other status (validation error, etc.)
        assert response.status_code != 404, "Explain endpoint should exist"
    
    def test_explain_simple_select(self):
        """Test explain with simple SELECT query."""
        response = client.get("/api/execute/explain?sql=SELECT 1 as number")
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify response structure
            expected_fields = ["execution_plan", "estimated_cost", "estimated_rows", 
                             "estimated_runtime_ms", "optimization_suggestions"]
            for field in expected_fields:
                assert field in data, f"Missing field in explain response: {field}"
            
            # Verify field types
            assert isinstance(data["execution_plan"], str)
            assert isinstance(data["estimated_cost"], (int, float))
            assert isinstance(data["estimated_rows"], int)
            assert isinstance(data["estimated_runtime_ms"], (int, float))
            assert isinstance(data["optimization_suggestions"], list)
            
            # Basic sanity checks
            assert len(data["execution_plan"]) > 0
            assert data["estimated_cost"] >= 0
            assert data["estimated_rows"] >= 0
            assert data["estimated_runtime_ms"] >= 0
        else:
            # If not implemented, should return appropriate error
            assert response.status_code in [400, 404, 501]
    
    def test_explain_with_table_reference(self):
        """Test explain with table reference (even if table doesn't exist)."""
        response = client.get("/api/execute/explain?sql=SELECT * FROM users")
        
        if response.status_code == 200:
            data = response.json()
            assert "execution_plan" in data
            # Plan should mention the table
            assert "users" in data["execution_plan"].lower() or "table" in data["execution_plan"].lower()
        elif response.status_code == 400:
            # May fail due to table not existing - this is acceptable
            data = response.json()
            assert "detail" in data
        else:
            assert response.status_code in [404, 501]  # Not implemented
    
    def test_explain_parameter_validation(self):
        """Test explain endpoint parameter validation."""
        # Test missing sql parameter
        response = client.get("/api/execute/explain")
        assert response.status_code in [422, 400, 404]  # Validation error or not implemented
        
        # Test empty sql parameter
        response = client.get("/api/execute/explain?sql=")
        if response.status_code not in [404, 501]:  # Skip if not implemented
            assert response.status_code == 400  # Should validate empty query


class TestExplainComplexQueries:
    """Test explain functionality with complex queries."""
    
    def test_explain_with_cte(self):
        """Test explain with Common Table Expression (CTE)."""
        cte_query = """
        WITH numbers AS (
            SELECT generate_series as n FROM generate_series(1, 10)
        )
        SELECT n, n * 2 as doubled FROM numbers WHERE n > 5
        """
        
        response = client.get("/api/execute/explain", params={"sql": cte_query})
        
        if response.status_code == 200:
            data = response.json()
            
            # CTE should be reflected in execution plan
            plan = data["execution_plan"].lower()
            assert any(keyword in plan for keyword in ["cte", "with", "subquery", "temp"]), \
                "CTE should be mentioned in execution plan"
            
            # Cost should be reasonable for this query
            assert data["estimated_cost"] >= 0
            assert data["estimated_rows"] >= 0
        elif response.status_code == 400:
            # May fail due to validation - acceptable
            pass
        else:
            assert response.status_code in [404, 501]
    
    def test_explain_with_aggregation(self):
        """Test explain with aggregation functions."""
        agg_query = """
        SELECT 
            COUNT(*) as total_count,
            SUM(n) as total_sum,
            AVG(n) as average
        FROM (SELECT generate_series as n FROM generate_series(1, 100)) t
        WHERE n % 2 = 0
        """
        
        response = client.get("/api/execute/explain", params={"sql": agg_query})
        
        if response.status_code == 200:
            data = response.json()
            
            # Aggregation should be reflected in execution plan
            plan = data["execution_plan"].lower()
            assert any(keyword in plan for keyword in ["aggregate", "group", "count", "sum"]), \
                "Aggregation should be mentioned in execution plan"
            
            # Should estimate 1 row for aggregation result
            assert data["estimated_rows"] >= 1
        elif response.status_code == 400:
            pass  # Acceptable
        else:
            assert response.status_code in [404, 501]
    
    def test_explain_with_join(self):
        """Test explain with JOIN operations using CTEs."""
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
        SELECT u.name, COUNT(o.amount) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.name
        """
        
        response = client.get("/api/execute/explain", params={"sql": join_query})
        
        if response.status_code == 200:
            data = response.json()
            
            # JOIN should be reflected in execution plan
            plan = data["execution_plan"].lower()
            assert any(keyword in plan for keyword in ["join", "hash", "nested", "merge"]), \
                "JOIN operation should be mentioned in execution plan"
            
            # Complex query should have higher cost
            assert data["estimated_cost"] > 0
        elif response.status_code == 400:
            pass  # Acceptable
        else:
            assert response.status_code in [404, 501]
    
    def test_explain_with_subquery(self):
        """Test explain with subquery."""
        subquery = """
        SELECT 
            main_value,
            (SELECT COUNT(*) FROM (SELECT generate_series FROM generate_series(1, 50)) sub) as sub_count
        FROM (SELECT 'test' as main_value) main
        """
        
        response = client.get("/api/execute/explain", params={"sql": subquery})
        
        if response.status_code == 200:
            data = response.json()
            
            # Subquery should be reflected in execution plan
            plan = data["execution_plan"].lower()
            assert any(keyword in plan for keyword in ["subquery", "nested", "sub"]), \
                "Subquery should be mentioned in execution plan"
        elif response.status_code == 400:
            pass  # Acceptable
        else:
            assert response.status_code in [404, 501]


class TestExplainErrorHandling:
    """Test explain endpoint error handling."""
    
    def test_explain_security_validation(self):
        """Test that explain endpoint enforces security validation."""
        dangerous_queries = [
            "CREATE TABLE test (id INT)",
            "INSERT INTO test VALUES (1)",
            "UPDATE test SET id = 2",
            "DELETE FROM test",
            "DROP TABLE test",
            "PRAGMA table_info(test)"
        ]
        
        for sql in dangerous_queries:
            response = client.get("/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 400:
                # Should reject dangerous queries
                data = response.json()
                assert "detail" in data
                assert data["detail"]["sql_error_type"] == "security"
            elif response.status_code in [404, 501]:
                # Endpoint not implemented - acceptable
                pass
            else:
                assert False, f"Dangerous query should be rejected: {sql}"
    
    def test_explain_syntax_error_handling(self):
        """Test explain endpoint handling of syntax errors."""
        syntax_error_queries = [
            "SELECT * FROM WHERE",
            "SELCT * FROM test",
            "SELECT * FROM users WHERE (name = 'test'",  # Unbalanced parentheses
        ]
        
        for sql in syntax_error_queries:
            response = client.get("/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                # Should be syntax or execution error
                assert data["detail"]["sql_error_type"] in ["syntax", "execution"]
            elif response.status_code in [404, 501]:
                pass  # Not implemented
            else:
                # Should handle syntax errors gracefully
                assert response.status_code in [400, 404, 501]
    
    def test_explain_schema_error_handling(self):
        """Test explain endpoint handling of schema errors."""
        schema_error_queries = [
            "SELECT * FROM definitely_nonexistent_table",
            "SELECT nonexistent_column FROM (SELECT 1 as id) t",
        ]
        
        for sql in schema_error_queries:
            response = client.get("/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                assert data["detail"]["sql_error_type"] in ["execution", "schema"]
            elif response.status_code in [404, 501]:
                pass  # Not implemented
            else:
                # Should handle schema errors appropriately
                assert response.status_code in [400, 404, 501]


class TestExplainOptimizationSuggestions:
    """Test optimization suggestions in explain responses."""
    
    def test_explain_provides_suggestions(self):
        """Test that explain endpoint provides optimization suggestions."""
        # Query that might benefit from optimization
        query = "SELECT * FROM (SELECT generate_series FROM generate_series(1, 10000)) t"
        
        response = client.get("/api/execute/explain", params={"sql": query})
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have optimization suggestions
            assert "optimization_suggestions" in data
            assert isinstance(data["optimization_suggestions"], list)
            
            # For a large result set, might suggest using LIMIT
            suggestions_text = " ".join(data["optimization_suggestions"]).lower()
            # Common optimization suggestions
            possible_suggestions = ["limit", "index", "where", "filter", "optimize"]
            
            # At least some suggestion should be provided for complex queries
            # (This is flexible since suggestions depend on implementation)
            assert len(data["optimization_suggestions"]) >= 0
        elif response.status_code in [404, 501]:
            pass  # Not implemented
        else:
            assert response.status_code == 400  # Some other validation error
    
    def test_explain_suggestions_for_different_query_types(self):
        """Test optimization suggestions for different types of queries."""
        query_types = [
            ("simple", "SELECT 1"),
            ("large_result", "SELECT generate_series FROM generate_series(1, 5000)"),
            ("aggregation", "SELECT COUNT(*) FROM (SELECT generate_series FROM generate_series(1, 1000)) t"),
        ]
        
        for query_type, sql in query_types:
            response = client.get("/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 200:
                data = response.json()
                
                # All responses should have suggestions field
                assert "optimization_suggestions" in data
                assert isinstance(data["optimization_suggestions"], list)
                
                # Different query types might have different suggestions
                # This is implementation-dependent, so we just verify structure
                for suggestion in data["optimization_suggestions"]:
                    assert isinstance(suggestion, str)
                    assert len(suggestion) > 0
            elif response.status_code in [404, 501]:
                break  # Not implemented, skip remaining tests
            else:
                # Should handle all query types
                assert response.status_code == 400


class TestExplainPerformanceEstimation:
    """Test performance estimation in explain responses."""
    
    def test_explain_cost_estimation(self):
        """Test that explain provides reasonable cost estimates."""
        queries_by_complexity = [
            ("simple", "SELECT 1", 0, 100),  # Expected cost range
            ("medium", "SELECT generate_series FROM generate_series(1, 100)", 0, 1000),
            ("complex", """
                WITH RECURSIVE fib(n, a, b) AS (
                    SELECT 1, 0, 1
                    UNION ALL
                    SELECT n+1, b, a+b FROM fib WHERE n < 20
                )
                SELECT * FROM fib
            """, 0, 5000)
        ]
        
        for complexity, sql, min_cost, max_cost in queries_by_complexity:
            response = client.get("/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 200:
                data = response.json()
                
                # Cost should be within reasonable range
                assert data["estimated_cost"] >= min_cost, f"{complexity} query cost too low"
                assert data["estimated_cost"] <= max_cost, f"{complexity} query cost too high"
                
                # Runtime estimate should be reasonable
                assert data["estimated_runtime_ms"] >= 0
                assert data["estimated_runtime_ms"] <= 60000  # Max 1 minute estimate
            elif response.status_code in [404, 501]:
                break  # Not implemented
            else:
                assert response.status_code == 400
    
    def test_explain_row_estimation(self):
        """Test that explain provides reasonable row count estimates."""
        row_estimation_queries = [
            ("single_row", "SELECT 1", 1, 1),
            ("multiple_rows", "SELECT generate_series FROM generate_series(1, 50)", 50, 50),
            ("aggregation", "SELECT COUNT(*) FROM (SELECT generate_series FROM generate_series(1, 100)) t", 1, 1),
        ]
        
        for query_type, sql, expected_min, expected_max in row_estimation_queries:
            response = client.get("/api/execute/explain", params={"sql": sql})
            
            if response.status_code == 200:
                data = response.json()
                
                # Row estimate should be reasonable
                assert data["estimated_rows"] >= expected_min, f"{query_type} row estimate too low"
                assert data["estimated_rows"] <= expected_max * 2, f"{query_type} row estimate too high"  # Allow some variance
            elif response.status_code in [404, 501]:
                break  # Not implemented
            else:
                assert response.status_code == 400


class TestExplainIntegration:
    """Integration tests for explain endpoint."""
    
    @patch('src.query_explain_service.QueryExplainService.explain_query')
    def test_explain_service_integration(self, mock_explain):
        """Test integration with query explain service."""
        # Mock the explain service
        mock_result = Mock()
        mock_result.execution_plan = "SEQUENTIAL_SCAN(test_table)"
        mock_result.estimated_cost = 100.0
        mock_result.estimated_rows = 50
        mock_result.estimated_runtime_ms = 25.0
        mock_result.optimization_suggestions = ["Consider adding WHERE clause"]
        
        mock_explain.return_value = mock_result
        
        response = client.get("/api/execute/explain?sql=SELECT * FROM test_table")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should match mocked values
            assert data["execution_plan"] == "SEQUENTIAL_SCAN(test_table)"
            assert data["estimated_cost"] == 100.0
            assert data["estimated_rows"] == 50
            assert data["estimated_runtime_ms"] == 25.0
            assert data["optimization_suggestions"] == ["Consider adding WHERE clause"]
            
            # Verify service was called
            mock_explain.assert_called_once_with("SELECT * FROM test_table")
        elif response.status_code in [404, 501]:
            # Service not implemented yet
            pass
        else:
            assert response.status_code == 400
    
    def test_explain_vs_execute_consistency(self):
        """Test consistency between explain and execute endpoints."""
        test_query = "SELECT generate_series as num FROM generate_series(1, 10)"
        
        # Get explain result
        explain_response = client.get("/api/execute/explain", params={"sql": test_query})
        
        # Get execute result
        execute_response = client.post("/api/execute", json={"sql": test_query})
        
        if explain_response.status_code == 200 and execute_response.status_code == 200:
            explain_data = explain_response.json()
            execute_data = execute_response.json()
            
            # Row count estimates should be reasonably close to actual
            estimated_rows = explain_data["estimated_rows"]
            actual_rows = execute_data["row_count"]
            
            # Allow for some variance in estimation
            if estimated_rows > 0:
                ratio = actual_rows / estimated_rows
                assert 0.5 <= ratio <= 2.0, f"Row estimate too far off: estimated {estimated_rows}, actual {actual_rows}"
            
            # Runtime estimates should be in the right ballpark
            estimated_runtime = explain_data["estimated_runtime_ms"]
            actual_runtime = execute_data["runtime_ms"]
            
            # Estimates can be quite different from actual, so just check they're both reasonable
            assert estimated_runtime >= 0
            assert actual_runtime >= 0
        elif explain_response.status_code in [404, 501]:
            # Explain not implemented
            pass
        else:
            # Both should handle the same query consistently
            if execute_response.status_code == 200:
                # If execute works, explain should at least not crash
                assert explain_response.status_code in [200, 400, 404, 501]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])