from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import duckdb
import os
import threading
import time
import uuid
import json
from queue import Queue, Empty
from contextlib import contextmanager
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
        TableInfo,
        ExecuteRequest,
        ExecuteResponse,
        ExplainResponse,
        SQLErrorResponse,
        Dashboard,
        DashboardRequest,
        ChartConfig,
        ChatRequest,
        ConversationalResponse
    )
    
    # Import the components
    from .file_upload_handler import FileUploadHandler
    from .database_manager import DatabaseManager
    from .schema_service import SchemaService
    from .chat_service import ChatService
    from .auth import verify_api_key, SecurityHeadersMiddleware
    from .rate_limiter import RateLimitMiddleware, api_rate_limiter
    
    # Import SQL execution components
    from .sql_validator import SQLValidator
    from .query_executor import QueryExecutor
    from .performance_monitor import get_performance_monitor
    from .query_explain_service import QueryExplainService
    
    # Import error handling
    from .error_handlers import ErrorHandler, handle_api_exception
    from .exceptions import (
        DemoDataNotFoundError,
        FileUploadError,
        DatabaseError,
        SchemaExtractionError,
        ValidationError,
        QueryExecutionError,
        SQLSyntaxError,
        SQLSecurityError,
        QueryTimeoutError,
        ResultSetTooLargeError,
        SQLSchemaError,
        ConcurrentQueryLimitError,
        QueryExplainError
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
        TableInfo,
        ExecuteRequest,
        ExecuteResponse,
        ExplainResponse,
        SQLErrorResponse,
        Dashboard,
        DashboardRequest,
        ChartConfig,
        ChatRequest,
        ConversationalResponse
    )
    
    # Import the components
    from file_upload_handler import FileUploadHandler
    from database_manager import DatabaseManager
    from schema_service import SchemaService
    from chat_service import ChatService
    from auth import verify_api_key, SecurityHeadersMiddleware
    from rate_limiter import RateLimitMiddleware, api_rate_limiter
    
    # Import SQL execution components
    from sql_validator import SQLValidator
    from query_executor import QueryExecutor
    from performance_monitor import get_performance_monitor
    from query_explain_service import QueryExplainService
    
    # Import error handling
    from error_handlers import ErrorHandler, handle_api_exception
    from exceptions import (
        DemoDataNotFoundError,
        FileUploadError,
        DatabaseError,
        SchemaExtractionError,
        ValidationError,
        QueryExecutionError,
        SQLSyntaxError,
        SQLSecurityError,
        QueryTimeoutError,
        ResultSetTooLargeError,
        SQLSchemaError,
        ConcurrentQueryLimitError,
        QueryExplainError
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

import threading
from queue import Queue, Empty
from contextlib import contextmanager

class DatabaseConnectionPool:
    """Manages a pool of database connections for concurrent access."""
    
    def __init__(self, db_path: str, pool_size: int = 5):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to the DuckDB database file
            pool_size: Maximum number of connections in the pool
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created_connections = 0
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Pre-create initial connection to test database access
        self._create_connection()
        logger.info(f"Database connection pool initialized: {self.db_path} (max_size={pool_size})")
    
    def _create_connection(self):
        """Create a new database connection."""
        try:
            conn = duckdb.connect(self.db_path)
            # Test the connection
            conn.execute("SELECT 1").fetchone()
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {str(e)}")
            raise HTTPException(
                status_code=503, 
                detail="Database service temporarily unavailable"
            )
    
    @contextmanager
    def get_connection(self, timeout: float = 5.0):
        """
        Get a connection from the pool with timeout.
        
        Args:
            timeout: Maximum time to wait for a connection
            
        Yields:
            DuckDB connection instance
        """
        conn = None
        created_new = False
        
        try:
            # Try to get existing connection from pool first
            try:
                conn = self._pool.get_nowait()
                logger.debug("Retrieved connection from pool")
            except Empty:
                # Pool is empty, create new connection if under limit
                with self._lock:
                    if self._created_connections < self.pool_size:
                        conn = self._create_connection()
                        self._created_connections += 1
                        created_new = True
                        logger.debug(f"Created new connection ({self._created_connections}/{self.pool_size})")
                    else:
                        # Wait for a connection to become available with shorter timeout
                        try:
                            conn = self._pool.get(timeout=timeout)
                            logger.debug("Retrieved connection from pool after waiting")
                        except Empty:
                            logger.error(f"Connection pool timeout after {timeout}s")
                            raise HTTPException(
                                status_code=503, 
                                detail="Database connection pool exhausted"
                            )
            
            # Minimal connection test - don't test if we just created it
            if not created_new:
                try:
                    conn.execute("SELECT 1").fetchone()
                except Exception as e:
                    logger.warning(f"Connection test failed, creating new one: {str(e)}")
                    try:
                        conn.close()
                    except:
                        pass
                    conn = self._create_connection()
                    created_new = True
            
            yield conn
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            if conn and created_new:
                try:
                    conn.close()
                except:
                    pass
                with self._lock:
                    self._created_connections -= 1
            raise
        except Exception as e:
            # Check if this is a SQL-related error that should be passed through
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["syntax error", "parser error", "parse error", "table", "column", "not found", "does not exist"]):
                # This is a SQL error, not a connection error - let it bubble up
                if conn and created_new:
                    try:
                        conn.close()
                    except:
                        pass
                    with self._lock:
                        self._created_connections -= 1
                raise e
            
            # This is a genuine connection error
            logger.error(f"Failed to get database connection: {str(e)}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
                if created_new:
                    with self._lock:
                        self._created_connections -= 1
            raise HTTPException(
                status_code=503, 
                detail="Database service temporarily unavailable"
            )
        finally:
            # Return connection to pool if it's healthy
            if conn:
                try:
                    # Try to return to pool with short timeout
                    try:
                        self._pool.put_nowait(conn)
                        logger.debug("Returned connection to pool")
                    except:
                        # Pool is full, close the connection
                        logger.debug("Pool full, closing connection")
                        conn.close()
                        with self._lock:
                            self._created_connections -= 1
                except Exception as e:
                    logger.warning(f"Connection failed to return to pool, discarding: {str(e)}")
                    try:
                        conn.close()
                    except:
                        pass
                    with self._lock:
                        self._created_connections -= 1
    
    def close_all(self):
        """Close all connections in the pool."""
        closed_count = 0
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                closed_count += 1
            except Empty:
                break
            except Exception as e:
                logger.warning(f"Error closing pooled connection: {str(e)}")
        
        logger.info(f"Closed {closed_count} pooled connections")


class DatabaseConnection:
    """Manages database connection with error handling, reconnection, and connection pooling."""
    
    def __init__(self, db_path: str, enable_pooling: bool = True, pool_size: int = 5):
        """
        Initialize database connection manager.
        
        Args:
            db_path: Path to the DuckDB database file
            enable_pooling: Whether to use connection pooling for concurrent access
            pool_size: Maximum number of connections in the pool
        """
        self.db_path = db_path
        self.enable_pooling = enable_pooling
        
        if enable_pooling:
            self._pool = DatabaseConnectionPool(db_path, pool_size)
            self._conn = None  # No single connection when pooling
            logger.info(f"Database connection manager initialized with pooling: {self.db_path}")
        else:
            self._pool = None
            self._conn = None
            self._connect()
            logger.info(f"Database connection manager initialized without pooling: {self.db_path}")
    
    def _connect(self):
        """Establish single database connection (non-pooled mode)."""
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
        if self.enable_pooling:
            # Use connection pool with shorter timeout
            with self._pool.get_connection(timeout=2.0) as conn:
                try:
                    if parameters:
                        return conn.execute(query, parameters)
                    else:
                        return conn.execute(query)
                except Exception as e:
                    logger.warning(f"Pooled query failed: {str(e)}")
                    # Re-raise the original exception instead of wrapping it
                    raise e
        else:
            # Use single connection with reconnection
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
        """Get query description (only works in non-pooled mode)."""
        if self.enable_pooling:
            logger.warning("Description property not available in pooled mode")
            return None
        return self._conn.description if self._conn else None
    
    @contextmanager
    def get_connection(self, timeout: float = 2.0):
        """
        Get a database connection for direct use.
        
        Args:
            timeout: Maximum time to wait for a connection
        
        Yields:
            DuckDB connection instance
        """
        if self.enable_pooling:
            with self._pool.get_connection(timeout=timeout) as conn:
                yield conn
        else:
            if not self._conn:
                self._connect()
            yield self._conn
    
    def close(self):
        """Close database connection(s)."""
        if self.enable_pooling and self._pool:
            self._pool.close_all()
            logger.info("Database connection pool closed")
        elif self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

# Initialize shared database connection
db_connection = DatabaseConnection(DB_PATH)

# Initialize components for CSV upload functionality with shared connection
file_handler = FileUploadHandler(data_directory="data")
db_manager = DatabaseManager(db_path=DB_PATH, shared_connection=db_connection)
schema_service = SchemaService(db_manager=db_manager)

# Initialize SQL execution configuration
try:
    from .sql_execution_config import get_sql_execution_config
except ImportError:
    from sql_execution_config import get_sql_execution_config

sql_config = get_sql_execution_config()

# Initialize SQL execution components with configuration
sql_validator = SQLValidator()
query_executor = QueryExecutor(
    db_connection, 
    timeout_seconds=sql_config.query_timeout_seconds, 
    max_rows=sql_config.max_result_rows,
    max_concurrent=sql_config.max_concurrent_queries,
    memory_limit_mb=sql_config.memory_limit_mb
)
performance_monitor = get_performance_monitor(slow_query_threshold_ms=sql_config.slow_query_threshold_ms)
query_explain_service = QueryExplainService(db_connection, sql_validator)

# Initialize chart recommendation service
try:
    from .chart_recommendation_service import ChartRecommendationService
except ImportError:
    from chart_recommendation_service import ChartRecommendationService

chart_recommendation_service = ChartRecommendationService()

# Initialize conversation history manager
try:
    from .conversation_history_manager import ConversationHistoryManager
except ImportError:
    from conversation_history_manager import ConversationHistoryManager

conversation_history_manager = ConversationHistoryManager()

# Initialize chat service with chart recommendation and conversation history
chat_service = ChatService(
    query_executor=query_executor,
    chart_recommendation_service=chart_recommendation_service,
    conversation_history_manager=conversation_history_manager
)

# Initialize performance optimization components
try:
    from .response_cache import get_response_cache
    from .streaming_response import get_streaming_manager
except ImportError:
    from response_cache import get_response_cache
    from streaming_response import get_streaming_manager

response_cache = get_response_cache()
streaming_manager = get_streaming_manager()

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
            return sql_validator.validate_query_legacy(v)
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

@app.post("/api/test")
async def test_endpoint(request: Request):
    """Test endpoint to debug request handling"""
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            return {"message": "JSON received", "body": body}
        else:
            return {"message": "Non-JSON request", "content_type": content_type}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)}"}

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
    try:
        logger.info(f"Ingesting CSV from path: {upload_result.file_path}")
        table_metadata = db_manager.ingest_csv(
            csv_path=upload_result.file_path,
            table_name="sales"
        )
        logger.info(f"Ingestion successful: {table_metadata}")
    except Exception as e:
        logger.error(f"DatabaseManager error: {type(e).__name__}: {str(e)}")
        raise
    
    # Generate initial question suggestions for the uploaded data
    try:
        initial_suggestions = chat_service.generate_initial_data_questions(table_metadata.table_name)
        logger.info(f"Generated {len(initial_suggestions)} initial question suggestions")
    except Exception as e:
        logger.warning(f"Failed to generate initial suggestions: {str(e)}")
        initial_suggestions = [
            "What does my data look like overall?",
            "How much data do I have to work with?",
            "What are the main patterns in my data?"
        ]
    
    # Return successful response
    logger.info(f"Upload completed successfully: {table_metadata.table_name}")
    return UploadResponse(
        table=table_metadata.table_name,
        columns=table_metadata.columns,
        suggested_questions=initial_suggestions[:5]  # Limit to 5 suggestions
    )

