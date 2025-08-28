"""
Unit tests for DatabaseManager class.
"""

import pytest
import tempfile
import os
import csv
from pathlib import Path
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_manager import DatabaseManager
from models import ColumnInfo, TableMetadata, TableInfo, DatabaseSchema


class TestDatabaseManager:
    """Test cases for DatabaseManager class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""
        # Create a temporary directory and generate a path, but don't create the file
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.duckdb')
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
    
    @pytest.fixture
    def sample_csv_path(self):
        """Create a sample CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'age', 'salary'])
            writer.writerow([1, 'John Doe', 30, 50000.0])
            writer.writerow([2, 'Jane Smith', 25, 60000.0])
            writer.writerow([3, 'Bob Johnson', 35, 55000.0])
            csv_path = f.name
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
    
    def test_database_manager_initialization(self, temp_db_path):
        """Test DatabaseManager initialization."""
        manager = DatabaseManager(temp_db_path)
        assert manager.db_path == temp_db_path
        assert manager.conn is not None
        manager.close()
    
    def test_data_directory_creation(self):
        """Test that data directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'subdir', 'test.duckdb')
            manager = DatabaseManager(db_path)
            assert os.path.exists(os.path.dirname(db_path))
            manager.close()
    
    def test_ingest_csv_success(self, db_manager, sample_csv_path):
        """Test successful CSV ingestion."""
        result = db_manager.ingest_csv(sample_csv_path, 'test_table')
        
        assert isinstance(result, TableMetadata)
        assert result.table_name == 'test_table'
        assert result.row_count == 3
        assert len(result.columns) == 4
        
        # Check column names
        column_names = [col.name for col in result.columns]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'age' in column_names
        assert 'salary' in column_names
    
    def test_ingest_csv_file_not_found(self, db_manager):
        """Test CSV ingestion with non-existent file."""
        with pytest.raises(FileNotFoundError):
            db_manager.ingest_csv('nonexistent.csv', 'test_table')
    
    def test_ingest_csv_replaces_existing_table(self, db_manager, sample_csv_path):
        """Test that CSV ingestion replaces existing table."""
        # First ingestion
        result1 = db_manager.ingest_csv(sample_csv_path, 'test_table')
        assert result1.row_count == 3
        
        # Create a different CSV with more rows
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'age', 'salary'])
            writer.writerow([1, 'Alice', 28, 70000.0])
            writer.writerow([2, 'Bob', 32, 80000.0])
            writer.writerow([3, 'Charlie', 29, 75000.0])
            writer.writerow([4, 'Diana', 31, 85000.0])
            writer.writerow([5, 'Eve', 27, 72000.0])
            new_csv_path = f.name
        
        try:
            # Second ingestion should replace the table
            result2 = db_manager.ingest_csv(new_csv_path, 'test_table')
            assert result2.row_count == 5
        finally:
            os.unlink(new_csv_path)
    
    def test_get_schema_empty_database(self, db_manager):
        """Test getting schema from empty database."""
        schema = db_manager.get_schema()
        assert isinstance(schema, DatabaseSchema)
        assert len(schema.tables) == 0
    
    def test_get_schema_with_tables(self, db_manager, sample_csv_path):
        """Test getting schema from database with tables."""
        # Add a table
        db_manager.ingest_csv(sample_csv_path, 'test_table')
        
        schema = db_manager.get_schema()
        assert isinstance(schema, DatabaseSchema)
        assert len(schema.tables) == 1
        assert 'test_table' in schema.tables
        
        table_schema = schema.tables['test_table']
        assert table_schema.name == 'test_table'
        assert table_schema.row_count == 3
        assert len(table_schema.columns) == 4
        assert len(table_schema.sample_rows) <= 5  # Should be limited to 5 rows
    
    def test_get_table_info_success(self, db_manager, sample_csv_path):
        """Test getting table information."""
        db_manager.ingest_csv(sample_csv_path, 'test_table')
        
        table_info = db_manager.get_table_info('test_table')
        assert isinstance(table_info, TableInfo)
        assert table_info.name == 'test_table'
        assert table_info.total_rows == 3
        assert len(table_info.columns) == 4
        assert len(table_info.sample_data) == 3
        
        # Check sample data structure
        sample_row = table_info.sample_data[0]
        assert 'id' in sample_row
        assert 'name' in sample_row
        assert 'age' in sample_row
        assert 'salary' in sample_row
    
    def test_get_table_info_nonexistent_table(self, db_manager):
        """Test getting info for non-existent table."""
        with pytest.raises(Exception):
            db_manager.get_table_info('nonexistent_table')
    
    def test_table_exists(self, db_manager, sample_csv_path):
        """Test table existence check."""
        # Table doesn't exist initially
        assert not db_manager.table_exists('test_table')
        
        # Create table
        db_manager.ingest_csv(sample_csv_path, 'test_table')
        
        # Table should exist now
        assert db_manager.table_exists('test_table')
        
        # Non-existent table should return False
        assert not db_manager.table_exists('nonexistent_table')
    
    def test_get_table_columns(self, db_manager, sample_csv_path):
        """Test getting table columns."""
        db_manager.ingest_csv(sample_csv_path, 'test_table')
        
        columns = db_manager._get_table_columns('test_table')
        assert len(columns) == 4
        
        column_names = [col.name for col in columns]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'age' in column_names
        assert 'salary' in column_names
        
        # Check that all columns have types
        for col in columns:
            assert col.type is not None
            assert len(col.type) > 0
    
    def test_get_table_row_count(self, db_manager, sample_csv_path):
        """Test getting table row count."""
        db_manager.ingest_csv(sample_csv_path, 'test_table')
        
        row_count = db_manager._get_table_row_count('test_table')
        assert row_count == 3
    
    def test_context_manager(self, temp_db_path, sample_csv_path):
        """Test DatabaseManager as context manager."""
        with DatabaseManager(temp_db_path) as manager:
            result = manager.ingest_csv(sample_csv_path, 'test_table')
            assert result.row_count == 3
        # Connection should be closed after exiting context
    
    def test_multiple_tables(self, db_manager, sample_csv_path):
        """Test handling multiple tables."""
        # Create first table
        db_manager.ingest_csv(sample_csv_path, 'table1')
        
        # Create second CSV with different structure
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['product_id', 'product_name', 'price'])
            writer.writerow([1, 'Widget A', 19.99])
            writer.writerow([2, 'Widget B', 29.99])
            csv2_path = f.name
        
        try:
            # Create second table
            db_manager.ingest_csv(csv2_path, 'table2')
            
            # Check schema contains both tables
            schema = db_manager.get_schema()
            assert len(schema.tables) == 2
            assert 'table1' in schema.tables
            assert 'table2' in schema.tables
            
            # Check table1 structure
            table1 = schema.tables['table1']
            assert len(table1.columns) == 4
            assert table1.row_count == 3
            
            # Check table2 structure
            table2 = schema.tables['table2']
            assert len(table2.columns) == 3
            assert table2.row_count == 2
            
        finally:
            os.unlink(csv2_path)
    
    def test_sample_data_limit(self, db_manager):
        """Test that sample data is limited to 5 rows."""
        # Create CSV with more than 5 rows
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'value'])
            for i in range(10):  # 10 rows
                writer.writerow([i, f'value_{i}'])
            csv_path = f.name
        
        try:
            db_manager.ingest_csv(csv_path, 'test_table')
            table_info = db_manager.get_table_info('test_table')
            
            # Should have 10 total rows but only 5 sample rows
            assert table_info.total_rows == 10
            assert len(table_info.sample_data) == 5
            
        finally:
            os.unlink(csv_path)


if __name__ == '__main__':
    pytest.main([__file__])