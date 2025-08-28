from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import duckdb
import os
from typing import Dict, Any, List, Optional

# Import the new models
try:
    from .models import (
        UploadResponse, 
        ColumnInfo, 
        DatabaseSchema, 
        TableSchema, 
        ErrorResponse,
        UploadResult,
        TableMetadata,
        TableInfo
    )
    
    # Import the components
    from .file_upload_handler import FileUploadHandler
    from .database_manager import DatabaseManager
    from .schema_service import SchemaService
    from .auth import verify_api_key, SecurityHeadersMiddleware
    from .rate_limiter import RateLimitMiddleware, api_rate_limiter
    
    # Import error handling
    from .error_handlers import ErrorHandler, handle_api_exception
    from .exceptions import (
        DemoDataNotFoundError,
        FileUploadError,
        DatabaseError,
        SchemaExtractionError
    )
    from .logging_config import get_logger, DashlyLogger
except ImportError:
    from models import (
        UploadResponse, 
        ColumnInfo, 
        DatabaseSchema, 
        TableSchema, 
        ErrorResponse,
        UploadResult,
        TableMetadata,
        TableInfo
    )
    
    # Import the components
    from file_upload_handler import FileUploadHandler
    from database_manager import DatabaseManager
    from schema_service import SchemaService
    from auth import verify_api_key, SecurityHeadersMiddleware
    from rate_limiter import RateLimitMiddleware, api_rate_limiter
    
    # Import error handling
    from error_handlers import ErrorHandler, handle_api_exception
    from exceptions import (
        DemoDataNotFoundError,
        FileUploadError,
        DatabaseError,
        SchemaExtractionError
    )
    from logging_config import get_logger, DashlyLogger

app = FastAPI(title="Dashly API", version="0.1.0")

# Validate security configuration on startup
try:
    from .auth import SecurityConfig
    SecurityConfig.validate_config()
except ImportError:
    from auth import SecurityConfig
    SecurityConfig.validate_config()

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, rate_limiter=api_rate_limiter)

# CORS middleware for frontend communication - configurable for security
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Configure logging
logger = get_logger(__name__)

# Initialize DuckDB connection - using data/demo.duckdb for consistency
DB_PATH = "data/demo.duckdb"

