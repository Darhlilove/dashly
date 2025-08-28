"""
Integration tests for performance monitoring system.

Tests integration with existing logging, models, and potential query execution components.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from performance_monitor import PerformanceMonitor, get_performance_monitor
from models import (
    QueryMetricsResponse, QueryExecutionRecordResponse, PerformanceStatsResponse,
    ExecuteRequest, ExecuteResponse
)
from datetime import datetime


class TestPerformanceMonitorIntegration:
    """Integration tests for performance monitoring system."""
    
    @pytest.fixture
    def monitor(self):
        """Create a fresh performance monitor for each test."""
        return PerformanceMonitor(slow_query_threshold_ms=100.0)
    
    def test_integration_with_pydantic_models(self, monitor):
        """Test integration with Pydantic response models."""
        # Record some sample executions
        monitor.record_execution("SELECT * FROM users", 50.0, True, row_count=100)
        monitor.record_execution("SELECT * FROM orders", 150.0, True, row_count=500)  # Slow
        monitor.record_execution("SELECT * FROM invalid", 25.0, False, error_message="Table not found")
        
        # Get performance stats
        stats = monitor.get_performance_stats()
        
        # Convert to Pydantic models
        metrics_response = QueryMetricsResponse(
            total_queries=stats.metrics.total_queries,
            successful_queries=stats.metrics.successful_queries,
            failed_queries=stats.metrics.failed_queries,
            average_runtime_ms=stats.metrics.average_runtime_ms,
            slow_queries_count=stats.metrics.slow_queries_count,
            timeout_count=stats.metrics.timeout_count,
            min_runtime_ms=stats.metrics.min_runtime_ms,
            max_runtime_ms=stats.metrics.max_runtime_ms,
            total_runtime_ms=stats.metrics.total_runtime_ms
        )
        
        # Verify model creation
        assert metrics_response.total_queries == 3
        assert metrics_response.successful_queries == 2
        assert metrics_response.failed_queries == 1
        assert metrics_response.slow_queries_count == 1
        
        # Convert query records to response models
        recent_query_responses = [
            QueryExecutionRecordResponse(
                sql=record.sql,
                runtime_ms=record.runtime_ms,
                success=record.success,
                timestamp=record.timestamp,
                error_message=record.error_message,
                row_count=record.row_count,
                truncated=record.truncated
            )
            for record in stats.recent_queries
        ]
        
        assert len(recent_query_responses) == 3
        assert all(isinstance(resp, QueryExecutionRecordResponse) for resp in recent_query_responses)
        
        # Create full performance stats response
        performance_response = PerformanceStatsResponse(
            metrics=metrics_response,
            recent_queries=recent_query_responses,
            slow_queries=[
                QueryExecutionRecordResponse(
                    sql=record.sql,
                    runtime_ms=record.runtime_ms,
                    success=record.success,
                    timestamp=record.timestamp,
                    error_message=record.error_message,
                    row_count=record.row_count,
                    truncated=record.truncated
                )
                for record in stats.slow_queries
            ],
            error_queries=[
                QueryExecutionRecordResponse(
                    sql=record.sql,
                    runtime_ms=record.runtime_ms,
                    success=record.success,
                    timestamp=record.timestamp,
                    error_message=record.error_message,
                    row_count=record.row_count,
                    truncated=record.truncated
                )
                for record in stats.error_queries
            ],
            uptime_seconds=stats.uptime_seconds,
            queries_per_minute=stats.queries_per_minute
        )
        
        # Verify full response model
        assert isinstance(performance_response, PerformanceStatsResponse)
        assert performance_response.metrics.total_queries == 3
        assert len(performance_response.slow_queries) == 1
        assert len(performance_response.error_queries) == 1
    
    def test_simulated_query_execution_workflow(self, monitor):
        """Test simulated query execution workflow with performance monitoring."""
        # Simulate API request
        request = ExecuteRequest(sql="SELECT id, name FROM users WHERE active = true")
        
        # Simulate query execution with timing
        with monitor.time_operation("query_execution") as timing:
            # Simulate some processing time
            import time
            time.sleep(0.01)  # 10ms
            
            # Simulate successful execution
            columns = ["id", "name"]
            rows = [[1, "Alice"], [2, "Bob"], [3, "Charlie"]]
            row_count = len(rows)
            
            # Get execution time
            runtime_ms = timing.get_elapsed_ms()
        
        # Record the execution
        monitor.record_execution(
            sql=request.sql,
            runtime_ms=runtime_ms,
            success=True,
            row_count=row_count
        )
        
        # Create response
        response = ExecuteResponse(
            columns=columns,
            rows=rows,
            row_count=row_count,
            runtime_ms=runtime_ms,
            truncated=False
        )
        
        # Verify workflow
        assert response.runtime_ms >= 10.0  # At least 10ms
        assert response.row_count == 3
        assert response.columns == ["id", "name"]
        
        # Verify monitoring recorded the execution
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 1
        assert stats.metrics.successful_queries == 1
        assert len(stats.recent_queries) == 1
        assert stats.recent_queries[0].sql == request.sql
    
    def test_error_handling_workflow(self, monitor):
        """Test error handling workflow with performance monitoring."""
        # Simulate API request with invalid SQL
        request = ExecuteRequest(sql="SELECT * FROM nonexistent_table")
        
        # Simulate query execution with error
        with monitor.time_operation("query_execution") as timing:
            # Simulate some processing time before error
            import time
            time.sleep(0.005)  # 5ms
            
            # Simulate error detection
            error_message = "Table 'nonexistent_table' does not exist"
            runtime_ms = timing.get_elapsed_ms()
        
        # Record the failed execution
        monitor.record_execution(
            sql=request.sql,
            runtime_ms=runtime_ms,
            success=False,
            error_message=error_message
        )
        
        # Verify error was recorded
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 1
        assert stats.metrics.successful_queries == 0
        assert stats.metrics.failed_queries == 1
        assert len(stats.error_queries) == 1
        assert stats.error_queries[0].error_message == error_message
    
    def test_slow_query_workflow(self, monitor):
        """Test slow query detection workflow."""
        # Simulate slow query request
        request = ExecuteRequest(sql="SELECT * FROM large_table ORDER BY complex_calculation")
        
        # Simulate slow query execution
        with monitor.time_operation("slow_query_execution") as timing:
            # Simulate long processing time
            import time
            time.sleep(0.12)  # 120ms (above 100ms threshold)
            
            # Simulate successful but slow execution
            columns = ["id", "data"]
            rows = [[i, f"data_{i}"] for i in range(1000)]  # Large result set
            row_count = len(rows)
            runtime_ms = timing.get_elapsed_ms()
        
        # Record the slow execution
        monitor.record_execution(
            sql=request.sql,
            runtime_ms=runtime_ms,
            success=True,
            row_count=row_count,
            truncated=True  # Simulate result truncation
        )
        
        # Create response with truncation warning
        response = ExecuteResponse(
            columns=columns,
            rows=rows[:100],  # Truncated results
            row_count=100,    # Truncated count
            runtime_ms=runtime_ms,
            truncated=True
        )
        
        # Verify slow query detection
        stats = monitor.get_performance_stats()
        assert stats.metrics.slow_queries_count == 1
        assert len(stats.slow_queries) == 1
        assert stats.slow_queries[0].runtime_ms >= 120.0
        assert stats.slow_queries[0].truncated is True
        
        # Verify response indicates truncation
        assert response.truncated is True
        assert len(response.rows) == 100  # Truncated
    
    def test_concurrent_execution_simulation(self, monitor):
        """Test concurrent query execution simulation."""
        import threading
        import time
        
        def simulate_query_execution(query_id, execution_time_ms):
            """Simulate a query execution in a separate thread."""
            sql = f"SELECT * FROM table_{query_id}"
            
            with monitor.time_operation(f"query_{query_id}") as timing:
                time.sleep(execution_time_ms / 1000.0)  # Convert to seconds
                runtime_ms = timing.get_elapsed_ms()
            
            monitor.record_execution(
                sql=sql,
                runtime_ms=runtime_ms,
                success=True,
                row_count=query_id * 10
            )
        
        # Start multiple concurrent "queries"
        threads = []
        execution_times = [50, 75, 120, 30, 200]  # Mix of fast and slow queries
        
        for i, exec_time in enumerate(execution_times):
            thread = threading.Thread(
                target=simulate_query_execution,
                args=(i + 1, exec_time)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Verify all executions were recorded
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 5
        assert stats.metrics.successful_queries == 5
        assert stats.metrics.slow_queries_count == 2  # 120ms and 200ms queries
        
        # Verify thread safety - all queries should be recorded
        recent_queries = monitor.get_recent_queries(10)
        assert len(recent_queries) == 5
        
        # Verify slow queries were detected
        slow_queries = monitor.get_slow_queries(10)
        assert len(slow_queries) == 2
        assert all(q.runtime_ms > 100.0 for q in slow_queries)
    
    def test_global_monitor_integration(self):
        """Test integration with global performance monitor."""
        # Get global monitor
        global_monitor = get_performance_monitor(slow_query_threshold_ms=200.0)
        
        # Record some executions
        global_monitor.record_execution("SELECT 1", 50.0, True)
        global_monitor.record_execution("SELECT 2", 250.0, True)  # Slow with 200ms threshold
        
        # Verify global monitor state
        stats = global_monitor.get_performance_stats()
        assert stats.metrics.total_queries == 2
        assert stats.metrics.slow_queries_count == 1
        
        # Get same instance
        same_monitor = get_performance_monitor()
        assert same_monitor is global_monitor
        
        # Verify state persists
        same_stats = same_monitor.get_performance_stats()
        assert same_stats.metrics.total_queries == 2


if __name__ == "__main__":
    pytest.main([__file__])