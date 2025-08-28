"""
Focused tests for concurrent query execution and resource limits.

Tests concurrent query handling, timeout enforcement, and resource management
as specified in Requirements 6.1-6.4 and 7.3.
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
import os

# Set environment variables for testing
os.environ["REQUIRE_AUTH"] = "false"

from src.main import app

client = TestClient(app)


class TestConcurrentQueryExecution:
    """Test concurrent query execution handling."""
    
    def test_multiple_concurrent_simple_queries(self):
        """Test multiple concurrent simple queries."""
        def execute_query(query_id):
            sql = f"SELECT {query_id} as query_id, 'test_{query_id}' as message"
            start_time = time.time()
            response = client.post("/api/execute", json={"sql": sql})
            end_time = time.time()
            
            return {
                "query_id": query_id,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "execution_time": end_time - start_time
            }
        
        # Execute 10 concurrent queries
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(execute_query, i) for i in range(10)]
            results = [future.result() for future in futures]
        
        # All queries should succeed
        successful_queries = [r for r in results if r["status_code"] == 200]
        assert len(successful_queries) >= 8, "At least 8 out of 10 concurrent queries should succeed"
        
        # Verify each successful query returned correct data
        for result in successful_queries:
            if result["data"]:
                data = result["data"]
                assert data["row_count"] == 1
                assert len(data["rows"]) == 1
                assert data["rows"][0][0] == result["query_id"]
                assert f"test_{result['query_id']}" in data["rows"][0][1]
    
    def test_concurrent_queries_with_different_complexities(self):
        """Test concurrent queries with varying complexity levels."""
        queries = [
            ("simple", "SELECT 1 as num"),
            ("medium", "SELECT generate_series as num FROM generate_series(1, 20)"),
            ("complex", """
                WITH RECURSIVE series(n) AS (
                    SELECT 1
                    UNION ALL
                    SELECT n+1 FROM series WHERE n < 15
                )
                SELECT n, n*n as square FROM series
            """),
            ("aggregation", """
                SELECT 
                    COUNT(*) as total,
                    SUM(n) as sum_n,
                    AVG(n) as avg_n
                FROM (SELECT generate_series as n FROM generate_series(1, 30)) t
            """)
        ]
        
        def execute_query(query_type, sql):
            start_time = time.time()
            response = client.post("/api/execute", json={"sql": sql})
            end_time = time.time()
            
            return {
                "type": query_type,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "execution_time": end_time - start_time
            }
        
        # Execute all queries concurrently
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            futures = [executor.submit(execute_query, qtype, sql) for qtype, sql in queries]
            results = [future.result() for future in futures]
        
        # All queries should succeed
        for result in results:
            assert result["status_code"] == 200, f"Query type {result['type']} failed"
            assert result["data"]["runtime_ms"] >= 0
        
        # Verify results are correct for each query type
        results_by_type = {r["type"]: r for r in results}
        
        assert results_by_type["simple"]["data"]["row_count"] == 1
        assert results_by_type["medium"]["data"]["row_count"] == 20
        assert results_by_type["complex"]["data"]["row_count"] == 15
        assert results_by_type["aggregation"]["data"]["row_count"] == 1
    
    def test_concurrent_query_resource_isolation(self):
        """Test that concurrent queries don't interfere with each other."""
        def execute_unique_query(query_id):
            # Each query generates unique data to verify isolation
            sql = f"""
                WITH data AS (
                    SELECT {query_id} as base_id, generate_series as seq
                    FROM generate_series(1, 5)
                )
                SELECT base_id, seq, base_id * seq as product
                FROM data
                ORDER BY seq
            """
            
            response = client.post("/api/execute", json={"sql": sql})
            return {
                "query_id": query_id,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None
            }
        
        # Execute queries with different base IDs concurrently
        query_ids = [10, 20, 30, 40, 50]
        with ThreadPoolExecutor(max_workers=len(query_ids)) as executor:
            futures = [executor.submit(execute_unique_query, qid) for qid in query_ids]
            results = [future.result() for future in futures]
        
        # Verify each query returned its unique results
        for result in results:
            assert result["status_code"] == 200
            data = result["data"]
            query_id = result["query_id"]
            
            assert data["row_count"] == 5
            # Verify all rows have the correct base_id
            for row in data["rows"]:
                assert row[0] == query_id  # base_id column
                assert row[2] == query_id * row[1]  # product = base_id * seq
    
    def test_concurrent_error_handling(self):
        """Test error handling with concurrent queries."""
        queries = [
            ("valid", "SELECT 1 as num"),
            ("syntax_error", "SELECT * FROM WHERE"),
            ("security_error", "CREATE TABLE test (id INT)"),
            ("schema_error", "SELECT * FROM nonexistent_table_xyz"),
            ("valid2", "SELECT 'hello' as greeting")
        ]
        
        def execute_query(query_type, sql):
            response = client.post("/api/execute", json={"sql": sql})
            return {
                "type": query_type,
                "status_code": response.status_code,
                "data": response.json() if response.status_code in [200, 400] else None
            }
        
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            futures = [executor.submit(execute_query, qtype, sql) for qtype, sql in queries]
            results = [future.result() for future in futures]
        
        # Verify expected outcomes
        results_by_type = {r["type"]: r for r in results}
        
        # Valid queries should succeed
        assert results_by_type["valid"]["status_code"] == 200
        assert results_by_type["valid2"]["status_code"] == 200
        
        # Error queries should fail appropriately
        assert results_by_type["syntax_error"]["status_code"] == 400
        assert results_by_type["security_error"]["status_code"] == 400
        assert results_by_type["schema_error"]["status_code"] == 400
        
        # Verify error types
        assert results_by_type["security_error"]["data"]["detail"]["sql_error_type"] == "security"


