"""
Comprehensive API tests for the CSV upload endpoint.
Tests cover upload functionality, demo data, error scenarios, and edge cases.
"""

import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """id,product_name,category,region,sales_amount,quantity
1,Widget A,Electronics,North,1500.00,10
2,Widget B,Electronics,South,2300.50,15
3,Gadget X,Home,East,890.25,5
4,Tool Y,Industrial,West,3200.00,8"""


@pytest.fixture
def sample_csv_file(sample_csv_content):
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_csv_content)
        f.flush()
        yield f.name
    
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


class TestUploadEndpoint:
    """Test cases for the /api/upload endpoint."""

    def test_upload_valid_csv_file(self, sample_csv_file):
        """Test uploading a valid CSV file."""
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            response = client.post('/api/upload', files=files)
        
        # Verify response status and structure
        assert response.status_code == 200
        
        data = response.json()
        assert 'table' in data
        assert 'columns' in data
        assert data['table'] == 'sales'
        assert isinstance(data['columns'], list)
        assert len(data['columns']) > 0
        
        # Verify column structure
        for column in data['columns']:
            assert 'name' in column
            assert 'type' in column
            assert isinstance(column['name'], str)
            assert isinstance(column['type'], str)

    def test_upload_with_demo_data_flag(self):
        """Test upload endpoint with demo data flag."""
        response = client.post('/api/upload', data={'use_demo': True})
        
        # Check if demo data is available
        if response.status_code == 404:
            pytest.skip("Demo data not available")
        
        # Verify successful response
        assert response.status_code == 200
        
        data = response.json()
        assert 'table' in data
        assert 'columns' in data
        assert data['table'] == 'sales'
        assert isinstance(data['columns'], list)
        assert len(data['columns']) > 0

    def test_upload_without_file_or_demo_flag(self):
        """Test upload endpoint without file or demo flag."""
        response = client.post('/api/upload')
        
        # Should return 400 Bad Request
        assert response.status_code == 400
        
        data = response.json()
        assert 'detail' in data

    def test_upload_response_format(self, sample_csv_file):
        """Test that upload response follows the correct format."""
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            response = client.post('/api/upload', files=files)
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required fields
        assert 'table' in data
        assert 'columns' in data
        
        # Verify data types
        assert isinstance(data['table'], str)
        assert isinstance(data['columns'], list)
        
        # Verify table name
        assert data['table'] == 'sales'
        
        # Verify columns structure
        for column in data['columns']:
            assert isinstance(column, dict)
            assert 'name' in column
            assert 'type' in column
            assert isinstance(column['name'], str)
            assert isinstance(column['type'], str)
            assert len(column['name']) > 0
            assert len(column['type']) > 0

    def test_upload_creates_sales_table(self, sample_csv_file):
        """Test that upload creates the sales table in the database."""
        # First upload a file
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        assert upload_response.status_code == 200
        
        # Then check schema to verify table exists
        schema_response = client.get('/api/schema')
        assert schema_response.status_code == 200
        
        schema_data = schema_response.json()
        assert 'tables' in schema_data
        assert 'sales' in schema_data['tables']
        
        # Verify sales table has correct structure
        sales_table = schema_data['tables']['sales']
        assert 'name' in sales_table
        assert 'columns' in sales_table
        assert 'sample_rows' in sales_table
        assert 'row_count' in sales_table
        
        assert sales_table['name'] == 'sales'
        assert sales_table['row_count'] > 0
        assert len(sales_table['columns']) > 0

    def test_upload_http_status_codes(self, sample_csv_file):
        """Test various HTTP status codes returned by upload endpoint."""
        
        # Test successful upload (200)
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            response = client.post('/api/upload', files=files)
        assert response.status_code == 200
        
        # Test missing file (400)
        response = client.post('/api/upload')
        assert response.status_code == 400
        
        # Test demo data (200 or 404 if not available)
        response = client.post('/api/upload', data={'use_demo': True})
        assert response.status_code in [200, 404]

    def test_upload_error_response_format(self):
        """Test that error responses follow the correct format."""
        # Test with missing file
        response = client.post('/api/upload')
        
        assert response.status_code == 400
        
        data = response.json()
        assert 'detail' in data
        assert isinstance(data['detail'], str)
        assert len(data['detail']) > 0


