"""
Unit tests for the performance monitoring system.

Tests timing context management, execution time measurement, slow query detection,
and performance metrics tracking functionality.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from performance_monitor import (
    PerformanceMonitor, TimingContext, QueryMetrics, QueryExecutionRecord,
    PerformanceStats, get_performance_monitor
)


class TestTimingContext:
    """Test cases for TimingContext class."""
    
    def test_timing_context_basic_usage(self):
        """Test basic timing context functionality."""
        with TimingContext("test_operation") as timing:
            time.sleep(0.01)  # Sleep for 10ms
            elapsed = timing.get_elapsed_ms()
            
        # Should have measured at least 10ms
        assert elapsed >= 10.0
        assert elapsed < 50.0  # Should be reasonable
        assert timing.start_time is not None
        assert timing.end_time is not None
    
    def test_timing_context_with_exception(self):
        """Test timing context when exception occurs."""
        with pytest.raises(ValueError):
            with TimingContext("test_operation") as timing:
                time.sleep(0.005)  # Sleep for 5ms
                raise ValueError("Test exception")
        
        # Should still have timing information
        elapsed = timing.get_elapsed_ms()
        assert elapsed >= 5.0
        assert timing.start_time is not None
        assert timing.end_time is not None
    
    def test_timing_context_get_elapsed_before_end(self):
        """Test getting elapsed time before context ends."""
        with TimingContext("test_operation") as timing:
            time.sleep(0.005)
            elapsed_during = timing.get_elapsed_ms()
            time.sleep(0.005)
        
        elapsed_after = timing.get_elapsed_ms()
        
        # Elapsed time should increase
        assert elapsed_during >= 5.0
        assert elapsed_after > elapsed_during
    
    def test_timing_context_no_start_time(self):
        """Test timing context when start time is not set."""
        timing = TimingContext("test")
        elapsed = timing.get_elapsed_ms()
        assert elapsed == 0.0


class TestPerformanceMonitor:
    """Test cases for PerformanceMonitor class."""
    
    @pytest.fixture
    def monitor(self):
        """Create a fresh performance monitor for each test."""
        return PerformanceMonitor(slow_query_threshold_ms=100.0, max_history_size=50)
    
    def test_performance_monitor_initialization(self, monitor):
        """Test performance monitor initialization."""
        assert monitor.slow_query_threshold_ms == 100.0
        assert monitor.max_history_size == 50
        assert isinstance(monitor.start_time, datetime)
        
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 0
        assert stats.metrics.successful_queries == 0
        assert stats.metrics.failed_queries == 0
    
    def test_start_timing(self, monitor):
        """Test starting timing operation."""
        timing_context = monitor.start_timing("test_query")
        assert isinstance(timing_context, TimingContext)
        assert timing_context.operation_name == "test_query"
    
    def test_time_operation_context_manager(self, monitor):
        """Test time_operation context manager."""
        with monitor.time_operation("test_operation") as timing:
            time.sleep(0.01)
            elapsed = timing.get_elapsed_ms()
        
        assert elapsed >= 10.0
        assert isinstance(timing, TimingContext)
    
    def test_record_successful_execution(self, monitor):
        """Test recording successful query execution."""
        sql = "SELECT * FROM test_table"
        runtime_ms = 50.0
        row_count = 100
        
        monitor.record_execution(sql, runtime_ms, True, row_count=row_count)
        
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 1
        assert stats.metrics.successful_queries == 1
        assert stats.metrics.failed_queries == 0
        assert stats.metrics.average_runtime_ms == runtime_ms
        assert stats.metrics.min_runtime_ms == runtime_ms
        assert stats.metrics.max_runtime_ms == runtime_ms
        assert stats.metrics.total_runtime_ms == runtime_ms
        
        recent_queries = monitor.get_recent_queries(1)
        assert len(recent_queries) == 1
        assert recent_queries[0].sql == sql
        assert recent_queries[0].runtime_ms == runtime_ms
        assert recent_queries[0].success is True
        assert recent_queries[0].row_count == row_count
    
    def test_record_failed_execution(self, monitor):
        """Test recording failed query execution."""
        sql = "SELECT * FROM nonexistent_table"
        runtime_ms = 25.0
        error_message = "Table does not exist"
        
        monitor.record_execution(sql, runtime_ms, False, error_message=error_message)
        
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 1
        assert stats.metrics.successful_queries == 0
        assert stats.metrics.failed_queries == 1
        assert stats.metrics.average_runtime_ms == 0.0  # No successful queries
        
        error_queries = monitor.get_error_queries(1)
        assert len(error_queries) == 1
        assert error_queries[0].sql == sql
        assert error_queries[0].runtime_ms == runtime_ms
        assert error_queries[0].success is False
        assert error_queries[0].error_message == error_message
    
    def test_slow_query_detection(self, monitor):
        """Test slow query detection and recording."""
        # Normal query (below threshold)
        monitor.record_execution("SELECT 1", 50.0, True)
        
        # Slow query (above threshold)
        slow_sql = "SELECT * FROM large_table"
        monitor.record_execution(slow_sql, 150.0, True)
        
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 2
        assert stats.metrics.slow_queries_count == 1
        
        slow_queries = monitor.get_slow_queries(1)
        assert len(slow_queries) == 1
        assert slow_queries[0].sql == slow_sql
        assert slow_queries[0].runtime_ms == 150.0
    
    def test_is_slow_query(self, monitor):
        """Test slow query detection logic."""
        assert monitor.is_slow_query(150.0) is True  # Above threshold
        assert monitor.is_slow_query(100.0) is False  # At threshold
        assert monitor.is_slow_query(50.0) is False   # Below threshold
    
    def test_timeout_detection(self, monitor):
        """Test timeout error detection."""
        monitor.record_execution(
            "SELECT * FROM slow_table", 
            30000.0, 
            False, 
            error_message="Query execution timeout"
        )
        
        stats = monitor.get_performance_stats()
        assert stats.metrics.timeout_count == 1
        assert stats.metrics.failed_queries == 1
    
    def test_multiple_executions_metrics(self, monitor):
        """Test metrics calculation with multiple executions."""
        # Record multiple successful queries
        runtimes = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, runtime in enumerate(runtimes):
            monitor.record_execution(f"SELECT {i}", runtime, True, row_count=i*10)
        
        # Record one failed query
        monitor.record_execution("SELECT bad", 15.0, False, error_message="Syntax error")
        
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 6
        assert stats.metrics.successful_queries == 5
        assert stats.metrics.failed_queries == 1
        assert stats.metrics.average_runtime_ms == 30.0  # Average of successful queries
        assert stats.metrics.min_runtime_ms == 10.0
        assert stats.metrics.max_runtime_ms == 50.0
        assert stats.metrics.total_runtime_ms == 150.0
    
    def test_query_history_limit(self, monitor):
        """Test query history size limiting."""
        # Record more queries than the history limit
        for i in range(60):  # More than max_history_size (50)
            monitor.record_execution(f"SELECT {i}", 10.0, True)
        
        recent_queries = monitor.get_recent_queries(100)  # Request more than available
        assert len(recent_queries) <= monitor.max_history_size
        
        # Should have the most recent queries
        assert recent_queries[-1].sql == "SELECT 59"
    
    def test_long_sql_truncation(self, monitor):
        """Test truncation of long SQL queries in records."""
        long_sql = "SELECT " + "column_name, " * 100 + "FROM table"  # Very long query
        monitor.record_execution(long_sql, 25.0, True)
        
        recent_queries = monitor.get_recent_queries(1)
        recorded_sql = recent_queries[0].sql
        
        # Should be truncated
        assert len(recorded_sql) <= 203  # 200 chars + "..."
        assert recorded_sql.endswith("...")
    
    def test_truncated_results_tracking(self, monitor):
        """Test tracking of truncated query results."""
        monitor.record_execution("SELECT * FROM big_table", 100.0, True, 
                                row_count=10000, truncated=True)
        
        recent_queries = monitor.get_recent_queries(1)
        assert recent_queries[0].truncated is True
        assert recent_queries[0].row_count == 10000
    
    def test_reset_metrics(self, monitor):
        """Test resetting performance metrics."""
        # Record some data
        monitor.record_execution("SELECT 1", 50.0, True)
        monitor.record_execution("SELECT 2", 150.0, True)  # Slow query
        monitor.record_execution("SELECT bad", 25.0, False, error_message="Error")
        
        # Verify data exists
        stats_before = monitor.get_performance_stats()
        assert stats_before.metrics.total_queries == 3
        
        # Reset metrics
        monitor.reset_metrics()
        
        # Verify reset
        stats_after = monitor.get_performance_stats()
        assert stats_after.metrics.total_queries == 0
        assert stats_after.metrics.successful_queries == 0
        assert stats_after.metrics.failed_queries == 0
        assert stats_after.metrics.slow_queries_count == 0
        assert len(monitor.get_recent_queries()) == 0
        assert len(monitor.get_slow_queries()) == 0
        assert len(monitor.get_error_queries()) == 0
    
    def test_set_slow_query_threshold(self, monitor):
        """Test updating slow query threshold."""
        original_threshold = monitor.slow_query_threshold_ms
        new_threshold = 200.0
        
        monitor.set_slow_query_threshold(new_threshold)
        assert monitor.slow_query_threshold_ms == new_threshold
        
        # Test with new threshold
        monitor.record_execution("SELECT 1", 150.0, True)  # Below new threshold
        stats = monitor.get_performance_stats()
        assert stats.metrics.slow_queries_count == 0
        
        monitor.record_execution("SELECT 2", 250.0, True)  # Above new threshold
        stats = monitor.get_performance_stats()
        assert stats.metrics.slow_queries_count == 1
    
    def test_queries_per_minute_calculation(self, monitor):
        """Test queries per minute calculation."""
        # Record several queries
        for i in range(5):
            monitor.record_execution(f"SELECT {i}", 10.0, True)
        
        stats = monitor.get_performance_stats()
        # Should have some queries per minute value
        assert stats.queries_per_minute >= 0.0
    
    def test_thread_safety(self, monitor):
        """Test thread safety of performance monitor."""
        def record_queries(thread_id, count):
            for i in range(count):
                monitor.record_execution(f"SELECT {thread_id}_{i}", 10.0, True)
        
        # Create multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=record_queries, args=(thread_id, 10))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all queries were recorded
        stats = monitor.get_performance_stats()
        assert stats.metrics.total_queries == 50  # 5 threads * 10 queries each
        assert stats.metrics.successful_queries == 50
    
    def test_performance_stats_structure(self, monitor):
        """Test the structure of performance stats."""
        # Record some sample data
        monitor.record_execution("SELECT 1", 50.0, True, row_count=10)
        monitor.record_execution("SELECT 2", 150.0, True, row_count=20)  # Slow
        monitor.record_execution("SELECT bad", 25.0, False, error_message="Error")
        
        stats = monitor.get_performance_stats()
        
        # Check stats structure
        assert isinstance(stats.metrics, QueryMetrics)
        assert isinstance(stats.recent_queries, list)
        assert isinstance(stats.slow_queries, list)
        assert isinstance(stats.error_queries, list)
        assert isinstance(stats.uptime_seconds, float)
        assert isinstance(stats.queries_per_minute, float)
        
        # Check content
        assert len(stats.recent_queries) <= 10  # Limited to last 10
        assert len(stats.slow_queries) == 1
        assert len(stats.error_queries) == 1
        assert stats.uptime_seconds > 0
    
    @patch('performance_monitor.get_logger')
    def test_logging_integration(self, mock_get_logger, monitor):
        """Test integration with logging system."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Create new monitor to trigger logger setup
        test_monitor = PerformanceMonitor()
        
        # Record a slow query
        test_monitor.record_execution("SELECT * FROM slow_table", 2000.0, True)
        
        # Verify warning was logged for slow query
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Slow query detected" in warning_call
        assert "2000.00ms" in warning_call
    
    def test_log_performance_summary(self, monitor):
        """Test performance summary logging."""
        # Record some sample data
        monitor.record_execution("SELECT 1", 50.0, True)
        monitor.record_execution("SELECT 2", 150.0, True)  # Slow query
        monitor.record_execution("SELECT bad", 25.0, False, error_message="Error")
        
        # This should not raise an exception
        monitor.log_performance_summary()


