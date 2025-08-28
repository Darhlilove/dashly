"""
Test DatabaseManager with the actual demo database path.
"""

import pytest
import os
import csv
import tempfile
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_manager import DatabaseManager


class TestDatabaseDemoPath:
    """Test DatabaseManager with demo database path."""
    
    @pytest.fixture
    def sample_csv_path(self):
        """Create a sample CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'date', 'product_name', 'category', 'region', 'sales_amount', 'quantity', 'customer_id'])
            writer.writerow([1, '2023-01-15', 'Widget A', 'Electronics', 'North', 1250.50, 5, 101])
            writer.writerow([2, '2023-01-16', 'Gadget B', 'Electronics', 'South', 890.25, 3, 102])
            csv_path = f.name
        yield csv_path
        # Cleanup
        if os.path.exists(csv_path):
            os.unlink(csv_path)
    
    def test_default_database_path_creation(self, sample_csv_path):
        """Test that DatabaseManager creates the default data directory and database."""
        # Clean up any existing demo database
        demo_db_path = "data/demo.duckdb"
        if os.path.exists(demo_db_path):
            os.unlink(demo_db_path)
        if os.path.exists("data") and not os.listdir("data"):
            os.rmdir("data")
        
        try:
            # Create DatabaseManager with default path
            with DatabaseManager() as db_manager:
                # Verify the database path is correct
                assert db_manager.db_path == "data/demo.duckdb"
                
                # Verify data directory was created
                assert os.path.exists("data")
                
                # Test basic functionality
                result = db_manager.ingest_csv(sample_csv_path, 'sales')
                assert result.table_name == 'sales'
                assert result.row_count == 2
                
                # Verify database file was created
                assert os.path.exists("data/demo.duckdb")
                
                # Test schema retrieval
                schema = db_manager.get_schema()
                assert 'sales' in schema.tables
                
        finally:
            # Cleanup
            if os.path.exists(demo_db_path):
                os.unlink(demo_db_path)
    
    def test_data_directory_already_exists(self, sample_csv_path):
        """Test DatabaseManager when data directory already exists."""
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        demo_db_path = "data/demo.duckdb"
        if os.path.exists(demo_db_path):
            os.unlink(demo_db_path)
        
        try:
            with DatabaseManager() as db_manager:
                result = db_manager.ingest_csv(sample_csv_path, 'sales')
                assert result.row_count == 2
                
                # Verify database file was created in existing directory
                assert os.path.exists("data/demo.duckdb")
                
        finally:
            # Cleanup
            if os.path.exists(demo_db_path):
                os.unlink(demo_db_path)


if __name__ == '__main__':
    pytest.main([__file__])