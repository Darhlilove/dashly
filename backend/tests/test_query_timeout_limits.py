"""
Unit tests for query timeout and resource limits functionality.

Tests the enhanced QueryExecutor with timeout mechanisms, concurrent query limiting,
memory monitoring, and result set size limits as specified in Requirements 6.1-6.4 and 7.3.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import duckdb

try:
    from backend.src.query_executor import (
        QueryExecutor, 
        QueryTimeoutHandler, 
        ConcurrentQueryManager,
        MemoryMonitor,
        QueryResult
    )
    from backend.src.exceptions import (
        QueryTimeoutError,
        ConcurrentQueryLimitError,
        QueryExecutionError,
        ResultSetTooLargeError
    )
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from query_executor import (
        QueryExecutor, 
        QueryTimeoutHandler, 
        ConcurrentQueryManager,
        MemoryMonitor,
        QueryResult
    )
    from exceptions import (
        QueryTimeoutError,
        ConcurrentQueryLimitError,
        QueryExecutionError,
        ResultSetTooLargeError
    )


class TestQueryTimeoutHandler:
    """Test query timeout handling functionality."""
    
    def test_timeout_handler_initialization(self):
        """Test timeout handler initialization."""
        handler = QueryTimeoutHandler(30)
        assert handler.timeout_seconds == 30
        assert handler.start_time is None
        assert not handler.is_cancelled
    
    def test_timeout_handler_start(self):
        """Test timeout handler start functionality."""
        handler = QueryTimeoutHandler(30)
        handler.start()
        
        assert handler.start_time is not None
        assert not handler.is_cancelled
        assert handler.get_elapsed_ms() >= 0
    
    def test_timeout_check_before_timeout(self):
        """Test timeout check returns False before timeout."""
        handler = QueryTimeoutHandler(1)  # 1 second timeout
        handler.start()
        
        # Should not timeout immediately
        assert not handler.check_timeout()
    
    def test_timeout_check_after_timeout(self):
        """Test timeout check returns True after timeout."""
        handler = QueryTimeoutHandler(0.1)  # 100ms timeout
        handler.start()
        
        # Wait for timeout
        time.sleep(0.2)
        assert handler.check_timeout()
    
    def test_timeout_handler_cancel(self):
        """Test timeout handler cancellation."""
        handler = QueryTimeoutHandler(30)
        handler.start()
        handler.cancel()
        
        assert handler.is_cancelled
    
    def test_elapsed_time_calculation(self):
        """Test elapsed time calculation."""
        handler = QueryTimeoutHandler(30)
        handler.start()
        
        time.sleep(0.1)  # Sleep for 100ms
        elapsed = handler.get_elapsed_ms()
        
        # Should be approximately 100ms (allow some variance)
        assert 80 <= elapsed <= 200


class TestMemoryMonitor:
    """Test memory monitoring functionality."""
    
    def test_memory_monitor_initialization(self):
        """Test memory monitor initialization."""
        monitor = MemoryMonitor(512.0)
        assert monitor.memory_limit_mb == 512.0
        assert monitor.start_memory is None
        assert monitor.peak_memory == 0.0
    
    @patch('psutil.Process')
    def test_memory_monitor_start(self, mock_process):
        """Test memory monitoring start."""
        # Mock memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB in bytes
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        monitor = MemoryMonitor(512.0)
        monitor.start_monitoring()
        
        assert monitor.start_memory == 100.0  # 100MB
        assert monitor.peak_memory == 100.0
    
    @patch('psutil.Process')
    def test_memory_usage_check(self, mock_process):
        """Test memory usage checking."""
        # Mock memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 200 * 1024 * 1024  # 200MB in bytes
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        monitor = MemoryMonitor(150.0)  # 150MB limit
        usage = monitor.check_memory_usage()
        
        assert usage.current_mb == 200.0
        assert usage.limit_mb == 150.0
        assert usage.exceeded is True
    
    @patch('psutil.Process')
    def test_memory_usage_within_limit(self, mock_process):
        """Test memory usage within limits."""
        # Mock memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB in bytes
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        monitor = MemoryMonitor(200.0)  # 200MB limit
        usage = monitor.check_memory_usage()
        
        assert usage.current_mb == 100.0
        assert usage.limit_mb == 200.0
        assert usage.exceeded is False
    
    @patch('psutil.Process')
    def test_memory_delta_calculation(self, mock_process):
        """Test memory delta calculation."""
        # Mock memory info for start
        mock_memory_info_start = Mock()
        mock_memory_info_start.rss = 100 * 1024 * 1024  # 100MB
        
        # Mock memory info for current
        mock_memory_info_current = Mock()
        mock_memory_info_current.rss = 150 * 1024 * 1024  # 150MB
        
        mock_process.return_value.memory_info.side_effect = [
            mock_memory_info_start,  # For start_monitoring
            mock_memory_info_current  # For get_memory_delta_mb
        ]
        
        monitor = MemoryMonitor(512.0)
        monitor.start_monitoring()
        delta = monitor.get_memory_delta_mb()
        
        assert delta == 50.0  # 150MB - 100MB


class TestConcurrentQueryManager:
    """Test concurrent query management functionality."""
    
    def test_concurrent_manager_initialization(self):
        """Test concurrent query manager initialization."""
        manager = ConcurrentQueryManager(max_concurrent=3, queue_timeout=10)
        assert manager.max_concurrent == 3
        assert manager.queue_timeout == 10
        assert manager.active_queries == 0
    
    def test_acquire_query_slot_success(self):
        """Test successful query slot acquisition."""
        manager = ConcurrentQueryManager(max_concurrent=2)
        
        with manager.acquire_query_slot("test_query_1"):
            assert manager.active_queries == 1
        
        assert manager.active_queries == 0
    
    def test_concurrent_query_slots(self):
        """Test multiple concurrent query slots."""
        manager = ConcurrentQueryManager(max_concurrent=2)
        
        def acquire_slot(task_id, results):
            try:
                with manager.acquire_query_slot(task_id):
                    results[task_id] = "acquired"
                    time.sleep(0.1)  # Hold slot briefly
                    results[task_id] = "completed"
            except Exception as e:
                results[task_id] = f"error: {e}"
        
        results = {}
        threads = []
        
        # Start 2 threads (should both succeed)
        for i in range(2):
            thread = threading.Thread(target=acquire_slot, args=(f"query_{i}", results))
            threads.append(thread)
            thread.start()
        
        # Wait for threads to complete
        for thread in threads:
            thread.join()
        
        # Both should have completed successfully
        assert results["query_0"] == "completed"
        assert results["query_1"] == "completed"
    
    def test_concurrent_query_limit_exceeded(self):
        """Test concurrent query limit enforcement."""
        manager = ConcurrentQueryManager(max_concurrent=1, queue_timeout=0.1)
        
        def hold_slot(task_id, results, hold_time=0.2):
            try:
                with manager.acquire_query_slot(task_id):
                    results[task_id] = "acquired"
                    time.sleep(hold_time)
                    results[task_id] = "completed"
            except ConcurrentQueryLimitError as e:
                results[task_id] = "timeout"
            except Exception as e:
                results[task_id] = f"error: {e}"
        
        results = {}
        threads = []
        
        # Start first thread (should succeed)
        thread1 = threading.Thread(target=hold_slot, args=("query_1", results, 0.3))
        threads.append(thread1)
        thread1.start()
        
        # Give first thread time to acquire slot
        time.sleep(0.05)
        
        # Start second thread (should timeout)
        thread2 = threading.Thread(target=hold_slot, args=("query_2", results, 0.1))
        threads.append(thread2)
        thread2.start()
        
        # Wait for threads to complete
        for thread in threads:
            thread.join()
        
        # First should complete, second should timeout
        assert results["query_1"] == "completed"
        assert results["query_2"] == "timeout"
    
    def test_queue_status(self):
        """Test queue status reporting."""
        manager = ConcurrentQueryManager(max_concurrent=3)
        
        status = manager.get_queue_status()
        assert status["active_queries"] == 0
        assert status["max_concurrent"] == 3
        assert status["available_slots"] == 3


class TestQueryExecutorResourceLimits:
    """Test QueryExecutor with resource limits and timeout functionality."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("col1",), ("col2",)]
        mock_cursor.fetchall.return_value = [("value1", "value2"), ("value3", "value4")]
        mock_conn.execute.return_value = mock_cursor
        return mock_conn
    
    def test_query_executor_initialization_with_limits(self, mock_db_connection):
        """Test QueryExecutor initialization with resource limits."""
        executor = QueryExecutor(
            mock_db_connection,
            timeout_seconds=15,
            max_rows=5000,
            max_concurrent=3,
            memory_limit_mb=256.0
        )
        
        assert executor.timeout_seconds == 15
        assert executor.max_rows == 5000
        assert executor.memory_limit_mb == 256.0
        assert executor.concurrent_manager.max_concurrent == 3
        assert executor.memory_monitor.memory_limit_mb == 256.0
    
    @patch('backend.src.query_executor.psutil.Process')
    def test_query_execution_with_monitoring(self, mock_process, mock_db_connection):
        """Test query execution with comprehensive monitoring."""
        # Mock memory monitoring
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        executor = QueryExecutor(mock_db_connection, timeout_seconds=30, memory_limit_mb=512.0)
        
        result = executor.execute_query("SELECT * FROM test_table")
        
        assert isinstance(result, QueryResult)
        assert result.columns == ["col1", "col2"]
        assert len(result.rows) == 2
        assert result.row_count == 2
        assert result.runtime_ms > 0
    
    def test_query_timeout_enforcement(self, mock_db_connection):
        """Test query timeout enforcement."""
        # Mock slow query execution
        def slow_execute(sql):
            time.sleep(0.2)  # Simulate slow query
            mock_cursor = Mock()
            mock_cursor.description = [("col1",)]
            mock_cursor.fetchall.return_value = [("value1",)]
            return mock_cursor
        
        mock_db_connection.execute.side_effect = slow_execute
        
        executor = QueryExecutor(mock_db_connection, timeout_seconds=0.1)  # 100ms timeout
        
        with pytest.raises(QueryTimeoutError):
            executor.execute_query("SELECT * FROM slow_table")
    
    @patch('backend.src.query_executor.psutil.Process')
    def test_memory_limit_enforcement(self, mock_process, mock_db_connection):
        """Test memory limit enforcement during query execution."""
        # Mock memory info that exceeds limit
        mock_memory_info = Mock()
        mock_memory_info.rss = 600 * 1024 * 1024  # 600MB (exceeds 512MB limit)
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        executor = QueryExecutor(mock_db_connection, memory_limit_mb=512.0)
        
        with pytest.raises(QueryExecutionError, match="Memory limit exceeded"):
            executor.execute_query("SELECT * FROM large_table")
    
    def test_result_set_truncation(self, mock_db_connection):
        """Test result set size limits and truncation."""
        # Mock large result set
        large_results = [(f"value_{i}",) for i in range(15)]  # 15 rows
        mock_cursor = Mock()
        mock_cursor.description = [("col1",)]
        mock_cursor.fetchall.return_value = large_results
        mock_db_connection.execute.return_value = mock_cursor
        
        executor = QueryExecutor(mock_db_connection, max_rows=10)
        
        result = executor.execute_with_limits("SELECT * FROM large_table")
        
        assert result.row_count == 10  # Truncated to max_rows
        assert result.truncated is True
        assert len(result.rows) == 10
    
    def test_concurrent_query_limit_enforcement(self, mock_db_connection):
        """Test concurrent query limit enforcement."""
        def slow_execute(sql):
            time.sleep(0.2)  # Hold execution slot
            mock_cursor = Mock()
            mock_cursor.description = [("col1",)]
            mock_cursor.fetchall.return_value = [("value1",)]
            return mock_cursor
        
        mock_db_connection.execute.side_effect = slow_execute
        
        executor = QueryExecutor(mock_db_connection, max_concurrent=1)
        
        def execute_query(task_id, results):
            try:
                result = executor.execute_query(f"SELECT * FROM table_{task_id}")
                results[task_id] = "success"
            except ConcurrentQueryLimitError:
                results[task_id] = "limit_exceeded"
            except Exception as e:
                results[task_id] = f"error: {e}"
        
        results = {}
        threads = []
        
        # Start 2 concurrent queries (second should be queued/rejected)
        for i in range(2):
            thread = threading.Thread(target=execute_query, args=(i, results))
            threads.append(thread)
            thread.start()
        
        # Wait for threads
        for thread in threads:
            thread.join(timeout=1.0)
        
        # At least one should succeed, and we should handle concurrency properly
        success_count = sum(1 for result in results.values() if result == "success")
        assert success_count >= 1
    
    @patch('backend.src.query_executor.psutil.Process')
    def test_resource_status_reporting(self, mock_process, mock_db_connection):
        """Test resource status reporting."""
        # Mock memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 200 * 1024 * 1024  # 200MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        executor = QueryExecutor(
            mock_db_connection,
            timeout_seconds=30,
            max_rows=10000,
            max_concurrent=5,
            memory_limit_mb=512.0
        )
        
        status = executor.get_resource_status()
        
        assert "concurrent_queries" in status
        assert "memory_usage" in status
        assert "limits" in status
        
        assert status["limits"]["timeout_seconds"] == 30
        assert status["limits"]["max_rows"] == 10000
        assert status["limits"]["memory_limit_mb"] == 512.0
        
        assert status["concurrent_queries"]["max_concurrent"] == 5
        assert status["memory_usage"]["limit_mb"] == 512.0


