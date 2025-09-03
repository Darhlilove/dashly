"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime


class ColumnInfo(BaseModel):
    """Information about a database column."""
    name: str
    type: str


class UploadResponse(BaseModel):
    """Response model for CSV upload endpoint."""
    table: str
    columns: List[ColumnInfo]
    suggested_questions: Optional[List[str]] = None


class TableSchema(BaseModel):
    """Schema information for a database table."""
    name: str
    columns: List[ColumnInfo]
    sample_rows: List[Dict[str, Any]]
    row_count: int


class DatabaseSchema(BaseModel):
    """Complete database schema information."""
    tables: Dict[str, TableSchema]


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: str
    detail: str


# Internal data structures for processing
class UploadResult(BaseModel):
    """Internal result from file upload processing."""
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None


class TableMetadata(BaseModel):
    """Internal metadata about a database table."""
    table_name: str
    columns: List[ColumnInfo]
    row_count: int


class TableInfo(BaseModel):
    """Internal table information structure."""
    name: str
    columns: List[ColumnInfo]
    sample_data: List[Dict[str, Any]]
    total_rows: int


# SQL Execution API Models
class ExecuteRequest(BaseModel):
    """Request model for SQL execution endpoint."""
    sql: str


class ExecuteResponse(BaseModel):
    """Response model for SQL execution endpoint."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    runtime_ms: float
    truncated: bool = False


class ExplainResponse(BaseModel):
    """Response model for SQL explain endpoint."""
    execution_plan: str
    estimated_cost: float
    estimated_rows: int
    estimated_runtime_ms: float
    optimization_suggestions: List[str]


class SQLErrorResponse(BaseModel):
    """Error response model for SQL execution failures."""
    error: str
    detail: str
    sql_error_type: str  # "syntax", "security", "execution", "timeout"
    position: Optional[int] = None  # For syntax errors
    suggestions: Optional[List[str]] = None


# Performance Monitoring Models
class QueryMetricsResponse(BaseModel):
    """Response model for query performance metrics."""
    total_queries: int
    successful_queries: int
    failed_queries: int
    average_runtime_ms: float
    slow_queries_count: int
    timeout_count: int
    min_runtime_ms: float
    max_runtime_ms: float
    total_runtime_ms: float


class QueryExecutionRecordResponse(BaseModel):
    """Response model for query execution record."""
    sql: str
    runtime_ms: float
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None
    row_count: Optional[int] = None
    truncated: bool = False


class PerformanceStatsResponse(BaseModel):
    """Response model for comprehensive performance statistics."""
    metrics: QueryMetricsResponse
    recent_queries: List[QueryExecutionRecordResponse]
    slow_queries: List[QueryExecutionRecordResponse]
    error_queries: List[QueryExecutionRecordResponse]
    uptime_seconds: float
    queries_per_minute: float


# Internal SQL Processing Models
class ParsedQuery(BaseModel):
    """Internal model for parsed SQL query information."""
    query_type: str  # "SELECT", "INSERT", etc.
    tables: List[str]
    columns: List[str]
    has_joins: bool
    has_aggregations: bool
    complexity_score: int


class SecurityViolation(BaseModel):
    """Internal model for SQL security violations."""
    violation_type: str
    description: str
    severity: str  # "error", "warning"
    position: Optional[int] = None


class ValidationResult(BaseModel):
    """Internal model for SQL validation results."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    parsed_query: Optional[ParsedQuery] = None
    security_violations: List[SecurityViolation] = []


# Dashboard Models
class ChartConfig(BaseModel):
    """Chart configuration for dashboard visualization."""
    type: str  # "bar", "line", "pie", "table"
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    title: Optional[str] = None
    color_scheme: Optional[str] = None


class DashboardRequest(BaseModel):
    """Request model for creating/updating dashboards."""
    name: str
    question: str
    sql: str
    chartConfig: ChartConfig


class Dashboard(BaseModel):
    """Dashboard model for API responses."""
    id: str
    name: str
    question: str
    sql: str
    chartConfig: ChartConfig
    createdAt: str


# Chat Service Models
class ChatRequest(BaseModel):
    """Request model for chat interactions."""
    message: str
    conversation_id: Optional[str] = None


class ConversationalResponse(BaseModel):
    """Response model for conversational chat interactions."""
    message: str
    chart_config: Optional[ChartConfig] = None
    insights: List[str] = []
    follow_up_questions: List[str] = []
    processing_time_ms: float
    conversation_id: str