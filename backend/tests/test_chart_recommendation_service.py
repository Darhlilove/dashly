"""
Tests for the ChartRecommendationService to verify automatic dashboard updates functionality.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chart_recommendation_service import ChartRecommendationService
from models import ExecuteResponse, ChartConfig


class TestChartRecommendationService:
    """Test cases for ChartRecommendationService automatic dashboard updates."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = ChartRecommendationService()
    
    def test_should_create_visualization_with_suitable_data(self):
        """Test that visualization is recommended for suitable data structures."""
        # Create mock query results with suitable data for visualization
        query_results = ExecuteResponse(
            columns=["month", "sales", "region"],
            rows=[
                ["2023-01", 1000, "North"],
                ["2023-02", 1200, "North"],
                ["2023-03", 1100, "South"],
                ["2023-04", 1300, "South"],
            ],
            row_count=4,
            runtime_ms=50.0,
            truncated=False
        )
        
        user_question = "Show me sales by month"
        
        result = self.service.should_create_visualization(query_results, user_question)
        
        assert result is True, "Should recommend visualization for suitable data with visualization keywords"
    
    def test_should_not_create_visualization_for_empty_results(self):
        """Test that no visualization is recommended for empty results."""
        query_results = ExecuteResponse(
            columns=["sales"],
            rows=[],
            row_count=0,
            runtime_ms=10.0,
            truncated=False
        )
        
        user_question = "Show me sales data"
        
        result = self.service.should_create_visualization(query_results, user_question)
        
        assert result is False, "Should not recommend visualization for empty results"
    
    def test_should_not_create_visualization_for_large_datasets(self):
        """Test that no visualization is recommended for very large datasets."""
        # Create large dataset (over 100 rows)
        large_rows = [["value"] for _ in range(150)]
        
        query_results = ExecuteResponse(
            columns=["data"],
            rows=large_rows,
            row_count=150,
            runtime_ms=100.0,
            truncated=False
        )
        
        user_question = "Show me all data"
        
        result = self.service.should_create_visualization(query_results, user_question)
        
        assert result is False, "Should not recommend visualization for very large datasets"
    
    def test_should_create_visualization_for_single_metric(self):
        """Test that visualization is recommended for meaningful single metrics."""
        query_results = ExecuteResponse(
            columns=["total_sales"],
            rows=[[50000]],
            row_count=1,
            runtime_ms=20.0,
            truncated=False
        )
        
        user_question = "What is the total sales?"
        
        result = self.service.should_create_visualization(query_results, user_question)
        
        assert result is True, "Should recommend visualization for meaningful single metrics"
    
    def test_recommend_line_chart_for_time_series(self):
        """Test that line chart is recommended for time series data."""
        query_results = ExecuteResponse(
            columns=["date", "revenue"],
            rows=[
                ["2023-01-01", 1000],
                ["2023-02-01", 1200],
                ["2023-03-01", 1100],
            ],
            row_count=3,
            runtime_ms=30.0,
            truncated=False
        )
        
        user_question = "Show me revenue over time"
        
        chart_config = self.service.recommend_chart_config(query_results, user_question)
        
        assert chart_config is not None, "Should recommend a chart for time series data"
        assert chart_config.type == "line", "Should recommend line chart for time series"
        assert chart_config.x_axis == "date", "Should use date column for x-axis"
        assert chart_config.y_axis == "revenue", "Should use revenue column for y-axis"
    
    def test_recommend_bar_chart_for_categorical_data(self):
        """Test that bar chart is recommended for categorical data."""
        query_results = ExecuteResponse(
            columns=["category", "count"],
            rows=[
                ["Electronics", 50],
                ["Clothing", 30],
                ["Books", 20],
            ],
            row_count=3,
            runtime_ms=25.0,
            truncated=False
        )
        
        user_question = "Show me sales by category"
        
        chart_config = self.service.recommend_chart_config(query_results, user_question)
        
        assert chart_config is not None, "Should recommend a chart for categorical data"
        assert chart_config.type == "bar", "Should recommend bar chart for categorical data"
        assert chart_config.x_axis == "category", "Should use category column for x-axis"
        assert chart_config.y_axis == "count", "Should use count column for y-axis"
    
    def test_recommend_pie_chart_for_distribution(self):
        """Test that pie chart is recommended for distribution questions."""
        query_results = ExecuteResponse(
            columns=["region", "sales"],
            rows=[
                ["North", 40],
                ["South", 35],
                ["East", 15],
                ["West", 10],
            ],
            row_count=4,
            runtime_ms=20.0,
            truncated=False
        )
        
        user_question = "Show me the distribution of sales by region"
        
        chart_config = self.service.recommend_chart_config(query_results, user_question)
        
        assert chart_config is not None, "Should recommend a chart for distribution data"
        assert chart_config.type == "pie", "Should recommend pie chart for distribution questions"
        assert chart_config.x_axis == "region", "Should use region column for x-axis"
        assert chart_config.y_axis == "sales", "Should use sales column for y-axis"
    
    def test_no_recommendation_for_unsuitable_data(self):
        """Test that no chart is recommended for unsuitable data structures."""
        query_results = ExecuteResponse(
            columns=["description", "comments", "notes"],
            rows=[
                ["This is a very long customer description that contains detailed information about the customer", "Additional comments here", "More notes"],
                ["Another very long description with lots of text that makes it unsuitable for charting", "More comments", "Additional notes"],
            ],
            row_count=2,
            runtime_ms=15.0,
            truncated=False
        )
        
        user_question = "Show me customer information"
        
        chart_config = self.service.recommend_chart_config(query_results, user_question)
        
        assert chart_config is None, "Should not recommend chart for text-heavy data with no numeric columns"
    
    def test_generate_chart_title_from_question(self):
        """Test that appropriate chart titles are generated from user questions."""
        test_cases = [
            ("Show me sales by month", "Sales by month"),
            ("What is the total revenue?", "Total revenue"),
            ("Can you show the distribution of customers by region?", "Distribution of customers by region"),
            ("How much did we sell last year?", "How much did we sell last year?"),  # Keep meaningful questions
        ]
        
        for question, expected_title in test_cases:
            query_results = ExecuteResponse(
                columns=["test"],
                rows=[["data"]],
                row_count=1,
                runtime_ms=10.0,
                truncated=False
            )
            
            title = self.service._generate_chart_title(question, query_results)
            assert title == expected_title, f"Expected '{expected_title}' but got '{title}' for question '{question}'"
    
    def test_column_type_detection(self):
        """Test that column types are correctly detected."""
        # Test numeric column detection
        numeric_values = [100, 200, 300, 400]
        assert self.service._is_numeric_column(numeric_values) is True
        
        # Test datetime column detection
        datetime_values = ["2023-01-01", "2023-02-01", "2023-03-01"]
        assert self.service._is_datetime_column(datetime_values) is True
        
        # Test mixed data (should not be numeric or datetime)
        mixed_values = ["text", 123, "2023-01-01"]
        assert self.service._is_numeric_column(mixed_values) is False
        assert self.service._is_datetime_column(mixed_values) is False
    
    def test_suitable_structure_detection(self):
        """Test that suitable data structures for charts are correctly identified."""
        # Suitable structure: numeric + categorical
        suitable_analysis = [
            {"name": "category", "type": "categorical", "unique_count": 3},
            {"name": "value", "type": "numeric", "unique_count": 10},
        ]
        
        result = self.service._has_suitable_structure_for_charts(suitable_analysis)
        assert result is True, "Should identify suitable structure with categorical + numeric"
        
        # Unsuitable structure: all text
        unsuitable_analysis = [
            {"name": "name", "type": "text", "unique_count": 50},
            {"name": "description", "type": "text", "unique_count": 50},
        ]
        
        result = self.service._has_suitable_structure_for_charts(unsuitable_analysis)
        assert result is False, "Should not identify text-only data as suitable for charts"
    
    def test_integration_with_chat_service_workflow(self):
        """Test the complete workflow as it would be used by ChatService."""
        # Simulate a typical chat service workflow
        query_results = ExecuteResponse(
            columns=["month", "sales"],
            rows=[
                ["January", 10000],
                ["February", 12000],
                ["March", 11000],
            ],
            row_count=3,
            runtime_ms=40.0,
            truncated=False
        )
        
        user_question = "Show me monthly sales trends"
        
        # Step 1: Check if visualization should be created
        should_create = self.service.should_create_visualization(query_results, user_question)
        assert should_create is True, "Should recommend visualization for this data"
        
        # Step 2: Get chart recommendation
        chart_config = self.service.recommend_chart_config(query_results, user_question)
        assert chart_config is not None, "Should provide chart configuration"
        assert chart_config.type in ["line", "bar"], "Should recommend appropriate chart type"
        assert chart_config.title is not None, "Should include chart title"
        
        # Verify the chart config is suitable for automatic dashboard updates
        assert hasattr(chart_config, 'x_axis'), "Chart config should have x_axis for dashboard"
        assert hasattr(chart_config, 'y_axis'), "Chart config should have y_axis for dashboard"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])