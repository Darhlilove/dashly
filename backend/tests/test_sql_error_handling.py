"""
Comprehensive tests for SQL error handling functionality.

Tests all error scenarios for SQL execution API including syntax errors,
security violations, execution errors, timeouts, and error response formatting.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from src.exceptions import (
    QueryExecutionError,
    SQLSyntaxError,
    SQLSecurityError,
    QueryTimeoutError,
    ResultSetTooLargeError,
    QueryExplainError,
    SQLSchemaError,
    ConcurrentQueryLimitError
)
from src.error_handlers import ErrorHandler
from src.models import SQLErrorResponse


class TestSQLExceptionClasses:
    """Test custom SQL exception classes."""
    
    def test_query_execution_error_basic(self):
        """Test basic QueryExecutionError functionality."""
        error = QueryExecutionError("Test error")
        assert str(error) == "Test error"
        assert error.sql_error_type == "execution"
        assert error.position is None
        assert error.suggestions == []
    
    def test_query_execution_error_with_details(self):
        """Test QueryExecutionError with all details."""
        error = QueryExecutionError(
            "Test error",
            error_code="TEST_ERROR",
            sql_error_type="custom",
            position=15,
            suggestions=["Fix this", "Try that"]
        )
        assert str(error) == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.sql_error_type == "custom"
        assert error.position == 15
        assert error.suggestions == ["Fix this", "Try that"]
    
    def test_sql_syntax_error(self):
        """Test SQLSyntaxError initialization and defaults."""
        error = SQLSyntaxError("Invalid syntax", position=10)
        assert str(error) == "Invalid syntax"
        assert error.sql_error_type == "syntax"
        assert error.position == 10
        assert error.error_code == "SQL_SYNTAX_ERROR"
        assert any("SQL syntax" in suggestion for suggestion in error.suggestions)
    
    def test_sql_security_error(self):
        """Test SQLSecurityError initialization and defaults."""
        error = SQLSecurityError("DDL not allowed", violation_type="ddl_operation")
        assert str(error) == "DDL not allowed"
        assert error.sql_error_type == "security"
        assert error.violation_type == "ddl_operation"
        assert error.error_code == "SQL_SECURITY_ERROR"
        assert any("SELECT statements only" in suggestion for suggestion in error.suggestions)
    
    def test_query_timeout_error(self):
        """Test QueryTimeoutError initialization and defaults."""
        error = QueryTimeoutError("Query timed out", timeout_seconds=30)
        assert str(error) == "Query timed out"
        assert error.sql_error_type == "timeout"
        assert error.timeout_seconds == 30
        assert error.error_code == "QUERY_TIMEOUT_ERROR"
        assert any("Simplify the query" in suggestion for suggestion in error.suggestions)
    
    def test_result_set_too_large_error(self):
        """Test ResultSetTooLargeError initialization and defaults."""
        error = ResultSetTooLargeError(
            "Too many rows", 
            max_rows=10000, 
            actual_rows=50000
        )
        assert str(error) == "Too many rows"
        assert error.sql_error_type == "execution"
        assert error.max_rows == 10000
        assert error.actual_rows == 50000
        assert any("LIMIT clause" in suggestion for suggestion in error.suggestions)
    
    def test_sql_schema_error(self):
        """Test SQLSchemaError initialization and defaults."""
        error = SQLSchemaError(
            "Table not found", 
            missing_object="users", 
            object_type="table"
        )
        assert str(error) == "Table not found"
        assert error.sql_error_type == "execution"
        assert error.missing_object == "users"
        assert error.object_type == "table"
        assert any("available tables" in suggestion for suggestion in error.suggestions)
    
    def test_concurrent_query_limit_error(self):
        """Test ConcurrentQueryLimitError initialization and defaults."""
        error = ConcurrentQueryLimitError("Too many queries", max_concurrent=5)
        assert str(error) == "Too many queries"
        assert error.sql_error_type == "execution"
        assert error.max_concurrent == 5
        assert any("Wait for other queries" in suggestion for suggestion in error.suggestions)


class TestErrorHandler:
    """Test ErrorHandler class functionality."""
    
    def test_handle_sql_syntax_error(self):
        """Test handling of SQL syntax errors."""
        error = SQLSyntaxError("Invalid SELECT", position=5)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error, context="test_query")
            
            # Check logging
            mock_logger.error.assert_called_once()
            
            # Check HTTP exception
            assert http_exc.status_code == 400
            assert isinstance(http_exc.detail, dict)
            assert http_exc.detail["error"] == "sqlsyntax_failed"
            assert http_exc.detail["sql_error_type"] == "syntax"
            assert http_exc.detail["position"] == 5
            assert "Check SQL syntax" in http_exc.detail["suggestions"]
    
    def test_handle_sql_security_error(self):
        """Test handling of SQL security errors with security logging."""
        error = SQLSecurityError("DDL not allowed", violation_type="ddl_operation")
        
        with patch('src.error_handlers.logger') as mock_logger:
            
            with patch('src.logging_config.DashlyLogger') as mock_dashly_logger:
                http_exc = ErrorHandler.handle_exception(error, context="test_query")
                
                # Check security logging
                mock_dashly_logger.log_security_event.assert_called_once()
                args = mock_dashly_logger.log_security_event.call_args[0]
                assert "SQL_SECURITY_VIOLATION_ddl_operation" in args[1]
                
                # Check HTTP exception
                assert http_exc.status_code == 400
                assert isinstance(http_exc.detail, dict)
                assert http_exc.detail["error"] == "sqlsecurity_failed"
                assert http_exc.detail["sql_error_type"] == "security"
    
    def test_handle_query_timeout_error(self):
        """Test handling of query timeout errors."""
        error = QueryTimeoutError("Query timed out after 30s", timeout_seconds=30)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Check HTTP exception
            assert http_exc.status_code == 408
            assert isinstance(http_exc.detail, dict)
            assert http_exc.detail["error"] == "querytimeout_failed"
            assert http_exc.detail["sql_error_type"] == "timeout"
            assert "Simplify the query" in http_exc.detail["suggestions"]
    
    def test_handle_result_set_too_large_error(self):
        """Test handling of result set too large errors."""
        error = ResultSetTooLargeError("Result set too large", max_rows=10000)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Check HTTP exception
            assert http_exc.status_code == 400
            assert isinstance(http_exc.detail, dict)
            assert http_exc.detail["error"] == "resultsettoolarge_failed"
            assert http_exc.detail["sql_error_type"] == "execution"
    
    def test_handle_sql_schema_error(self):
        """Test handling of SQL schema errors."""
        error = SQLSchemaError("Table 'users' not found", missing_object="users")
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Check HTTP exception
            assert http_exc.status_code == 400
            assert isinstance(http_exc.detail, dict)
            assert http_exc.detail["error"] == "sqlschema_failed"
            assert http_exc.detail["sql_error_type"] == "execution"
    
    def test_handle_concurrent_query_limit_error(self):
        """Test handling of concurrent query limit errors."""
        error = ConcurrentQueryLimitError("Too many concurrent queries", max_concurrent=5)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Check HTTP exception
            assert http_exc.status_code == 429
            assert isinstance(http_exc.detail, dict)
            assert http_exc.detail["error"] == "concurrentquerylimit_failed"
            assert http_exc.detail["sql_error_type"] == "execution"
    
    def test_handle_query_explain_error(self):
        """Test handling of query explain errors."""
        error = QueryExplainError("Failed to explain query")
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Check HTTP exception
            assert http_exc.status_code == 400
            assert "Query explanation failed" in str(http_exc.detail)
    
    def test_create_sql_error_response(self):
        """Test creation of SQL-specific error responses."""
        response = ErrorHandler.create_sql_error_response(
            error="test_error",
            detail="Test error message",
            sql_error_type="syntax",
            position=15,
            suggestions=["Fix syntax", "Check query"]
        )
        
        assert response["error"] == "test_error"
        assert response["detail"] == "Test error message"
        assert response["sql_error_type"] == "syntax"
        assert response["position"] == 15
        assert response["suggestions"] == ["Fix syntax", "Check query"]
    
    def test_create_sql_error_response_minimal(self):
        """Test creation of SQL error response with minimal data."""
        response = ErrorHandler.create_sql_error_response(
            error="test_error",
            detail="Test error message",
            sql_error_type="execution"
        )
        
        assert response["error"] == "test_error"
        assert response["detail"] == "Test error message"
        assert response["sql_error_type"] == "execution"
        assert "position" not in response
        assert "suggestions" not in response


class TestErrorResponseFormatting:
    """Test error response formatting and structure."""
    
    def test_sql_error_response_structure(self):
        """Test that SQL error responses match expected structure."""
        error = SQLSyntaxError("Invalid syntax", position=10)
        
        with patch('src.error_handlers.logger'):
            http_exc = ErrorHandler.handle_exception(error)
            
            # Verify response structure matches SQLErrorResponse model
            response = http_exc.detail
            assert "error" in response
            assert "detail" in response
            assert "sql_error_type" in response
            assert "position" in response
            assert "suggestions" in response
            
            # Verify data types
            assert isinstance(response["error"], str)
            assert isinstance(response["detail"], str)
            assert isinstance(response["sql_error_type"], str)
            assert isinstance(response["position"], int)
            assert isinstance(response["suggestions"], list)
    
    def test_error_response_serialization(self):
        """Test that error responses can be serialized to JSON."""
        import json
        
        error = SQLSecurityError("DDL not allowed", position=5)
        
        with patch('src.error_handlers.logger'), \
             patch('src.logging_config.DashlyLogger'):
            
            http_exc = ErrorHandler.handle_exception(error)
            
            # Should be able to serialize to JSON
            json_str = json.dumps(http_exc.detail)
            parsed = json.loads(json_str)
            
            assert parsed["error"] == "sqlsecurity_failed"
            assert parsed["sql_error_type"] == "security"
            assert parsed["position"] == 5


class TestErrorLogging:
    """Test error logging functionality."""
    
    def test_security_violation_logging(self):
        """Test that security violations are properly logged."""
        error = SQLSecurityError("DDL not allowed", violation_type="ddl_operation")
        
        with patch('src.error_handlers.logger') as mock_logger, \
             patch('src.logging_config.DashlyLogger') as mock_dashly_logger:
            
            ErrorHandler.handle_exception(error, context="test_endpoint")
            
            # Check that security event was logged
            mock_dashly_logger.log_security_event.assert_called_once()
            args = mock_dashly_logger.log_security_event.call_args[0]
            
            # Verify logging parameters
            assert args[1] == "SQL_SECURITY_VIOLATION_ddl_operation"
            assert "SQL security violation" in args[2]
            assert "test_endpoint" in args[2]
    
    def test_general_error_logging(self):
        """Test that general errors are properly logged."""
        error = QueryExecutionError("Database connection failed")
        
        with patch('src.error_handlers.logger') as mock_logger:
            ErrorHandler.handle_exception(error, context="execute_query")
            
            # Check that error was logged
            mock_logger.error.assert_called_once()
            log_message = mock_logger.error.call_args[0][0]
            
            assert "QueryExecutionError" in log_message
            assert "execute_query" in log_message
    
    def test_position_tracking_in_logs(self):
        """Test that position information is preserved in error handling."""
        error = SQLSyntaxError("Missing FROM clause", position=25)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Position should be in the response
            assert http_exc.detail["position"] == 25
    
    def test_suggestions_in_error_response(self):
        """Test that suggestions are included in error responses."""
        custom_suggestions = ["Use proper syntax", "Check documentation"]
        error = SQLSyntaxError("Invalid query", suggestions=custom_suggestions)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Custom suggestions should be in the response
            assert http_exc.detail["suggestions"] == custom_suggestions


class TestErrorHandlerDecorators:
    """Test error handler decorators."""
    
    @pytest.mark.asyncio
    async def test_handle_api_exception_decorator(self):
        """Test the async API exception decorator."""
        from src.error_handlers import handle_api_exception
        
        @handle_api_exception
        async def test_endpoint():
            raise SQLSyntaxError("Test syntax error", position=5)
        
        with patch('src.error_handlers.logger'), \
             pytest.raises(HTTPException) as exc_info:
            
            await test_endpoint()
            
            # Should convert to HTTPException
            assert exc_info.value.status_code == 400
            assert isinstance(exc_info.value.detail, dict)
            assert exc_info.value.detail["sql_error_type"] == "syntax"
    
    def test_handle_sync_api_exception_decorator(self):
        """Test the sync API exception decorator."""
        from src.error_handlers import handle_sync_api_exception
        
        @handle_sync_api_exception
        def test_sync_endpoint():
            raise QueryTimeoutError("Test timeout", timeout_seconds=30)
        
        with patch('src.error_handlers.logger'), \
             pytest.raises(HTTPException) as exc_info:
            
            test_sync_endpoint()
            
            # Should convert to HTTPException
            assert exc_info.value.status_code == 408
            assert isinstance(exc_info.value.detail, dict)
            assert exc_info.value.detail["sql_error_type"] == "timeout"
    
    @pytest.mark.asyncio
    async def test_decorator_preserves_http_exceptions(self):
        """Test that decorators preserve existing HTTPExceptions."""
        from src.error_handlers import handle_api_exception
        from fastapi import HTTPException
        
        @handle_api_exception
        async def test_endpoint():
            raise HTTPException(status_code=404, detail="Not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint()
            
            # Should preserve original HTTPException
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Not found"


class TestErrorScenarios:
    """Test specific error scenarios that might occur in production."""
    
    def test_nested_exception_handling(self):
        """Test handling of nested exceptions."""
        # Simulate a case where a QueryExecutionError wraps another exception
        original_error = ValueError("Invalid parameter")
        wrapped_error = QueryExecutionError(f"Query failed: {str(original_error)}")
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(wrapped_error)
            
            assert http_exc.status_code == 400
            assert "Query failed: Invalid parameter" in http_exc.detail["detail"]
    
    def test_unicode_error_messages(self):
        """Test handling of error messages with unicode characters."""
        error = SQLSyntaxError("Invalid character: 'ñ' at position 10", position=10)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Should handle unicode properly
            assert "ñ" in http_exc.detail["detail"]
            assert http_exc.detail["position"] == 10
    
    def test_very_long_error_messages(self):
        """Test handling of very long error messages."""
        long_message = "A" * 1000  # Very long error message
        error = QueryExecutionError(long_message)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # Should handle long messages without issues
            assert len(http_exc.detail["detail"]) == 1000
    
    def test_none_values_in_error_attributes(self):
        """Test handling of None values in error attributes."""
        error = SQLSyntaxError("Test error", position=None, suggestions=None)
        
        with patch('src.error_handlers.logger') as mock_logger:
            http_exc = ErrorHandler.handle_exception(error)
            
            # None position should not be included in response
            assert "position" not in http_exc.detail or http_exc.detail["position"] is None
            # None suggestions should result in default suggestions
            assert len(http_exc.detail["suggestions"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])