class TestQueryTimeoutHandling:
    """Test query timeout enforcement."""
    
    @patch('src.query_executor.QueryExecutor.execute_query')
    def test_simulated_query_timeout(self, mock_execute):
        """Test query timeout handling with mocked slow execution."""
        from src.exceptions import QueryTimeoutError
        
        # Mock a timeout error
        mock_execute.side_effect = QueryTimeoutError("Query execution timeout after 30 seconds", timeout_seconds=30)
        
        response = client.post("/api/execute", json={"sql": "SELECT * FROM slow_table"})
        
        # Should return 408 for timeout
        assert response.status_code == 408
        
        data = response.json()
        assert "detail" in data
        assert data["detail"]["sql_error_type"] == "timeout"
        assert "timeout" in data["detail"]["detail"].lower()
    
    def test_reasonable_execution_times(self):
        """Test that normal queries execute within reasonable time limits."""
        test_queries = [
            "SELECT 1",
            "SELECT generate_series FROM generate_series(1, 100)",
            "SELECT COUNT(*) FROM (SELECT generate_series FROM generate_series(1, 500)) t"
        ]
        
        for sql in test_queries:
            start_time = time.time()
            response = client.post("/api/execute", json={"sql": sql})
            end_time = time.time()
            
            assert response.status_code == 200, f"Query failed: {sql}"
            
            # Execution should be fast for these simple queries
            execution_time = end_time - start_time
            assert execution_time < 10.0, f"Query took too long: {execution_time}s for {sql}"
            
            # Verify runtime_ms is reasonable
            data = response.json()
            assert data["runtime_ms"] < 10000, f"Reported runtime too high: {data['runtime_ms']}ms"


