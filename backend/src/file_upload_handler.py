"""
File upload handler for CSV processing.
"""

import os
import csv
import io
from typing import Optional
from fastapi import UploadFile
from pathlib import Path

try:
    from .models import UploadResult
    from .exceptions import (
        FileUploadError,
        InvalidFileFormatError,
        FileSizeExceededError,
        FileValidationError,
        InvalidPathError
    )
    from .logging_config import get_logger
    from .security_config import SecurityConfig
except ImportError:
    from models import UploadResult
    from exceptions import (
        FileUploadError,
        InvalidFileFormatError,
        FileSizeExceededError,
        FileValidationError,
        InvalidPathError
    )
    from logging_config import get_logger
    from security_config import SecurityConfig

logger = get_logger(__name__)


class FileUploadHandler:
    """Handles CSV file upload, validation, and storage operations."""
    
    def __init__(self, data_directory: str = "data"):
        """
        Initialize the file upload handler.
        
        Args:
            data_directory: Directory where files will be stored
        """
        self.data_directory = self._validate_data_directory(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        self.target_filename = "sales.csv"
        self.config = SecurityConfig()
        logger.info(f"FileUploadHandler initialized with directory: {self.data_directory}")
    
    def _validate_data_directory(self, data_directory: str) -> Path:
        """
        Validate and resolve data directory path.
        
        Args:
            data_directory: Directory path to validate
            
        Returns:
            Path: Validated directory path
            
        Raises:
            InvalidPathError: If directory path is invalid
        """
        try:
            # Resolve to absolute path
            resolved_path = Path(data_directory).resolve()
            project_root = Path.cwd().resolve()
            
            # Ensure path is within project directory
            if not str(resolved_path).startswith(str(project_root)):
                logger.error(f"Data directory outside project bounds: {data_directory}")
                raise InvalidPathError("Data directory must be within project directory")
            
            return resolved_path
            
        except Exception as e:
            logger.error(f"Data directory validation failed: {e}")
            raise InvalidPathError(f"Invalid data directory: {data_directory}")
    
    async def process_upload(self, file: Optional[UploadFile] = None, use_demo: bool = False) -> UploadResult:
        """
        Process file upload or demo data request.
        
        Args:
            file: Uploaded CSV file (optional if use_demo is True)
            use_demo: Whether to use demo data instead of uploaded file
            
        Returns:
            UploadResult with success status and file path or error message
            
        Raises:
            FileUploadError: If upload processing fails
            InvalidFileFormatError: If file format is invalid
        """
        logger.info(f"Processing upload request: use_demo={use_demo}, file_provided={file is not None}")
        
        try:
            if use_demo:
                logger.info("Processing demo data request")
                return await self._handle_demo_data()
            
            if file is None:
                logger.warning("No file provided and demo flag not set")
                raise FileUploadError("No file provided and demo flag not set")
            
            # Validate the uploaded file
            logger.info(f"Validating uploaded file: {file.filename}")
            self.validate_csv_file(file)
            
            # Save the file
            target_path = self.data_directory / self.target_filename
            await self.save_csv_file(file, str(target_path))
            
            logger.info(f"File upload successful: {target_path}")
            return UploadResult(
                success=True,
                file_path=str(target_path)
            )
            
        except (FileUploadError, InvalidFileFormatError, FileSizeExceededError, FileValidationError):
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during upload processing: {e}")
            raise FileUploadError(f"Upload processing failed: {str(e)}")
    
    def validate_csv_file(self, file: UploadFile) -> None:
        """
        Validate that the uploaded file is a valid CSV.
        
        Args:
            file: The uploaded file to validate
            
        Raises:
            InvalidFileFormatError: If file format is invalid
            FileSizeExceededError: If file size exceeds limits
        """
        logger.debug(f"Validating CSV file: {file.filename}")
        
        try:
            # Check if filename exists
            if not file.filename:
                logger.warning("File uploaded without filename")
                raise InvalidFileFormatError("File must have a filename")
            
            # Check file extension
            if not file.filename.lower().endswith('.csv'):
                logger.warning(f"Invalid file extension: {file.filename}")
                raise InvalidFileFormatError("File must have .csv extension")
            
            # Check content type if provided
            if file.content_type and not (
                file.content_type.startswith('text/') or 
                file.content_type == 'application/csv'
            ):
                logger.warning(f"Invalid content type: {file.content_type}")
                raise InvalidFileFormatError("Invalid file content type")
            
            # Check file size
            max_size_bytes = self.config.MAX_CSV_SIZE_MB * 1024 * 1024
            if file.size and file.size > max_size_bytes:
                logger.warning(f"File size exceeds limit: {file.size} bytes (max: {max_size_bytes})")
                raise FileSizeExceededError(f"File size exceeds {self.config.MAX_CSV_SIZE_MB}MB limit")
            
            logger.debug("CSV file validation passed")
            
        except (InvalidFileFormatError, FileSizeExceededError):
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during file validation: {e}")
            raise InvalidFileFormatError("File validation failed")
    
    async def save_csv_file(self, file: UploadFile, target_path: str) -> None:
        """
        Save uploaded CSV file to target location.
        
        Args:
            file: The uploaded file to save
            target_path: Path where the file should be saved
            
        Raises:
            FileValidationError: If CSV content validation fails
            FileUploadError: If file saving fails
        """
        logger.info(f"Saving CSV file to: {target_path}")
        
        try:
            # Validate target path
            self._validate_target_path(target_path)
            
            # Read file content
            content = await file.read()
            logger.debug(f"Read {len(content)} bytes from uploaded file")
            
            # Validate CSV content by trying to parse it
            try:
                content_str = content.decode('utf-8')
            except UnicodeDecodeError as e:
                logger.error(f"File encoding error: {e}")
                raise FileValidationError("File is not valid UTF-8 encoded CSV")
            
            # Parse CSV to validate format
            try:
                csv_reader = csv.reader(io.StringIO(content_str))
                header = next(csv_reader)
                
                if not header or not any(header):
                    logger.error("CSV file appears to be empty or has no valid header")
                    raise FileValidationError("CSV file appears to be empty")
                
                logger.debug(f"CSV header validated: {len(header)} columns")
                
            except StopIteration:
                logger.error("CSV file has no content")
                raise FileValidationError("CSV file appears to be empty")
            except csv.Error as e:
                logger.error(f"CSV parsing error: {e}")
                raise FileValidationError(f"Invalid CSV format: {str(e)}")
            
            # Write to target location atomically
            temp_path = target_path + '.tmp'
            try:
                with open(temp_path, 'w', newline='', encoding='utf-8') as f:
                    f.write(content_str)
                
                # Atomic move
                os.rename(temp_path, target_path)
                logger.info(f"CSV file saved successfully: {target_path}")
                
            except OSError as e:
                # Clean up temp file if it exists
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                logger.error(f"File system error during save: {e}")
                raise FileUploadError(f"Failed to save file: {str(e)}")
                
        except (FileValidationError, FileUploadError):
            # Re-raise domain-specific exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error during file save: {e}")
            raise FileUploadError(f"Failed to save file: {str(e)}")
        finally:
            # Reset file pointer for potential reuse
            try:
                await file.seek(0)
            except Exception as e:
                logger.warning(f"Could not reset file pointer: {e}")
    
    def _validate_target_path(self, target_path: str) -> None:
        """
        Validate target file path for security.
        
        Args:
            target_path: Path to validate
            
        Raises:
            InvalidPathError: If path is invalid or unsafe
        """
        try:
            # Resolve to absolute path
            resolved_path = Path(target_path).resolve()
            project_root = Path.cwd().resolve()
            
            # Ensure path is within project directory
            if not str(resolved_path).startswith(str(project_root)):
                logger.error(f"Target path outside project bounds: {target_path}")
                raise InvalidPathError("Target path outside project directory")
            
            # Ensure parent directory exists
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
        except InvalidPathError:
            raise
        except Exception as e:
            logger.error(f"Target path validation failed: {e}")
            raise InvalidPathError(f"Invalid target path: {target_path}")
    
    async def _handle_demo_data(self) -> UploadResult:
        """
        Handle demo data request by checking if demo CSV exists.
        
        Returns:
            UploadResult indicating demo data availability
            
        Raises:
            DemoDataError: If demo data handling fails
        """
        try:
            from .exceptions import DemoDataError, DemoDataNotFoundError
        except ImportError:
            from exceptions import DemoDataError, DemoDataNotFoundError
        
        try:
            demo_path = self.data_directory / self.target_filename
            logger.info(f"Handling demo data request: {demo_path}")
            
            # Check if demo data already exists in target location
            if demo_path.exists():
                logger.info("Demo data already exists in target location")
                return UploadResult(
                    success=True,
                    file_path=str(demo_path)
                )
            
            # For now, just return success - actual demo data copying will be handled in main.py
            # This allows the upload flow to continue and handle demo data appropriately
            logger.info("Demo data request processed, file path prepared")
            return UploadResult(
                success=True,
                file_path=str(demo_path)
            )
            
        except Exception as e:
            logger.error(f"Demo data handling failed: {e}")
            raise DemoDataError(f"Demo data processing failed: {str(e)}")
    
    def get_target_file_path(self) -> str:
        """
        Get the target file path for CSV storage.
        
        Returns:
            String path to the target CSV file
        """
        return str(self.data_directory / self.target_filename)