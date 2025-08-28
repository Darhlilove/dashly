"""
Unit tests for QueryExplainService.

Tests query explanation functionality, cost estimation, execution plan generation,
and optimization suggestions.
"""

import pytest
import duckdb
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# Import the service and related classes
try:
    from backend.src.query_explain_service import (
        QueryExplainService,
        ExplanationResult,
        ExecutionPlan,
        CostEstimate,
        QueryComplexity
    )
    from backend.src.sql_validator import SQLValidator, ValidationResult
    from backend.src.exceptions import QueryExplainError, ValidationError
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from query_explain_service import (
        QueryExplainService,
        ExplanationResult,
        ExecutionPlan,
        CostEstimate,
        QueryComplexity
    )
    from sql_validator import SQLValidator, ValidationResult
    from exceptions import QueryExplainError, ValidationError


class TestQueryExplainService:
    """Test cases for QueryExplainService functionality."""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor
        return mock_conn
    
    @pytest.fixture
    def mock_sql_validator(self):
        """Create a mock SQL validator."""
        validator = Mock(spec=SQLValidator)
        validator.validate_query.return_value = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        return validator
    
    @pytest.fixture
    def explain_service(self, mock_db_connection, mock_sql_validator):
        """Create QueryExplainService instance with mocked dependencies."""
        return QueryExplainService(mock_db_connection, mock_sql_validator)
    
    @pytest.fixture
    def sample_execution_plan(self):
        """Sample execution plan text for testing."""
        return """┌───────────────────────────┐
│         SEQ_SCAN          │
│    ─────────────────────   │
│        Table: users       │
│   Type: Sequential Scan   │
│                           │
│        Projections:       │
│             name          │
│             age           │
│                           │
│          ~1000 Rows       │
└───────────────────────────┘"""
    
    def test_init(self, mock_db_connection, mock_sql_validator):
        """Test QueryExplainService initialization."""
        service = QueryExplainService(mock_db_connection, mock_sql_validator)
        
        assert service.db_connection == mock_db_connection
        assert service.sql_validator == mock_sql_validator
        assert service.base_cost_per_row == 0.001
        assert service.join_cost_multiplier == 2.0
    
    def test_init_with_default_validator(self, mock_db_connection):
        """Test initialization with default SQL validator."""
        with patch('backend.src.query_explain_service.SQLValidator') as mock_validator_class:
            mock_validator_instance = Mock()
            mock_validator_class.return_value = mock_validator_instance
            
            service = QueryExplainService(mock_db_connection)
            
            assert service.db_connection == mock_db_connection
            assert service.sql_validator == mock_validator_instance
            mock_validator_class.assert_called_once()
    
    def test_explain_query_success(self, explain_service, sample_execution_plan):
        """Test successful query explanation."""
        sql = "SELECT name, age FROM users WHERE age > 25"
        
        # Mock the execution plan (DuckDB format: ('physical_plan', 'actual_plan_text'))
        explain_service.db_connection.execute.return_value.fetchall.return_value = [
            ('physical_plan', sample_execution_plan)
        ]
        
        result = explain_service.explain_query(sql)
        
        assert isinstance(result, ExplanationResult)
        assert result.execution_plan == sample_execution_plan
        assert result.estimated_cost > 0
        assert result.estimated_rows > 0
        assert result.estimated_runtime_ms > 0
        assert isinstance(result.optimization_suggestions, list)
        assert len(result.optimization_suggestions) > 0
        
        # Verify SQL validator was called
        explain_service.sql_validator.validate_query.assert_called_once_with(sql)
    
    def test_explain_query_validation_failure(self, explain_service):
        """Test query explanation with validation failure."""
        sql = "DROP TABLE users"
        
        # Mock validation failure
        explain_service.sql_validator.validate_query.return_value = ValidationResult(
            is_valid=False,
            errors=["Only SELECT statements are allowed"],
            warnings=[]
        )
        
        with pytest.raises(ValidationError) as exc_info:
            explain_service.explain_query(sql)
        
        assert "Query validation failed" in str(exc_info.value)
        assert "Only SELECT statements are allowed" in str(exc_info.value)
    
    def test_explain_query_database_error(self, explain_service):
        """Test query explanation with database error."""
        sql = "SELECT * FROM users"
        
        # Mock database error
        explain_service.db_connection.execute.side_effect = Exception("Database connection failed")
        
        with pytest.raises(QueryExplainError) as exc_info:
            explain_service.explain_query(sql)
        
        assert "Failed to explain query" in str(exc_info.value)
    
    def test_get_execution_plan_success(self, explain_service, sample_execution_plan):
        """Test successful execution plan generation."""
        sql = "SELECT name FROM users"
        
        # Mock the EXPLAIN query result (DuckDB format)
        explain_service.db_connection.execute.return_value.fetchall.return_value = [
            ('physical_plan', sample_execution_plan)
        ]
        
        plan = explain_service.get_execution_plan(sql)
        
        assert isinstance(plan, ExecutionPlan)
        assert plan.plan_text == sample_execution_plan
        assert isinstance(plan.operations, list)
        assert isinstance(plan.table_scans, list)
        assert isinstance(plan.joins, list)
        assert isinstance(plan.aggregations, list)
        
        # Verify EXPLAIN query was executed
        expected_explain_sql = f"EXPLAIN {sql}"
        explain_service.db_connection.execute.assert_called_with(expected_explain_sql)
    
    def test_get_execution_plan_with_multiple_rows(self, explain_service):
        """Test execution plan generation with multiple result rows."""
        sql = "SELECT * FROM users"
        
        # Mock multiple rows in EXPLAIN result (DuckDB format)
        plan_rows = [
            ('physical_plan', "┌─────────────────────────────────────┐\n│         PROJECTION                  │\n└─────────────────────────────────────┘")
        ]
        explain_service.db_connection.execute.return_value.fetchall.return_value = plan_rows
        
        plan = explain_service.get_execution_plan(sql)
        
        expected_text = plan_rows[0][1]  # Get the actual plan text from the tuple
        assert plan.plan_text == expected_text
    
    def test_get_execution_plan_database_error(self, explain_service):
        """Test execution plan generation with database error."""
        sql = "SELECT * FROM users"
        
        # Mock database error
        explain_service.db_connection.execute.side_effect = Exception("EXPLAIN failed")
        
        with pytest.raises(QueryExplainError) as exc_info:
            explain_service.get_execution_plan(sql)
        
        assert "Failed to generate execution plan" in str(exc_info.value)
    
    def test_estimate_cost_simple_query(self, explain_service, sample_execution_plan):
        """Test cost estimation for simple query."""
        sql = "SELECT name FROM users"
        
        # Mock execution plan (DuckDB format)
        explain_service.db_connection.execute.return_value.fetchall.return_value = [
            ('physical_plan', sample_execution_plan)
        ]
        
        cost = explain_service.estimate_cost(sql)
        
        assert isinstance(cost, CostEstimate)
        assert cost.estimated_cost > 0
        assert cost.estimated_rows > 0
        assert cost.estimated_runtime_ms > 0
        assert cost.complexity_score >= 1
    
    def test_estimate_cost_complex_query_with_joins(self, explain_service):
        """Test cost estimation for complex query with joins."""
        sql = "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id"
        
        # Mock execution plan with joins (DuckDB format)
        plan_with_joins = """┌───────────────────────────┐
│         HASH_JOIN         │
│    ─────────────────────   │
│        ~5000 Rows         │
└───────────────────────────┘"""
        explain_service.db_connection.execute.return_value.fetchall.return_value = [
            ('physical_plan', plan_with_joins)
        ]
        
        cost = explain_service.estimate_cost(sql)
        
        # Cost should be higher due to join
        assert cost.estimated_cost > 1.0  # Should have join multiplier applied
        assert cost.complexity_score > 1  # Should be more complex
    
    def test_estimate_cost_with_aggregation(self, explain_service):
        """Test cost estimation for query with aggregation."""
        sql = "SELECT COUNT(*) FROM users GROUP BY age"
        
        # Mock execution plan with aggregation (DuckDB format)
        plan_with_agg = """┌───────────────────────────┐
│       HASH_GROUP_BY       │
│    ─────────────────────   │
│         ~100 Rows         │
└───────────────────────────┘"""
        explain_service.db_connection.execute.return_value.fetchall.return_value = [
            ('physical_plan', plan_with_agg)
        ]
        
        cost = explain_service.estimate_cost(sql)
        
        # Cost should include aggregation multiplier
        assert cost.estimated_cost > 0.1  # Should have aggregation cost
        assert cost.complexity_score >= 2  # Should account for aggregation
    
    def test_estimate_cost_error_handling(self, explain_service):
        """Test cost estimation error handling with default values."""
        sql = "SELECT * FROM users"
        
        # Mock error in execution plan
        explain_service.db_connection.execute.side_effect = Exception("Plan failed")
        
        cost = explain_service.estimate_cost(sql)
        
        # Should return default values
        assert cost.estimated_cost == 1.0
        assert cost.estimated_rows == 100
        assert cost.estimated_runtime_ms == 10.0
        assert cost.complexity_score == 1
    
    def test_extract_row_estimate_from_plan(self, explain_service):
        """Test row estimate extraction from execution plan."""
        plan_text = "SEQ_SCAN users ~2500 Rows"
        
        rows = explain_service._extract_row_estimate(plan_text)
        
        assert rows == 2500
    
    def test_extract_row_estimate_no_info(self, explain_service):
        """Test row estimate extraction when no information available."""
        plan_text = "PROJECTION name, age"
        
        rows = explain_service._extract_row_estimate(plan_text)
        
        assert rows == 1000  # Default value
    
    def test_calculate_complexity_score_simple(self, explain_service):
        """Test complexity score calculation for simple query."""
        sql = "SELECT name FROM users"
        plan = ExecutionPlan(
            plan_text="SEQ_SCAN users",
            plan_tree={},
            operations=["seq_scan"],
            table_scans=["users"],
            joins=[],
            aggregations=[]
        )
        
        score = explain_service._calculate_complexity_score(sql, plan)
        
        assert score == 1  # Base score for simple query
    
    def test_calculate_complexity_score_complex(self, explain_service):
        """Test complexity score calculation for complex query."""
        sql = """
        WITH user_stats AS (
            SELECT user_id, COUNT(*) as post_count
            FROM posts
            GROUP BY user_id
        )
        SELECT u.name, us.post_count
        FROM users u
        JOIN user_stats us ON u.id = us.user_id
        WHERE us.post_count > 5
        ORDER BY us.post_count DESC
        """
        
        plan = ExecutionPlan(
            plan_text="Complex plan",
            plan_tree={},
            operations=["hash_join", "hash_group_by", "sort"],
            table_scans=["users", "posts"],
            joins=["hash_join"],
            aggregations=["hash_group_by"]
        )
        
        score = explain_service._calculate_complexity_score(sql, plan)
        
        assert score > 5  # Should be high complexity
    
    def test_extract_operations_from_plan(self, explain_service):
        """Test operation extraction from execution plan."""
        plan_text = """
        HASH_JOIN
        ├── SEQ_SCAN users
        └── HASH_GROUP_BY
            └── SEQ_SCAN posts
        """
        
        operations = explain_service._extract_operations(plan_text)
        
        assert "seq scan" in operations
        assert "hash join" in operations
        assert "hash group by" in operations
    
    def test_extract_table_scans_from_plan(self, explain_service):
        """Test table scan extraction from execution plan."""
        plan_text = """
        SEQ_SCAN users
        SEQ_SCAN posts
        """
        
        scans = explain_service._extract_table_scans(plan_text)
        
        assert "users" in scans
        assert "posts" in scans
        assert len(scans) == 2
    
    def test_extract_joins_from_plan(self, explain_service):
        """Test join extraction from execution plan."""
        plan_text = """
        HASH_JOIN
        NESTED_LOOP_JOIN
        """
        
        joins = explain_service._extract_joins(plan_text)
        
        assert "hash join" in joins
        assert "nested loop join" in joins
    
    def test_extract_aggregations_from_plan(self, explain_service):
        """Test aggregation extraction from execution plan."""
        plan_text = """
        HASH_GROUP_BY
        AGGREGATE
        WINDOW
        """
        
        aggregations = explain_service._extract_aggregations(plan_text)
        
        assert "hash group by" in aggregations
        assert "aggregate" in aggregations
        assert "window" in aggregations
    
    def test_generate_optimization_suggestions_high_cost(self, explain_service):
        """Test optimization suggestions for high-cost query."""
        sql = "SELECT * FROM large_table"
        
        plan = ExecutionPlan(
            plan_text="SEQ_SCAN large_table",
            plan_tree={},
            operations=["seq_scan"],
            table_scans=["large_table"],
            joins=[],
            aggregations=[]
        )
        
        cost = CostEstimate(
            estimated_cost=150.0,  # High cost
            estimated_rows=50000,  # Large result set
            estimated_runtime_ms=2000.0,  # Slow query
            complexity_score=3
        )
        
        suggestions = explain_service._generate_optimization_suggestions(sql, plan, cost)
        
        assert any("WHERE clauses" in s for s in suggestions)
        assert any("LIMIT" in s for s in suggestions)
        assert any("SELECT *" in s for s in suggestions)
        assert any("significant time" in s for s in suggestions)
    
    def test_generate_optimization_suggestions_multiple_joins(self, explain_service):
        """Test optimization suggestions for query with multiple joins."""
        sql = "SELECT * FROM a JOIN b ON a.id = b.a_id JOIN c ON b.id = c.b_id JOIN d ON c.id = d.c_id"
        
        plan = ExecutionPlan(
            plan_text="Multiple joins",
            plan_tree={},
            operations=["hash_join", "hash_join", "hash_join"],
            table_scans=["a", "b", "c", "d"],
            joins=["hash_join", "hash_join", "hash_join"],
            aggregations=[]
        )
        
        cost = CostEstimate(
            estimated_cost=50.0,
            estimated_rows=1000,
            estimated_runtime_ms=500.0,
            complexity_score=8
        )
        
        suggestions = explain_service._generate_optimization_suggestions(sql, plan, cost)
        
        assert any("Multiple joins" in s for s in suggestions)
        assert any("indexing" in s for s in suggestions)
        assert any("High complexity" in s for s in suggestions)
    
    def test_generate_optimization_suggestions_well_optimized(self, explain_service):
        """Test optimization suggestions for well-optimized query."""
        sql = "SELECT name FROM users WHERE id = 123"
        
        plan = ExecutionPlan(
            plan_text="Simple scan",
            plan_tree={},
            operations=["seq_scan"],
            table_scans=["users"],
            joins=[],
            aggregations=[]
        )
        
        cost = CostEstimate(
            estimated_cost=0.1,
            estimated_rows=1,
            estimated_runtime_ms=5.0,
            complexity_score=1
        )
        
        suggestions = explain_service._generate_optimization_suggestions(sql, plan, cost)
        
        assert any("well-optimized" in s for s in suggestions)
    
    def test_create_plan_tree(self, explain_service):
        """Test plan tree creation."""
        plan_text = "SEQ_SCAN users\nPROJECTION name, age"
        operations = ["seq_scan", "projection"]
        
        tree = explain_service._create_plan_tree(plan_text, operations)
        
        assert tree["root"] == "query_execution"
        assert tree["operations"] == operations
        assert tree["estimated_complexity"] == len(operations)
        assert "plan_summary" in tree