class TestGlobalPerformanceMonitor:
    """Test cases for global performance monitor functionality."""
    
    def test_get_performance_monitor_singleton(self):
        """Test that get_performance_monitor returns singleton instance."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2  # Should be the same instance
        assert isinstance(monitor1, PerformanceMonitor)
    
    def test_get_performance_monitor_with_threshold(self):
        """Test get_performance_monitor with custom threshold."""
        # Reset global instance for this test
        import performance_monitor
        performance_monitor._performance_monitor = None
        
        monitor = get_performance_monitor(slow_query_threshold_ms=500.0)
        assert monitor.slow_query_threshold_ms == 500.0
        
        # Subsequent calls should return same instance regardless of threshold
        monitor2 = get_performance_monitor(slow_query_threshold_ms=1000.0)
        assert monitor2 is monitor
        assert monitor2.slow_query_threshold_ms == 500.0  # Original threshold preserved


class TestQueryExecutionRecord:
    """Test cases for QueryExecutionRecord data class."""
    
    def test_query_execution_record_creation(self):
        """Test creating QueryExecutionRecord."""
        timestamp = datetime.now()
        record = QueryExecutionRecord(
            sql="SELECT * FROM test",
            runtime_ms=100.0,
            success=True,
            timestamp=timestamp,
            row_count=50,
            truncated=False
        )
        
        assert record.sql == "SELECT * FROM test"
        assert record.runtime_ms == 100.0
        assert record.success is True
        assert record.timestamp == timestamp
        assert record.row_count == 50
        assert record.truncated is False
        assert record.error_message is None
    
    def test_query_execution_record_with_error(self):
        """Test creating QueryExecutionRecord with error."""
        record = QueryExecutionRecord(
            sql="SELECT * FROM nonexistent",
            runtime_ms=25.0,
            success=False,
            timestamp=datetime.now(),
            error_message="Table not found"
        )
        
        assert record.success is False
        assert record.error_message == "Table not found"
        assert record.row_count is None


class TestQueryMetrics:
    """Test cases for QueryMetrics data class."""
    
    def test_query_metrics_defaults(self):
        """Test QueryMetrics default values."""
        metrics = QueryMetrics()
        
        assert metrics.total_queries == 0
        assert metrics.successful_queries == 0
        assert metrics.failed_queries == 0
        assert metrics.average_runtime_ms == 0.0
        assert metrics.slow_queries_count == 0
        assert metrics.timeout_count == 0
        assert metrics.min_runtime_ms == float('inf')
        assert metrics.max_runtime_ms == 0.0
        assert metrics.total_runtime_ms == 0.0
    
    def test_query_metrics_with_values(self):
        """Test QueryMetrics with custom values."""
        metrics = QueryMetrics(
            total_queries=100,
            successful_queries=95,
            failed_queries=5,
            average_runtime_ms=150.5,
            slow_queries_count=10,
            timeout_count=2,
            min_runtime_ms=5.0,
            max_runtime_ms=5000.0,
            total_runtime_ms=14297.5
        )
        
        assert metrics.total_queries == 100
        assert metrics.successful_queries == 95
        assert metrics.failed_queries == 5
        assert metrics.average_runtime_ms == 150.5
        assert metrics.slow_queries_count == 10
        assert metrics.timeout_count == 2
        assert metrics.min_runtime_ms == 5.0
        assert metrics.max_runtime_ms == 5000.0
        assert metrics.total_runtime_ms == 14297.5


if __name__ == "__main__":
    pytest.main([__file__])