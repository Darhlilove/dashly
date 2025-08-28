"""
Integration tests for DatabaseManager with the existing application.
"""

import pytest
import tempfile
import os
import csv
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database_manager import DatabaseManager


class TestDatabaseIntegration:
    """Integration tests for DatabaseManager."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'integration_test.duckdb')
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
    
    @pytest.fixture
    def sales_csv_path(self):
        """Create a realistic sales CSV file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'date', 'product_name', 'category', 'region', 'sales_amount', 'quantity', 'customer_id'])
            writer.writerow([1, '2023-01-15', 'Widget A', 'Electronics', 'North', 1250.50, 5, 101])
            writer.writerow([2, '2023-01-16', 'Gadget B', 'Electronics', 'South', 890.25, 3, 102])
            writer.writerow([3, '2023-01-17', 'Tool C', 'Hardware', 'East', 2100.00, 10, 103])
            writer.writerow([4, '2023-01-18', 'Widget A', 'Electronics', 'West', 750.75, 3, 104])
            writer.writerow([5, '2023-01-19', 'Service D', 'Services', 'North', 1500.00, 1, 105])
            csv_path = f.name
        yield csv_path
        # Cleanup
        if os.path.exists(csv_path):
            os.unlink(csv_path)
    
    def test_end_to_end_csv_ingestion_and_schema_retrieval(self, temp_db_path, sales_csv_path):
        """Test complete workflow: CSV ingestion → schema retrieval."""
        with DatabaseManager(temp_db_path) as db_manager:
            # Step 1: Ingest CSV
            result = db_manager.ingest_csv(sales_csv_path, 'sales')
            
            # Verify ingestion result
            assert result.table_name == 'sales'
            assert result.row_count == 5
            assert len(result.columns) == 8
            
            # Step 2: Get complete schema
            schema = db_manager.get_schema()
            
            # Verify schema structure
            assert len(schema.tables) == 1
            assert 'sales' in schema.tables
            
            sales_table = schema.tables['sales']
            assert sales_table.name == 'sales'
            assert sales_table.row_count == 5
            assert len(sales_table.columns) == 8
            assert len(sales_table.sample_rows) == 5
            
            # Step 3: Verify specific table info
            table_info = db_manager.get_table_info('sales')
            assert table_info.name == 'sales'
            assert table_info.total_rows == 5
            
            # Verify column names match expected sales data structure
            column_names = [col.name for col in table_info.columns]
            expected_columns = ['id', 'date', 'product_name', 'category', 'region', 'sales_amount', 'quantity', 'customer_id']
            for expected_col in expected_columns:
                assert expected_col in column_names
            
            # Verify sample data structure
            sample_row = table_info.sample_data[0]
            assert 'id' in sample_row
            assert 'product_name' in sample_row
            assert 'sales_amount' in sample_row
            
            # Verify data types are reasonable
            assert sample_row['id'] == 1
            assert sample_row['product_name'] == 'Widget A'
            assert sample_row['sales_amount'] == 1250.5
    
    def test_database_persistence_across_connections(self, temp_db_path, sales_csv_path):
        """Test that data persists when reconnecting to the same database."""
        # First connection: ingest data
        with DatabaseManager(temp_db_path) as db_manager1:
            result = db_manager1.ingest_csv(sales_csv_path, 'sales')
            assert result.row_count == 5
        
        # Second connection: verify data is still there
        with DatabaseManager(temp_db_path) as db_manager2:
            assert db_manager2.table_exists('sales')
            
            table_info = db_manager2.get_table_info('sales')
            assert table_info.total_rows == 5
            
            schema = db_manager2.get_schema()
            assert 'sales' in schema.tables
    
    def test_multiple_csv_ingestions(self, temp_db_path, sales_csv_path):
        """Test ingesting multiple different CSV files."""
        with DatabaseManager(temp_db_path) as db_manager:
            # Ingest first CSV as 'sales'
            result1 = db_manager.ingest_csv(sales_csv_path, 'sales')
            assert result1.row_count == 5
            
            # Create a different CSV for products
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['product_id', 'product_name', 'category', 'price', 'in_stock'])
                writer.writerow([1, 'Widget A', 'Electronics', 250.10, True])
                writer.writerow([2, 'Gadget B', 'Electronics', 296.75, False])
                writer.writerow([3, 'Tool C', 'Hardware', 210.00, True])
                products_csv_path = f.name
            
            try:
                # Ingest second CSV as 'products'
                result2 = db_manager.ingest_csv(products_csv_path, 'products')
                assert result2.row_count == 3
                
                # Verify both tables exist
                schema = db_manager.get_schema()
                assert len(schema.tables) == 2
                assert 'sales' in schema.tables
                assert 'products' in schema.tables
                
                # Verify table structures
                sales_table = schema.tables['sales']
                products_table = schema.tables['products']
                
                assert sales_table.row_count == 5
                assert products_table.row_count == 3
                assert len(sales_table.columns) == 8
                assert len(products_table.columns) == 5
                
            finally:
                os.unlink(products_csv_path)
    
    def test_error_handling_with_nonexistent_csv(self, temp_db_path):
        """Test error handling with non-existent CSV file."""
        with DatabaseManager(temp_db_path) as db_manager:
            # This should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                db_manager.ingest_csv('nonexistent_file.csv', 'invalid_table')
    
    def test_schema_with_different_data_types(self, temp_db_path):
        """Test schema extraction with various data types."""
        # Create CSV with different data types
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['int_col', 'float_col', 'string_col', 'date_col', 'bool_col'])
            writer.writerow([1, 3.14, 'hello', '2023-01-01', 'true'])
            writer.writerow([2, 2.71, 'world', '2023-01-02', 'false'])
            writer.writerow([3, 1.41, 'test', '2023-01-03', 'true'])
            mixed_csv_path = f.name
        
        try:
            with DatabaseManager(temp_db_path) as db_manager:
                result = db_manager.ingest_csv(mixed_csv_path, 'mixed_types')
                
                # Verify ingestion
                assert result.row_count == 3
                assert len(result.columns) == 5
                
                # Get detailed table info
                table_info = db_manager.get_table_info('mixed_types')
                
                # Verify column names
                column_names = [col.name for col in table_info.columns]
                expected_columns = ['int_col', 'float_col', 'string_col', 'date_col', 'bool_col']
                for expected_col in expected_columns:
                    assert expected_col in column_names
                
                # Verify sample data
                sample_row = table_info.sample_data[0]
                assert sample_row['int_col'] == 1
                assert sample_row['string_col'] == 'hello'
                
        finally:
            os.unlink(mixed_csv_path)


if __name__ == '__main__':
    pytest.main([__file__])