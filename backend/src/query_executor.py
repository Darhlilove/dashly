"""
Query Executor for SQL execution with DuckDB integration.

Provides secure query execution with timeout handling, resource limits,
and result formatting for API responses.
"""

import asyncio
import time
import threading
import psutil
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
from queue import Queue, Empty
import duckdb

try:
    from .exceptions import (
        QueryExecutionError,
        SQLSyntaxError,
        SQLSchemaError,
        QueryTimeoutError,
        ResultSetTooLargeError,
        DatabaseConnectionError,
        ConcurrentQueryLimitError
    )
    from .logging_config import get_logger, DashlyLogger
    from .response_cache import get_response_cache
    from .streaming_response import get_streaming_manager, QueryStreamProcessor
except ImportError:
    from exceptions import (
        QueryExecutionError,
        SQLSyntaxError,
        SQLSchemaError,
        QueryTimeoutError,
        ResultSetTooLargeError,
        DatabaseConnectionError,
        ConcurrentQueryLimitError
    )
    from logging_config import get_logger, DashlyLogger
    from response_cache import get_response_cache
    from streaming_response import get_streaming_manager, QueryStreamProcessor

logger = get_logger(__name__)


@dataclass
class QueryResult:
    """Result of SQL query execution."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    runtime_ms: float
    truncated: bool = False


@dataclass
class FormattedResults:
    """Formatted query results for API responses."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    runtime_ms: float
    truncated: bool = False


@dataclass
class MemoryUsage:
    """Memory usage information."""
    current_mb: float
    peak_mb: float
    limit_mb: float
    exceeded: bool = False


@dataclass
class QueryTask:
    """Represents a queued query task."""
    sql: str
    timeout: int
    max_rows: Optional[int]
    task_id: str
    created_at: float


class MemoryMonitor:
    """Monitors memory usage during query execution."""
    
    def __init__(self, memory_limit_mb: float = 512.0):
        """
        Initialize memory monitor.
        
        Args:
            memory_limit_mb: Memory limit in megabytes (Requirements 6.4)
        """
        self.memory_limit_mb = memory_limit_mb
        self.process = psutil.Process(os.getpid())
        self.start_memory = None
        self.peak_memory = 0.0
        
    def start_monitoring(self):
        """Start memory monitoring."""
        try:
            memory_info = self.process.memory_info()
            self.start_memory = memory_info.rss / 1024 / 1024  # Convert to MB
            self.peak_memory = self.start_memory
            logger.debug(f"Memory monitoring started: {self.start_memory:.2f} MB")
        except Exception as e:
            logger.warning(f"Failed to start memory monitoring: {e}")
            self.start_memory = 0.0
    
    def check_memory_usage(self) -> MemoryUsage:
        """
        Check current memory usage.
        
        Returns:
            MemoryUsage: Current memory usage information
        """
        try:
            memory_info = self.process.memory_info()
            current_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            
            # Update peak memory
            if current_mb > self.peak_memory:
                self.peak_memory = current_mb
            
            exceeded = current_mb > self.memory_limit_mb
            
            return MemoryUsage(
                current_mb=current_mb,
                peak_mb=self.peak_memory,
                limit_mb=self.memory_limit_mb,
                exceeded=exceeded
            )
        except Exception as e:
            logger.warning(f"Failed to check memory usage: {e}")
            return MemoryUsage(
                current_mb=0.0,
                peak_mb=0.0,
                limit_mb=self.memory_limit_mb,
                exceeded=False
            )
    
    def get_memory_delta_mb(self) -> float:
        """Get memory usage delta since monitoring started."""
        if self.start_memory is None:
            return 0.0
        
        try:
            memory_info = self.process.memory_info()
            current_mb = memory_info.rss / 1024 / 1024
            return current_mb - self.start_memory
        except Exception as e:
            logger.warning(f"Failed to calculate memory delta: {e}")
            return 0.0


