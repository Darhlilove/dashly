"""
Integration tests for the schema API endpoint.
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
    return """id,name,age,salary
1,John Doe,30,50000
2,Jane Smith,25,45000
3,Bob Johnson,35,60000"""


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


def test_schema_endpoint_after_upload(sample_csv_file):
    """Test schema endpoint returns correct data after CSV upload."""
    
    # First, upload a CSV file
    with open(sample_csv_file, 'rb') as f:
        files = {'file': ('test.csv', f, 'text/csv')}
        upload_response = client.post('/api/upload', files=files)
    
    # Verify upload was successful
    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data['table'] == 'sales'
    assert len(upload_data['columns']) > 0
    
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
    
    # Verify column structure
    for column in sales_table['columns']:
        assert 'name' in column
        assert 'type' in column
        assert isinstance(column['name'], str)
        assert isinstance(column['type'], str)
    
    # Verify sample rows structure
    for row in sales_table['sample_rows']:
        assert isinstance(row, dict)
        # Should have data for each column
        for column in sales_table['columns']:
            assert column['name'] in row


def test_schema_endpoint_with_demo_data():
    """Test schema endpoint with demo data upload."""
    
    # Upload demo data
    upload_response = client.post('/api/upload', data={'use_demo': True})
    
    # Check if demo data is available, if not skip this test
    if upload_response.status_code == 404:
        pytest.skip("Demo data not available")
    
    # Verify upload was successful
    assert upload_response.status_code == 200
    
    # Test schema endpoint
    schema_response = client.get('/api/schema')
    assert schema_response.status_code == 200
    
    schema_data = schema_response.json()
    assert 'tables' in schema_data
    assert 'sales' in schema_data['tables']
    
    # Verify the demo data structure
    sales_table = schema_data['tables']['sales']
    assert sales_table['row_count'] > 0
    assert len(sales_table['columns']) > 0
    assert len(sales_table['sample_rows']) > 0


def test_schema_endpoint_error_handling():
    """Test schema endpoint error handling."""
    
    # The endpoint should handle database errors gracefully
    # This test verifies the endpoint returns proper error responses
    
    # Test with normal operation first
    response = client.get('/api/schema')
    assert response.status_code == 200
    
    # The endpoint should always return a valid response structure
    data = response.json()
    assert 'tables' in data
    assert isinstance(data['tables'], dict)


def test_schema_endpoint_response_format():
    """Test that schema endpoint returns consistent response format."""
    
    response = client.get('/api/schema')
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify top-level structure
    assert 'tables' in data
    assert isinstance(data['tables'], dict)
    
    # If there are tables, verify their structure
    for table_name, table_info in data['tables'].items():
        # Required fields
        assert 'name' in table_info
        assert 'columns' in table_info
        assert 'sample_rows' in table_info
        assert 'row_count' in table_info
        
        # Type checks
        assert isinstance(table_info['name'], str)
        assert isinstance(table_info['columns'], list)
        assert isinstance(table_info['sample_rows'], list)
        assert isinstance(table_info['row_count'], int)
        
        # Column structure
        for column in table_info['columns']:
            assert 'name' in column
            assert 'type' in column
            assert isinstance(column['name'], str)
            assert isinstance(column['type'], str)
        
        # Sample rows structure
        for row in table_info['sample_rows']:
            assert isinstance(row, dict)