"""
Performance monitoring system for SQL query execution.

Provides timing context management, execution time measurement, slow query detection,
and performance metrics tracking with logging capabilities.
"""

import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque

try:
    from .logging_config import get_logger
except ImportError:
    from logging_config import get_logger


@dataclass
class QueryMetrics:
    """Performance metrics for query execution."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    average_runtime_ms: float = 0.0
    slow_queries_count: int = 0
    timeout_count: int = 0
    min_runtime_ms: float = float('inf')
    max_runtime_ms: float = 0.0
    total_runtime_ms: float = 0.0


@dataclass
class QueryExecutionRecord:
    """Record of a single query execution."""
    sql: str
    runtime_ms: float
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None
    row_count: Optional[int] = None
    truncated: bool = False


@dataclass
class PerformanceStats:
    """Comprehensive performance statistics."""
    metrics: QueryMetrics
    recent_queries: List[QueryExecutionRecord]
    slow_queries: List[QueryExecutionRecord]
    error_queries: List[QueryExecutionRecord]
    uptime_seconds: float
    queries_per_minute: float


class TimingContext:
    """Context manager for measuring execution time."""
    
    def __init__(self, operation_name: str = "operation"):
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.logger = get_logger(__name__)
    
    def __enter__(self) -> 'TimingContext':
        """Start timing the operation."""
        self.start_time = time.perf_counter()
        self.logger.debug(f"Started timing: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End timing the operation."""
        self.end_time = time.perf_counter()
        elapsed_ms = self.get_elapsed_ms()
        
        if exc_type is None:
            self.logger.debug(f"Completed timing: {self.operation_name} ({elapsed_ms:.2f}ms)")
        else:
            self.logger.debug(f"Failed timing: {self.operation_name} ({elapsed_ms:.2f}ms) - {exc_type.__name__}")
    
    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0.0
        
        end_time = self.end_time if self.end_time is not None else time.perf_counter()
        return (end_time - self.start_time) * 1000.0