class ConcurrentQueryManager:
    """Manages concurrent query execution and queuing."""
    
    def __init__(self, max_concurrent: int = 5, queue_timeout: int = 30):
        """
        Initialize concurrent query manager.
        
        Args:
            max_concurrent: Maximum number of concurrent queries (Requirements 6.3)
            queue_timeout: Maximum time to wait in queue (seconds)
        """
        self.max_concurrent = max_concurrent
        self.queue_timeout = queue_timeout
        self.active_queries = 0
        self.query_queue = Queue()
        self._lock = threading.Lock()
        self._active_lock = threading.Semaphore(max_concurrent)
        
        logger.info(f"ConcurrentQueryManager initialized: max_concurrent={max_concurrent}")
    
    @contextmanager
    def acquire_query_slot(self, task_id: str):
        """
        Acquire a query execution slot with queuing.
        
        Args:
            task_id: Unique identifier for the query task
            
        Raises:
            ConcurrentQueryLimitError: If queue is full or timeout exceeded
        """
        acquired = False
        start_time = time.time()
        
        try:
            # Try to acquire semaphore with timeout
            acquired = self._active_lock.acquire(timeout=self.queue_timeout)
            
            if not acquired:
                wait_time = time.time() - start_time
                logger.warning(f"Query {task_id} timed out waiting for execution slot after {wait_time:.2f}s")
                raise ConcurrentQueryLimitError(
                    f"Query timed out waiting for execution slot after {wait_time:.2f}s",
                    max_concurrent=self.max_concurrent
                )
            
            with self._lock:
                self.active_queries += 1
                
            wait_time = time.time() - start_time
            logger.info(f"Query {task_id} acquired execution slot after {wait_time:.2f}s wait (active: {self.active_queries})")
            
            yield
            
        except Exception as e:
            # Don't log here as the error will be logged by the caller
            raise
        finally:
            if acquired:
                with self._lock:
                    self.active_queries -= 1
                self._active_lock.release()
                logger.debug(f"Query {task_id} released execution slot (active: {self.active_queries})")
    
    def get_queue_status(self) -> dict:
        """Get current queue status."""
        with self._lock:
            return {
                "active_queries": self.active_queries,
                "max_concurrent": self.max_concurrent,
                "queue_size": self.query_queue.qsize(),
                "available_slots": self.max_concurrent - self.active_queries
            }