class DatabaseConnection:
    """Manages database connection with error handling and reconnection."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._conn = duckdb.connect(self.db_path)
            logger.info(f"Database connection established: {self.db_path}")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise HTTPException(
                status_code=503, 
                detail="Database service temporarily unavailable"
            )
    
    def execute(self, query: str, parameters=None):
        """Execute query with automatic reconnection on failure."""
        try:
            if parameters:
                return self._conn.execute(query, parameters)
            else:
                return self._conn.execute(query)
        except Exception as e:
            logger.warning(f"Query failed, attempting reconnection: {str(e)}")
            try:
                self._connect()
                if parameters:
                    return self._conn.execute(query, parameters)
                else:
                    return self._conn.execute(query)
            except Exception as reconnect_error:
                logger.error(f"Database reconnection failed: {str(reconnect_error)}")
                raise HTTPException(
                    status_code=503, 
                    detail="Database service temporarily unavailable"
                )
    
    @property
    def description(self):
        """Get query description."""
        return self._conn.description
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

# Initialize shared database connection
db_connection = DatabaseConnection(DB_PATH)

# Initialize components for CSV upload functionality
file_handler = FileUploadHandler(data_directory="data")
db_manager = DatabaseManager(db_path=DB_PATH)
schema_service = SchemaService(db_manager=db_manager)

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query")
    sql_query: Optional[str] = Field(None, description="Direct SQL query (will be validated)")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()
    
    @validator('sql_query')
    def validate_sql_query(cls, v):
        if v is not None:
            # Import here to avoid circular imports
            try:
                from .sql_validator import sql_validator
            except ImportError:
                from sql_validator import sql_validator
            
            # Use comprehensive SQL validator
            return sql_validator.validate_query(v)
        return v
    
class QueryResponse(BaseModel):
    sql: str
    data: List[Dict[str, Any]]
    chart_type: str
    columns: List[str]

@app.get("/")
async def root():
    return {"message": "Dashly API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/upload", response_model=UploadResponse)
@handle_api_exception
async def upload_csv(
    file: Optional[UploadFile] = File(None),
    use_demo: bool = Form(False),
    authenticated: bool = Depends(verify_api_key)
):
    """
    Upload CSV file and ingest into DuckDB database.
    
    Args:
        file: CSV file to upload (optional if use_demo is True)
        use_demo: Whether to use demo data instead of uploaded file
        
    Returns:
        UploadResponse: Information about the uploaded table and columns
        
    Raises:
        HTTPException: Various HTTP status codes based on error type
    """
    DashlyLogger.log_api_request(logger, "POST", "/api/upload", 0)  # Will be updated with actual status
    logger.info(f"Upload request: use_demo={use_demo}, file_provided={file is not None}")
    
    # Process the upload using FileUploadHandler
    upload_result = await file_handler.process_upload(file=file, use_demo=use_demo)
    
    # Handle demo data case
    if use_demo:
        # Securely resolve demo data path within project boundaries
        import shutil
        from pathlib import Path
        
        try:
            # Get project root and validate demo path is within boundaries
            project_root = Path.cwd().resolve()
            project_demo_path = (project_root / "data" / "demo_sales.csv").resolve()
            backend_demo_path = (project_root / "backend" / "data" / "sales.csv").resolve()
            
            # Security check: ensure paths are within project directory
            if not str(project_demo_path).startswith(str(project_root)):
                DashlyLogger.log_security_event(
                    logger, 
                    "INVALID_DEMO_PATH", 
                    f"Demo path outside project: {project_demo_path}"
                )
                raise HTTPException(status_code=403, detail="Invalid demo data path")
            
            if not str(backend_demo_path).startswith(str(project_root)):
                DashlyLogger.log_security_event(
                    logger, 
                    "INVALID_BACKEND_PATH", 
                    f"Backend path outside project: {backend_demo_path}"
                )
                raise HTTPException(status_code=403, detail="Invalid backend data path")
            
            if not project_demo_path.exists():
                logger.warning("Demo data file not found")
                raise DemoDataNotFoundError("Demo data not available. Please run the demo data generation script first.")
            
            # Ensure backend data directory exists
            backend_demo_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy demo file to backend data directory
            shutil.copy2(str(project_demo_path), str(backend_demo_path))
            upload_result.file_path = str(backend_demo_path)
            logger.info(f"Demo data copied to: {backend_demo_path}")
            
        except DemoDataNotFoundError:
            raise
        except (OSError, ValueError) as e:
            logger.error(f"Demo data access failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to access demo data")
    
    # Ingest the CSV into DuckDB using DatabaseManager
    table_metadata = db_manager.ingest_csv(
        csv_path=upload_result.file_path,
        table_name="sales"
    )
    
    # Return successful response
    logger.info(f"Upload completed successfully: {table_metadata.table_name}")
    return UploadResponse(
        table=table_metadata.table_name,
        columns=table_metadata.columns
    )

@app.post("/api/query", response_model=QueryResponse)
@handle_api_exception
async def process_query(request: QueryRequest, authenticated: bool = Depends(verify_api_key)):
    """
    Process natural language query and return SQL + data + chart recommendation
    """
    logger.info(f"Processing query request: {request.query[:50]}...")
    
    # Import SQL validator
    try:
        from .sql_validator import sql_validator
    except ImportError:
        from sql_validator import sql_validator
    
    # Determine SQL query to execute
    if request.sql_query:
        # Direct SQL query provided - already validated by pydantic validator
        sql_to_execute = request.sql_query
        logger.info("Using provided SQL query")
    else:
        # TODO: Implement LLM integration for NL to SQL translation
        # For now, return a mock response with validation
        mock_sql = "SELECT * FROM sales LIMIT 10"
        sql_to_execute = sql_validator.validate_query(mock_sql)
        logger.info("Using mock SQL query (LLM integration pending)")
    
    # Execute validated query against DuckDB with connection error handling
    try:
        result = db_connection.execute(sql_to_execute).fetchall()
        columns = [desc[0] for desc in db_connection.description]
        
        # Convert to list of dictionaries
        data = [dict(zip(columns, row)) for row in result]
        
        # Limit result size for security
        if len(data) > 1000:
            logger.warning(f"Large result set truncated: {len(data)} rows -> 1000 rows")
            data = data[:1000]
        
        # TODO: Implement chart type recommendation logic
        chart_type = "bar"
        
        logger.info(f"Query processed successfully: {len(data)} rows returned")
        return QueryResponse(
            sql=sql_to_execute,
            data=data,
            chart_type=chart_type,
            columns=columns
        )
        
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Query execution failed. Please check your SQL syntax."
        )

@app.get("/api/schema", response_model=Dict[str, Any])
@handle_api_exception
async def get_database_schema(authenticated: bool = Depends(verify_api_key)):
    """
    Get comprehensive database schema information including tables, columns, and sample data.
    
    Returns:
        Dict[str, Any]: Complete database schema with table metadata
        
    Raises:
        HTTPException: 500 if database access fails
    """
    logger.info("Schema request received")
    
    # Use SchemaService to get all tables schema
    schema_data = schema_service.get_all_tables_schema()
    
    # Handle empty database scenario
    if not schema_data["tables"]:
        logger.info("No tables found in database")
        return {
            "tables": {},
            "message": "No tables found in database"
        }
    
    logger.info(f"Schema retrieved: {len(schema_data['tables'])} tables")
    return schema_data

@app.get("/api/tables")
@handle_api_exception
async def list_tables(authenticated: bool = Depends(verify_api_key)):
    """List available tables in the database"""
    logger.info("Tables list request received")
    
    # Execute query with connection error handling
    result = db_connection.execute("SHOW TABLES").fetchall()
    tables = [row[0] for row in result]
    
    logger.info(f"Tables listed: {len(tables)} tables found")
    return {"tables": tables}

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    try:
        db_connection.close()
        logger.info("Database connection closed")
        if hasattr(db_manager, 'close'):
            db_manager.close()
            logger.info("Database manager connection closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)