@app.post("/api/demo", response_model=UploadResponse)
@handle_api_exception
async def use_demo_data(
    authenticated: bool = Depends(verify_api_key)
):
    """
    Use demo data and ingest into DuckDB database.
    
    Returns:
        UploadResponse: Information about the demo table and columns
        
    Raises:
        HTTPException: Various HTTP status codes based on error type
    """
    DashlyLogger.log_api_request(logger, "POST", "/api/demo", 0)
    logger.info("Demo data request received")
    
    # Process demo data using FileUploadHandler
    upload_result = await file_handler.process_upload(file=None, use_demo=True)
    
    # Handle demo data case - copy demo file to backend data directory
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
    try:
        logger.info(f"Ingesting CSV from path: {upload_result.file_path}")
        table_metadata = db_manager.ingest_csv(
            csv_path=upload_result.file_path,
            table_name="sales"
        )
        logger.info(f"Ingestion successful: {table_metadata}")
    except Exception as e:
        logger.error(f"DatabaseManager error: {type(e).__name__}: {str(e)}")
        raise
    
    # Generate initial question suggestions for the demo data
    try:
        initial_suggestions = chat_service.generate_initial_data_questions(table_metadata.table_name)
        logger.info(f"Generated {len(initial_suggestions)} initial question suggestions for demo data")
    except Exception as e:
        logger.warning(f"Failed to generate initial suggestions for demo data: {str(e)}")
        initial_suggestions = [
            "What does this demo data show?",
            "What patterns can I find in this sample data?",
            "How can I explore this dataset?"
        ]
    
    # Return successful response
    logger.info(f"Demo data loaded successfully: {table_metadata.table_name}")
    return UploadResponse(
        table=table_metadata.table_name,
        columns=table_metadata.columns,
        suggested_questions=initial_suggestions[:5]  # Limit to 5 suggestions
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
        sql_to_execute = sql_validator.validate_query_legacy(mock_sql)
        logger.info("Using mock SQL query (LLM integration pending)")
    
    # Execute validated query against DuckDB with connection error handling
    try:
        with db_connection.get_connection() as conn:
            result = conn.execute(sql_to_execute).fetchall()
            columns = [desc[0] for desc in conn.description]
        
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

@app.post("/api/chat", response_model=ConversationalResponse)
@handle_api_exception
async def process_chat_message(
    request: ChatRequest, 
    authenticated: bool = Depends(verify_api_key)
):
    """
    Process natural language chat message and return conversational response.
    
    This endpoint provides a beginner-friendly chat interface that hides
    technical complexity and returns conversational responses with insights
    and follow-up question suggestions.
    
    Args:
        request: ChatRequest containing the user's natural language message
        authenticated: Authentication verification dependency
        
    Returns:
        ConversationalResponse: Conversational response with insights and suggestions
        
    Raises:
        HTTPException: Various HTTP status codes based on error type
    """
    start_time = time.time()
    logger.info(f"Processing chat message: '{request.message[:50]}...'")
    
    try:
        # Process the chat message using ChatService with performance optimizations
        response = await chat_service.process_chat_message(request)
        
        logger.info(f"Chat message processed successfully in {response.processing_time_ms:.2f}ms")
        return response
        
    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}")
        
        # Return a beginner-friendly error response instead of raising HTTPException
        # This ensures the chat interface always gets a conversational response
        return ConversationalResponse(
            message="I'm having trouble processing your message right now. Please try again or rephrase your question.",
            chart_config=None,
            insights=["There was a technical issue processing your request."],
            follow_up_questions=[
                "Try asking your question differently",
                "What would you like to know about your data?",
                "Should we try a simpler question first?"
            ],
            processing_time_ms=(time.time() - start_time) * 1000,
            conversation_id=request.conversation_id or str(uuid.uuid4())
        )