class QueryTimeoutHandler:
    """Handles query timeout using threading with improved cancellation."""
    
    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        self.start_time = None
        self.is_cancelled = False
        self._lock = threading.Lock()
        self._timeout_thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start the timeout timer."""
        self.start_time = time.time()
        self.is_cancelled = False
        self._stop_event.clear()
    
    def check_timeout(self) -> bool:
        """Check if query has timed out."""
        if self.start_time is None:
            return False
        
        elapsed = time.time() - self.start_time
        return elapsed > self.timeout_seconds
    
    def cancel(self):
        """Cancel the timeout."""
        with self._lock:
            self.is_cancelled = True
            self._stop_event.set()
    
    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) * 1000


class QueryExecutor:
    """
    Executes validated SQL queries against DuckDB with security and performance controls.
    
    Provides query execution with timeout handling, resource limits, concurrent query
    management, and memory monitoring for API responses.
    """
    
    def __init__(self, db_connection, timeout_seconds: int = 30, max_rows: int = 10000,
                 max_concurrent: int = 5, memory_limit_mb: float = 512.0):
        """
        Initialize QueryExecutor with DuckDB connection and resource limits.
        
        Args:
            db_connection: DuckDB connection instance
            timeout_seconds: Maximum query execution time (Requirements 6.1)
            max_rows: Maximum number of rows to return (Requirements 6.2)
            max_concurrent: Maximum concurrent queries (Requirements 6.3)
            memory_limit_mb: Memory limit in MB (Requirements 6.4)
        """
        self.db_connection = db_connection
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows
        self.memory_limit_mb = memory_limit_mb
        
        # Initialize resource management components
        self.concurrent_manager = ConcurrentQueryManager(max_concurrent)
        self.memory_monitor = MemoryMonitor(memory_limit_mb)
        self._execution_lock = threading.Lock()
        
        # Performance optimization components (Requirements 6.1, 6.2)
        self.response_cache = get_response_cache()
        self.streaming_manager = get_streaming_manager()
        self.stream_processor = QueryStreamProcessor(self.streaming_manager)
        
        logger.info(f"QueryExecutor initialized with performance optimizations: timeout={timeout_seconds}s, "
                   f"max_rows={max_rows}, max_concurrent={max_concurrent}, memory_limit={memory_limit_mb}MB")
    
    def execute_query(self, sql: str, timeout: int = None) -> QueryResult:
        """
        Execute SQL query with comprehensive resource management.
        
        Args:
            sql: Validated SQL query to execute
            timeout: Optional timeout override (seconds)
            
        Returns:
            QueryResult: Query execution results
            
        Raises:
            QueryTimeoutError: If query execution exceeds timeout
            ConcurrentQueryLimitError: If concurrent query limit exceeded
            QueryExecutionError: If query execution fails
            DatabaseConnectionError: If database connection fails
        """
        effective_timeout = timeout or self.timeout_seconds
        task_id = f"query_{int(time.time() * 1000)}"
        
        logger.info(f"Executing query {task_id} with timeout {effective_timeout}s: {sql[:100]}...")
        
        # Check cache first for performance optimization (Requirements 6.1)
        from .models import ExecuteResponse
        cached_result = self.response_cache.get_query_result(sql)
        if cached_result:
            logger.info(f"Cache hit for query {task_id}: {sql[:50]}...")
            return QueryResult(
                columns=cached_result.columns,
                rows=cached_result.rows,
                row_count=len(cached_result.rows),
                runtime_ms=1.0,  # Very fast for cached
                truncated=cached_result.truncated if hasattr(cached_result, 'truncated') else False
            )
        
        # Acquire concurrent query slot with queuing (Requirements 6.3)
        with self.concurrent_manager.acquire_query_slot(task_id):
            timeout_handler = QueryTimeoutHandler(effective_timeout)
            
            try:
                # Start timing and memory monitoring
                timeout_handler.start()
                self.memory_monitor.start_monitoring()
                
                # Execute query with comprehensive monitoring
                result = self._execute_with_monitoring(sql, timeout_handler, task_id)
                
                runtime_ms = timeout_handler.get_elapsed_ms()
                memory_delta = self.memory_monitor.get_memory_delta_mb()
                
                logger.info(f"Query {task_id} executed successfully in {runtime_ms:.2f}ms, "
                           f"{result.row_count} rows, memory delta: {memory_delta:.2f}MB")
                
                # Cache successful results for future use (Requirements 6.1)
                if runtime_ms < 2000 and result.row_count < 5000:  # Only cache fast, reasonable-sized results
                    try:
                        execute_response = ExecuteResponse(
                            columns=result.columns,
                            rows=result.rows,
                            row_count=result.row_count,
                            runtime_ms=runtime_ms,
                            truncated=result.truncated
                        )
                        self.response_cache.cache_query_result(
                            sql, 
                            execute_response,
                            ttl=600  # 10 minutes TTL for query results
                        )
                    except Exception as cache_error:
                        logger.warning(f"Failed to cache query result: {cache_error}")
                
                return result
                
            except QueryTimeoutError:
                logger.warning(f"Query {task_id} timed out after {effective_timeout}s: {sql[:50]}...")
                raise
            except Exception as e:
                runtime_ms = timeout_handler.get_elapsed_ms()
                error_msg = str(e)
                logger.error(f"Query execution failed after {runtime_ms:.2f}ms: {error_msg}")
                
                # Detect specific error types and raise appropriate exceptions
                if any(keyword in error_msg.lower() for keyword in ["table", "column", "not found", "does not exist"]):
                    # Schema-related error
                    missing_object = None
                    object_type = "table"
                    
                    # Try to extract object name from error message
                    import re
                    table_match = re.search(r"table['\s]*(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                    column_match = re.search(r"column['\s]*(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                    
                    if table_match:
                        missing_object = table_match.group(2)
                        object_type = "table"
                    elif column_match:
                        missing_object = column_match.group(2)
                        object_type = "column"
                    
                    raise SQLSchemaError(
                        message=error_msg,
                        missing_object=missing_object,
                        object_type=object_type
                    )
                elif any(keyword in error_msg.lower() for keyword in ["syntax", "parse", "invalid"]):
                    # Syntax-related error
                    raise SQLSyntaxError(message=error_msg)
                else:
                    # General execution error
                    raise QueryExecutionError(f"Query execution failed: {error_msg}")
            finally:
                timeout_handler.cancel()
    
    def execute_with_limits(self, sql: str, max_rows: int = None) -> QueryResult:
        """
        Execute query with comprehensive resource limits and truncation.
        
        Args:
            sql: Validated SQL query to execute
            max_rows: Optional max rows override
            
        Returns:
            QueryResult: Query execution results with truncation info
            
        Raises:
            ResultSetTooLargeError: If result set exceeds limits (Requirements 6.2)
        """
        effective_max_rows = max_rows or self.max_rows
        
        # Modify query to include LIMIT clause for efficiency
        limited_sql = self._add_limit_clause(sql, effective_max_rows + 1)  # +1 to detect truncation
        
        logger.info(f"Executing query with row limit {effective_max_rows}: {sql[:100]}...")
        
        try:
            result = self.execute_query(limited_sql)
            
            # Check if results were truncated (Requirements 6.2)
            if result.row_count > effective_max_rows:
                logger.warning(f"Result set truncated: {result.row_count} -> {effective_max_rows} rows")
                result.rows = result.rows[:effective_max_rows]
                result.row_count = effective_max_rows
                result.truncated = True
                
                # Add truncation warning to result
                logger.info(f"Query result truncated to {effective_max_rows} rows due to size limits")
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution with limits failed: {str(e)}")
            raise
    
    def format_results(self, raw_results: Any) -> FormattedResults:
        """
        Format raw DuckDB results for API responses.
        
        Args:
            raw_results: Raw results from DuckDB query execution
            
        Returns:
            FormattedResults: Formatted results for API response
        """
        try:
            # Extract column names from cursor description
            if hasattr(raw_results, 'description') and raw_results.description:
                columns = [desc[0] for desc in raw_results.description]
            else:
                columns = []
            
            # Extract rows
            if hasattr(raw_results, 'fetchall'):
                rows_data = raw_results.fetchall()
            else:
                rows_data = raw_results if isinstance(raw_results, list) else []
            
            # Convert to list of lists for JSON serialization
            rows = []
            for row in rows_data:
                if isinstance(row, (list, tuple)):
                    # Convert any non-serializable types to strings
                    formatted_row = [self._format_value(val) for val in row]
                    rows.append(formatted_row)
                else:
                    # Single value row
                    rows.append([self._format_value(row)])
            
            row_count = len(rows)
            
            logger.debug(f"Formatted results: {row_count} rows, {len(columns)} columns")
            
            return FormattedResults(
                columns=columns,
                rows=rows,
                row_count=row_count,
                runtime_ms=0.0,  # Will be set by caller
                truncated=False
            )
            
        except Exception as e:
            logger.error(f"Result formatting failed: {str(e)}")
            raise QueryExecutionError(f"Failed to format query results: {str(e)}")
    
    def _execute_with_monitoring(self, sql: str, timeout_handler: QueryTimeoutHandler, task_id: str) -> QueryResult:
        """
        Execute query with comprehensive timeout and memory monitoring.
        
        Args:
            sql: SQL query to execute
            timeout_handler: Timeout handler instance
            task_id: Unique task identifier for logging
            
        Returns:
            QueryResult: Query execution results
            
        Raises:
            QueryTimeoutError: If query times out
            QueryExecutionError: If execution fails or memory limit exceeded
        """
        try:
            # Use threading lock to prevent concurrent executions that could interfere
            with self._execution_lock:
                # Check timeout before starting
                if timeout_handler.check_timeout():
                    raise QueryTimeoutError(f"Query {task_id} timed out before execution")
                
                # Check memory before execution
                memory_usage = self.memory_monitor.check_memory_usage()
                if memory_usage.exceeded:
                    raise QueryExecutionError(
                        f"Memory limit exceeded before query execution: "
                        f"{memory_usage.current_mb:.2f}MB > {memory_usage.limit_mb}MB"
                    )
                
                # Execute the query using connection pool
                logger.debug(f"Starting query execution for {task_id}")
                try:
                    with self.db_connection.get_connection() as conn:
                        cursor = conn.execute(sql)
                        
                        # Check timeout and memory after execution starts
                        if timeout_handler.check_timeout():
                            raise QueryTimeoutError(f"Query {task_id} execution timed out")
                        
                        memory_usage = self.memory_monitor.check_memory_usage()
                        if memory_usage.exceeded:
                            logger.warning(f"Memory limit exceeded during query {task_id}: "
                                         f"{memory_usage.current_mb:.2f}MB > {memory_usage.limit_mb}MB")
                            raise QueryExecutionError(
                                f"Memory limit exceeded during query execution: "
                                f"{memory_usage.current_mb:.2f}MB > {memory_usage.limit_mb}MB"
                            )
                        
                        # Fetch results with monitoring
                        logger.debug(f"Fetching results for query {task_id}")
                        rows_data = cursor.fetchall()
                        
                        # Check timeout and memory after fetching
                        if timeout_handler.check_timeout():
                            raise QueryTimeoutError(f"Query {task_id} result fetching timed out")
                        
                        memory_usage = self.memory_monitor.check_memory_usage()
                        if memory_usage.exceeded:
                            logger.warning(f"Memory limit exceeded during result fetching for {task_id}: "
                                         f"{memory_usage.current_mb:.2f}MB > {memory_usage.limit_mb}MB")
                            # Don't fail here, just log warning as results are already fetched
                        
                        # Get column information
                        columns = [desc[0] for desc in cursor.description] if cursor.description else []
                        
                except Exception as e:
                    # Handle DuckDB-specific errors and convert them to appropriate exceptions
                    error_msg = str(e)
                    
                    # Check for syntax errors
                    if any(keyword in error_msg.lower() for keyword in ["syntax error", "parser error", "parse error"]):
                        raise SQLSyntaxError(message=error_msg)
                    
                    # Check for schema-related errors
                    elif any(keyword in error_msg.lower() for keyword in ["table", "column", "not found", "does not exist"]):
                        missing_object = None
                        object_type = "table"
                        
                        # Try to extract object name from error message
                        import re
                        table_match = re.search(r"table['\s]*(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                        column_match = re.search(r"column['\s]*(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                        
                        if table_match:
                            missing_object = table_match.group(2)
                            object_type = "table"
                        elif column_match:
                            missing_object = column_match.group(2)
                            object_type = "column"
                        
                        raise SQLSchemaError(
                            message=error_msg,
                            missing_object=missing_object,
                            object_type=object_type
                        )
                    
                    # Check for timeout-related errors
                    elif "timeout" in error_msg.lower():
                        raise QueryTimeoutError(f"Query {task_id} execution timed out: {error_msg}")
                    
                    # General execution error
                    else:
                        raise QueryExecutionError(error_msg)
                
                # Format rows for API response
                rows = []
                for row in rows_data:
                    formatted_row = [self._format_value(val) for val in row]
                    rows.append(formatted_row)
                
                runtime_ms = timeout_handler.get_elapsed_ms()
                
                logger.debug(f"Query {task_id} completed: {len(rows)} rows, "
                           f"peak memory: {memory_usage.peak_mb:.2f}MB")
                
                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    runtime_ms=runtime_ms,
                    truncated=False
                )
                
        except QueryTimeoutError:
            raise
        except Exception as e:
            error_msg = str(e)
            
            if "timeout" in error_msg.lower():
                raise QueryTimeoutError(f"Query {task_id} execution timed out: {error_msg}")
            elif "memory limit exceeded" in error_msg.lower():
                # Memory limit error - already formatted
                raise QueryExecutionError(error_msg)
            elif any(keyword in error_msg.lower() for keyword in ["table", "column", "not found", "does not exist"]):
                # Schema-related error
                missing_object = None
                object_type = "table"
                
                # Try to extract object name from error message
                import re
                table_match = re.search(r"table['\s]*(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                column_match = re.search(r"column['\s]*(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                
                if table_match:
                    missing_object = table_match.group(2)
                    object_type = "table"
                elif column_match:
                    missing_object = column_match.group(2)
                    object_type = "column"
                
                raise SQLSchemaError(
                    message=error_msg,
                    missing_object=missing_object,
                    object_type=object_type
                )
            elif any(keyword in error_msg.lower() for keyword in ["syntax", "parse", "invalid"]):
                # Syntax-related error
                raise SQLSyntaxError(message=error_msg)
            else:
                raise QueryExecutionError(error_msg)
    
    def get_resource_status(self) -> dict:
        """
        Get current resource usage status.
        
        Returns:
            dict: Resource usage information
        """
        queue_status = self.concurrent_manager.get_queue_status()
        memory_usage = self.memory_monitor.check_memory_usage()
        
        return {
            "concurrent_queries": queue_status,
            "memory_usage": {
                "current_mb": memory_usage.current_mb,
                "peak_mb": memory_usage.peak_mb,
                "limit_mb": memory_usage.limit_mb,
                "usage_percent": (memory_usage.current_mb / memory_usage.limit_mb) * 100
            },
            "limits": {
                "timeout_seconds": self.timeout_seconds,
                "max_rows": self.max_rows,
                "memory_limit_mb": self.memory_limit_mb
            }
        }
    
    def _add_limit_clause(self, sql: str, limit: int) -> str:
        """
        Add LIMIT clause to SQL query if not already present.
        
        Args:
            sql: Original SQL query
            limit: Row limit to add
            
        Returns:
            str: SQL query with LIMIT clause
        """
        sql_upper = sql.upper().strip()
        
        # Check if LIMIT already exists
        if 'LIMIT' in sql_upper:
            # Extract existing limit and use the smaller value
            limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
            if limit_match:
                existing_limit = int(limit_match.group(1))
                if existing_limit <= limit:
                    return sql  # Keep existing smaller limit
                else:
                    # Replace with smaller limit
                    return re.sub(r'LIMIT\s+\d+', f'LIMIT {limit}', sql, flags=re.IGNORECASE)
        
        # Add LIMIT clause
        return f"{sql.rstrip(';')} LIMIT {limit}"
    
    def _format_value(self, value: Any) -> Any:
        """
        Format a single value for JSON serialization.
        
        Args:
            value: Value to format
            
        Returns:
            Any: JSON-serializable value
        """
        if value is None:
            return None
        elif isinstance(value, (int, float, str, bool)):
            return value
        elif hasattr(value, 'isoformat'):  # datetime objects
            return value.isoformat()
        elif isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        else:
            # Try to preserve numeric types
            try:
                # Check if it's a decimal/numeric type that should stay as float
                if hasattr(value, '__float__'):
                    return float(value)
                elif hasattr(value, '__int__'):
                    return int(value)
            except (ValueError, TypeError):
                pass
            # Convert other types to string
            return str(value)
    
    async def execute_query_with_streaming(self, sql: str, stream_id: str, timeout: int = None) -> QueryResult:
        """
        Execute SQL query with streaming updates for better perceived performance.
        
        Args:
            sql: Validated SQL query to execute
            stream_id: Stream identifier for progress updates
            timeout: Optional timeout override (seconds)
            
        Returns:
            QueryResult: Query execution results
        """
        # Use streaming processor for better UX (Requirements 6.2)
        return await self.stream_processor.execute_with_streaming(
            stream_id,
            self.execute_query,
            sql,
            timeout
        )


# Import required for _add_limit_clause method
import re