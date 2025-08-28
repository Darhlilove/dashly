#!/usr/bin/env python3
"""
Integration test for secure DatabaseManager functionality.
"""

import os
from pathlib import Path
from database_manager import DatabaseManager


def test_secure_csv_ingestion():
    """Test complete secure CSV ingestion workflow."""
    
    # Setup
    test_data_dir = Path("data/test")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_data_dir / "integration_test.duckdb"
    
    # Clean up any existing test database
    if db_path.exists():
        db_path.unlink()
    
    db = DatabaseManager(str(db_path))
    
    try:
        # Create test CSV data in allowed directory
        test_csv_path = test_data_dir / "test_sales.csv"
        csv_content = """date,region,product,sales_amount,customer_email,phone
2023-01-15,North,Widget A,1250.50,john.doe@email.com,555-0123
2023-01-16,South,Widget B,890.25,jane.smith@email.com,555-0456
2023-01-17,East,Widget A,1100.75,bob.johnson@email.com,555-0789
2023-01-18,West,Widget C,750.00,alice.brown@email.com,555-0321
2023-01-19,North,Widget B,950.25,charlie.davis@email.com,555-0654
2023-01-20,South,Widget A,1350.00,diana.wilson@email.com,555-0987"""
        
        with open(test_csv_path, 'w') as f:
            f.write(csv_content)
        
        print(f"Ingesting CSV: {test_csv_path}")
        metadata = db.ingest_csv(str(test_csv_path), "sales_data")
        
        print(f"✓ Ingested table: {metadata.table_name}")
        print(f"✓ Columns: {len(metadata.columns)}")
        print(f"✓ Rows: {metadata.row_count}")
        
        # Test schema retrieval
        schema = db.get_schema()
        print(f"✓ Schema contains {len(schema.tables)} tables")
        
        # Test table info retrieval (should sanitize sensitive data)
        table_info = db.get_table_info("sales_data")
        print(f"✓ Table info retrieved for: {table_info.name}")
        print(f"✓ Sample data rows: {len(table_info.sample_data)}")
        
        # Verify sensitive data is redacted
        for row in table_info.sample_data:
            if "customer_email" in row:
                assert row["customer_email"] == "[REDACTED]", "Email should be redacted"
            if "phone" in row:
                assert row["phone"] == "[REDACTED]", "Phone should be redacted"
        
        print("✓ Sensitive data properly redacted")
        
        # Test table existence check
        assert db.table_exists("sales_data"), "Table should exist"
        assert not db.table_exists("nonexistent_table"), "Nonexistent table should return False"
        
        print("✓ Table existence checks working")
        
        print("\n🎉 All integration tests passed!")
        
    finally:
        db.close()
        # Clean up test files
        if db_path.exists():
            db_path.unlink()
        test_csv_path = test_data_dir / "test_sales.csv"
        if test_csv_path.exists():
            test_csv_path.unlink()


if __name__ == "__main__":
    test_secure_csv_ingestion()