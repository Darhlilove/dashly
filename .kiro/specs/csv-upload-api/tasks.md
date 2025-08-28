# Implementation Plan

- [x] 1. Set up project dependencies and configuration

  - Update backend/requirements.txt with required packages (fastapi, uvicorn, duckdb, python-multipart, pytest)
  - Ensure data directory structure exists for file storage
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 2. Create data models and response schemas

  - Implement Pydantic models for API responses (UploadResponse, ColumnInfo, DatabaseSchema, TableSchema, ErrorResponse)
  - Add type definitions for internal data structures
  - _Requirements: 1.3, 3.2, 5.4_

- [x] 3. Implement database manager component

  - Create DatabaseManager class with DuckDB integration methods
  - Implement CSV ingestion functionality (ingest_csv method)
  - Add table metadata extraction methods (get_table_info, get_schema)
  - Write unit tests for database operations
  - _Requirements: 1.2, 3.1, 3.2, 7.4_

- [x] 4. Implement file upload handler

  - Create FileUploadHandler class for CSV file processing
  - Add file validation methods (validate_csv_file)
  - Implement file saving functionality (save_csv_file)
  - Add support for demo data flag processing
  - Write unit tests for file handling operations
  - _Requirements: 1.1, 2.1, 5.1, 5.2, 7.1_

- [x] 5. Create schema service component

  - Implement SchemaService class for database metadata operations
  - Add methods to extract table schemas and sample data
  - Format schema information for API responses
  - Write unit tests for schema extraction
  - _Requirements: 3.1, 3.2, 3.3, 7.4_

- [x] 6. Implement POST /api/upload endpoint

  - Add upload endpoint to existing FastAPI application in main.py
  - Integrate FileUploadHandler and DatabaseManager
  - Handle multipart form data with file field
  - Support demo data flag parameter
  - Implement proper error handling with HTTP status codes
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 5.1, 5.2, 5.3_

- [x] 7. Implement GET /api/schema endpoint

  - Add schema endpoint to existing FastAPI application
  - Integrate SchemaService for metadata retrieval
  - Return comprehensive database schema information
  - Handle empty database scenarios
  - Implement error handling for database access failures
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.4_

- [x] 8. Create demo data generation script

  - Implement scripts/init_demo.py with realistic sales data generation
  - Generate 500 sample rows with appropriate columns (id, date, product_name, category, region, sales_amount, quantity, customer_id)
  - Save generated data to data/sales.csv
  - Load demo data into DuckDB as sales table
  - Create necessary directory structure if missing
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 9. Write comprehensive API tests

  - Create test files in backend/tests/ directory
  - Implement tests for /api/upload endpoint with sample CSV data
  - Test upload endpoint with demo data flag
  - Verify correct response format and HTTP status codes
  - Test /api/schema endpoint functionality
  - Assert sales table exists with correct columns after upload
  - Test error scenarios and edge cases
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 10. Update database connection configuration

  - Modify existing DuckDB connection in main.py to use data/demo.duckdb
  - Ensure connection reuse across new endpoints
  - Add proper connection error handling
  - _Requirements: 1.2, 3.4, 5.4_

- [x] 11. Add error handling and logging

  - Implement comprehensive exception handling across all components
  - Add appropriate HTTP status codes for different error scenarios
  - Create custom exception classes for domain-specific errors
  - Add logging for debugging while keeping client responses safe
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 12. Integration testing and validation
  - Test complete end-to-end flow: upload CSV → verify schema endpoint
  - Validate demo data generation → API interaction workflow
  - Test database persistence across multiple requests
  - Verify all requirements are met through integration tests
  - _Requirements: 7.1, 7.2, 7.3, 7.4_
