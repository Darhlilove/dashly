"""
Tests for Pydantic models used in SQL execution API.
"""

import pytest
from pydantic import ValidationError
from typing import Any, List
from src.models import (
    ExecuteRequest,
    ExecuteResponse,
    ExplainResponse,
    SQLErrorResponse,
    ParsedQuery,
    SecurityViolation,
    ValidationResult
)


class TestExecuteRequest:
    """Tests for ExecuteRequest model."""
    
    def test_valid_execute_request(self):
        """Test creating a valid ExecuteRequest."""
        request = ExecuteRequest(sql="SELECT * FROM users")
        assert request.sql == "SELECT * FROM users"
    
    def test_execute_request_empty_sql(self):
        """Test ExecuteRequest with empty SQL string."""
        request = ExecuteRequest(sql="")
        assert request.sql == ""
    
    def test_execute_request_missing_sql(self):
        """Test ExecuteRequest validation fails without sql field."""
        with pytest.raises(ValidationError) as exc_info:
            ExecuteRequest()
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("sql",)
    
    def test_execute_request_invalid_type(self):
        """Test ExecuteRequest validation fails with non-string sql."""
        with pytest.raises(ValidationError) as exc_info:
            ExecuteRequest(sql=123)
        
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "string_type"


class TestExecuteResponse:
    """Tests for ExecuteResponse model."""
    
    def test_valid_execute_response(self):
        """Test creating a valid ExecuteResponse."""
        response = ExecuteResponse(
            columns=["id", "name", "email"],
            rows=[[1, "John", "john@example.com"], [2, "Jane", "jane@example.com"]],
            row_count=2,
            runtime_ms=150.5
        )
        
        assert response.columns == ["id", "name", "email"]
        assert len(response.rows) == 2
        assert response.row_count == 2
        assert response.runtime_ms == 150.5
        assert response.truncated is False  # Default value
    
    def test_execute_response_with_truncation(self):
        """Test ExecuteResponse with truncation flag."""
        response = ExecuteResponse(
            columns=["id"],
            rows=[[i] for i in range(100)],
            row_count=10000,
            runtime_ms=500.0,
            truncated=True
        )
        
        assert response.truncated is True
        assert response.row_count == 10000
        assert len(response.rows) == 100
    
    def test_execute_response_empty_results(self):
        """Test ExecuteResponse with empty results."""
        response = ExecuteResponse(
            columns=["count"],
            rows=[],
            row_count=0,
            runtime_ms=25.0
        )
        
        assert len(response.columns) == 1
        assert len(response.rows) == 0
        assert response.row_count == 0
    
    def test_execute_response_missing_required_fields(self):
        """Test ExecuteResponse validation fails without required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ExecuteResponse(columns=["id"])
        
        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "rows" in required_fields
        assert "row_count" in required_fields
        assert "runtime_ms" in required_fields
    
    def test_execute_response_invalid_types(self):
        """Test ExecuteResponse validation with invalid types."""
        with pytest.raises(ValidationError) as exc_info:
            ExecuteResponse(
                columns="not_a_list",
                rows="not_a_list",
                row_count="not_an_int",
                runtime_ms="not_a_float"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 4


class TestExplainResponse:
    """Tests for ExplainResponse model."""
    
    def test_valid_explain_response(self):
        """Test creating a valid ExplainResponse."""
        response = ExplainResponse(
            execution_plan="SEQUENTIAL_SCAN(users)",
            estimated_cost=100.5,
            estimated_rows=1000,
            estimated_runtime_ms=50.0,
            optimization_suggestions=["Add index on user_id", "Consider LIMIT clause"]
        )
        
        assert response.execution_plan == "SEQUENTIAL_SCAN(users)"
        assert response.estimated_cost == 100.5
        assert response.estimated_rows == 1000
        assert response.estimated_runtime_ms == 50.0
        assert len(response.optimization_suggestions) == 2
    
    def test_explain_response_empty_suggestions(self):
        """Test ExplainResponse with empty optimization suggestions."""
        response = ExplainResponse(
            execution_plan="INDEX_SCAN(users_idx)",
            estimated_cost=10.0,
            estimated_rows=100,
            estimated_runtime_ms=5.0,
            optimization_suggestions=[]
        )
        
        assert len(response.optimization_suggestions) == 0
    
    def test_explain_response_missing_fields(self):
        """Test ExplainResponse validation fails without required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ExplainResponse(execution_plan="SCAN")
        
        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "estimated_cost" in required_fields
        assert "estimated_rows" in required_fields
        assert "estimated_runtime_ms" in required_fields
        assert "optimization_suggestions" in required_fields