class PerformanceMonitor:
    """
    Performance monitoring system for SQL query execution.
    
    Provides timing context management, execution time measurement,
    slow query detection, and performance metrics tracking.
    """
    
    def __init__(self, slow_query_threshold_ms: float = 1000.0, max_history_size: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            slow_query_threshold_ms: Threshold in milliseconds for slow query detection
            max_history_size: Maximum number of query records to keep in history
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.max_history_size = max_history_size
        self.start_time = datetime.now()
        
        # Thread-safe metrics tracking
        self._lock = threading.RLock()
        self._metrics = QueryMetrics()
        
        # Query history (using deque for efficient append/pop operations)
        self._query_history: deque = deque(maxlen=max_history_size)
        self._slow_queries: deque = deque(maxlen=100)  # Keep last 100 slow queries
        self._error_queries: deque = deque(maxlen=100)  # Keep last 100 error queries
        
        # Performance tracking
        self._query_times_by_minute: Dict[datetime, int] = defaultdict(int)
        
        self.logger = get_logger(__name__)
        self.logger.info(f"PerformanceMonitor initialized with slow query threshold: {slow_query_threshold_ms}ms")
    
    def start_timing(self, operation_name: str = "query_execution") -> TimingContext:
        """
        Start timing an operation.
        
        Args:
            operation_name: Name of the operation being timed
            
        Returns:
            TimingContext: Context manager for timing the operation
        """
        return TimingContext(operation_name)
    
    @contextmanager
    def time_operation(self, operation_name: str = "operation"):
        """
        Context manager for timing operations with automatic recording.
        
        Args:
            operation_name: Name of the operation being timed
            
        Yields:
            TimingContext: The timing context
        """
        with self.start_timing(operation_name) as timing_context:
            yield timing_context
    
    def record_execution(self, sql: str, runtime_ms: float, success: bool, 
                        error_message: Optional[str] = None, row_count: Optional[int] = None,
                        truncated: bool = False) -> None:
        """
        Record a query execution for performance tracking.
        
        Args:
            sql: The SQL query that was executed
            runtime_ms: Execution time in milliseconds
            success: Whether the query executed successfully
            error_message: Error message if query failed
            row_count: Number of rows returned (if successful)
            truncated: Whether results were truncated
        """
        with self._lock:
            # Create execution record
            record = QueryExecutionRecord(
                sql=sql[:200] + "..." if len(sql) > 200 else sql,  # Truncate long queries for logging
                runtime_ms=runtime_ms,
                success=success,
                timestamp=datetime.now(),
                error_message=error_message,
                row_count=row_count,
                truncated=truncated
            )
            
            # Add to history
            self._query_history.append(record)
            
            # Update metrics
            self._metrics.total_queries += 1
            
            if success:
                self._metrics.successful_queries += 1
                self._metrics.total_runtime_ms += runtime_ms
                
                # Update min/max runtime
                if runtime_ms < self._metrics.min_runtime_ms:
                    self._metrics.min_runtime_ms = runtime_ms
                if runtime_ms > self._metrics.max_runtime_ms:
                    self._metrics.max_runtime_ms = runtime_ms
                
                # Update average runtime
                self._metrics.average_runtime_ms = (
                    self._metrics.total_runtime_ms / self._metrics.successful_queries
                )
                
                # Check for slow query
                if self.is_slow_query(runtime_ms):
                    self._metrics.slow_queries_count += 1
                    self._slow_queries.append(record)
                    self.logger.warning(
                        f"Slow query detected: {runtime_ms:.2f}ms > {self.slow_query_threshold_ms}ms - "
                        f"Query: {record.sql}"
                    )
            else:
                self._metrics.failed_queries += 1
                self._error_queries.append(record)
                
                # Check if this was a timeout error
                if error_message and "timeout" in error_message.lower():
                    self._metrics.timeout_count += 1
                
                self.logger.error(f"Query execution failed: {error_message} - Query: {record.sql}")
            
            # Track queries per minute
            current_minute = datetime.now().replace(second=0, microsecond=0)
            self._query_times_by_minute[current_minute] += 1
            
            # Clean up old minute data (keep last hour)
            cutoff_time = current_minute - timedelta(hours=1)
            keys_to_remove = [k for k in self._query_times_by_minute.keys() if k < cutoff_time]
            for key in keys_to_remove:
                del self._query_times_by_minute[key]
            
            # Log execution summary
            status = "SUCCESS" if success else "FAILED"
            row_info = f" ({row_count} rows)" if row_count is not None else ""
            truncated_info = " [TRUNCATED]" if truncated else ""
            
            self.logger.info(
                f"Query execution: {status} - {runtime_ms:.2f}ms{row_info}{truncated_info}"
            )
    
    def is_slow_query(self, runtime_ms: float) -> bool:
        """
        Check if a query execution time qualifies as slow.
        
        Args:
            runtime_ms: Query execution time in milliseconds
            
        Returns:
            bool: True if query is considered slow
        """
        return runtime_ms > self.slow_query_threshold_ms
    
    def get_performance_stats(self) -> PerformanceStats:
        """
        Get comprehensive performance statistics.
        
        Returns:
            PerformanceStats: Current performance statistics
        """
        with self._lock:
            # Calculate uptime
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
            
            # Calculate queries per minute (average over last hour)
            total_queries_last_hour = sum(self._query_times_by_minute.values())
            minutes_with_data = len(self._query_times_by_minute)
            queries_per_minute = (
                total_queries_last_hour / max(minutes_with_data, 1)
                if minutes_with_data > 0 else 0.0
            )
            
            return PerformanceStats(
                metrics=QueryMetrics(
                    total_queries=self._metrics.total_queries,
                    successful_queries=self._metrics.successful_queries,
                    failed_queries=self._metrics.failed_queries,
                    average_runtime_ms=self._metrics.average_runtime_ms,
                    slow_queries_count=self._metrics.slow_queries_count,
                    timeout_count=self._metrics.timeout_count,
                    min_runtime_ms=self._metrics.min_runtime_ms if self._metrics.min_runtime_ms != float('inf') else 0.0,
                    max_runtime_ms=self._metrics.max_runtime_ms,
                    total_runtime_ms=self._metrics.total_runtime_ms
                ),
                recent_queries=list(self._query_history)[-10:],  # Last 10 queries
                slow_queries=list(self._slow_queries)[-10:],     # Last 10 slow queries
                error_queries=list(self._error_queries)[-10:],   # Last 10 error queries
                uptime_seconds=uptime_seconds,
                queries_per_minute=queries_per_minute
            )
    
    def get_recent_queries(self, limit: int = 10) -> List[QueryExecutionRecord]:
        """
        Get recent query execution records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List[QueryExecutionRecord]: Recent query records
        """
        with self._lock:
            return list(self._query_history)[-limit:]
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryExecutionRecord]:
        """
        Get recent slow query execution records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List[QueryExecutionRecord]: Recent slow query records
        """
        with self._lock:
            return list(self._slow_queries)[-limit:]
    
    def get_error_queries(self, limit: int = 10) -> List[QueryExecutionRecord]:
        """
        Get recent error query execution records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List[QueryExecutionRecord]: Recent error query records
        """
        with self._lock:
            return list(self._error_queries)[-limit:]
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics and history."""
        with self._lock:
            self._metrics = QueryMetrics()
            self._query_history.clear()
            self._slow_queries.clear()
            self._error_queries.clear()
            self._query_times_by_minute.clear()
            self.start_time = datetime.now()
            
            self.logger.info("Performance metrics reset")
    
    def set_slow_query_threshold(self, threshold_ms: float) -> None:
        """
        Update the slow query threshold.
        
        Args:
            threshold_ms: New threshold in milliseconds
        """
        with self._lock:
            old_threshold = self.slow_query_threshold_ms
            self.slow_query_threshold_ms = threshold_ms
            
            self.logger.info(f"Slow query threshold updated: {old_threshold}ms -> {threshold_ms}ms")
    
    def log_performance_summary(self) -> None:
        """Log a summary of current performance metrics."""
        stats = self.get_performance_stats()
        metrics = stats.metrics
        
        self.logger.info(
            f"Performance Summary - "
            f"Total: {metrics.total_queries}, "
            f"Success: {metrics.successful_queries}, "
            f"Failed: {metrics.failed_queries}, "
            f"Slow: {metrics.slow_queries_count}, "
            f"Avg Runtime: {metrics.average_runtime_ms:.2f}ms, "
            f"QPM: {stats.queries_per_minute:.1f}"
        )


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(slow_query_threshold_ms: float = 1000.0) -> PerformanceMonitor:
    """
    Get the global performance monitor instance.
    
    Args:
        slow_query_threshold_ms: Threshold for slow query detection
        
    Returns:
        PerformanceMonitor: Global performance monitor instance
    """
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor(slow_query_threshold_ms)
    
    return _performance_monitor