@app.post("/api/chat/stream")
@handle_api_exception
async def chat_stream_endpoint(
    request: ChatRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Process chat message with streaming updates for better perceived performance.
    
    Args:
        request: ChatRequest containing the user's message
        authenticated: Authentication verification dependency
        
    Returns:
        Streaming response with real-time updates
    """
    from fastapi.responses import StreamingResponse
    import uuid
    
    stream_id = str(uuid.uuid4())
    logger.info(f"Starting streaming chat for: '{request.message[:50]}...' (stream: {stream_id})")
    
    async def generate_stream():
        try:
            # Process with streaming updates
            response = await chat_service.process_chat_message_with_streaming(request, stream_id)
            
            # Stream the events
            async for event in streaming_manager.create_stream(stream_id):
                yield f"data: {event}\n\n"
                
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}")
            error_event = {
                "event": "error",
                "data": {"error": str(e)},
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@app.get("/api/performance/stats")
@handle_api_exception
async def get_performance_stats(authenticated: bool = Depends(verify_api_key)):
    """
    Get comprehensive performance statistics for monitoring.
    
    Returns:
        Performance statistics including cache hit rates, query times, etc.
    """
    try:
        # Get cache statistics
        cache_stats = response_cache.get_cache_stats()
        
        # Get query executor statistics
        query_stats = query_executor.get_resource_status()
        
        # Get performance monitor statistics
        perf_stats = performance_monitor.get_performance_stats()
        
        return {
            "cache_performance": cache_stats,
            "query_performance": query_stats,
            "execution_metrics": {
                "total_queries": perf_stats.metrics.total_queries,
                "successful_queries": perf_stats.metrics.successful_queries,
                "failed_queries": perf_stats.metrics.failed_queries,
                "average_runtime_ms": perf_stats.metrics.average_runtime_ms,
                "slow_queries_count": perf_stats.metrics.slow_queries_count,
                "queries_per_minute": perf_stats.queries_per_minute,
                "uptime_seconds": perf_stats.uptime_seconds
            },
            "optimization_status": {
                "caching_enabled": True,
                "streaming_enabled": True,
                "concurrent_queries_enabled": True,
                "memory_monitoring_enabled": True
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance statistics")

@app.post("/api/performance/cache/clear")
@handle_api_exception
async def clear_performance_cache(authenticated: bool = Depends(verify_api_key)):
    """
    Clear performance caches for testing or maintenance.
    
    Returns:
        Status of cache clearing operation
    """
    try:
        # Clear all caches
        response_cache.invalidate_chat_cache()
        response_cache.invalidate_query_cache()
        
        logger.info("Performance caches cleared successfully")
        
        return {
            "status": "success",
            "message": "All performance caches cleared",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to clear caches: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear performance caches")

@app.get("/api/conversations/{conversation_id}/history")
@handle_api_exception
async def get_conversation_history(
    conversation_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get conversation history for a specific conversation.
    
    Args:
        conversation_id: ID of the conversation
        authenticated: Authentication verification dependency
        
    Returns:
        List of messages in the conversation
    """
    logger.info(f"Getting conversation history for: {conversation_id}")
    
    try:
        history = chat_service.get_conversation_history(conversation_id)
        return {"conversation_id": conversation_id, "messages": history}
    except Exception as e:
        logger.error(f"Failed to get conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation history")

@app.get("/api/conversations/{conversation_id}/context")
@handle_api_exception
async def get_conversation_context(
    conversation_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get conversation context for enhanced processing.
    
    Args:
        conversation_id: ID of the conversation
        authenticated: Authentication verification dependency
        
    Returns:
        Context information including recent messages and topics
    """
    logger.info(f"Getting conversation context for: {conversation_id}")
    
    try:
        context = chat_service.get_conversation_context(conversation_id)
        return {"conversation_id": conversation_id, "context": context}
    except Exception as e:
        logger.error(f"Failed to get conversation context: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation context")

@app.get("/api/conversations/{conversation_id}/summary")
@handle_api_exception
async def get_conversation_summary(
    conversation_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get conversation summary for display purposes.
    
    Args:
        conversation_id: ID of the conversation
        authenticated: Authentication verification dependency
        
    Returns:
        Summary information about the conversation
    """
    logger.info(f"Getting conversation summary for: {conversation_id}")
    
    try:
        summary = chat_service.get_conversation_summary(conversation_id)
        return summary
    except Exception as e:
        logger.error(f"Failed to get conversation summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation summary")

@app.delete("/api/conversations/{conversation_id}")
@handle_api_exception
async def clear_conversation(
    conversation_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Clear a conversation's history.
    
    Args:
        conversation_id: ID of the conversation to clear
        authenticated: Authentication verification dependency
        
    Returns:
        Success status
    """
    logger.info(f"Clearing conversation: {conversation_id}")
    
    try:
        success = chat_service.clear_conversation_history(conversation_id)
        if success:
            return {"message": "Conversation cleared successfully", "conversation_id": conversation_id}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear conversation")

@app.post("/api/conversations/cleanup")
@handle_api_exception
async def cleanup_expired_conversations(
    authenticated: bool = Depends(verify_api_key)
):
    """
    Clean up expired conversations.
    
    Args:
        authenticated: Authentication verification dependency
        
    Returns:
        Number of conversations cleaned up
    """
    logger.info("Cleaning up expired conversations")
    
    try:
        cleaned_count = chat_service.cleanup_expired_conversations()
        return {"message": f"Cleaned up {cleaned_count} expired conversations", "count": cleaned_count}
    except Exception as e:
        logger.error(f"Failed to cleanup conversations: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cleanup conversations")
        error_response = ConversationalResponse(
            message="I'm having some trouble right now, but I'm here to help! Let's try a different approach to exploring your data.",
            chart_config=None,
            insights=["There was a temporary issue processing your request."],
            follow_up_questions=[
                "What would you like to know about your data?",
                "Should we start with a simple overview?",
                "Try asking about totals or summaries"
            ],
            processing_time_ms=0.0,
            conversation_id=request.conversation_id or ""
        )
        
        return error_response

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
    with db_connection.get_connection() as conn:
        result = conn.execute("SHOW TABLES").fetchall()
        tables = [row[0] for row in result]
    
    logger.info(f"Tables listed: {len(tables)} tables found")
    return {"tables": tables}

@app.post("/api/execute", response_model=ExecuteResponse)
@handle_api_exception
async def execute_sql_query(
    request: ExecuteRequest, 
    authenticated: bool = Depends(verify_api_key)
):
    """
    Execute validated SQL query against the DuckDB database.
    
    This endpoint provides secure SQL query execution with comprehensive validation,
    performance monitoring, and error handling. Only SELECT statements are allowed.
    
    Args:
        request: ExecuteRequest containing the SQL query to execute
        authenticated: Authentication verification dependency
        
    Returns:
        ExecuteResponse: Query results with columns, rows, metadata, and timing
        
    Raises:
        HTTPException: Various status codes based on error type:
            - 400: SQL validation errors, execution errors
            - 408: Query timeout errors
            - 422: Invalid request format
            - 500: Internal server errors
    """
    # Log the incoming request
    DashlyLogger.log_api_request(logger, "POST", "/api/execute", 0)
    logger.info(f"SQL execution request: {request.sql[:100]}...")
    
    # Start performance monitoring
    with performance_monitor.start_timing("sql_execution") as timing_context:
        # Step 1: Validate the SQL query - Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
        logger.debug("Starting SQL validation")
        validation_result = sql_validator.validate_query(request.sql)
        
        if not validation_result.is_valid:
            # Log security violations
            for violation in validation_result.security_violations:
                DashlyLogger.log_security_event(
                    logger, 
                    violation.violation_type.upper(), 
                    f"{violation.description} - Query: {request.sql[:50]}..."
                )
            
            # Record failed execution in performance monitor
            runtime_ms = timing_context.get_elapsed_ms()
            performance_monitor.record_execution(
                sql=request.sql,
                runtime_ms=runtime_ms,
                success=False,
                error_message=f"Validation failed: {'; '.join(validation_result.errors)}"
            )
            
            # Determine the type of validation error and create appropriate exception
            first_violation = validation_result.security_violations[0] if validation_result.security_violations else None
            
            if first_violation and first_violation.violation_type == "syntax_error":
                # Syntax error with position tracking
                raise SQLSyntaxError(
                    message=validation_result.errors[0],
                    position=first_violation.position
                )
            elif first_violation and "non_select" in first_violation.violation_type:
                # Security violation
                raise SQLSecurityError(
                    message=validation_result.errors[0],
                    violation_type=first_violation.violation_type,
                    position=first_violation.position
                )
            else:
                # General validation error
                error_detail = "; ".join(validation_result.errors)
                raise SQLSyntaxError(message=error_detail)
        
        logger.info("SQL validation passed")
        
        try:
            # Step 2: Execute the validated query - Requirements 1.2, 1.3, 6.1, 6.2
            logger.debug("Starting query execution")
            query_result = query_executor.execute_with_limits(request.sql, max_rows=10000)
            
            logger.info(f"Query executed successfully: {query_result.row_count} rows in {query_result.runtime_ms:.2f}ms")
            
            # Step 3: Record successful execution in performance monitor - Requirements 3.1, 3.2, 3.3
            performance_monitor.record_execution(
                sql=request.sql,
                runtime_ms=query_result.runtime_ms,
                success=True,
                row_count=query_result.row_count,
                truncated=query_result.truncated
            )
            
            # Step 4: Format and return response - Requirements 1.3, 1.5
            response = ExecuteResponse(
                columns=query_result.columns,
                rows=query_result.rows,
                row_count=query_result.row_count,
                runtime_ms=query_result.runtime_ms,
                truncated=query_result.truncated
            )
            
            # Log successful response
            logger.info(f"SQL execution completed successfully: {query_result.row_count} rows, {query_result.runtime_ms:.2f}ms")
            if query_result.truncated:
                logger.warning(f"Results truncated to {query_result.row_count} rows")
            
            return response
            
        except (SQLSyntaxError, SQLSecurityError, QueryTimeoutError, 
                ResultSetTooLargeError, SQLSchemaError, ConcurrentQueryLimitError) as e:
            # Handle SQL-specific errors with detailed context - Requirements 5.1, 5.2, 5.3, 5.4
            runtime_ms = timing_context.get_elapsed_ms()
            
            performance_monitor.record_execution(
                sql=request.sql,
                runtime_ms=runtime_ms,
                success=False,
                error_message=str(e)
            )
            
            # Use ErrorHandler to convert to appropriate HTTP response
            http_exc = ErrorHandler.handle_exception(e, context="sql_execution")
            raise http_exc
            
        except QueryExecutionError as e:
            # Handle general query execution errors - Requirements 5.2, 5.4
            runtime_ms = timing_context.get_elapsed_ms()
            error_msg = str(e)
            
            performance_monitor.record_execution(
                sql=request.sql,
                runtime_ms=runtime_ms,
                success=False,
                error_message=error_msg
            )
            
            # Determine if this is a schema-related error and create specific exception
            if any(keyword in error_msg.lower() for keyword in ["table", "column", "not found", "does not exist"]):
                # Extract table/column name if possible
                missing_object = None
                if "table" in error_msg.lower():
                    # Try to extract table name from error message
                    import re
                    match = re.search(r"table['\s]*(['\"]?)(\w+)\1", error_msg, re.IGNORECASE)
                    if match:
                        missing_object = match.group(2)
                
                schema_error = SQLSchemaError(
                    message=error_msg,
                    missing_object=missing_object,
                    object_type="table" if "table" in error_msg.lower() else "column"
                )
                http_exc = ErrorHandler.handle_exception(schema_error, context="sql_execution")
                raise http_exc
            else:
                # General execution error
                http_exc = ErrorHandler.handle_exception(e, context="sql_execution")
                raise http_exc
            
        except Exception as e:
            # Handle unexpected errors - Requirements 5.2
            runtime_ms = timing_context.get_elapsed_ms()
            
            performance_monitor.record_execution(
                sql=request.sql,
                runtime_ms=runtime_ms,
                success=False,
                error_message=str(e)
            )
            
            # Use ErrorHandler for consistent error handling
            http_exc = ErrorHandler.handle_exception(e, context="sql_execution")
            raise http_exc

@app.get("/api/execute/explain", response_model=ExplainResponse)
@handle_api_exception
async def explain_sql_query(
    sql: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Analyze SQL query and return execution plan with cost estimation.
    
    This endpoint provides query analysis using DuckDB's EXPLAIN functionality
    without executing the actual query. It returns detailed execution plans,
    cost estimates, and optimization suggestions.
    
    Args:
        sql: SQL query to analyze (query parameter)
        authenticated: Authentication verification dependency
        
    Returns:
        ExplainResponse: Query analysis with execution plan and cost estimation
        
    Raises:
        HTTPException: Various status codes based on error type:
            - 400: SQL validation errors, explain failures
            - 422: Invalid request format
            - 500: Internal server errors
    """
    # Log the incoming request
    DashlyLogger.log_api_request(logger, "GET", "/api/execute/explain", 0)
    logger.info(f"SQL explain request: {sql[:100]}...")
    
    # Start performance monitoring
    with performance_monitor.start_timing("sql_explain") as timing_context:
        try:
            # Step 1: Generate comprehensive query explanation - Requirements 4.1, 4.2, 4.3, 4.4, 4.5
            logger.debug("Starting query explanation")
            explanation_result = query_explain_service.explain_query(sql)
            
            logger.info(f"Query explanation completed: cost={explanation_result.estimated_cost:.2f}, "
                       f"rows={explanation_result.estimated_rows}, "
                       f"time={explanation_result.estimated_runtime_ms:.2f}ms")
            
            # Step 2: Record successful explanation in performance monitor
            runtime_ms = timing_context.get_elapsed_ms()
            performance_monitor.record_execution(
                sql=f"EXPLAIN {sql}",
                runtime_ms=runtime_ms,
                success=True,
                row_count=0,  # EXPLAIN doesn't return data rows
                truncated=False
            )
            
            # Step 3: Format and return response - Requirements 4.3, 4.4, 4.5
            response = ExplainResponse(
                execution_plan=explanation_result.execution_plan,
                estimated_cost=explanation_result.estimated_cost,
                estimated_rows=explanation_result.estimated_rows,
                estimated_runtime_ms=explanation_result.estimated_runtime_ms,
                optimization_suggestions=explanation_result.optimization_suggestions
            )
            
            # Log successful response
            logger.info(f"SQL explain completed successfully: cost={explanation_result.estimated_cost:.2f}, "
                       f"suggestions={len(explanation_result.optimization_suggestions)}")
            
            return response
            
        except ValidationError as e:
            # Handle validation errors - Requirements 4.1
            runtime_ms = timing_context.get_elapsed_ms()
            error_msg = str(e)
            logger.warning(f"SQL validation error in explain: {error_msg}")
            
            performance_monitor.record_execution(
                sql=f"EXPLAIN {sql}",
                runtime_ms=runtime_ms,
                success=False,
                error_message=f"Validation error: {error_msg}"
            )
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "sql_validation_failed",
                    "detail": error_msg,
                    "sql_error_type": "syntax",
                    "position": None,
                    "suggestions": ["Check SQL syntax", "Ensure query is a valid SELECT statement"]
                }
            )
            
        except QueryExplainError as e:
            # Handle explain-specific errors - Requirements 4.5
            runtime_ms = timing_context.get_elapsed_ms()
            error_msg = str(e)
            logger.error(f"Query explain error: {error_msg}")
            
            performance_monitor.record_execution(
                sql=f"EXPLAIN {sql}",
                runtime_ms=runtime_ms,
                success=False,
                error_message=f"Explain error: {error_msg}"
            )
            
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "query_explain_failed",
                    "detail": error_msg,
                    "sql_error_type": "explain",
                    "position": None,
                    "suggestions": ["Check query syntax", "Ensure tables exist", "Try a simpler query"]
                }
            )
            
        except Exception as e:
            # Handle unexpected errors - Requirements 4.5
            runtime_ms = timing_context.get_elapsed_ms()
            error_msg = str(e)
            logger.error(f"Unexpected error during SQL explain: {error_msg}")
            
            performance_monitor.record_execution(
                sql=f"EXPLAIN {sql}",
                runtime_ms=runtime_ms,
                success=False,
                error_message=f"Unexpected error: {error_msg}"
            )
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "internal_server_error",
                    "detail": "An unexpected error occurred during query analysis",
                    "sql_error_type": "internal",
                    "position": None,
                    "suggestions": ["Try again later", "Contact support if the problem persists"]
                }
            )