class TestSQLErrorResponse:
    """Tests for SQLErrorResponse model."""
    
    def test_valid_sql_error_response(self):
        """Test creating a valid SQLErrorResponse."""
        error_response = SQLErrorResponse(
            error="sql_validation_failed",
            detail="DDL operations are not allowed",
            sql_error_type="security",
            position=None,
            suggestions=["Use SELECT statements only"]
        )
        
        assert error_response.error == "sql_validation_failed"
        assert error_response.detail == "DDL operations are not allowed"
        assert error_response.sql_error_type == "security"
        assert error_response.position is None
        assert len(error_response.suggestions) == 1
    
    def test_sql_error_response_with_position(self):
        """Test SQLErrorResponse with syntax error position."""
        error_response = SQLErrorResponse(
            error="syntax_error",
            detail="Unexpected token 'FORM' at position 15",
            sql_error_type="syntax",
            position=15
        )
        
        assert error_response.position == 15
        assert error_response.sql_error_type == "syntax"
        assert error_response.suggestions is None  # Default value
    
    def test_sql_error_response_timeout(self):
        """Test SQLErrorResponse for timeout error."""
        error_response = SQLErrorResponse(
            error="query_timeout",
            detail="Query execution exceeded 30 second limit",
            sql_error_type="timeout"
        )
        
        assert error_response.sql_error_type == "timeout"
    
    def test_sql_error_response_execution_error(self):
        """Test SQLErrorResponse for execution error."""
        error_response = SQLErrorResponse(
            error="table_not_found",
            detail="Table 'invalid_table' does not exist",
            sql_error_type="execution",
            suggestions=["Check available tables with /api/schema"]
        )
        
        assert error_response.sql_error_type == "execution"
        assert "Check available tables" in error_response.suggestions[0]
    
    def test_sql_error_response_missing_required_fields(self):
        """Test SQLErrorResponse validation fails without required fields."""
        with pytest.raises(ValidationError) as exc_info:
            SQLErrorResponse(error="test_error")
        
        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "detail" in required_fields
        assert "sql_error_type" in required_fields