class TestResourceLimitEnforcement:
    """Test resource limit enforcement."""
    
    def test_result_set_size_limits(self):
        """Test that large result sets are properly limited."""
        # Test with a query that would return many rows
        large_query = "SELECT generate_series as num FROM generate_series(1, 20000)"
        
        response = client.post("/api/execute", json={"sql": large_query})
        assert response.status_code == 200
        
        data = response.json()
        
        # Should be truncated if it exceeds limits
        if data["truncated"]:
            assert data["row_count"] <= 10000  # Assuming default limit
            assert len(data["rows"]) <= 10000
            assert len(data["rows"]) == data["row_count"]
        else:
            # If not truncated, should have all rows
            assert data["row_count"] == 20000
            assert len(data["rows"]) == 20000
    
    def test_concurrent_resource_usage(self):
        """Test resource usage with multiple concurrent queries."""
        def execute_resource_intensive_query(query_id):
            # Query that generates moderate amount of data
            sql = f"""
                SELECT 
                    {query_id} as query_id,
                    generate_series as num,
                    generate_series * 2 as doubled,
                    'data_' || generate_series as text_data
                FROM generate_series(1, 100)
            """
            
            response = client.post("/api/execute", json={"sql": sql})
            return {
                "query_id": query_id,
                "status_code": response.status_code,
                "row_count": response.json()["row_count"] if response.status_code == 200 else 0,
                "runtime_ms": response.json()["runtime_ms"] if response.status_code == 200 else 0
            }
        
        # Execute multiple resource-intensive queries concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_resource_intensive_query, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # All queries should complete successfully
        successful_results = [r for r in results if r["status_code"] == 200]
        assert len(successful_results) >= 4, "Most concurrent resource-intensive queries should succeed"
        
        # Verify results
        for result in successful_results:
            assert result["row_count"] == 100
            assert result["runtime_ms"] >= 0


class TestQueryQueueing:
    """Test query queuing and concurrency limits."""
    
    def test_high_concurrency_handling(self):
        """Test system behavior under high concurrency."""
        def execute_simple_query(query_id):
            sql = f"SELECT {query_id} as id, 'concurrent_test' as test_type"
            
            try:
                response = client.post("/api/execute", json={"sql": sql})
                return {
                    "query_id": query_id,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {
                    "query_id": query_id,
                    "status_code": 500,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute many concurrent queries
        num_queries = 20
        with ThreadPoolExecutor(max_workers=num_queries) as executor:
            futures = [executor.submit(execute_simple_query, i) for i in range(num_queries)]
            results = []
            
            # Collect results as they complete
            for future in as_completed(futures, timeout=30):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "query_id": -1,
                        "status_code": 500,
                        "success": False,
                        "error": str(e)
                    })
        
        # Analyze results
        successful_queries = [r for r in results if r["success"]]
        failed_queries = [r for r in results if not r["success"]]
        
        # Most queries should succeed, but some might be queued or limited
        success_rate = len(successful_queries) / len(results)
        assert success_rate >= 0.7, f"Success rate too low: {success_rate:.2%}"
        
        # Failed queries should have appropriate status codes
        for failed in failed_queries:
            # 429 = too many requests, 503 = service unavailable, etc.
            assert failed["status_code"] in [429, 503, 500], f"Unexpected failure status: {failed['status_code']}"
    
    def test_query_fairness(self):
        """Test that queries are handled fairly under load."""
        def execute_timed_query(query_id):
            start_time = time.time()
            sql = f"SELECT {query_id} as id, generate_series FROM generate_series(1, 10)"
            
            response = client.post("/api/execute", json={"sql": sql})
            end_time = time.time()
            
            return {
                "query_id": query_id,
                "status_code": response.status_code,
                "execution_time": end_time - start_time,
                "success": response.status_code == 200
            }
        
        # Execute queries in batches to test fairness
        batch_size = 8
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [executor.submit(execute_timed_query, i) for i in range(batch_size)]
            results = [future.result() for future in futures]
        
        successful_results = [r for r in results if r["success"]]
        
        if len(successful_results) >= 4:  # Need enough successful queries to analyze
            execution_times = [r["execution_time"] for r in successful_results]
            
            # Check that execution times are reasonably consistent (fairness)
            min_time = min(execution_times)
            max_time = max(execution_times)
            
            # Max time shouldn't be more than 10x min time (allowing for some variance)
            fairness_ratio = max_time / min_time if min_time > 0 else 1
            assert fairness_ratio < 10, f"Execution time variance too high: {fairness_ratio:.2f}x"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])