# Dashboard Management Endpoints
# In-memory storage for MVP (replace with database in production)
dashboards_storage: Dict[str, Dashboard] = {}

@app.get("/api/dashboards", response_model=List[Dashboard])
@handle_api_exception
async def get_dashboards(authenticated: bool = Depends(verify_api_key)):
    """Get all saved dashboards."""
    logger.info("Dashboards list request received")
    dashboards = list(dashboards_storage.values())
    logger.info(f"Returning {len(dashboards)} dashboards")
    return dashboards

@app.post("/api/dashboards", response_model=Dashboard)
@handle_api_exception
async def save_dashboard(
    request: DashboardRequest, 
    authenticated: bool = Depends(verify_api_key)
):
    """Save a new dashboard."""
    logger.info(f"Dashboard save request: {request.name}")
    
    # Generate unique ID
    import uuid
    dashboard_id = str(uuid.uuid4())
    
    # Create dashboard with timestamp
    from datetime import datetime
    dashboard = Dashboard(
        id=dashboard_id,
        name=request.name,
        question=request.question,
        sql=request.sql,
        chartConfig=request.chartConfig,
        createdAt=datetime.utcnow().isoformat()
    )
    
    # Store dashboard
    dashboards_storage[dashboard_id] = dashboard
    
    logger.info(f"Dashboard saved successfully: {dashboard_id}")
    return dashboard

