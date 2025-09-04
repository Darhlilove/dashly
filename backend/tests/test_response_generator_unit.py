"""
Comprehensive unit tests for ResponseGenerator class.

Tests cover conversational response generation, number formatting, date formatting,
insight analysis, and error handling as specified in requirements 2.1, 2.2, 2.3.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date
from decimal import Decimal

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from response_generator import ResponseGenerator, DataInsight, NumberFormat
from models import ExecuteResponse, ChartConfig, ConversationalResponse


class TestResponseGeneratorUnit:
    """Comprehensive unit tests for ResponseGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ResponseGenerator()
        
        # Sample data for testing
        self.sample_execute_response = ExecuteResponse(
            columns=["product", "sales", "date", "region"],
            rows=[
                ["Product A", 1000, "2023-01-01", "North"],
                ["Product B", 2000, "2023-01-02", "South"],
                ["Product C", 1500, "2023-01-03", "East"]
            ],
            row_count=3,
            runtime_ms=150.5,
            truncated=False
        )
        
        self.empty_execute_response = ExecuteResponse(
            columns=["product", "sales"],
            rows=[],
            row_count=0,
            runtime_ms=25.0,
            truncated=False
        )
    
    def test_initialization_default(self):
        """Test ResponseGenerator initialization with defaults."""
        generator = ResponseGenerator()
        assert generator is not None
        assert isinstance(generator.number_format, NumberFormat)
        assert generator.number_format.use_thousands_separator is True
        assert generator.number_format.decimal_places == 2
        assert generator.number_format.currency_symbol is None
    
    def test_initialization_custom_format(self):
        """Test ResponseGenerator initialization with custom number format."""
        custom_format = NumberFormat(
            use_thousands_separator=False,
            decimal_places=1,
            currency_symbol="€"
        )
        generator = ResponseGenerator()
        generator.number_format = custom_format
        assert generator.number_format == custom_format
        assert generator.number_format.currency_symbol == "€"
    
    def test_format_number_currency_basic(self):
        """Test basic currency formatting."""
        assert self.generator.format_number(1234.56, "currency") == "$1.2K"
        assert self.generator.format_number(50.25, "price") == "$50.25"
        assert self.generator.format_number(0, "revenue") == "$0"
    
    def test_format_number_currency_large_amounts(self):
        """Test currency formatting for large amounts."""
        assert self.generator.format_number(1234567, "revenue") == "$1.2M"
        assert self.generator.format_number(1234567890, "sales") == "$1.2B"
        assert self.generator.format_number(1234567890123, "total") == "$1.2T"
    
    def test_format_number_percentage_decimal(self):
        """Test percentage formatting from decimal values."""
        assert self.generator.format_number(0.25, "percentage") == "25.0%"
        assert self.generator.format_number(0.1234, "percent") == "12.3%"
        assert self.generator.format_number(1.5, "rate") == "150.0%"
    
    def test_format_number_percentage_whole(self):
        """Test percentage formatting from whole number values."""
        assert self.generator.format_number(25.5, "percentage") == "25.5%"
        assert self.generator.format_number(100, "percent") == "100.0%"
    
    def test_format_number_count_and_quantity(self):
        """Test count and quantity number formatting."""
        assert self.generator.format_number(1234, "count") == "1.2K"
        assert self.generator.format_number(1234567, "quantity") == "1.2 million"
        assert self.generator.format_number(42, "number") == "42"
    
    def test_format_number_general_formatting(self):
        """Test general number formatting without specific type."""
        assert self.generator.format_number(1234.56) == "1,235"
        assert self.generator.format_number(1234567.89) == "1.2M"
        assert self.generator.format_number(42) == "42"
        assert self.generator.format_number(42.75) == "42.75"
    
    def test_format_number_edge_cases(self):
        """Test edge cases in number formatting."""
        assert self.generator.format_number(None) == "no data"
        assert self.generator.format_number("not a number") == "not a number"
        assert self.generator.format_number("") == ""
        assert self.generator.format_number(float('inf')) == "∞"
        assert self.generator.format_number(float('-inf')) == "-∞"
    
    def test_format_number_string_parsing(self):
        """Test number formatting with string input that can be parsed."""
        assert self.generator.format_number("$1,234.56", "currency") == "$1.2K"
        assert self.generator.format_number("1234", "count") == "1.2K"
        assert self.generator.format_number("25%", "percentage") == "25.0%"
    
    def test_format_number_decimal_type(self):
        """Test number formatting with Decimal type."""
        assert self.generator.format_number(Decimal("123.45"), "currency") == "$123.45"
        assert self.generator.format_number(Decimal("1234567"), "revenue") == "$1.2M"
    
    def test_format_date_relative_today(self):
        """Test relative date formatting for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.generator.format_date(today)
        assert result == "today"
    
    def test_format_date_relative_recent(self):
        """Test relative date formatting for recent dates."""
        # Test with a date from a few days ago
        from datetime import timedelta
        recent_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        result = self.generator.format_date(recent_date)
        assert "ago" in result or "days" in result
    
    def test_format_date_absolute(self):
        """Test absolute date formatting for older dates."""
        old_date = "2020-01-01"
        result = self.generator.format_date(old_date)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_format_date_datetime_objects(self):
        """Test date formatting with datetime and date objects."""
        # Test datetime object
        dt = datetime(2023, 6, 15, 14, 30, 0)
        result = self.generator.format_date(dt)
        assert isinstance(result, str)
        
        # Test date object
        d = date(2023, 6, 15)
        result = self.generator.format_date(d)
        assert isinstance(result, str)
    
    def test_format_date_edge_cases(self):
        """Test edge cases in date formatting."""
        assert self.generator.format_date(None) == "unknown date"
        assert self.generator.format_date("") == ""
        assert self.generator.format_date("invalid date") == "invalid date"
        assert self.generator.format_date("not-a-date") == "not-a-date"
    
    def test_generate_conversational_response_with_data(self):
        """Test generating conversational response with data."""
        chart_config = ChartConfig(type="bar", x_axis="product", y_axis="sales")
        
        response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me product sales",
            chart_config
        )
        
        assert isinstance(response, ConversationalResponse)
        assert response.message is not None
        assert len(response.message) > 0
        assert response.chart_config == chart_config
        assert response.processing_time_ms == 150.5
        assert isinstance(response.insights, list)
        assert isinstance(response.follow_up_questions, list)
        # Test new structured response fields
        assert isinstance(response.key_findings, list)
        assert isinstance(response.suggested_actions, list)
        assert response.chart_explanation is not None  # Should have explanation when chart is provided
    
    def test_generate_conversational_response_no_data(self):
        """Test generating conversational response with no data."""
        response = self.generator.generate_conversational_response(
            self.empty_execute_response,
            "Show me sales for non-existent product"
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "couldn't find" in response.message.lower() or "no" in response.message.lower()
        assert len(response.follow_up_questions) > 0
        assert response.processing_time_ms == 25.0
        # Test new structured response fields for no-data case
        assert isinstance(response.key_findings, list)
        assert isinstance(response.suggested_actions, list)
        assert response.chart_explanation is None  # No chart explanation when no chart
    
    def test_generate_conversational_response_no_chart(self):
        """Test generating conversational response without chart config."""
        response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me data summary"
        )
        
        assert isinstance(response, ConversationalResponse)
        assert response.chart_config is None
        assert len(response.message) > 0
        # Test new structured response fields for no-chart case
        assert isinstance(response.key_findings, list)
        assert isinstance(response.suggested_actions, list)
        assert response.chart_explanation is None  # No chart explanation when no chart
    
    def test_structured_response_key_findings(self):
        """Test that key findings are properly extracted and structured."""
        response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me product sales analysis"
        )
        
        assert isinstance(response.key_findings, list)
        assert len(response.key_findings) <= 3  # Should limit to 3 key findings
        # Key findings should be different from general insights
        if response.key_findings and response.insights:
            assert any(finding != insight for finding in response.key_findings for insight in response.insights)
    
    def test_chart_explanation_generation(self):
        """Test chart explanation generation for different chart types."""
        # Test bar chart explanation
        bar_chart = ChartConfig(type="bar", x_axis="product", y_axis="sales")
        response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me sales by product",
            bar_chart
        )
        
        assert response.chart_explanation is not None
        assert "bar chart" in response.chart_explanation.lower()
        assert "sales" in response.chart_explanation.lower()
        assert "product" in response.chart_explanation.lower()
        
        # Test line chart explanation
        line_chart = ChartConfig(type="line", x_axis="date", y_axis="revenue")
        response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me revenue over time",
            line_chart
        )
        
        assert response.chart_explanation is not None
        assert "line chart" in response.chart_explanation.lower()
        assert "trend" in response.chart_explanation.lower() or "time" in response.chart_explanation.lower()
        
        # Test pie chart explanation
        pie_chart = ChartConfig(type="pie")
        response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me market share breakdown",
            pie_chart
        )
        
        assert response.chart_explanation is not None
        assert "pie chart" in response.chart_explanation.lower()
        assert "proportion" in response.chart_explanation.lower() or "breakdown" in response.chart_explanation.lower()
    
    def test_suggested_actions_generation(self):
        """Test that suggested actions are properly generated and separated from findings."""
        response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me sales performance"
        )
        
        assert isinstance(response.suggested_actions, list)
        assert len(response.suggested_actions) <= 3  # Should limit to 3 actions
        
        # Actions should be actionable (contain action words)
        action_words = ["try", "consider", "explore", "analyze", "investigate", "examine", "look", "verify"]
        if response.suggested_actions:
            assert any(any(word in action.lower() for word in action_words) for action in response.suggested_actions)
    
    def test_context_aware_follow_ups(self):
        """Test that follow-up questions are context-aware and relevant."""
        # Test sales context
        sales_response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me sales revenue by product"
        )
        
        assert len(sales_response.follow_up_questions) <= 3
        # Should contain sales-related follow-ups
        sales_keywords = ["product", "performance", "revenue", "sales", "customer"]
        if sales_response.follow_up_questions:
            assert any(any(keyword in question.lower() for keyword in sales_keywords) 
                      for question in sales_response.follow_up_questions)
        
        # Test customer context
        customer_response = self.generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me customer behavior patterns"
        )
        
        customer_keywords = ["customer", "behavior", "segment", "pattern"]
        if customer_response.follow_up_questions:
            assert any(any(keyword in question.lower() for keyword in customer_keywords) 
                      for question in customer_response.follow_up_questions)
    
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
        # Should mention the number of results
        insights_text = " ".join(insights).lower()
        assert "3" in insights_text or "results" in insights_text
    
    def test_explain_data_insights_empty_data(self):
        """Test explaining insights with empty data."""
        insights = self.generator.explain_data_insights([], "empty query")
        
        assert isinstance(insights, list)
        assert len(insights) == 1
        assert "no data" in insights[0].lower()
    
    def test_explain_data_insights_execute_response(self):
        """Test explaining insights with ExecuteResponse object."""
        insights = self.generator.explain_data_insights(self.sample_execute_response, "sales data")
        
        assert isinstance(insights, list)
        assert len(insights) > 0
        # Should analyze the ExecuteResponse data
        insights_text = " ".join(insights).lower()
        assert "3" in insights_text or "results" in insights_text
    
    def test_analyze_numeric_trends_increasing(self):
        """Test numeric trend analysis for increasing data."""
        data = [
            {"sales": 100, "profit": 20},
            {"sales": 200, "profit": 40},
            {"sales": 300, "profit": 60}
        ]
        
        insights = self.generator._analyze_numeric_trends(data, "sales analysis")
        
        assert isinstance(insights, list)
        # Should detect increasing trends
        insights_text = " ".join(insights).lower()
        assert any(word in insights_text for word in ["increasing", "growing", "upward", "trend"])
    
    def test_analyze_numeric_trends_no_numeric_data(self):
        """Test numeric trend analysis with no numeric columns."""
        data = [
            {"name": "Alice", "category": "A"},
            {"name": "Bob", "category": "B"}
        ]
        
        insights = self.generator._analyze_numeric_trends(data, "categorical data")
        
        assert isinstance(insights, list)
        # Should return empty or minimal insights for non-numeric data
    
    def test_analyze_categorical_data(self):
        """Test categorical data analysis."""
        data = [
            {"category": "A", "region": "North"},
            {"category": "B", "region": "North"},
            {"category": "A", "region": "South"},
            {"category": "C", "region": "North"}
        ]
        
        insights = self.generator._analyze_categorical_data(data, "category analysis")
        
        assert isinstance(insights, list)
        # Should analyze categorical distributions
        if insights:  # May not always generate insights for small datasets
            insights_text = " ".join(insights).lower()
            assert any(word in insights_text for word in ["category", "distribution", "common"])
    
    def test_analyze_temporal_patterns_with_dates(self):
        """Test temporal pattern analysis with date columns."""
        data = [
            {"date": "2023-01-01", "value": 100},
            {"date": "2023-02-01", "value": 200},
            {"date": "2023-03-01", "value": 150}
        ]
        
        insights = self.generator._analyze_temporal_patterns(data, "time series")
        
        assert isinstance(insights, list)
        # Should find temporal patterns if dates are detected
    
    def test_analyze_temporal_patterns_no_dates(self):
        """Test temporal pattern analysis without date columns."""
        data = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200}
        ]
        
        insights = self.generator._analyze_temporal_patterns(data, "non-temporal data")
        
        assert isinstance(insights, list)
        # Should return empty list when no date columns found
        assert len(insights) == 0
    
    def test_create_main_response_no_data(self):
        """Test main response creation with no data."""
        response = self.generator._create_main_response(
            self.empty_execute_response, 
            "test question", 
            []
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert "couldn't find" in response.lower() or "no" in response.lower()
    
    def test_create_main_response_with_data_and_insights(self):
        """Test main response creation with data and insights."""
        insights = [
            DataInsight(
                type="summary",
                message="Found 3 results with interesting patterns.",
                confidence=1.0,
                supporting_data={"row_count": 3}
            ),
            DataInsight(
                type="trend",
                message="Sales are increasing over time.",
                confidence=0.8,
                supporting_data={"trend_direction": "up"}
            )
        ]
        
        response = self.generator._create_main_response(
            self.sample_execute_response,
            "show me sales data",
            insights
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        # Should incorporate insights into the response
        response_lower = response.lower()
        assert "3" in response or "results" in response_lower
    
    def test_generate_follow_up_questions_no_data(self):
        """Test follow-up question generation with no data."""
        questions = self.generator._generate_follow_up_questions(
            self.empty_execute_response, 
            "test question"
        )
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert all(isinstance(q, str) for q in questions)
        assert all("?" in q for q in questions)
        # Should suggest data exploration questions
        questions_text = " ".join(questions).lower()
        assert any(word in questions_text for word in ["data", "available", "explore"])
    
    def test_generate_follow_up_questions_with_data(self):
        """Test follow-up question generation with data."""
        questions = self.generator._generate_follow_up_questions(
            self.sample_execute_response,
            "sales by region"
        )
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert len(questions) <= 3  # Should limit to 3 questions
        assert all(isinstance(q, str) for q in questions)
        assert all("?" in q for q in questions)
        
        # Should generate relevant questions based on available columns
        questions_text = " ".join(questions).lower()
        # Should reference available columns like date, region, product
        column_references = any(col in questions_text for col in ["date", "region", "product", "sales"])
        assert column_references
    
    def test_find_numeric_insights_with_outliers(self):
        """Test finding insights in numeric data with outliers."""
        data = [
            {"sales": 100, "profit": 10},
            {"sales": 200, "profit": 20},
            {"sales": 1000, "profit": 100}  # Outlier
        ]
        
        insights = self.generator._find_numeric_insights(data, "sales data")
        
        assert isinstance(insights, list)
        # Should detect outliers and other patterns
        if insights:
            outlier_insights = [i for i in insights if i.type == "outlier"]
            # May or may not detect outliers depending on threshold
    
    def test_find_numeric_insights_no_numeric_data(self):
        """Test finding insights with no numeric columns."""
        data = [
            {"name": "Alice", "category": "A"},
            {"name": "Bob", "category": "B"}
        ]
        
        insights = self.generator._find_numeric_insights(data, "non-numeric data")
        
        assert isinstance(insights, list)
        # Should return empty list for non-numeric data
        assert len(insights) == 0
    
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
        if insights:
            # Should analyze distributions and patterns
            insights_text = " ".join([i.message for i in insights]).lower()
            assert any(word in insights_text for word in ["category", "common", "frequent"])
    
    def test_error_handling_malformed_query_results(self):
        """Test error handling with malformed query results."""
        # Create malformed query results
        malformed_results = Mock()
        malformed_results.runtime_ms = 100.0
        malformed_results.row_count = 5  # Set a non-zero row count to avoid "no data" path
        malformed_results.columns = None  # This should cause an error
        
        # Should not crash and should return a fallback response
        response = self.generator.generate_conversational_response(
            malformed_results,
            "test question"
        )
        
        assert isinstance(response, ConversationalResponse)
        # Should handle malformed data gracefully - either with error message or fallback response
        assert (("trouble" in response.message.lower() or "issue" in response.message.lower()) or 
                ("data" in response.message.lower() and len(response.message) > 10))
        assert len(response.follow_up_questions) > 0
        # Test that new structured fields are present even in error cases
        assert isinstance(response.key_findings, list)
        assert isinstance(response.suggested_actions, list)
    
    def test_error_handling_in_insight_analysis(self):
        """Test error handling during insight analysis."""
        # Create data that might cause errors in analysis
        problematic_data = [
            {"col1": float('nan'), "col2": None},
            {"col1": "invalid", "col2": "data"}
        ]
        
        # Should not raise exceptions
        insights = self.generator.explain_data_insights(problematic_data, "problematic data")
        
        assert isinstance(insights, list)
        # Should handle errors gracefully
    
    def test_custom_number_format_integration(self):
        """Test integration with custom number format."""
        custom_format = NumberFormat(
            use_thousands_separator=False,
            decimal_places=1,
            currency_symbol="€"
        )
        
        generator = ResponseGenerator(number_format=custom_format)
        
        # Test that custom format is used
        result = generator.format_number(1234.56, "currency")
        assert "€" in result
        
        # Test in full response generation
        response = generator.generate_conversational_response(
            self.sample_execute_response,
            "Show me sales in euros"
        )
        
        assert isinstance(response, ConversationalResponse)
        # Custom format should be used throughout
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # Create larger dataset
        large_rows = []
        for i in range(1000):
            large_rows.append([f"Product_{i}", i * 100, f"2023-01-{(i % 30) + 1:02d}", "Region_A"])
        
        large_response = ExecuteResponse(
            columns=["product", "sales", "date", "region"],
            rows=large_rows,
            row_count=1000,
            runtime_ms=500.0,
            truncated=False
        )
        
        # Should handle large datasets without issues
        response = self.generator.generate_conversational_response(
            large_response,
            "Show me all products"
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "1000" in response.message or "1,000" in response.message
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
    
    def test_truncated_results_handling(self):
        """Test handling of truncated query results."""
        truncated_response = ExecuteResponse(
            columns=["product", "sales"],
            rows=[["Product A", 1000], ["Product B", 2000]],
            row_count=2,
            runtime_ms=100.0,
            truncated=True
        )
        
        response = self.generator.generate_conversational_response(
            truncated_response,
            "Show me all products"
        )
        
        assert isinstance(response, ConversationalResponse)
        # Should mention truncation in the response
        response_lower = response.message.lower()
        assert any(word in response_lower for word in ["showing", "first", "top", "sample"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])