class TestQueryExplainServiceIntegration:
    """Integration tests with real DuckDB connection."""
    
    @pytest.fixture
    def real_db_connection(self):
        """Create a real DuckDB connection for integration tests."""
        conn = duckdb.connect(":memory:")
        
        # Create test table
        conn.execute("""
            CREATE TABLE test_users (
                id INTEGER,
                name VARCHAR,
                age INTEGER,
                city VARCHAR
            )
        """)
        
        # Insert test data
        conn.execute("""
            INSERT INTO test_users VALUES
            (1, 'Alice', 25, 'New York'),
            (2, 'Bob', 30, 'San Francisco'),
            (3, 'Charlie', 35, 'Chicago'),
            (4, 'Diana', 28, 'Boston'),
            (5, 'Eve', 32, 'Seattle')
        """)
        
        return conn
    
    @pytest.fixture
    def integration_service(self, real_db_connection):
        """Create QueryExplainService with real database connection."""
        return QueryExplainService(real_db_connection)
    
    def test_explain_simple_select(self, integration_service):
        """Test explaining a simple SELECT query with real database."""
        sql = "SELECT name, age FROM test_users WHERE age > 25"
        
        result = integration_service.explain_query(sql)
        
        assert isinstance(result, ExplanationResult)
        assert len(result.execution_plan) > 0
        assert result.estimated_cost > 0
        assert result.estimated_rows > 0
        assert len(result.optimization_suggestions) > 0
    
    def test_explain_join_query(self, integration_service):
        """Test explaining a JOIN query with real database."""
        # Create second table for join
        integration_service.db_connection.execute("""
            CREATE TABLE test_orders (
                id INTEGER,
                user_id INTEGER,
                amount DECIMAL
            )
        """)
        
        integration_service.db_connection.execute("""
            INSERT INTO test_orders VALUES
            (1, 1, 100.50),
            (2, 2, 75.25),
            (3, 1, 200.00)
        """)
        
        sql = """
        SELECT u.name, SUM(o.amount) as total
        FROM test_users u
        JOIN test_orders o ON u.id = o.user_id
        GROUP BY u.name
        """
        
        result = integration_service.explain_query(sql)
        
        assert isinstance(result, ExplanationResult)
        # Check that the plan contains join-related information or that complexity increased
        plan_lower = result.execution_plan.lower()
        has_join_info = ("join" in plan_lower or "hash" in plan_lower or 
                        "nested" in plan_lower or len(result.plan_details.joins) > 0)
        assert has_join_info or result.cost_details.complexity_score > 1
        assert result.cost_details.complexity_score > 1  # Should be more complex due to join and aggregation
    
    def test_cost_estimation_accuracy(self, integration_service):
        """Test that cost estimation provides reasonable values."""
        sql = "SELECT * FROM test_users"
        
        cost = integration_service.estimate_cost(sql)
        
        assert cost.estimated_cost > 0
        assert cost.estimated_rows >= 5  # We inserted 5 rows
        assert cost.estimated_runtime_ms > 0
        assert cost.complexity_score >= 1
    
    def test_optimization_suggestions_relevance(self, integration_service):
        """Test that optimization suggestions are relevant to the query."""
        sql = "SELECT * FROM test_users WHERE age > 20 ORDER BY name"
        
        result = integration_service.explain_query(sql)
        
        suggestions = result.optimization_suggestions
        assert len(suggestions) > 0
        
        # Should suggest avoiding SELECT *
        assert any("SELECT *" in s for s in suggestions)


if __name__ == "__main__":
    pytest.main([__file__])