# Requirements Document

## Introduction

This feature implements a FastAPI backend service that enables CSV file upload, ingestion into DuckDB, and schema introspection. The backend serves as the data processing layer for the dashly application, providing endpoints for file upload and database schema retrieval to support the natural language to dashboard generation workflow.

## Requirements

### Requirement 1

**User Story:** As a dashly user, I want to upload CSV files through an API endpoint, so that I can ingest my data into the system for dashboard generation.

#### Acceptance Criteria

1. WHEN a user sends a POST request to `/api/upload` with a CSV file in the `file` field THEN the system SHALL save the CSV to `data/sales.csv`
2. WHEN the CSV is successfully saved THEN the system SHALL ingest the data into DuckDB at `data/demo.duckdb` as table `sales`
3. WHEN the ingestion is complete THEN the system SHALL return a JSON response with table name and column metadata in format `{ "table": "sales", "columns": [ {name, type}, ... ] }`
4. WHEN the upload fails due to invalid file format THEN the system SHALL return HTTP 400 with error message
5. WHEN the upload fails due to server error THEN the system SHALL return HTTP 500 with error message

### Requirement 2

**User Story:** As a dashly user, I want to use demo data instead of uploading my own file, so that I can quickly test the system functionality.

#### Acceptance Criteria

1. WHEN a user sends a POST request to `/api/upload` with a demo data flag THEN the system SHALL use pre-generated demo data instead of requiring file upload
2. WHEN demo data is requested THEN the system SHALL load the demo data into DuckDB as table `sales`
3. WHEN demo data loading is complete THEN the system SHALL return the same JSON response format as file upload

### Requirement 3

**User Story:** As a dashly frontend application, I want to retrieve database schema information, so that I can understand the available tables and columns for query generation.

#### Acceptance Criteria

1. WHEN a client sends a GET request to `/api/schema` THEN the system SHALL return JSON schema for all tables in DuckDB
2. WHEN schema is requested THEN the response SHALL include table names, column names, column types, and sample rows
3. WHEN no tables exist in the database THEN the system SHALL return an empty schema structure
4. WHEN database access fails THEN the system SHALL return HTTP 500 with error message

### Requirement 4

**User Story:** As a developer, I want the backend to use specific Python packages, so that the implementation follows the project's technology constraints.

#### Acceptance Criteria

1. WHEN the backend is implemented THEN it SHALL use fastapi for the web framework
2. WHEN the backend is implemented THEN it SHALL use uvicorn for the ASGI server
3. WHEN the backend is implemented THEN it SHALL use duckdb for database operations
4. WHEN file uploads are handled THEN it SHALL use python-multipart for multipart form processing

### Requirement 5

**User Story:** As a developer, I want proper error handling and HTTP status codes, so that clients can handle different scenarios appropriately.

#### Acceptance Criteria

1. WHEN any API endpoint succeeds THEN it SHALL return appropriate 2xx status codes
2. WHEN client sends invalid requests THEN the system SHALL return 4xx status codes with descriptive error messages
3. WHEN server encounters internal errors THEN the system SHALL return 5xx status codes with error messages
4. WHEN database operations fail THEN the system SHALL handle exceptions gracefully and return appropriate error responses

### Requirement 6

**User Story:** As a developer, I want demo data generation capabilities, so that I can test the system without manual data preparation.

#### Acceptance Criteria

1. WHEN the demo script is executed THEN it SHALL generate `data/sales.csv` with 500 sample rows
2. WHEN demo data is generated THEN it SHALL include realistic sales data with appropriate columns
3. WHEN demo data is generated THEN it SHALL automatically load the data into DuckDB
4. WHEN demo script runs THEN it SHALL create the necessary directory structure if it doesn't exist

### Requirement 7

**User Story:** As a developer, I want comprehensive unit tests, so that I can verify the API functionality works correctly.

#### Acceptance Criteria

1. WHEN tests are executed THEN they SHALL test the `/api/upload` endpoint with sample CSV data
2. WHEN upload tests run THEN they SHALL verify the correct response format and HTTP status codes
3. WHEN schema tests run THEN they SHALL verify `/api/schema` returns correct table and column information
4. WHEN tests complete THEN they SHALL assert that the `sales` table exists with correct columns
5. WHEN tests are implemented THEN they SHALL use pytest as the testing framework
