#!/usr/bin/env python3
"""
Security tests for DatabaseManager.

Tests various security scenarios to ensure proper validation.
"""

import os
import tempfile
import pytest
from pathlib import Path

from database_manager import DatabaseManager


def test_sql_injection_protection():
    """Test that SQL injection attempts are blocked."""
    
    # Use a path within the project directory
    test_data_dir = Path("data/test")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_data_dir / "test.duckdb"
    
    db = DatabaseManager(str(db_path))
    
    # Test malicious table names
    malicious_names = [
            "test'; DROP TABLE users; --",
            "test OR 1=1",
            "test; INSERT INTO admin VALUES ('hacker')",
            "../../../etc/passwd",
            "test\"; DROP DATABASE;",
    ]
    
    for malicious_name in malicious_names:
        try:
            db._validate_table_name(malicious_name)
            assert False, f"Should have rejected malicious table name: {malicious_name}"
        except ValueError:
            pass  # Expected behavior
    
    db.close()


def test_path_traversal_protection():
    """Test that path traversal attempts are blocked."""
    
    # Use a path within the project directory
    test_data_dir = Path("data/test")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_data_dir / "test2.duckdb"
    
    db = DatabaseManager(str(db_path))
    
    # Test malicious paths
    malicious_paths = [
            "../../../etc/passwd",
            "../../sensitive_file.txt",
            "/etc/hosts",
            "C:\\Windows\\System32\\config\\SAM",
            "~/.ssh/id_rsa",
    ]
    
    for malicious_path in malicious_paths:
        try:
            db._validate_csv_path(malicious_path)
            assert False, f"Should have rejected malicious path: {malicious_path}"
        except (ValueError, FileNotFoundError):
            pass  # Expected behavior
    
    db.close()


def test_file_size_validation():
    """Test that large files are rejected."""
    
    # Use a path within the project directory
    test_data_dir = Path("data/test")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_data_dir / "test3.duckdb"
    
    # Create a large dummy file in project directory
    large_file = test_data_dir / "large.csv"
    with open(large_file, 'w') as f:
        # Write more than 100MB of data
        for i in range(1000000):
            f.write("a" * 200 + "\n")  # 200+ chars per line
    
    db = DatabaseManager(str(db_path))
    
    try:
        db._validate_csv_size(str(large_file))
        assert False, "Should have rejected large file"
    except ValueError as e:
        assert "too large" in str(e)
    finally:
        # Clean up large file
        if large_file.exists():
            large_file.unlink()
    
    db.close()


def test_sensitive_data_sanitization():
    """Test that sensitive data is properly sanitized."""
    
    # Use a path within the project directory
    test_data_dir = Path("data/test")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_data_dir / "test4.duckdb"
    
    db = DatabaseManager(str(db_path))
    
    # Test data with sensitive fields
    sample_data = [
            {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "555-1234",
                "password": "secret123",
                "age": 30
            },
            {
                "name": "Jane Smith", 
                "email": "jane@example.com",
                "phone": "555-5678",
                "password": "password456",
                "age": 25
            }
    ]
    
    sanitized = db._sanitize_sample_data(sample_data)
    
    # Check that sensitive fields are redacted
    for row in sanitized:
        assert row["email"] == "[REDACTED]"
        assert row["phone"] == "[REDACTED]"
        assert row["password"] == "[REDACTED]"
        # Non-sensitive fields should remain
        assert row["name"] != "[REDACTED]"
        assert row["age"] != "[REDACTED]"
    
    db.close()


def test_valid_table_names():
    """Test that valid table names are accepted."""
    
    # Use a path within the project directory
    test_data_dir = Path("data/test")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    db_path = test_data_dir / "test5.duckdb"
    
    db = DatabaseManager(str(db_path))
    
    valid_names = [
            "sales",
            "user_data",
            "_private_table",
            "Table123",
            "a" * 64,  # Max length
    ]
    
    for valid_name in valid_names:
        try:
            result = db._validate_table_name(valid_name)
            assert result == valid_name
        except ValueError:
            assert False, f"Should have accepted valid table name: {valid_name}"
    
    db.close()


if __name__ == "__main__":
    print("Running security tests...")
    
    test_sql_injection_protection()
    print("✓ SQL injection protection test passed")
    
    test_path_traversal_protection()
    print("✓ Path traversal protection test passed")
    
    test_file_size_validation()
    print("✓ File size validation test passed")
    
    test_sensitive_data_sanitization()
    print("✓ Sensitive data sanitization test passed")
    
    test_valid_table_names()
    print("✓ Valid table names test passed")
    
    print("\nAll security tests passed! ✅")