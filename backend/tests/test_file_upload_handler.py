"""
Unit tests for FileUploadHandler class.
"""

import pytest
import tempfile
import os
import io
from pathlib import Path
from fastapi import UploadFile
from unittest.mock import Mock, AsyncMock

# Add the src directory to the path so we can import our modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from file_upload_handler import FileUploadHandler
from models import UploadResult


def create_upload_file(filename: str, content: bytes, content_type: str = None) -> UploadFile:
    """Helper function to create UploadFile for testing."""
    file_obj = io.BytesIO(content)
    upload_file = UploadFile(filename=filename, file=file_obj, size=len(content))
    # Manually set content_type using object.__setattr__ to bypass property
    if content_type:
        object.__setattr__(upload_file, '_content_type', content_type)
    return upload_file


class TestFileUploadHandler:
    """Test cases for FileUploadHandler class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def handler(self, temp_dir):
        """Create a FileUploadHandler instance for testing."""
        return FileUploadHandler(data_directory=temp_dir)
    
    @pytest.fixture
    def valid_csv_content(self):
        """Sample valid CSV content for testing."""
        return "id,name,value\n1,Product A,100\n2,Product B,200\n"
    
    @pytest.fixture
    def valid_csv_file(self, valid_csv_content):
        """Create a mock UploadFile with valid CSV content."""
        return create_upload_file("test.csv", valid_csv_content.encode('utf-8'), "text/csv")
    
    def test_init_creates_directory(self, temp_dir):
        """Test that handler creates data directory if it doesn't exist."""
        data_dir = os.path.join(temp_dir, "new_data_dir")
        handler = FileUploadHandler(data_directory=data_dir)
        
        assert os.path.exists(data_dir)
        assert handler.data_directory == Path(data_dir)
        assert handler.target_filename == "sales.csv"
    
    def test_validate_csv_file_valid(self, handler, valid_csv_file):
        """Test validation of valid CSV file."""
        result = handler.validate_csv_file(valid_csv_file)
        assert result is True
    
    def test_validate_csv_file_invalid_extension(self, handler):
        """Test validation fails for non-CSV file extension."""
        upload_file = create_upload_file("test.txt", b"test content", "text/plain")
        
        result = handler.validate_csv_file(upload_file)
        assert result is False
    
    def test_validate_csv_file_no_filename(self, handler):
        """Test validation fails when filename is None."""
        upload_file = create_upload_file(None, b"test content")
        
        result = handler.validate_csv_file(upload_file)
        assert result is False
    
    def test_validate_csv_file_too_large(self, handler):
        """Test validation fails for files that are too large."""
        # Create a file that reports as too large
        file_obj = io.BytesIO(b"test content")
        upload_file = UploadFile(filename="test.csv", file=file_obj, size=60 * 1024 * 1024)
        
        result = handler.validate_csv_file(upload_file)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_save_csv_file_success(self, handler, valid_csv_file, valid_csv_content):
        """Test successful CSV file saving."""
        target_path = handler.get_target_file_path()
        
        await handler.save_csv_file(valid_csv_file, target_path)
        
        # Verify file was saved correctly
        assert os.path.exists(target_path)
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == valid_csv_content
    
    @pytest.mark.asyncio
    async def test_save_csv_file_invalid_utf8(self, handler):
        """Test saving fails with invalid UTF-8 content."""
        # Create file with invalid UTF-8 bytes
        upload_file = create_upload_file("test.csv", b'\xff\xfe\x00\x00invalid')
        
        target_path = handler.get_target_file_path()
        
        with pytest.raises(ValueError, match="not valid UTF-8"):
            await handler.save_csv_file(upload_file, target_path)
    
    @pytest.mark.asyncio
    async def test_save_csv_file_empty_csv(self, handler):
        """Test saving fails with empty CSV content."""
        upload_file = create_upload_file("test.csv", b"")
        
        target_path = handler.get_target_file_path()
        
        with pytest.raises(ValueError, match="appears to be empty"):
            await handler.save_csv_file(upload_file, target_path)
    
    @pytest.mark.asyncio
    async def test_process_upload_success(self, handler, valid_csv_file):
        """Test successful file upload processing."""
        result = await handler.process_upload(file=valid_csv_file, use_demo=False)
        
        assert result.success is True
        assert result.file_path == handler.get_target_file_path()
        assert result.error_message is None
        
        # Verify file was actually saved
        assert os.path.exists(result.file_path)
    
    @pytest.mark.asyncio
    async def test_process_upload_demo_data(self, handler):
        """Test processing with demo data flag."""
        result = await handler.process_upload(file=None, use_demo=True)
        
        assert result.success is True
        assert result.file_path == handler.get_target_file_path()
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_process_upload_no_file_no_demo(self, handler):
        """Test processing fails when no file and no demo flag."""
        result = await handler.process_upload(file=None, use_demo=False)
        
        assert result.success is False
        assert result.file_path is None
        assert "No file provided" in result.error_message
    
    @pytest.mark.asyncio
    async def test_process_upload_invalid_file(self, handler):
        """Test processing fails with invalid file."""
        # Create invalid file (wrong extension)
        upload_file = create_upload_file("test.txt", b"test content")
        
        result = await handler.process_upload(file=upload_file, use_demo=False)
        
        assert result.success is False
        assert result.file_path is None
        assert "Invalid CSV file format" in result.error_message
    
    def test_get_target_file_path(self, handler, temp_dir):
        """Test getting target file path."""
        expected_path = os.path.join(temp_dir, "sales.csv")
        actual_path = handler.get_target_file_path()
        
        assert actual_path == expected_path
    
    @pytest.mark.asyncio
    async def test_process_upload_handles_exceptions(self, handler, temp_dir):
        """Test that process_upload handles unexpected exceptions gracefully."""
        # Create a file that will cause an exception during processing
        upload_file = create_upload_file("test.csv", b"id,name\n1,test")
        
        # Make the data directory read-only to cause a permission error
        os.chmod(temp_dir, 0o444)
        
        try:
            result = await handler.process_upload(file=upload_file, use_demo=False)
            
            assert result.success is False
            assert result.file_path is None
            assert "Upload processing failed" in result.error_message
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_dir, 0o755)


class TestFileUploadHandlerIntegration:
    """Integration tests for FileUploadHandler."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def handler(self, temp_dir):
        """Create a FileUploadHandler instance for testing."""
        return FileUploadHandler(data_directory=temp_dir)
    
    @pytest.mark.asyncio
    async def test_full_upload_workflow(self, handler):
        """Test complete upload workflow from validation to storage."""
        # Create a realistic CSV file
        csv_content = """id,date,product_name,category,region,sales_amount,quantity,customer_id
1,2023-01-01,Widget A,Electronics,North,1500.00,5,101
2,2023-01-02,Widget B,Electronics,South,2300.50,3,102
3,2023-01-03,Gadget C,Home,East,750.25,2,103
"""
        
        upload_file = create_upload_file("sales_data.csv", csv_content.encode('utf-8'), "text/csv")
        
        # Process the upload
        result = await handler.process_upload(file=upload_file, use_demo=False)
        
        # Verify success
        assert result.success is True
        assert result.file_path is not None
        assert os.path.exists(result.file_path)
        
        # Verify file content
        with open(result.file_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
            assert saved_content == csv_content
        
        # Verify we can read it as CSV
        import csv
        with open(result.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3
            assert rows[0]['product_name'] == 'Widget A'
            assert rows[1]['sales_amount'] == '2300.50'