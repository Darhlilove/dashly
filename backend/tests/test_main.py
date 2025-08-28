import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Dashly API is running"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_list_tables():
    response = client.get("/api/tables")
    assert response.status_code == 200
    assert "tables" in response.json()

@pytest.mark.asyncio
async def test_process_query():
    query_data = {"query": "show me sales by region"}
    response = client.post("/api/query", json=query_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "sql" in data
    assert "data" in data
    assert "chart_type" in data
    assert "columns" in data

def test_get_schema_empty_database():
    """Test schema endpoint with empty database."""
    response = client.get("/api/schema")
    assert response.status_code == 200
    
    data = response.json()
    assert "tables" in data
    # Empty database should return empty tables dict
    assert isinstance(data["tables"], dict)

def test_get_schema_endpoint_structure():
    """Test that schema endpoint returns proper structure."""
    response = client.get("/api/schema")
    assert response.status_code == 200
    
    data = response.json()
    assert "tables" in data
    
    # If there are tables, verify structure
    for table_name, table_info in data["tables"].items():
        assert "name" in table_info
        assert "columns" in table_info
        assert "sample_rows" in table_info
        assert "row_count" in table_info
        
        # Verify columns structure
        for column in table_info["columns"]:
            assert "name" in column
            assert "type" in column