"""
Integration tests for QueryExecutor with actual DuckDB.

Tests query execution against real DuckDB database with sample data.
"""

import pytest
import tempfile
import os
import duckdb
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from query_executor import QueryExecutor, QueryResult
from exceptions import QueryExecutionError, QueryTimeoutError


class TestQueryExecutorIntegration:
    """Integration tests with real DuckDB database."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        # Create a temporary directory and file path
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.duckdb')
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
    
    @pytest.fixture
    def db_connection(self, temp_db_path):
        """Create DuckDB connection with sample data."""
        conn = duckdb.connect(temp_db_path)
        
        # Create sample table with test data
        conn.execute("""
            CREATE TABLE sales (
                id INTEGER,
                product VARCHAR,
                quantity INTEGER,
                price DECIMAL(10,2),
                sale_date DATE
            )
        """)
        
        # Insert sample data
        conn.execute("""
            INSERT INTO sales VALUES
            (1, 'Widget A', 10, 25.50, '2023-01-15'),
            (2, 'Widget B', 5, 45.00, '2023-01-16'),
            (3, 'Widget C', 8, 30.75, '2023-01-17'),
            (4, 'Widget A', 15, 25.50, '2023-01-18'),
            (5, 'Widget B', 3, 45.00, '2023-01-19')
        """)
        
        yield conn
        conn.close()
    
    @pytest.fixture
    def query_executor(self, db_connection):
        """Create QueryExecutor with real DuckDB connection."""
        return QueryExecutor(db_connection, timeout_seconds=30, max_rows=1000)
    
    def test_execute_simple_select(self, query_executor):
        """Test executing simple SELECT query."""
        sql = "SELECT id, product, quantity FROM sales WHERE id <= 3"
        
        result = query_executor.execute_query(sql)
        
        assert isinstance(result, QueryResult)
        assert result.columns == ['id', 'product', 'quantity']
        assert result.row_count == 3
        assert result.rows[0] == [1, 'Widget A', 10]
        assert result.rows[1] == [2, 'Widget B', 5]
        assert result.rows[2] == [3, 'Widget C', 8]
        assert result.runtime_ms > 0
        assert not result.truncated
    
    def test_execute_aggregation_query(self, query_executor):
        """Test executing query with aggregation."""
        sql = "SELECT product, SUM(quantity) as total_qty, AVG(price) as avg_price FROM sales GROUP BY product ORDER BY product"
        
        result = query_executor.execute_query(sql)
        
        assert result.columns == ['product', 'total_qty', 'avg_price']
        assert result.row_count == 3
        
        # Check Widget A aggregation
        widget_a_row = next(row for row in result.rows if row[0] == 'Widget A')
        assert widget_a_row[1] == 25  # total quantity: 10 + 15
        assert widget_a_row[2] == 25.5  # average price
    
    def test_execute_join_query(self, query_executor, db_connection):
        """Test executing query with JOIN."""
        # Create another table for join
        db_connection.execute("""
            CREATE TABLE products (
                name VARCHAR,
                category VARCHAR
            )
        """)
        
        db_connection.execute("""
            INSERT INTO products VALUES
            ('Widget A', 'Electronics'),
            ('Widget B', 'Electronics'),
            ('Widget C', 'Tools')
        """)
        
        sql = """
            SELECT s.product, p.category, SUM(s.quantity) as total_qty
            FROM sales s
            JOIN products p ON s.product = p.name
            GROUP BY s.product, p.category
            ORDER BY s.product
        """
        
        result = query_executor.execute_query(sql)
        
        assert result.columns == ['product', 'category', 'total_qty']
        assert result.row_count == 3
        
        # Verify join results
        widget_a_row = next(row for row in result.rows if row[0] == 'Widget A')
        assert widget_a_row[1] == 'Electronics'
        assert widget_a_row[2] == 25
    
    def test_execute_with_date_functions(self, query_executor):
        """Test executing query with date functions."""
        sql = """
            SELECT 
                EXTRACT(year FROM sale_date) as year,
                EXTRACT(month FROM sale_date) as month,
                COUNT(*) as sales_count
            FROM sales
            GROUP BY EXTRACT(year FROM sale_date), EXTRACT(month FROM sale_date)
        """
        
        result = query_executor.execute_query(sql)
        
        assert result.columns == ['year', 'month', 'sales_count']
        assert result.row_count == 1  # All sales in 2023-01
        assert result.rows[0] == [2023, 1, 5]
    
    def test_execute_with_limits_truncation(self, query_executor):
        """Test query execution with result truncation."""
        sql = "SELECT * FROM sales"
        
        result = query_executor.execute_with_limits(sql, max_rows=3)
        
        assert result.row_count == 3
        assert result.truncated
        assert len(result.rows) == 3
    
    def test_execute_with_limits_no_truncation(self, query_executor):
        """Test query execution without truncation."""
        sql = "SELECT * FROM sales"
        
        result = query_executor.execute_with_limits(sql, max_rows=10)
        
        assert result.row_count == 5  # All 5 rows
        assert not result.truncated
        assert len(result.rows) == 5
    
    def test_execute_empty_result_set(self, query_executor):
        """Test executing query that returns no results."""
        sql = "SELECT * FROM sales WHERE id > 1000"
        
        result = query_executor.execute_query(sql)
        
        assert result.row_count == 0
        assert len(result.rows) == 0
        assert len(result.columns) == 5  # All columns from sales table
        assert not result.truncated
    
    def test_execute_syntax_error(self, query_executor):
        """Test executing query with syntax error."""
        sql = "SELCT * FROM sales"  # Typo in SELECT
        
        with pytest.raises(QueryExecutionError) as exc_info:
            query_executor.execute_query(sql)
        
        assert "Query execution failed" in str(exc_info.value)
    
    def test_execute_table_not_found(self, query_executor):
        """Test executing query against non-existent table."""
        sql = "SELECT * FROM non_existent_table"
        
        with pytest.raises(QueryExecutionError) as exc_info:
            query_executor.execute_query(sql)
        
        assert "Query execution failed" in str(exc_info.value)
    
    def test_execute_column_not_found(self, query_executor):
        """Test executing query with non-existent column."""
        sql = "SELECT non_existent_column FROM sales"
        
        with pytest.raises(QueryExecutionError) as exc_info:
            query_executor.execute_query(sql)
        
        assert "Query execution failed" in str(exc_info.value)
    
    def test_execute_complex_query(self, query_executor):
        """Test executing complex query with subqueries and window functions."""
        sql = """
            SELECT 
                product,
                quantity,
                price,
                ROW_NUMBER() OVER (PARTITION BY product ORDER BY sale_date) as row_num,
                AVG(price) OVER (PARTITION BY product) as avg_product_price
            FROM sales
            WHERE quantity > (SELECT AVG(quantity) FROM sales)
            ORDER BY product, sale_date
        """
        
        result = query_executor.execute_query(sql)
        
        assert result.columns == ['product', 'quantity', 'price', 'row_num', 'avg_product_price']
        assert result.row_count > 0
        assert result.runtime_ms > 0
    
    def test_execute_with_null_values(self, query_executor, db_connection):
        """Test executing query that handles NULL values."""
        # Insert row with NULL values
        db_connection.execute("""
            INSERT INTO sales VALUES (6, NULL, NULL, NULL, NULL)
        """)
        
        sql = """
            SELECT 
                id,
                COALESCE(product, 'Unknown') as product,
                COALESCE(quantity, 0) as quantity,
                COALESCE(price, 0.0) as price
            FROM sales
            WHERE id = 6
        """
        
        result = query_executor.execute_query(sql)
        
        assert result.row_count == 1
        assert result.rows[0] == [6, 'Unknown', 0, '0.00']
    
    def test_execute_performance_timing(self, query_executor):
        """Test that query execution timing is accurate."""
        # Execute a simple query and verify timing
        sql = "SELECT COUNT(*) FROM sales"
        
        import time
        start_time = time.time()
        result = query_executor.execute_query(sql)
        end_time = time.time()
        
        actual_runtime_ms = (end_time - start_time) * 1000
        
        # Runtime should be reasonably close to actual time
        # Allow for some variance due to overhead
        assert result.runtime_ms <= actual_runtime_ms + 50  # 50ms tolerance
        assert result.runtime_ms > 0
    
    def test_execute_with_existing_limit_clause(self, query_executor):
        """Test query execution when SQL already contains LIMIT."""
        sql = "SELECT * FROM sales LIMIT 2"
        
        result = query_executor.execute_with_limits(sql, max_rows=10)
        
        # Should respect the existing LIMIT of 2
        assert result.row_count == 2
        assert not result.truncated
    
    def test_format_results_with_real_data(self, query_executor):
        """Test result formatting with real DuckDB data types."""
        sql = """
            SELECT 
                id,
                product,
                quantity,
                price,
                sale_date,
                CAST(price * quantity as DECIMAL(10,2)) as total_value
            FROM sales
            WHERE id = 1
        """
        
        result = query_executor.execute_query(sql)
        
        assert result.columns == ['id', 'product', 'quantity', 'price', 'sale_date', 'total_value']
        assert result.row_count == 1
        
        row = result.rows[0]
        assert row[0] == 1  # id
        assert row[1] == 'Widget A'  # product
        assert row[2] == 10  # quantity
        assert row[3] == '25.50'  # price (DuckDB returns DECIMAL as string)
        assert '2023-01-15' in str(row[4])  # sale_date (formatted as string)
        assert row[5] == '255.00'  # total_value (DuckDB returns DECIMAL as string)


if __name__ == "__main__":
    pytest.main([__file__])