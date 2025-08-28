"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel
from typing import Dict, List, Any, Optional


class ColumnInfo(BaseModel):
    """Information about a database column."""
    name: str
    type: str


class UploadResponse(BaseModel):
    """Response model for CSV upload endpoint."""
    table: str
    columns: List[ColumnInfo]


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