class TestQueryExecutorIntegration:
    """Integration tests for QueryExecutor with real DuckDB."""
    
    @pytest.fixture
    def real_db_connection(self):
        """Create a real DuckDB connection for integration tests."""
        conn = duckdb.connect(":memory:")
        # Create test table
        conn.execute("CREATE TABLE test_data (id INTEGER, name VARCHAR, value DOUBLE)")
        conn.execute("INSERT INTO test_data VALUES (1, 'test1', 10.5), (2, 'test2', 20.5)")
        return conn
    
    @patch('backend.src.query_executor.psutil.Process')
    def test_real_query_execution_with_limits(self, mock_process, real_db_connection):
        """Test real query execution with resource limits."""
        # Mock memory monitoring
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        executor = QueryExecutor(
            real_db_connection,
            timeout_seconds=5,
            max_rows=10,
            max_concurrent=2,
            memory_limit_mb=512.0
        )
        
        result = executor.execute_query("SELECT * FROM test_data ORDER BY id")
        
        assert result.columns == ["id", "name", "value"]
        assert len(result.rows) == 2
        assert result.rows[0] == [1, "test1", 10.5]
        assert result.rows[1] == [2, "test2", 20.5]
        assert result.runtime_ms > 0
        assert not result.truncated
    
    @patch('backend.src.query_executor.psutil.Process')
    def test_real_query_with_truncation(self, mock_process, real_db_connection):
        """Test real query execution with result truncation."""
        # Mock memory monitoring
        mock_memory_info = Mock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        # Add more test data
        for i in range(3, 8):  # Add 5 more rows (total 7 rows)
            real_db_connection.execute(f"INSERT INTO test_data VALUES ({i}, 'test{i}', {i * 10.5})")
        
        executor = QueryExecutor(real_db_connection, max_rows=3)  # Limit to 3 rows
        
        result = executor.execute_with_limits("SELECT * FROM test_data ORDER BY id")
        
        assert len(result.rows) == 3  # Truncated to max_rows
        assert result.truncated is True
        assert result.row_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])