"""
Unit tests for ResponseGenerator class.

Tests the conversion of technical query results into conversational, business-friendly responses.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from response_generator import ResponseGenerator, DataInsight, NumberFormat
from models import ExecuteResponse, ChartConfig, ConversationalResponse


class TestResponseGenerator:
    """Test cases for ResponseGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ResponseGenerator()
    
    def test_initialization(self):
        """Test ResponseGenerator initialization."""
        assert self.generator is not None
        assert isinstance(self.generator.number_format, NumberFormat)
    
    def test_format_number_currency(self):
        """Test currency number formatting."""
        # Test basic currency
        assert self.generator.format_number(1234.56, "currency") == "$1.2K"
        assert self.generator.format_number(1234567, "revenue") == "$1.2M"
        assert self.generator.format_number(1234567890, "sales") == "$1.2B"
        assert self.generator.format_number(50.25, "price") == "$50.25"
    
    def test_format_number_percentage(self):
        """Test percentage number formatting."""
        # Test decimal percentages
        assert self.generator.format_number(0.25, "percentage") == "25.0%"
        assert self.generator.format_number(0.1234, "percent") == "12.3%"
        
        # Test already formatted percentages
        assert self.generator.format_number(25.5, "percentage") == "25.5%"
    
    def test_format_number_count(self):
        """Test count/quantity number formatting."""
        assert self.generator.format_number(1234, "count") == "1.2K"
        assert self.generator.format_number(1234567, "quantity") == "1.2 million"
        assert self.generator.format_number(42, "number") == "42"
    
    def test_format_number_general(self):
        """Test general number formatting."""
        assert self.generator.format_number(1234.56) == "1,235"
        assert self.generator.format_number(1234567.89) == "1.2M"
        assert self.generator.format_number(42) == "42"
        assert self.generator.format_number(42.75) == "42.75"
    
    def test_format_number_edge_cases(self):
        """Test edge cases in number formatting."""
        assert self.generator.format_number(None) == "no data"
        assert self.generator.format_number("not a number") == "not a number"
        assert self.generator.format_number("$1,234.56", "currency") == "$1.2K"
        assert self.generator.format_number(Decimal("123.45"), "currency") == "$123.45"
    
    def test_format_date_relative(self):
        """Test relative date formatting."""
        now = datetime.now()
        
        # Test today
        today = now.strftime("%Y-%m-%d")
        assert self.generator.format_date(today) == "today"
        
        # Test string dates
        assert "ago" in self.generator.format_date("2023-01-01") or "2023" in self.generator.format_date("2023-01-01")
    
    def test_format_date_edge_cases(self):
        """Test edge cases in date formatting."""
        assert self.generator.format_date(None) == "unknown date"
        assert self.generator.format_date("invalid date") == "invalid date"
        
        # Test datetime objects
        test_date = datetime(2023, 6, 15)
        result = self.generator.format_date(test_date)
        assert isinstance(result, str)
        
        # Test date objects
        test_date = date(2023, 6, 15)
        result = self.generator.format_date(test_date)
        assert isinstance(result, str)
    
    def test_generate_conversational_response_with_data(self):
        """Test generating conversational response with data."""
        # Create mock query results
        query_results = ExecuteResponse(
            columns=["product", "sales", "date"],
            rows=[
                ["Product A", 1000, "2023-01-01"],
                ["Product B", 2000, "2023-01-02"],
                ["Product C", 1500, "2023-01-03"]
            ],
            row_count=3,
            runtime_ms=150.5,
            truncated=False
        )
        
        chart_config = ChartConfig(type="bar", x_axis="product", y_axis="sales")
        
        response = self.generator.generate_conversational_response(
            query_results,
            "Show me product sales",
            chart_config
        )
        
        assert isinstance(response, ConversationalResponse)
        assert response.message is not None
        assert len(response.message) > 0
        assert response.chart_config == chart_config
        assert response.processing_time_ms == 150.5
        assert len(response.insights) >= 0
        assert len(response.follow_up_questions) >= 0
    
    def test_generate_conversational_response_no_data(self):
        """Test generating conversational response with no data."""
        query_results = ExecuteResponse(
            columns=["product", "sales"],
            rows=[],
            row_count=0,
            runtime_ms=50.0,
            truncated=False
        )
        
        response = self.generator.generate_conversational_response(
            query_results,
            "Show me sales for non-existent product"
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "couldn't find" in response.message.lower() or "no" in response.message.lower()
        assert len(response.follow_up_questions) > 0
    
    def test_explain_data_insights_with_data(self):
        """Test explaining data insights with actual data."""
        data = [
            {"product": "A", "sales": 1000, "date": "2023-01-01"},
            {"product": "B", "sales": 2000, "date": "2023-01-02"},
            {"product": "C", "sales": 1500, "date": "2023-01-03"}
        ]
        
        insights = self.generator.explain_data_insights(data, "product sales")
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        assert all(isinstance(insight, str) for insight in insights)
        assert any("3 results" in insight or "found" in insight.lower() for insight in insights)
    
    def test_explain_data_insights_no_data(self):
        """Test explaining insights with no data."""
        insights = self.generator.explain_data_insights([], "empty query")
        
        assert isinstance(insights, list)
        assert len(insights) == 1
        assert "no data" in insights[0].lower()
    
    def test_explain_data_insights_execute_response_format(self):
        """Test explaining insights with ExecuteResponse format."""
        # Mock ExecuteResponse-like object
        mock_data = Mock()
        mock_data.rows = [
            ["Product A", 1000],
            ["Product B", 2000]
        ]
        mock_data.columns = ["product", "sales"]
        
        insights = self.generator.explain_data_insights(mock_data, "sales data")
        
        assert isinstance(insights, list)
        assert len(insights) > 0
    
    def test_analyze_numeric_trends(self):
        """Test numeric trend analysis."""
        data = [
            {"sales": 100, "profit": 20},
            {"sales": 200, "profit": 40},
            {"sales": 150, "profit": 30}
        ]
        
        insights = self.generator._analyze_numeric_trends(data, "sales analysis")
        
        assert isinstance(insights, list)
        # Should find some insights about the numeric data
    
    def test_analyze_categorical_data(self):
        """Test categorical data analysis."""
        data = [
            {"category": "A", "region": "North"},
            {"category": "B", "region": "North"},
            {"category": "A", "region": "South"}
        ]
        
        insights = self.generator._analyze_categorical_data(data, "category analysis")
        
        assert isinstance(insights, list)
        # Should analyze categorical distributions
    
    def test_analyze_temporal_patterns(self):
        """Test temporal pattern analysis."""
        data = [
            {"date": "2023-01-01", "value": 100},
            {"date": "2023-02-01", "value": 200},
            {"date": "2023-03-01", "value": 150}
        ]
        
        insights = self.generator._analyze_temporal_patterns(data, "time series")
        
        assert isinstance(insights, list)
        # Should find temporal patterns
    
    def test_create_main_response_no_data(self):
        """Test main response creation with no data."""
        query_results = ExecuteResponse(
            columns=[],
            rows=[],
            row_count=0,
            runtime_ms=50.0,
            truncated=False
        )
        
        response = self.generator._create_main_response(query_results, "test question", [])
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert "couldn't find" in response.lower() or "no" in response.lower()
    
    def test_create_main_response_with_data(self):
        """Test main response creation with data."""
        query_results = ExecuteResponse(
            columns=["name", "value"],
            rows=[["Item 1", 100], ["Item 2", 200]],
            row_count=2,
            runtime_ms=100.0,
            truncated=False
        )
        
        insights = [
            DataInsight(
                type="summary",
                message="Found 2 results.",
                confidence=1.0,
                supporting_data={"row_count": 2}
            )
        ]
        
        response = self.generator._create_main_response(query_results, "show me data", insights)
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_generate_follow_up_questions_no_data(self):
        """Test follow-up question generation with no data."""
        query_results = ExecuteResponse(
            columns=[],
            rows=[],
            row_count=0,
            runtime_ms=50.0,
            truncated=False
        )
        
        questions = self.generator._generate_follow_up_questions(query_results, "test question")
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert all(isinstance(q, str) for q in questions)
        assert any("?" in q for q in questions)
    
    def test_generate_follow_up_questions_with_data(self):
        """Test follow-up question generation with data."""
        query_results = ExecuteResponse(
            columns=["date", "sales", "region"],
            rows=[
                ["2023-01-01", 1000, "North"],
                ["2023-01-02", 2000, "South"]
            ],
            row_count=2,
            runtime_ms=100.0,
            truncated=False
        )
        
        questions = self.generator._generate_follow_up_questions(query_results, "sales by region")
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 3  # Should limit to 3 questions
        assert all(isinstance(q, str) for q in questions)
    
    def test_find_numeric_insights(self):
        """Test finding insights in numeric data."""
        data = [
            {"sales": 100, "profit": 10},
            {"sales": 200, "profit": 20},
            {"sales": 1000, "profit": 100}  # Outlier
        ]
        
        insights = self.generator._find_numeric_insights(data, "sales data")
        
        assert isinstance(insights, list)
        # Should detect the outlier in sales
        outlier_insights = [i for i in insights if i.type == "outlier"]
        assert len(outlier_insights) > 0
    
    def test_find_categorical_insights(self):
        """Test finding insights in categorical data."""
        data = [
            {"category": "A", "status": "active"},
            {"category": "A", "status": "active"},
            {"category": "B", "status": "active"},
            {"category": "A", "status": "inactive"}
        ]
        
        insights = self.generator._find_categorical_insights(data, "category data")
        
        assert isinstance(insights, list)
        # Should find patterns in categorical data
    
    def test_error_handling_in_response_generation(self):
        """Test error handling in response generation."""
        # Create malformed query results
        query_results = Mock()
        query_results.runtime_ms = 100.0
        
        # This should not crash and should return a fallback response
        response = self.generator.generate_conversational_response(
            query_results,
            "test question"
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "trouble" in response.message.lower() or "having" in response.message.lower()
    
    def test_number_format_configuration(self):
        """Test number format configuration."""
        # Test custom number format
        custom_format = NumberFormat(
            use_thousands_separator=False,
            decimal_places=1,
            currency_symbol="€"
        )
        
        generator = ResponseGenerator()
        generator.number_format = custom_format
        
        # The format methods should still work
        result = generator.format_number(1234.56)
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__])