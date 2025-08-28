"""
Test that all imports work correctly.
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_database_manager_import():
    """Test that DatabaseManager can be imported."""
    from database_manager import DatabaseManager
    assert DatabaseManager is not None


def test_models_import():
    """Test that all models can be imported."""
    from models import (
        ColumnInfo, 
        UploadResponse, 
        DatabaseSchema, 
        TableSchema, 
        ErrorResponse,
        UploadResult,
        TableMetadata,
        TableInfo
    )
    
    # Verify all models are available
    assert ColumnInfo is not None
    assert UploadResponse is not None
    assert DatabaseSchema is not None
    assert TableSchema is not None
    assert ErrorResponse is not None
    assert UploadResult is not None
    assert TableMetadata is not None
    assert TableInfo is not None


def test_database_manager_with_models():
    """Test that DatabaseManager works with the models."""
    from database_manager import DatabaseManager
    from models import ColumnInfo, TableMetadata
    
    # Test that we can create instances
    column = ColumnInfo(name="test", type="VARCHAR")
    assert column.name == "test"
    assert column.type == "VARCHAR"
    
    metadata = TableMetadata(
        table_name="test_table",
        columns=[column],
        row_count=10
    )
    assert metadata.table_name == "test_table"
    assert len(metadata.columns) == 1
    assert metadata.row_count == 10


if __name__ == '__main__':
    test_database_manager_import()
    test_models_import()
    test_database_manager_with_models()
    print("All imports working correctly!")