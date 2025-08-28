"""
Database Manager for DuckDB operations.

Handles CSV ingestion, table metadata extraction, and schema operations.
"""

import duckdb
import os
import pandas as pd
import re
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from .models import ColumnInfo, TableMetadata, TableInfo, DatabaseSchema, TableSchema
    from .security_config import SecurityConfig
    from .exceptions import (
        DatabaseError,
        DatabaseConnectionError,
        TableNotFoundError,
        InvalidTableNameError,
        CSVIngestionError,
        SchemaExtractionError,
        PathTraversalError,
        InvalidPathError
    )
    from .logging_config import get_logger, DashlyLogger
except ImportError:
    from models import ColumnInfo, TableMetadata, TableInfo, DatabaseSchema, TableSchema
    from security_config import SecurityConfig
    from exceptions import (
        DatabaseError,
        DatabaseConnectionError,
        TableNotFoundError,
        InvalidTableNameError,
        CSVIngestionError,
        SchemaExtractionError,
        PathTraversalError,
        InvalidPathError
    )
    from logging_config import get_logger, DashlyLogger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages DuckDB database operations including CSV ingestion and schema extraction.
    """
    
    # Security configuration
    config = SecurityConfig()
    
    def __init__(self, db_path: str = "data/demo.duckdb", shared_connection=None):
        """
        Initialize DatabaseManager with DuckDB connection.
        
        Args:
            db_path: Path to the DuckDB database file
            shared_connection: Optional shared database connection to reuse
            
        Raises:
            DatabaseConnectionError: If database connection fails
        """
        try:
            self.db_path = self._validate_db_path(db_path)
            self._ensure_data_directory()
            
            # Use shared connection if provided, otherwise create new one
            if shared_connection is not None:
                # Store the shared connection wrapper for use
                self._shared_wrapper = shared_connection
                self.conn = None  # We'll use the wrapper's get_connection method
                self._owns_connection = False
                logger.info(f"DatabaseManager initialized with shared connection: {self.db_path}")
                
                # Test connection using the wrapper
                with shared_connection.get_connection() as conn:
                    conn.execute("SELECT 1").fetchone()
            else:
                self.conn = duckdb.connect(self.db_path)
                self._shared_wrapper = None
                self._owns_connection = True
                logger.info(f"DatabaseManager initialized with new connection: {self.db_path}")
                
                # Test connection
                self.conn.execute("SELECT 1").fetchone()
            logger.info("Database connection test successful")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise DatabaseConnectionError(f"Failed to initialize database connection: {str(e)}")
    
    def _validate_db_path(self, db_path: str) -> str:
        """
        Validate database path to prevent directory traversal.
        
        Args:
            db_path: Database file path to validate
            
        Returns:
            str: Validated absolute path
            
        Raises:
            ValueError: If path is invalid or outside allowed directory
        """
        try:
            # Resolve to absolute path
            resolved_path = Path(db_path).resolve()
            project_root = Path.cwd().resolve()
            
            # Ensure path is within project directory
            if not str(resolved_path).startswith(str(project_root)):
                raise ValueError("Database path outside project directory")
            
            # Ensure it's in the data directory
            data_dir = project_root / self.config.ALLOWED_DATA_DIR
            if not str(resolved_path).startswith(str(data_dir)):
                raise ValueError("Database must be in data directory")
            
            return str(resolved_path)
            
        except Exception as e:
            DashlyLogger.log_security_event(
                logger, 
                "INVALID_DB_PATH", 
                f"Database path validation failed: {db_path}"
            )
            raise InvalidPathError(f"Invalid database path: {db_path}")
    
    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists safely."""
        try:
            data_dir = Path(self.db_path).parent
            project_root = Path.cwd().resolve()
            
            # Double-check we're creating within project boundaries
            if not str(data_dir.resolve()).startswith(str(project_root)):
                raise ValueError("Data directory outside project bounds")
            
            data_dir.mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")
            raise DatabaseError(f"Failed to create data directory: {str(e)}")
    
    def _validate_table_name(self, table_name: str) -> str:
        """
        Validate table name to prevent SQL injection.
        
        Args:
            table_name: Table name to validate
            
        Returns:
            str: Validated table name
            
        Raises:
            ValueError: If table name is invalid
        """
        if not table_name or len(table_name) > self.config.MAX_TABLE_NAME_LENGTH:
            raise ValueError(f"Table name must be 1-{self.config.MAX_TABLE_NAME_LENGTH} characters")
        
        # Allow only alphanumeric characters and underscores, starting with letter or underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            DashlyLogger.log_security_event(
                logger, 
                "INVALID_TABLE_NAME", 
                f"Invalid table name attempted: {table_name}"
            )
            raise InvalidTableNameError("Table name contains invalid characters")
        
        return table_name
    
    def _validate_csv_path(self, csv_path: str) -> str:
        """
        Validate CSV path to prevent directory traversal.
        
        Args:
            csv_path: CSV file path to validate
            
        Returns:
            str: Validated absolute path
            
        Raises:
            ValueError: If path is invalid or outside allowed directory
        """
        try:
            # Resolve to absolute path
            resolved_path = Path(csv_path).resolve()
            project_root = Path.cwd().resolve()
            
            # Ensure path is within project directory
            if not str(resolved_path).startswith(str(project_root)):
                raise ValueError("CSV path outside project directory")
            
            # Check file exists
            if not resolved_path.exists():
                raise FileNotFoundError(f"CSV file not found: {csv_path}")
            
            # Check it's actually a file
            if not resolved_path.is_file():
                raise ValueError("Path is not a file")
            
            return str(resolved_path)
            
        except FileNotFoundError:
            raise
        except Exception as e:
            DashlyLogger.log_security_event(
                logger, 
                "INVALID_CSV_PATH", 
                f"CSV path validation failed: {csv_path}"
            )
            raise InvalidPathError(f"Invalid CSV path: {csv_path}")
    
    def _validate_csv_size(self, csv_path: str) -> None:
        """
        Validate CSV file size to prevent resource exhaustion.
        
        Args:
            csv_path: Path to CSV file
            
        Raises:
            ValueError: If file is too large
        """
        try:
            file_size = os.path.getsize(csv_path)
            max_size_bytes = self.config.MAX_CSV_SIZE_MB * 1024 * 1024
            
            if file_size > max_size_bytes:
                logger.warning(f"Large CSV file rejected: {file_size} bytes")
                raise ValueError(f"CSV file too large: {file_size} bytes (max: {max_size_bytes})")
                
        except OSError as e:
            logger.error(f"Failed to check CSV file size: {e}")
            raise DatabaseError("Cannot access CSV file")
    
    def _validate_csv_content(self, csv_path: str) -> None:
        """
        Basic validation of CSV file content.
        
        Args:
            csv_path: Path to CSV file
            
        Raises:
            ValueError: If file content is invalid
        """
        try:
            # Try to read first few lines to validate it's a proper CSV
            with open(csv_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line:
                    raise ValueError("CSV file is empty")
                
                # Basic check for CSV format (contains commas or is single column)
                if ',' not in first_line and len(first_line.split()) == 1:
                    # Could be single column, check second line
                    second_line = f.readline().strip()
                    if second_line and ',' not in second_line:
                        logger.info("Single column CSV detected")
                
        except UnicodeDecodeError:
            raise ValueError("CSV file contains invalid characters")
        except Exception as e:
            logger.error(f"CSV content validation failed: {e}")
            raise CSVIngestionError("Invalid CSV file format")
    
    def _sanitize_sample_data(self, sample_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sanitize sample data to prevent information disclosure.
        
        Args:
            sample_data: Raw sample data from database
            
        Returns:
            List[Dict[str, Any]]: Sanitized sample data
        """
        sanitized = []
        
        for row in sample_data:
            sanitized_row = {}
            for key, value in row.items():
                # Check if field name suggests sensitive data
                if self.config.is_sensitive_field(key):
                    sanitized_row[key] = "[REDACTED]"
                else:
                    # Convert to string and truncate if too long
                    str_value = str(value) if value is not None else None
                    if str_value and len(str_value) > self.config.MAX_FIELD_LENGTH:
                        sanitized_row[key] = str_value[:self.config.MAX_FIELD_LENGTH-3] + "..."
                    else:
                        sanitized_row[key] = value
                        
            sanitized.append(sanitized_row)
        
        return sanitized
    
    def ingest_csv(self, csv_path: str, table_name: str = "sales") -> TableMetadata:
        """
        Ingest CSV file into DuckDB table with security validation.
        
        Args:
            csv_path: Path to the CSV file to ingest
            table_name: Name of the table to create/replace
            
        Returns:
            TableMetadata: Information about the created table
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If validation fails
            Exception: If ingestion fails
        """
        # Validate all inputs
        validated_csv_path = self._validate_csv_path(csv_path)
        validated_table_name = self._validate_table_name(table_name)
        
        # Validate file size and content
        self._validate_csv_size(validated_csv_path)
        self._validate_csv_content(validated_csv_path)
        
        try:
            DashlyLogger.log_database_operation(
                logger, 
                "INGEST_CSV_START", 
                validated_table_name
            )
            
            # Drop table if it exists (using validated table name)
            # Use double quotes for safe identifier escaping in DuckDB
            escaped_table_name = f'"{validated_table_name}"'
            drop_sql = f"DROP TABLE IF EXISTS {escaped_table_name}"
            create_sql = f"CREATE TABLE {escaped_table_name} AS SELECT * FROM read_csv_auto(?)"
            
            if self._shared_wrapper:
                with self._shared_wrapper.get_connection() as conn:
                    conn.execute(drop_sql)
                    logger.debug(f"Dropped existing table: {validated_table_name}")
                    
                    # Create table from CSV using DuckDB's native CSV reader
                    # Use escaped table name and parameterized path
                    conn.execute(create_sql, [validated_csv_path])
                    logger.debug(f"Created table from CSV: {validated_table_name}")
            else:
                self.conn.execute(drop_sql)
                logger.debug(f"Dropped existing table: {validated_table_name}")
                
                # Create table from CSV using DuckDB's native CSV reader
                # Use escaped table name and parameterized path
                self.conn.execute(create_sql, [validated_csv_path])
                logger.debug(f"Created table from CSV: {validated_table_name}")
            
            # Get table metadata
            columns = self._get_table_columns(validated_table_name)
            row_count = self._get_table_row_count(validated_table_name)
            
            DashlyLogger.log_database_operation(
                logger, 
                "INGEST_CSV_SUCCESS", 
                validated_table_name, 
                success=True
            )
            logger.info(f"CSV ingestion successful: {row_count} rows, {len(columns)} columns")
            
            return TableMetadata(
                table_name=validated_table_name,
                columns=columns,
                row_count=row_count
            )
            
        except Exception as e:
            DashlyLogger.log_database_operation(
                logger, 
                "INGEST_CSV_FAILED", 
                validated_table_name, 
                success=False,
                error_details=str(e)
            )
            raise CSVIngestionError("Failed to ingest CSV file")
    
    def get_schema(self) -> DatabaseSchema:
        """
        Get complete database schema information with security measures.
        
        Returns:
            DatabaseSchema: Complete schema with all tables and their metadata
        """
        try:
            # Get all table names
            if self._shared_wrapper:
                with self._shared_wrapper.get_connection() as conn:
                    tables_result = conn.execute("SHOW TABLES").fetchall()
            else:
                tables_result = self.conn.execute("SHOW TABLES").fetchall()
            table_names = [str(row[0]) for row in tables_result]
            
            tables_schema = {}
            
            for table_name in table_names:
                try:
                    # Validate each table name (should be valid, but double-check)
                    validated_table_name = self._validate_table_name(table_name)
                    table_info = self.get_table_info(validated_table_name)
                    
                    tables_schema[validated_table_name] = TableSchema(
                        name=table_info.name,
                        columns=table_info.columns,
                        sample_rows=table_info.sample_data,
                        row_count=table_info.total_rows
                    )
                    
                except ValueError as e:
                    # Skip invalid table names
                    logger.warning(f"Skipping invalid table name: {table_name}")
                    continue
                except Exception as e:
                    # Skip tables that can't be processed
                    logger.error(f"Error processing table {table_name}: {e}")
                    continue
            
            return DatabaseSchema(tables=tables_schema)
            
        except Exception as e:
            DashlyLogger.log_database_operation(
                logger, 
                "GET_SCHEMA_FAILED", 
                success=False,
                error_details=str(e)
            )
            raise SchemaExtractionError("Failed to retrieve database schema")
    
    def get_table_info(self, table_name: str) -> TableInfo:
        """
        Get detailed information about a specific table with security measures.
        
        Args:
            table_name: Name of the table to inspect
            
        Returns:
            TableInfo: Detailed table information including columns and sanitized sample data
            
        Raises:
            ValueError: If table name is invalid
            Exception: If table doesn't exist or query fails
        """
        # Validate table name
        validated_table_name = self._validate_table_name(table_name)
        
        try:
            # Verify table exists first
            if not self.table_exists(validated_table_name):
                logger.warning(f"Requested table does not exist: {validated_table_name}")
                raise TableNotFoundError(f"Table {validated_table_name} does not exist")
            
            # Get column information
            columns = self._get_table_columns(validated_table_name)
            
            # Get sample data (limit to configured rows) - using validated table name
            escaped_table_name = f'"{validated_table_name}"'
            sample_sql = f"SELECT * FROM {escaped_table_name} LIMIT ?"
            
            if self._shared_wrapper:
                with self._shared_wrapper.get_connection() as conn:
                    sample_result = conn.execute(sample_sql, [self.config.MAX_SAMPLE_ROWS]).fetchall()
            else:
                sample_result = self.conn.execute(sample_sql, [self.config.MAX_SAMPLE_ROWS]).fetchall()
            column_names = [col.name for col in columns]
            
            # Create sample data dictionaries
            raw_sample_data = [
                dict(zip(column_names, row)) for row in sample_result
            ]
            
            # Sanitize sample data to prevent information disclosure
            sample_data = self._sanitize_sample_data(raw_sample_data)
            
            # Get total row count
            total_rows = self._get_table_row_count(validated_table_name)
            
            return TableInfo(
                name=validated_table_name,
                columns=columns,
                sample_data=sample_data,
                total_rows=total_rows
            )
            
        except (TableNotFoundError, InvalidTableNameError):
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            DashlyLogger.log_database_operation(
                logger, 
                "GET_TABLE_INFO_FAILED", 
                validated_table_name, 
                success=False,
                error_details=str(e)
            )
            raise SchemaExtractionError("Failed to retrieve table information")
    
    def _get_table_columns(self, table_name: str) -> List[ColumnInfo]:
        """
        Get column information for a table (assumes table_name is already validated).
        
        Args:
            table_name: Name of the table (must be pre-validated)
            
        Returns:
            List[ColumnInfo]: List of column information
        """
        try:
            # Use DESCRIBE to get column information
            # Note: table_name should already be validated by caller
            escaped_table_name = f'"{table_name}"'
            describe_sql = f"DESCRIBE {escaped_table_name}"
            
            if self._shared_wrapper:
                with self._shared_wrapper.get_connection() as conn:
                    columns_result = conn.execute(describe_sql).fetchall()
            else:
                columns_result = self.conn.execute(describe_sql).fetchall()
            
            columns = []
            for row in columns_result:
                # DuckDB DESCRIBE returns: column_name, column_type, null, key, default, extra
                column_name = str(row[0])  # Ensure string type
                column_type = str(row[1])  # Ensure string type
                columns.append(ColumnInfo(name=column_name, type=column_type))
            
            return columns
            
        except Exception as e:
            logger.error(f"Failed to get columns for table {table_name}: {e}")
            raise SchemaExtractionError("Failed to retrieve table columns")
    
    def _get_table_row_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table (assumes table_name is already validated).
        
        Args:
            table_name: Name of the table (must be pre-validated)
            
        Returns:
            int: Number of rows in the table
        """
        try:
            # Note: table_name should already be validated by caller
            escaped_table_name = f'"{table_name}"'
            count_sql = f"SELECT COUNT(*) FROM {escaped_table_name}"
            
            if self._shared_wrapper:
                with self._shared_wrapper.get_connection() as conn:
                    result = conn.execute(count_sql).fetchone()
            else:
                result = self.conn.execute(count_sql).fetchone()
            return int(result[0]) if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get row count for table {table_name}: {e}")
            raise SchemaExtractionError("Failed to retrieve table row count")
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        try:
            # Validate table name first
            validated_table_name = self._validate_table_name(table_name)
            
            # Get all tables
            if self._shared_wrapper:
                with self._shared_wrapper.get_connection() as conn:
                    tables_result = conn.execute("SHOW TABLES").fetchall()
            else:
                tables_result = self.conn.execute("SHOW TABLES").fetchall()
            table_names = [str(row[0]) for row in tables_result]
            return validated_table_name in table_names
            
        except ValueError:
            # Invalid table name
            return False
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False
    
    def close(self) -> None:
        """Close the database connection if owned by this manager."""
        if hasattr(self, 'conn') and self.conn and getattr(self, '_owns_connection', True):
            self.conn.close()
            logger.info("DatabaseManager closed owned connection")
        elif hasattr(self, 'conn') and self.conn:
            logger.info("DatabaseManager released shared connection (not closed)")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()