class TestParsedQuery:
    """Tests for ParsedQuery model."""
    
    def test_valid_parsed_query(self):
        """Test creating a valid ParsedQuery."""
        parsed = ParsedQuery(
            query_type="SELECT",
            tables=["users", "orders"],
            columns=["users.name", "orders.total"],
            has_joins=True,
            has_aggregations=False,
            complexity_score=3
        )
        
        assert parsed.query_type == "SELECT"
        assert len(parsed.tables) == 2
        assert len(parsed.columns) == 2
        assert parsed.has_joins is True
        assert parsed.has_aggregations is False
        assert parsed.complexity_score == 3
    
    def test_parsed_query_simple_select(self):
        """Test ParsedQuery for simple SELECT statement."""
        parsed = ParsedQuery(
            query_type="SELECT",
            tables=["users"],
            columns=["*"],
            has_joins=False,
            has_aggregations=False,
            complexity_score=1
        )
        
        assert len(parsed.tables) == 1
        assert parsed.has_joins is False
        assert parsed.complexity_score == 1
    
    def test_parsed_query_with_aggregations(self):
        """Test ParsedQuery with aggregation functions."""
        parsed = ParsedQuery(
            query_type="SELECT",
            tables=["sales"],
            columns=["COUNT(*)", "SUM(amount)", "AVG(price)"],
            has_joins=False,
            has_aggregations=True,
            complexity_score=2
        )
        
        assert parsed.has_aggregations is True
        assert len(parsed.columns) == 3
    
    def test_parsed_query_invalid_types(self):
        """Test ParsedQuery validation with invalid types."""
        with pytest.raises(ValidationError) as exc_info:
            ParsedQuery(
                query_type="SELECT",
                tables="not_a_list",
                columns="not_a_list",
                has_joins="not_a_bool",
                has_aggregations="not_a_bool",
                complexity_score="not_an_int"
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 5


class TestSecurityViolation:
    """Tests for SecurityViolation model."""
    
    def test_valid_security_violation(self):
        """Test creating a valid SecurityViolation."""
        violation = SecurityViolation(
            violation_type="ddl_operation",
            description="CREATE statement detected",
            severity="error",
            position=0
        )
        
        assert violation.violation_type == "ddl_operation"
        assert violation.description == "CREATE statement detected"
        assert violation.severity == "error"
        assert violation.position == 0
    
    def test_security_violation_warning(self):
        """Test SecurityViolation with warning severity."""
        violation = SecurityViolation(
            violation_type="complex_query",
            description="Query has high complexity score",
            severity="warning"
        )
        
        assert violation.severity == "warning"
        assert violation.position is None  # Default value
    
    def test_security_violation_missing_fields(self):
        """Test SecurityViolation validation fails without required fields."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityViolation(violation_type="test")
        
        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "description" in required_fields
        assert "severity" in required_fields


class TestValidationResult:
    """Tests for ValidationResult model."""
    
    def test_valid_validation_result_success(self):
        """Test creating a successful ValidationResult."""
        parsed_query = ParsedQuery(
            query_type="SELECT",
            tables=["users"],
            columns=["*"],
            has_joins=False,
            has_aggregations=False,
            complexity_score=1
        )
        
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            parsed_query=parsed_query,
            security_violations=[]
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.parsed_query is not None
        assert len(result.security_violations) == 0
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult with validation errors."""
        violation = SecurityViolation(
            violation_type="ddl_operation",
            description="DROP statement not allowed",
            severity="error"
        )
        
        result = ValidationResult(
            is_valid=False,
            errors=["DDL operations are prohibited"],
            warnings=[],
            parsed_query=None,
            security_violations=[violation]
        )
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.security_violations) == 1
        assert result.parsed_query is None
    
    def test_validation_result_with_warnings(self):
        """Test ValidationResult with warnings but valid query."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Query complexity is high"],
            parsed_query=None,
            security_violations=[]
        )
        
        assert result.is_valid is True
        assert len(result.warnings) == 1
    
    def test_validation_result_missing_required_fields(self):
        """Test ValidationResult validation fails without required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationResult()
        
        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "is_valid" in required_fields
        assert "errors" in required_fields
        assert "warnings" in required_fields


class TestModelIntegration:
    """Integration tests for model interactions."""
    
    def test_execute_request_to_response_flow(self):
        """Test typical request-response flow."""
        # Create request
        request = ExecuteRequest(sql="SELECT COUNT(*) FROM users")
        
        # Simulate successful response
        response = ExecuteResponse(
            columns=["count"],
            rows=[[42]],
            row_count=1,
            runtime_ms=25.5
        )
        
        assert request.sql == "SELECT COUNT(*) FROM users"
        assert response.columns[0] == "count"
        assert response.rows[0][0] == 42
    
    def test_validation_to_error_response_flow(self):
        """Test validation failure to error response flow."""
        # Create validation violation
        violation = SecurityViolation(
            violation_type="ddl_operation",
            description="CREATE statement detected",
            severity="error",
            position=0
        )
        
        # Create validation result
        validation_result = ValidationResult(
            is_valid=False,
            errors=["DDL operations are not allowed"],
            warnings=[],
            parsed_query=None,
            security_violations=[violation]
        )
        
        # Create error response
        error_response = SQLErrorResponse(
            error="sql_validation_failed",
            detail="DDL operations are not allowed",
            sql_error_type="security",
            suggestions=["Use SELECT statements only"]
        )
        
        assert validation_result.is_valid is False
        assert len(validation_result.security_violations) == 1
        assert error_response.sql_error_type == "security"
    
    def test_parsed_query_complexity_scoring(self):
        """Test ParsedQuery complexity scoring scenarios."""
        # Simple query
        simple = ParsedQuery(
            query_type="SELECT",
            tables=["users"],
            columns=["id", "name"],
            has_joins=False,
            has_aggregations=False,
            complexity_score=1
        )
        
        # Complex query with joins and aggregations
        complex_query = ParsedQuery(
            query_type="SELECT",
            tables=["users", "orders", "products"],
            columns=["users.name", "COUNT(orders.id)", "SUM(products.price)"],
            has_joins=True,
            has_aggregations=True,
            complexity_score=5
        )
        
        assert simple.complexity_score < complex_query.complexity_score
        assert complex_query.has_joins and complex_query.has_aggregations
        assert not (simple.has_joins or simple.has_aggregations)