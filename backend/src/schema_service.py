"""
Schema Service for database metadata operations.

Provides high-level interface for extracting table schemas and sample data,
formatting schema information for API responses.
"""

import logging
from typing import Dict, List, Any, Optional

try:
    from .database_manager import DatabaseManager
    from .models import DatabaseSchema, TableSchema, ColumnInfo
    from .security_config import SecurityConfig
    from .exceptions import (
        SchemaExtractionError,
        TableNotFoundError,
        InvalidTableNameError,
        ValidationError
    )
    from .logging_config import get_logger
except ImportError:
    from database_manager import DatabaseManager
    from models import DatabaseSchema, TableSchema, ColumnInfo
    from security_config import SecurityConfig
    from exceptions import (
        SchemaExtractionError,
        TableNotFoundError,
        InvalidTableNameError,
        ValidationError
    )
    from logging_config import get_logger

logger = get_logger(__name__)


class SchemaService:
    """
    Service for database schema operations and metadata extraction.
    
    Provides methods to extract table schemas, sample data, and format
    schema information for API responses.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SchemaService with a DatabaseManager instance.
        
        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager
        self.config = SecurityConfig()
    
    def get_all_tables_schema(self) -> Dict[str, Any]:
        """
        Get schema information for all tables in the database.
        
        Returns:
            Dict[str, Any]: Dictionary containing all table schemas formatted for API response
            
        Raises:
            Exception: If schema extraction fails
        """
        try:
            logger.info("Extracting schema for all tables")
            
            # Get complete database schema
            db_schema = self.db_manager.get_schema()
            
            # Format for API response
            formatted_schema = {
                "tables": {}
            }
            
            for table_name, table_schema in db_schema.tables.items():
                formatted_schema["tables"][table_name] = {
                    "name": table_schema.name,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.type
                        }
                        for col in table_schema.columns
                    ],
                    "sample_rows": table_schema.sample_rows,
                    "row_count": table_schema.row_count
                }
            
            logger.info(f"Schema extracted for {len(db_schema.tables)} tables")
            return formatted_schema
            
        except Exception as e:
            logger.error(f"Failed to extract all tables schema: {e}")
            raise SchemaExtractionError("Failed to retrieve database schema")
    
    def get_table_columns(self, table_name: str) -> List[ColumnInfo]:
        """
        Get column information for a specific table.
        
        Args:
            table_name: Name of the table to get columns for
            
        Returns:
            List[ColumnInfo]: List of column information
            
        Raises:
            ValueError: If table name is invalid
            Exception: If table doesn't exist or query fails
        """
        try:
            logger.info(f"Getting columns for table: {table_name}")
            
            # Get table info which includes columns
            table_info = self.db_manager.get_table_info(table_name)
            
            logger.info(f"Retrieved {len(table_info.columns)} columns for table {table_name}")
            return table_info.columns
            
        except (InvalidTableNameError, TableNotFoundError):
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get columns for table {table_name}: {e}")
            raise SchemaExtractionError(f"Failed to retrieve columns for table {table_name}")
    
    def get_sample_rows(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get sample rows from a specific table.
        
        Args:
            table_name: Name of the table to get sample data from
            limit: Maximum number of rows to return (default: 5)
            
        Returns:
            List[Dict[str, Any]]: List of sample rows as dictionaries
            
        Raises:
            ValueError: If table name is invalid or limit is invalid
            Exception: If table doesn't exist or query fails
        """
        try:
            # Validate limit parameter
            if limit <= 0 or limit > self.config.MAX_SAMPLE_ROWS:
                logger.warning(f"Invalid sample rows limit: {limit}")
                raise ValidationError(f"Limit must be between 1 and {self.config.MAX_SAMPLE_ROWS}")
            
            logger.info(f"Getting {limit} sample rows for table: {table_name}")
            
            # Get table info which includes sample data
            table_info = self.db_manager.get_table_info(table_name)
            
            # Return only the requested number of rows
            sample_rows = table_info.sample_data[:limit]
            
            logger.info(f"Retrieved {len(sample_rows)} sample rows for table {table_name}")
            return sample_rows
            
        except (ValidationError, InvalidTableNameError, TableNotFoundError):
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get sample rows for table {table_name}: {e}")
            raise SchemaExtractionError(f"Failed to retrieve sample data for table {table_name}")
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get complete schema information for a specific table.
        
        Args:
            table_name: Name of the table to get schema for
            
        Returns:
            Dict[str, Any]: Complete table schema formatted for API response
            
        Raises:
            ValueError: If table name is invalid
            Exception: If table doesn't exist or query fails
        """
        try:
            logger.info(f"Getting complete schema for table: {table_name}")
            
            # Get table info
            table_info = self.db_manager.get_table_info(table_name)
            
            # Format for API response
            schema = {
                "name": table_info.name,
                "columns": [
                    {
                        "name": col.name,
                        "type": col.type
                    }
                    for col in table_info.columns
                ],
                "sample_rows": table_info.sample_data,
                "row_count": table_info.total_rows
            }
            
            logger.info(f"Schema retrieved for table {table_name}")
            return schema
            
        except (InvalidTableNameError, TableNotFoundError):
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {e}")
            raise SchemaExtractionError(f"Failed to retrieve schema for table {table_name}")
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        try:
            return self.db_manager.table_exists(table_name)
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False
    
    def get_database_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the database including table count and basic statistics.
        
        Returns:
            Dict[str, Any]: Database summary information
        """
        try:
            logger.info("Getting database summary")
            
            # Get all tables schema
            all_schema = self.get_all_tables_schema()
            
            # Calculate summary statistics
            table_count = len(all_schema["tables"])
            total_rows = sum(
                table_info["row_count"] 
                for table_info in all_schema["tables"].values()
            )
            
            summary = {
                "table_count": table_count,
                "total_rows": total_rows,
                "tables": list(all_schema["tables"].keys())
            }
            
            logger.info(f"Database summary: {table_count} tables, {total_rows} total rows")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get database summary: {e}")
            raise SchemaExtractionError("Failed to retrieve database summary")