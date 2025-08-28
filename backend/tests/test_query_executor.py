"""
Unit tests for QueryExecutor class.

Tests query execution, timeout handling, result formatting, and resource limits.
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from typing import List, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from query_executor import QueryExecutor, QueryResult, FormattedResults, QueryTimeoutHandler
from exceptions import QueryExecutionError, QueryTimeoutError, DatabaseConnectionError


class TestQueryTimeoutHandler:
    """Test QueryTimeoutHandler functionality."""
    
    def test_timeout_handler_initialization(self):
        """Test timeout handler initialization."""
        handler = QueryTimeoutHandler(30)
        assert handler.timeout_seconds == 30
        assert handler.start_time is None
        assert not handler.is_cancelled
    
    def test_timeout_handler_start(self):
        """Test timeout handler start method."""
        handler = QueryTimeoutHandler(30)
        handler.start()
        assert handler.start_time is not None
        assert not handler.is_cancelled
    
    def test_timeout_handler_check_timeout_false(self):
        """Test timeout check returns False when not timed out."""
        handler = QueryTimeoutHandler(30)
        handler.start()
        assert not handler.check_timeout()
    
    def test_timeout_handler_check_timeout_true(self):
        """Test timeout check returns True when timed out."""
        handler = QueryTimeoutHandler(0.001)  # Very short timeout
        handler.start()
        time.sleep(0.002)  # Wait longer than timeout
        assert handler.check_timeout()
    
    def test_timeout_handler_get_elapsed_ms(self):
        """Test elapsed time calculation."""
        handler = QueryTimeoutHandler(30)
        handler.start()
        time.sleep(0.01)  # Sleep 10ms
        elapsed = handler.get_elapsed_ms()
        assert elapsed >= 10  # Should be at least 10ms
        assert elapsed < 100   # Should be less than 100ms
    
    def test_timeout_handler_cancel(self):
        """Test timeout handler cancellation."""
        handler = QueryTimeoutHandler(30)
        handler.cancel()
        assert handler.is_cancelled


class TestQueryExecutor:
    """Test QueryExecutor functionality."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create mock database connection with context manager support."""
        # Create the actual connection mock that will be returned by the context manager
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [('id',), ('name',), ('value',)]
        mock_cursor.fetchall.return_value = [
            (1, 'test1', 100.5),
            (2, 'test2', 200.0),
            (3, 'test3', 300.25)
        ]
        mock_conn.execute.return_value = mock_cursor
        
        # Create the context manager mock
        mock_context_manager = Mock()
        mock_context_manager.__enter__ = Mock(return_value=mock_conn)
        mock_context_manager.__exit__ = Mock(return_value=None)
        
        # Create the main database connection mock
        mock_db_connection = Mock()
        mock_db_connection.get_connection.return_value = mock_context_manager
        
        return mock_db_connection
    
    @pytest.fixture
    def query_executor(self, mock_db_connection):
        """Create QueryExecutor instance with mock connection."""
        return QueryExecutor(mock_db_connection, timeout_seconds=30, max_rows=1000)
    
    def test_query_executor_initialization(self, mock_db_connection):
        """Test QueryExecutor initialization."""
        executor = QueryExecutor(mock_db_connection, timeout_seconds=60, max_rows=5000)
        assert executor.db_connection == mock_db_connection
        assert executor.timeout_seconds == 60
        assert executor.max_rows == 5000
    
    def test_execute_query_success(self, query_executor, mock_db_connection):
        """Test successful query execution."""
        sql = "SELECT id, name, value FROM test_table"
        
        result = query_executor.execute_query(sql)
        
        assert isinstance(result, QueryResult)
        assert result.columns == ['id', 'name', 'value']
        assert len(result.rows) == 3
        assert result.rows[0] == [1, 'test1', 100.5]
        assert result.row_count == 3
        assert result.runtime_ms > 0
        assert not result.truncated
        
        # Verify the context manager was used and the connection executed the query
        mock_db_connection.get_connection.assert_called()
        mock_context_manager = mock_db_connection.get_connection.return_value
        mock_conn = mock_context_manager.__enter__.return_value
        mock_conn.execute.assert_called_once_with(sql)
    
    def test_execute_query_with_custom_timeout(self, query_executor, mock_db_connection):
        """Test query execution with custom timeout."""
        sql = "SELECT * FROM test_table"
        
        result = query_executor.execute_query(sql, timeout=60)
        
        assert isinstance(result, QueryResult)
        mock_db_connection.execute.assert_called_once_with(sql)
    
    def test_execute_query_database_error(self, query_executor, mock_db_connection):
        """Test query execution with database error."""
        mock_db_connection.execute.side_effect = Exception("Database connection failed")
        
        with pytest.raises(QueryExecutionError) as exc_info:
            query_executor.execute_query("SELECT * FROM test_table")
        
        assert "Query execution failed" in str(exc_info.value)
    
    def test_execute_query_timeout_error(self, query_executor, mock_db_connection):
        """Test query execution timeout."""
        # Mock a slow query by making execute sleep
        def slow_execute(sql):
            time.sleep(0.1)  # Sleep longer than timeout
            mock_cursor = Mock()
            mock_cursor.description = [('id',)]
            mock_cursor.fetchall.return_value = [(1,)]
            return mock_cursor
        
        mock_db_connection.execute.side_effect = slow_execute
        
        with pytest.raises(QueryTimeoutError):
            query_executor.execute_query("SELECT * FROM test_table", timeout=0.01)
    
    def test_execute_with_limits_no_truncation(self, query_executor, mock_db_connection):
        """Test query execution with limits when results fit within limit."""
        sql = "SELECT * FROM test_table"
        
        result = query_executor.execute_with_limits(sql, max_rows=1000)
        
        assert isinstance(result, QueryResult)
        assert result.row_count == 3
        assert not result.truncated
        
        # Should add LIMIT clause
        expected_sql = "SELECT * FROM test_table LIMIT 1001"
        mock_db_connection.execute.assert_called_once_with(expected_sql)
    
    def test_execute_with_limits_with_truncation(self, query_executor, mock_db_connection):
        """Test query execution with limits when results exceed limit."""
        # Mock more rows than the limit
        mock_cursor = Mock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.return_value = [
            (i, f'name{i}') for i in range(5)  # 5 rows
        ]
        mock_db_connection.execute.return_value = mock_cursor
        
        result = query_executor.execute_with_limits("SELECT * FROM test_table", max_rows=3)
        
        assert result.row_count == 3  # Truncated to 3
        assert result.truncated
        assert len(result.rows) == 3
    
    def test_execute_with_limits_existing_limit(self, query_executor, mock_db_connection):
        """Test query execution when SQL already has LIMIT clause."""
        sql = "SELECT * FROM test_table LIMIT 5"
        
        query_executor.execute_with_limits(sql, max_rows=1000)
        
        # Should keep existing smaller limit
        mock_db_connection.execute.assert_called_once_with("SELECT * FROM test_table LIMIT 5")
    
    def test_execute_with_limits_replace_larger_limit(self, query_executor, mock_db_connection):
        """Test query execution when existing LIMIT is larger than max_rows."""
        sql = "SELECT * FROM test_table LIMIT 2000"
        
        query_executor.execute_with_limits(sql, max_rows=1000)
        
        # Should replace with smaller limit
        expected_sql = "SELECT * FROM test_table LIMIT 1001"
        mock_db_connection.execute.assert_called_once_with(expected_sql)
    
    def test_format_results_success(self, query_executor):
        """Test successful result formatting."""
        mock_results = Mock()
        mock_results.description = [('id',), ('name',), ('value',)]
        mock_results.fetchall.return_value = [
            (1, 'test1', 100.5),
            (2, 'test2', None),
            (3, 'test3', 300.25)
        ]
        
        formatted = query_executor.format_results(mock_results)
        
        assert isinstance(formatted, FormattedResults)
        assert formatted.columns == ['id', 'name', 'value']
        assert len(formatted.rows) == 3
        assert formatted.rows[0] == [1, 'test1', 100.5]
        assert formatted.rows[1] == [2, 'test2', None]  # None should be preserved
        assert formatted.row_count == 3
        assert not formatted.truncated
    
    def test_format_results_no_description(self, query_executor):
        """Test result formatting when cursor has no description."""
        mock_results = Mock()
        mock_results.description = None
        mock_results.fetchall.return_value = [(1,), (2,), (3,)]
        
        formatted = query_executor.format_results(mock_results)
        
        assert formatted.columns == []
        assert len(formatted.rows) == 3
    
    def test_format_results_list_input(self, query_executor):
        """Test result formatting with list input."""
        raw_results = [(1, 'test1'), (2, 'test2')]
        
        formatted = query_executor.format_results(raw_results)
        
        assert formatted.columns == []
        assert len(formatted.rows) == 2
        assert formatted.rows[0] == [1, 'test1']
    
    def test_format_value_basic_types(self, query_executor):
        """Test value formatting for basic types."""
        assert query_executor._format_value(None) is None
        assert query_executor._format_value(42) == 42
        assert query_executor._format_value(3.14) == 3.14
        assert query_executor._format_value("test") == "test"
        assert query_executor._format_value(True) is True
        assert query_executor._format_value(False) is False
    
    def test_format_value_datetime(self, query_executor):
        """Test value formatting for datetime objects."""
        from datetime import datetime
        dt = datetime(2023, 1, 1, 12, 0, 0)
        formatted = query_executor._format_value(dt)
        assert formatted == "2023-01-01T12:00:00"
    
    def test_format_value_bytes(self, query_executor):
        """Test value formatting for bytes."""
        byte_data = b"test data"
        formatted = query_executor._format_value(byte_data)
        assert formatted == "test data"
    
    def test_format_value_other_types(self, query_executor):
        """Test value formatting for other types."""
        class CustomObject:
            def __str__(self):
                return "custom_object"
        
        obj = CustomObject()
        formatted = query_executor._format_value(obj)
        assert formatted == "custom_object"
    
    def test_add_limit_clause_no_existing_limit(self, query_executor):
        """Test adding LIMIT clause when none exists."""
        sql = "SELECT * FROM test_table"
        limited_sql = query_executor._add_limit_clause(sql, 100)
        assert limited_sql == "SELECT * FROM test_table LIMIT 100"
    
    def test_add_limit_clause_with_semicolon(self, query_executor):
        """Test adding LIMIT clause with semicolon removal."""
        sql = "SELECT * FROM test_table;"
        limited_sql = query_executor._add_limit_clause(sql, 100)
        assert limited_sql == "SELECT * FROM test_table LIMIT 100"
    
    def test_add_limit_clause_existing_smaller_limit(self, query_executor):
        """Test keeping existing smaller LIMIT."""
        sql = "SELECT * FROM test_table LIMIT 50"
        limited_sql = query_executor._add_limit_clause(sql, 100)
        assert limited_sql == "SELECT * FROM test_table LIMIT 50"
    
    def test_add_limit_clause_existing_larger_limit(self, query_executor):
        """Test replacing existing larger LIMIT."""
        sql = "SELECT * FROM test_table LIMIT 200"
        limited_sql = query_executor._add_limit_clause(sql, 100)
        assert limited_sql == "SELECT * FROM test_table LIMIT 100"
    
    def test_add_limit_clause_case_insensitive(self, query_executor):
        """Test LIMIT clause handling is case insensitive."""
        sql = "select * from test_table limit 200"
        limited_sql = query_executor._add_limit_clause(sql, 100)
        assert "LIMIT 100" in limited_sql
    
    def test_concurrent_query_execution(self, query_executor, mock_db_connection):
        """Test that concurrent queries are handled safely."""
        results = []
        errors = []
        
        def execute_query(query_id):
            try:
                sql = f"SELECT {query_id} as id"
                result = query_executor.execute_query(sql)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads to execute queries concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=execute_query, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All queries should succeed (though they'll be serialized by the lock)
        assert len(errors) == 0
        assert len(results) == 5
    
    def test_query_execution_with_empty_results(self, query_executor, mock_db_connection):
        """Test query execution with empty result set."""
        mock_cursor = Mock()
        mock_cursor.description = [('count',)]
        mock_cursor.fetchall.return_value = []
        mock_db_connection.execute.return_value = mock_cursor
        
        result = query_executor.execute_query("SELECT COUNT(*) FROM empty_table WHERE 1=0")
        
        assert result.row_count == 0
        assert len(result.rows) == 0
        assert result.columns == ['count']
        assert not result.truncated
    
    def test_query_execution_performance_logging(self, query_executor, mock_db_connection):
        """Test that query execution logs performance metrics."""
        with patch('query_executor.logger') as mock_logger:
            query_executor.execute_query("SELECT * FROM test_table")
            
            # Check that info logs were called for execution start and success
            assert mock_logger.info.call_count >= 2
            
            # Check that one of the calls mentions execution time
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("executed successfully" in call for call in log_calls)
    
    def test_query_execution_error_logging(self, query_executor, mock_db_connection):
        """Test that query execution errors are properly logged."""
        mock_db_connection.execute.side_effect = Exception("Test database error")
        
        with patch('query_executor.logger') as mock_logger:
            with pytest.raises(QueryExecutionError):
                query_executor.execute_query("SELECT * FROM test_table")
            
            # Check that error was logged
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "Query execution failed" in error_message


if __name__ == "__main__":
    pytest.main([__file__])