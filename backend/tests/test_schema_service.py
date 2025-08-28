"""
Unit tests for SchemaService class.
"""

import pytest
import tempfile
import os
import csv
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from schema_service import SchemaService
from database_manager import DatabaseManager
from models import ColumnInfo, TableInfo, DatabaseSchema, TableSchema


class TestSchemaService:
    """Test cases for SchemaService class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path within the data directory."""
        # Create a unique test database path within the data directory
        import uuid
        test_id = str(uuid.uuid4())[:8]
        db_path = f"data/test_{test_id}.duckdb"
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def sample_csv_path(self):
        """Create a sample CSV file for testing within the data directory."""
        import uuid
        test_id = str(uuid.uuid4())[:8]
        csv_path = f"data/test_{test_id}.csv"
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'age', 'salary'])
            writer.writerow([1, 'John Doe', 30, 50000.0])
            writer.writerow([2, 'Jane Smith', 25, 60000.0])
            writer.writerow([3, 'Bob Johnson', 35, 55000.0])
        
        yield csv_path
        # Cleanup
        if os.path.exists(csv_path):
            os.unlink(csv_path)
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance for testing."""
        manager = DatabaseManager(temp_db_path)
        yield manager
        manager.close()
    
    @pytest.fixture
    def schema_service(self, db_manager):
        """Create a SchemaService instance for testing."""
        return SchemaService(db_manager)
    
    @pytest.fixture
    def populated_schema_service(self, schema_service, sample_csv_path):
        """Create a SchemaService with populated database."""
        schema_service.db_manager.ingest_csv(sample_csv_path, 'test_table')
        return schema_service
    
    def test_schema_service_initialization(self, db_manager):
        """Test SchemaService initialization."""
        service = SchemaService(db_manager)
        assert service.db_manager == db_manager
        assert service.config is not None
    
    def test_get_all_tables_schema_empty_database(self, schema_service):
        """Test getting schema from empty database."""
        schema = schema_service.get_all_tables_schema()
        
        assert isinstance(schema, dict)
        assert 'tables' in schema
        assert len(schema['tables']) == 0
    
    def test_get_all_tables_schema_with_tables(self, populated_schema_service):
        """Test getting schema from database with tables."""
        schema = populated_schema_service.get_all_tables_schema()
        
        assert isinstance(schema, dict)
        assert 'tables' in schema
        assert len(schema['tables']) == 1
        assert 'test_table' in schema['tables']
        
        table_schema = schema['tables']['test_table']
        assert table_schema['name'] == 'test_table'
        assert table_schema['row_count'] == 3
        assert len(table_schema['columns']) == 4
        assert isinstance(table_schema['sample_rows'], list)
        
        # Check column structure
        columns = table_schema['columns']
        column_names = [col['name'] for col in columns]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'age' in column_names
        assert 'salary' in column_names
        
        # Check that each column has name and type
        for col in columns:
            assert 'name' in col
            assert 'type' in col
            assert isinstance(col['name'], str)
            assert isinstance(col['type'], str)
    
    def test_get_table_columns_success(self, populated_schema_service):
        """Test getting columns for a specific table."""
        columns = populated_schema_service.get_table_columns('test_table')
        
        assert isinstance(columns, list)
        assert len(columns) == 4
        
        column_names = [col.name for col in columns]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'age' in column_names
        assert 'salary' in column_names
        
        # Check that all columns are ColumnInfo instances
        for col in columns:
            assert isinstance(col, ColumnInfo)
            assert col.name is not None
            assert col.type is not None
    
    def test_get_table_columns_nonexistent_table(self, schema_service):
        """Test getting columns for non-existent table."""
        with pytest.raises(Exception):
            schema_service.get_table_columns('nonexistent_table')
    
    def test_get_table_columns_invalid_table_name(self, schema_service):
        """Test getting columns with invalid table name."""
        with pytest.raises(ValueError):
            schema_service.get_table_columns('invalid-table-name!')
    
    def test_get_sample_rows_success(self, populated_schema_service):
        """Test getting sample rows from a table."""
        sample_rows = populated_schema_service.get_sample_rows('test_table', limit=2)
        
        assert isinstance(sample_rows, list)
        assert len(sample_rows) == 2
        
        # Check sample row structure
        for row in sample_rows:
            assert isinstance(row, dict)
            assert 'id' in row
            assert 'name' in row
            assert 'age' in row
            assert 'salary' in row
    
    def test_get_sample_rows_default_limit(self, populated_schema_service):
        """Test getting sample rows with default limit."""
        sample_rows = populated_schema_service.get_sample_rows('test_table')
        
        assert isinstance(sample_rows, list)
        assert len(sample_rows) == 3  # All 3 rows since table has only 3 rows
    
    def test_get_sample_rows_invalid_limit(self, populated_schema_service):
        """Test getting sample rows with invalid limit."""
        with pytest.raises(ValueError):
            populated_schema_service.get_sample_rows('test_table', limit=0)
        
        with pytest.raises(ValueError):
            populated_schema_service.get_sample_rows('test_table', limit=-1)
        
        with pytest.raises(ValueError):
            populated_schema_service.get_sample_rows('test_table', limit=1000)  # Exceeds MAX_SAMPLE_ROWS
    
    def test_get_sample_rows_nonexistent_table(self, schema_service):
        """Test getting sample rows from non-existent table."""
        with pytest.raises(Exception):
            schema_service.get_sample_rows('nonexistent_table')
    
    def test_get_table_schema_success(self, populated_schema_service):
        """Test getting complete schema for a specific table."""
        schema = populated_schema_service.get_table_schema('test_table')
        
        assert isinstance(schema, dict)
        assert schema['name'] == 'test_table'
        assert schema['row_count'] == 3
        assert len(schema['columns']) == 4
        assert isinstance(schema['sample_rows'], list)
        
        # Check column structure
        columns = schema['columns']
        for col in columns:
            assert 'name' in col
            assert 'type' in col
        
        # Check sample rows
        assert len(schema['sample_rows']) == 3
        for row in schema['sample_rows']:
            assert isinstance(row, dict)
            assert 'id' in row
            assert 'name' in row
            assert 'age' in row
            assert 'salary' in row
    
    def test_get_table_schema_nonexistent_table(self, schema_service):
        """Test getting schema for non-existent table."""
        with pytest.raises(Exception):
            schema_service.get_table_schema('nonexistent_table')
    
    def test_get_table_schema_invalid_table_name(self, schema_service):
        """Test getting schema with invalid table name."""
        with pytest.raises(ValueError):
            schema_service.get_table_schema('invalid-table-name!')
    
    def test_table_exists_true(self, populated_schema_service):
        """Test table existence check for existing table."""
        assert populated_schema_service.table_exists('test_table') is True
    
    def test_table_exists_false(self, schema_service):
        """Test table existence check for non-existent table."""
        assert schema_service.table_exists('nonexistent_table') is False
    
    def test_table_exists_invalid_name(self, schema_service):
        """Test table existence check with invalid name."""
        assert schema_service.table_exists('invalid-table-name!') is False
    
    def test_get_database_summary_empty(self, schema_service):
        """Test getting database summary for empty database."""
        summary = schema_service.get_database_summary()
        
        assert isinstance(summary, dict)
        assert summary['table_count'] == 0
        assert summary['total_rows'] == 0
        assert summary['tables'] == []
    
    def test_get_database_summary_with_tables(self, populated_schema_service):
        """Test getting database summary with tables."""
        summary = populated_schema_service.get_database_summary()
        
        assert isinstance(summary, dict)
        assert summary['table_count'] == 1
        assert summary['total_rows'] == 3
        assert summary['tables'] == ['test_table']
    
    def test_get_database_summary_multiple_tables(self, schema_service, sample_csv_path):
        """Test getting database summary with multiple tables."""
        # Add first table
        schema_service.db_manager.ingest_csv(sample_csv_path, 'table1')
        
        # Create and add second table within data directory
        import uuid
        test_id = str(uuid.uuid4())[:8]
        csv2_path = f"data/test2_{test_id}.csv"
        
        with open(csv2_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'product_name'])
            writer.writerow([1, 'Widget A'])
            writer.writerow([2, 'Widget B'])
        
        try:
            schema_service.db_manager.ingest_csv(csv2_path, 'table2')
            
            summary = schema_service.get_database_summary()
            
            assert summary['table_count'] == 2
            assert summary['total_rows'] == 5  # 3 + 2
            assert len(summary['tables']) == 2
            assert 'table1' in summary['tables']
            assert 'table2' in summary['tables']
            
        finally:
            if os.path.exists(csv2_path):
                os.unlink(csv2_path)
    
    def test_sample_rows_limit_enforcement(self, schema_service):
        """Test that sample rows are limited correctly."""
        # Create CSV with more than 5 rows within data directory
        import uuid
        test_id = str(uuid.uuid4())[:8]
        csv_path = f"data/test_large_{test_id}.csv"
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'value'])
            for i in range(10):  # 10 rows
                writer.writerow([i, f'value_{i}'])
        
        try:
            schema_service.db_manager.ingest_csv(csv_path, 'test_table')
            
            # Test with limit of 3
            sample_rows = schema_service.get_sample_rows('test_table', limit=3)
            assert len(sample_rows) == 3
            
            # Test with default limit (should be 5)
            sample_rows = schema_service.get_sample_rows('test_table')
            assert len(sample_rows) == 5
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
    
    def test_error_handling_database_failure(self, schema_service):
        """Test error handling when database operations fail."""
        # Mock the database manager to raise an exception
        with patch.object(schema_service.db_manager, 'get_schema', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Failed to retrieve database schema"):
                schema_service.get_all_tables_schema()
    
    def test_error_handling_table_info_failure(self, schema_service):
        """Test error handling when table info retrieval fails."""
        # Mock the database manager to raise an exception
        with patch.object(schema_service.db_manager, 'get_table_info', side_effect=Exception("Table error")):
            with pytest.raises(Exception, match="Failed to retrieve columns for table test_table"):
                schema_service.get_table_columns('test_table')
    
    def test_api_response_format_consistency(self, populated_schema_service):
        """Test that API response formats are consistent."""
        # Test all_tables_schema format
        all_schema = populated_schema_service.get_all_tables_schema()
        assert 'tables' in all_schema
        
        table_schema_from_all = all_schema['tables']['test_table']
        
        # Test individual table schema format
        individual_schema = populated_schema_service.get_table_schema('test_table')
        
        # Both should have the same structure
        assert table_schema_from_all['name'] == individual_schema['name']
        assert table_schema_from_all['row_count'] == individual_schema['row_count']
        assert len(table_schema_from_all['columns']) == len(individual_schema['columns'])
        assert len(table_schema_from_all['sample_rows']) == len(individual_schema['sample_rows'])
    
    def test_column_info_format(self, populated_schema_service):
        """Test that column information is properly formatted."""
        columns = populated_schema_service.get_table_columns('test_table')
        
        for col in columns:
            assert isinstance(col, ColumnInfo)
            assert hasattr(col, 'name')
            assert hasattr(col, 'type')
            assert isinstance(col.name, str)
            assert isinstance(col.type, str)
            assert len(col.name) > 0
            assert len(col.type) > 0


if __name__ == '__main__':
    pytest.main([__file__])