class TestSchemaEndpoint:
    """Test cases for the /api/schema endpoint."""

    def test_schema_endpoint_basic_functionality(self):
        """Test basic schema endpoint functionality."""
        response = client.get('/api/schema')
        
        assert response.status_code == 200
        
        data = response.json()
        assert 'tables' in data
        assert isinstance(data['tables'], dict)

    def test_schema_endpoint_after_csv_upload(self, sample_csv_file):
        """Test schema endpoint returns correct data after CSV upload."""
        
        # First, upload a CSV file
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        # Verify upload was successful
        assert upload_response.status_code == 200
        
        # Now test the schema endpoint
        schema_response = client.get('/api/schema')
        assert schema_response.status_code == 200
        
        schema_data = schema_response.json()
        assert 'tables' in schema_data
        assert 'sales' in schema_data['tables']
        
        # Verify sales table structure
        sales_table = schema_data['tables']['sales']
        assert 'name' in sales_table
        assert 'columns' in sales_table
        assert 'sample_rows' in sales_table
        assert 'row_count' in sales_table
        
        assert sales_table['name'] == 'sales'
        assert sales_table['row_count'] > 0
        assert len(sales_table['columns']) > 0
        assert len(sales_table['sample_rows']) > 0

    def test_schema_endpoint_column_information(self, sample_csv_file):
        """Test that schema endpoint returns correct column information."""
        
        # Upload CSV with known columns
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('test.csv', f, 'text/csv')}
            client.post('/api/upload', files=files)
        
        response = client.get('/api/schema')
        assert response.status_code == 200
        
        data = response.json()
        sales_table = data['tables']['sales']
        
        # Verify columns exist and have correct structure
        columns = sales_table['columns']
        assert len(columns) > 0
        
        # Check that expected columns are present
        column_names = [col['name'] for col in columns]
        expected_columns = ['id', 'product_name', 'category', 'region', 'sales_amount', 'quantity']
        
        for expected_col in expected_columns:
            assert expected_col in column_names, f"Expected column '{expected_col}' not found in {column_names}"
        
        # Verify column types are provided
        for column in columns:
            assert 'name' in column
            assert 'type' in column
            assert isinstance(column['name'], str)
            assert isinstance(column['type'], str)
            assert len(column['name']) > 0
            assert len(column['type']) > 0


class TestAPIIntegration:
    """Integration tests for the complete API workflow."""

    def test_complete_upload_to_schema_flow(self, sample_csv_file):
        """Test complete flow: upload CSV → verify schema endpoint → validate data."""
        
        # Step 1: Upload CSV file
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('sales.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        # Verify upload success
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        
        # Validate upload response structure
        assert 'table' in upload_data
        assert 'columns' in upload_data
        assert upload_data['table'] == 'sales'
        assert len(upload_data['columns']) > 0
        
        # Step 2: Retrieve schema information
        schema_response = client.get('/api/schema')
        assert schema_response.status_code == 200
        schema_data = schema_response.json()
        
        # Validate schema response structure
        assert 'tables' in schema_data
        assert 'sales' in schema_data['tables']
        
        # Step 3: Validate sales table exists with correct structure
        sales_table = schema_data['tables']['sales']
        
        # Verify table metadata
        assert sales_table['name'] == 'sales'
        assert sales_table['row_count'] == 4  # 4 rows in our test data
        assert len(sales_table['columns']) == 6  # 6 columns in our test data
        assert len(sales_table['sample_rows']) > 0
        assert len(sales_table['sample_rows']) <= 5  # Should limit sample rows
        
        # Step 4: Verify expected columns exist
        column_names = [col['name'] for col in sales_table['columns']]
        expected_columns = ['id', 'product_name', 'category', 'region', 'sales_amount', 'quantity']
        
        for expected_col in expected_columns:
            assert expected_col in column_names, f"Expected column '{expected_col}' not found"

    def test_error_scenarios_integration(self):
        """Test error scenarios in the integration flow."""
        
        # Test 1: Upload without file, then check schema
        upload_response = client.post('/api/upload')
        assert upload_response.status_code == 400
        
        # Schema should still work (might be empty)
        schema_response = client.get('/api/schema')
        assert schema_response.status_code == 200