@app.get("/api/dashboards/{dashboard_id}", response_model=Dashboard)
@handle_api_exception
async def get_dashboard(
    dashboard_id: str, 
    authenticated: bool = Depends(verify_api_key)
):
    """Get a specific dashboard by ID."""
    logger.info(f"Dashboard get request: {dashboard_id}")
    
    if dashboard_id not in dashboards_storage:
        raise HTTPException(
            status_code=404,
            detail="Dashboard not found"
        )
    
    dashboard = dashboards_storage[dashboard_id]
    logger.info(f"Dashboard retrieved: {dashboard.name}")
    return dashboard

@app.get("/api/suggestions/initial")
@handle_api_exception
async def get_initial_question_suggestions(
    table_name: Optional[str] = None,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get initial question suggestions when data is uploaded.
    
    Args:
        table_name: Optional specific table name to analyze
        
    Returns:
        Dict containing suggested questions for initial exploration
    """
    try:
        logger.info(f"Getting initial question suggestions for table: {table_name or 'all tables'}")
        
        # Get suggestions from chat service
        suggestions = chat_service.generate_initial_data_questions(table_name)
        
        return {
            "suggestions": suggestions,
            "table_name": table_name,
            "suggestion_type": "initial_exploration"
        }
        
    except Exception as e:
        logger.error(f"Error getting initial question suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate initial question suggestions"
        )


@app.get("/api/suggestions/structure")
@handle_api_exception
async def get_structure_based_suggestions(authenticated: bool = Depends(verify_api_key)):
    """
    Get question suggestions based on available data structure.
    
    Returns:
        Dict containing questions suggested based on data structure
    """
    try:
        logger.info("Getting structure-based question suggestions")
        
        # Get schema information
        schema_info = schema_service.get_all_tables_schema()
        
        # Get suggestions from chat service
        suggestions = chat_service.suggest_questions_from_data_structure(schema_info)
        
        return {
            "suggestions": suggestions,
            "suggestion_type": "structure_based",
            "tables_analyzed": list(schema_info.get("tables", {}).keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting structure-based suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate structure-based suggestions"
        )


@app.get("/api/suggestions/contextual/{conversation_id}")
@handle_api_exception
async def get_contextual_suggestions(
    conversation_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get contextual question suggestions based on conversation history.
    
    Args:
        conversation_id: ID of the conversation
        
    Returns:
        Dict containing contextual question suggestions
    """
    try:
        logger.info(f"Getting contextual suggestions for conversation: {conversation_id}")
        
        # Get suggestions from chat service
        suggestions = chat_service.get_contextual_suggestions(conversation_id)
        
        return {
            "suggestions": suggestions,
            "conversation_id": conversation_id,
            "suggestion_type": "contextual"
        }
        
    except Exception as e:
        logger.error(f"Error getting contextual suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate contextual suggestions"
        )


@app.post("/api/insights/proactive")
@handle_api_exception
async def get_proactive_insights(
    request: Dict[str, Any],
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get proactive insights from query results.
    
    Args:
        request: Dict containing query_results and original_question
        
    Returns:
        Dict containing proactive insights with suggested actions
    """
    try:
        query_results = request.get("query_results")
        original_question = request.get("original_question", "")
        
        if not query_results:
            raise HTTPException(status_code=400, detail="query_results is required")
        
        logger.info(f"Getting proactive insights for question: {original_question[:50]}...")
        
        # Get insights from chat service
        insights = chat_service.get_proactive_insights(query_results, original_question)
        
        return {
            "insights": insights,
            "original_question": original_question,
            "insight_count": len(insights)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting proactive insights: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate proactive insights"
        )


@app.post("/api/translate", response_model=Dict[str, str])
@handle_api_exception
async def translate_query(
    request: Dict[str, str], 
    authenticated: bool = Depends(verify_api_key)
):
    """
    Translate natural language query to SQL using LLM.
    
    Args:
        request: Dictionary containing 'question' key with natural language query
        
    Returns:
        Dict containing 'sql' key with generated SQL query
    """
    logger.info(f"Translate request: {request.get('question', '')[:50]}...")
    
    question = request.get('question', '').strip()
    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )
    
    try:
        # Get database schema for context
        schema_data = schema_service.get_all_tables_schema()
        
        # Import and use LLM service
        try:
            from .llm_service import get_llm_service
        except ImportError:
            from llm_service import get_llm_service
        
        llm_service = get_llm_service()
        
        # Translate question to SQL using LLM
        sql = await llm_service.translate_to_sql(question, schema_data)
        
        logger.info(f"LLM generated SQL: {sql[:100]}...")
        return {"sql": sql}
        
    except Exception as e:
        logger.error(f"LLM translation failed: {str(e)}")
        
        # Fallback to pattern matching if LLM fails
        logger.info("Falling back to pattern matching...")
        question_lower = question.lower()
        
        # Use column name 'sales_amount' instead of 'amount' based on actual schema
        if 'revenue' in question_lower or 'sales' in question_lower:
            if 'monthly' in question_lower or 'month' in question_lower:
                sql = """SELECT 
    strftime('%Y-%m', date) as month,
    SUM(sales_amount) as total_revenue
FROM sales 
GROUP BY strftime('%Y-%m', date)
ORDER BY month"""
            elif 'region' in question_lower:
                sql = """SELECT 
    region,
    SUM(sales_amount) as total_revenue
FROM sales 
GROUP BY region
ORDER BY total_revenue DESC"""
            else:
                sql = "SELECT SUM(sales_amount) as total_revenue FROM sales"
        elif 'count' in question_lower or 'number' in question_lower:
            sql = "SELECT COUNT(*) as total_count FROM sales"
        elif 'average' in question_lower or 'avg' in question_lower:
            sql = "SELECT AVG(sales_amount) as average_amount FROM sales"
        elif 'top' in question_lower or 'best' in question_lower:
            sql = """SELECT 
    product,
    SUM(sales_amount) as total_sales
FROM sales 
GROUP BY product
ORDER BY total_sales DESC
LIMIT 10"""
        else:
            # Default query
            sql = "SELECT * FROM sales LIMIT 100"
        
        logger.info(f"Fallback generated SQL: {sql[:100]}...")
        return {"sql": sql}

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    try:
        # Cleanup LLM service
        try:
            from .llm_service import cleanup_llm_service
        except ImportError:
            from llm_service import cleanup_llm_service
        
        await cleanup_llm_service()
        logger.info("LLM service cleaned up")
        
        # Cleanup database connections
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