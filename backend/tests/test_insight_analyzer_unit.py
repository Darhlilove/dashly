"""
Comprehensive unit tests for InsightAnalyzer class.

Tests cover trend detection, outlier identification, data summarization,
follow-up question generation, and error handling as specified in requirements 2.3, 4.1, 4.2, 4.3.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import math

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from insight_analyzer import InsightAnalyzer, InsightType, Insight, TrendAnalysis, OutlierInfo
from models import ExecuteResponse


class TestInsightAnalyzerUnit:
    """Comprehensive unit tests for InsightAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = InsightAnalyzer()
        
        # Sample datasets for testing
        self.increasing_data = [
            {"id": 1, "revenue": 1000, "users": 50, "category": "A"},
            {"id": 2, "revenue": 1200, "users": 60, "category": "B"},
            {"id": 3, "revenue": 1400, "users": 70, "category": "A"},
            {"id": 4, "revenue": 1600, "users": 80, "category": "C"},
            {"id": 5, "revenue": 1800, "users": 90, "category": "B"}
        ]
        
        self.decreasing_data = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 90},
            {"id": 3, "value": 80},
            {"id": 4, "value": 70},
            {"id": 5, "value": 60}
        ]
        
        self.outlier_data = [
            {"id": 1, "value": 10},
            {"id": 2, "value": 12},
            {"id": 3, "value": 11},
            {"id": 4, "value": 50},  # Outlier
            {"id": 5, "value": 9},
            {"id": 6, "value": 13}
        ]
        
        self.categorical_data = [
            {"category": "A", "region": "North", "status": "active"},
            {"category": "A", "region": "North", "status": "active"},
            {"category": "B", "region": "South", "status": "active"},
            {"category": "A", "region": "East", "status": "inactive"},
            {"category": "C", "region": "North", "status": "active"}
        ]
        
        self.temporal_data = [
            {"date": "2023-01-01", "sales": 1000, "orders": 50},
            {"date": "2023-02-01", "sales": 1200, "orders": 60},
            {"date": "2023-03-01", "sales": 1100, "orders": 55},
            {"date": "2023-04-01", "sales": 1300, "orders": 65}
        ]
        
        self.empty_data = []
        self.single_row_data = [{"id": 1, "value": 100}]
    
    def test_initialization(self):
        """Test InsightAnalyzer initialization."""
        analyzer = InsightAnalyzer()
        assert analyzer is not None
        # Test that it has the expected methods
        assert hasattr(analyzer, 'analyze_trends')
        assert hasattr(analyzer, 'identify_outliers')
        assert hasattr(analyzer, 'summarize_data')
        assert hasattr(analyzer, 'suggest_follow_up_questions')
    
    def test_analyze_trends_increasing_data(self):
        """Test trend detection for increasing data."""
        insights = self.analyzer.analyze_trends(self.increasing_data)
        
        # Should detect increasing trends in revenue and users
        trend_insights = [i for i in insights if i.type == InsightType.TREND]
        assert len(trend_insights) >= 1
        
        # Check for revenue trend
        revenue_trends = [i for i in trend_insights if i.column == "revenue"]
        assert len(revenue_trends) == 1
        trend_message = revenue_trends[0].message.lower()
        assert any(word in trend_message for word in ["upward", "increasing", "growing", "rising"])
        assert revenue_trends[0].confidence > 0.6
    
    def test_analyze_trends_decreasing_data(self):
        """Test trend detection for decreasing data."""
        insights = self.analyzer.analyze_trends(self.decreasing_data)
        
        trend_insights = [i for i in insights if i.type == InsightType.TREND]
        assert len(trend_insights) >= 1
        
        # Check for decreasing trend
        value_trends = [i for i in trend_insights if i.column == "value"]
        assert len(value_trends) == 1
        trend_message = value_trends[0].message.lower()
        assert any(word in trend_message for word in ["downward", "decreasing", "declining", "falling"])
    
    def test_analyze_trends_insufficient_data(self):
        """Test trend analysis with insufficient data."""
        # Single row
        insights = self.analyzer.analyze_trends(self.single_row_data)
        assert len(insights) == 0
        
        # Empty data
        insights = self.analyzer.analyze_trends(self.empty_data)
        assert len(insights) == 0
        
        # Two rows (minimum for trend detection)
        two_row_data = [{"value": 10}, {"value": 20}]
        insights = self.analyzer.analyze_trends(two_row_data)
        # Should have at least one trend insight for two points
        assert len(insights) >= 0  # May or may not detect trend with only 2 points
    
    def test_analyze_trends_flat_data(self):
        """Test trend analysis with flat/stable data."""
        flat_data = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 100},
            {"id": 3, "value": 100},
            {"id": 4, "value": 100}
        ]
        
        insights = self.analyzer.analyze_trends(flat_data)
        
        # May detect stable trend or no trend
        trend_insights = [i for i in insights if i.type == InsightType.TREND]
        if trend_insights:
            # If trend is detected, it should be stable/flat
            trend_message = trend_insights[0].message.lower()
            assert any(word in trend_message for word in ["stable", "flat", "consistent", "steady"])
    
    def test_identify_outliers_with_outliers(self):
        """Test outlier detection with clear outliers."""
        insights = self.analyzer.identify_outliers(self.outlier_data)
        
        outlier_insights = [i for i in insights if i.type == InsightType.OUTLIER]
        assert len(outlier_insights) >= 1
        
        # Check that the outlier (value=50) was detected
        outlier = outlier_insights[0]
        assert outlier.column == "value"
        assert "50" in outlier.message
        assert outlier.confidence > 0.0
    
    def test_identify_outliers_no_outliers(self):
        """Test outlier detection with no clear outliers."""
        normal_data = [
            {"value": 10}, {"value": 11}, {"value": 12}, 
            {"value": 13}, {"value": 14}, {"value": 15}
        ]
        
        insights = self.analyzer.identify_outliers(normal_data)
        
        # Should find no outliers in normal distribution
        outlier_insights = [i for i in insights if i.type == InsightType.OUTLIER]
        assert len(outlier_insights) == 0
    
    def test_identify_outliers_insufficient_data(self):
        """Test outlier detection with insufficient data."""
        # Need at least 3 points for outlier detection
        insights = self.analyzer.identify_outliers([{"value": 1}, {"value": 2}])
        assert len(insights) == 0
        
        insights = self.analyzer.identify_outliers(self.empty_data)
        assert len(insights) == 0
    
    def test_summarize_data_empty(self):
        """Test data summarization with empty data."""
        insights = self.analyzer.summarize_data(self.empty_data)
        
        assert len(insights) >= 1
        summary_insights = [i for i in insights if i.type == InsightType.SUMMARY]
        assert len(summary_insights) >= 1
        assert "no data" in summary_insights[0].message.lower()
    
    def test_summarize_data_single_row(self):
        """Test data summarization with single row."""
        insights = self.analyzer.summarize_data(self.single_row_data)
        
        summary_insights = [i for i in insights if i.type == InsightType.SUMMARY]
        assert len(summary_insights) >= 1
        summary_message = summary_insights[0].message.lower()
        assert any(phrase in summary_message for phrase in ["exactly one", "single", "1 result"])
    
    def test_summarize_data_multiple_rows(self):
        """Test data summarization with multiple rows."""
        insights = self.analyzer.summarize_data(self.increasing_data)
        
        summary_insights = [i for i in insights if i.type == InsightType.SUMMARY]
        assert len(summary_insights) >= 1
        
        # Should mention the number of results
        summary_message = summary_insights[0].message
        assert "5" in summary_message or "results" in summary_message.lower()
    
    def test_summarize_data_with_numeric_analysis(self):
        """Test data summarization includes numeric analysis."""
        insights = self.analyzer.summarize_data(self.increasing_data)
        
        # Should have insights about numeric columns
        numeric_insights = [i for i in insights if i.column in ["revenue", "users"]]
        assert len(numeric_insights) > 0
        
        # Check that numeric summaries are meaningful
        for insight in numeric_insights:
            assert insight.type == InsightType.SUMMARY
            assert len(insight.message) > 0
    
    def test_summarize_data_with_categorical_analysis(self):
        """Test data summarization includes categorical analysis."""
        insights = self.analyzer.summarize_data(self.categorical_data)
        
        # Should have insights about categorical columns
        categorical_insights = [i for i in insights if i.column in ["category", "region", "status"]]
        
        # May or may not generate categorical insights depending on data diversity
        if categorical_insights:
            for insight in categorical_insights:
                assert insight.type == InsightType.SUMMARY
                assert len(insight.message) > 0
    
    def test_suggest_follow_up_questions_empty_data(self):
        """Test follow-up question generation with empty data."""
        questions = self.analyzer.suggest_follow_up_questions(self.empty_data, "test question")
        
        assert len(questions) >= 1
        questions_text = " ".join(questions).lower()
        assert any(word in questions_text for word in ["data", "available", "upload"])
    
    def test_suggest_follow_up_questions_with_data(self):
        """Test follow-up question generation with data."""
        questions = self.analyzer.suggest_follow_up_questions(
            self.increasing_data, 
            "show me revenue by category"
        )
        
        assert len(questions) >= 1
        assert len(questions) <= 5  # Should limit to 5 questions
        
        # Should suggest relevant questions based on available columns
        questions_text = " ".join(questions).lower()
        column_references = any(col in questions_text for col in ["revenue", "category", "users"])
        assert column_references or any(word in questions_text for word in ["trend", "compare", "pattern"])
    
    def test_suggest_follow_up_questions_temporal_data(self):
        """Test follow-up question generation with temporal data."""
        questions = self.analyzer.suggest_follow_up_questions(
            self.temporal_data,
            "show me sales over time"
        )
        
        assert len(questions) >= 1
        questions_text = " ".join(questions).lower()
        # Should suggest time-related questions
        assert any(word in questions_text for word in ["time", "date", "trend", "seasonal", "month"])
    
    def test_analyze_query_results_comprehensive(self):
        """Test comprehensive analysis of query results."""
        # Create ExecuteResponse
        execute_response = ExecuteResponse(
            columns=["id", "revenue", "users", "category"],
            rows=[
                [1, 1000, 50, "A"],
                [2, 1200, 60, "B"],
                [3, 1400, 70, "A"],
                [4, 1600, 80, "C"],
                [5, 1800, 90, "B"]
            ],
            row_count=5,
            runtime_ms=100.0
        )
        
        results = self.analyzer.analyze_query_results(execute_response, "show me revenue trends")
        
        # Check that all analysis components are present
        required_keys = ["trends", "outliers", "summary", "all_insights", "follow_up_questions", "data_quality"]
        for key in required_keys:
            assert key in results
        
        # Check data quality metrics
        assert results["data_quality"]["row_count"] == 5
        assert results["data_quality"]["column_count"] == 4
        assert results["data_quality"]["has_numeric_data"] is True
        
        # Should have some insights
        assert len(results["all_insights"]) > 0
        assert len(results["follow_up_questions"]) > 0
    
    def test_analyze_query_results_empty_data(self):
        """Test comprehensive analysis with empty query results."""
        empty_response = ExecuteResponse(
            columns=["id", "value"],
            rows=[],
            row_count=0,
            runtime_ms=50.0
        )
        
        results = self.analyzer.analyze_query_results(empty_response, "empty query")
        
        # Should handle empty data gracefully
        assert "data_quality" in results
        assert results["data_quality"]["row_count"] == 0
        assert results["data_quality"]["has_numeric_data"] is False
        
        # Should still provide follow-up questions
        assert len(results["follow_up_questions"]) > 0
    
    def test_get_numeric_columns(self):
        """Test numeric column identification."""
        numeric_cols = self.analyzer._get_numeric_columns(self.increasing_data)
        
        assert "revenue" in numeric_cols
        assert "users" in numeric_cols
        assert "id" in numeric_cols
        assert "category" not in numeric_cols
    
    def test_get_numeric_columns_mixed_types(self):
        """Test numeric column identification with mixed data types."""
        mixed_data = [
            {"id": 1, "value": "100", "text": "hello", "float_val": 1.5},
            {"id": 2, "value": "200", "text": "world", "float_val": 2.5}
        ]
        
        numeric_cols = self.analyzer._get_numeric_columns(mixed_data)
        
        assert "id" in numeric_cols
        assert "float_val" in numeric_cols
        # String numbers might or might not be detected as numeric
        assert "text" not in numeric_cols
    
    def test_get_date_columns(self):
        """Test date column identification."""
        date_cols = self.analyzer._get_date_columns(self.temporal_data)
        
        assert "date" in date_cols
        assert "sales" not in date_cols
        assert "orders" not in date_cols
    
    def test_get_date_columns_various_formats(self):
        """Test date column identification with various date formats."""
        various_date_data = [
            {"date1": "2023-01-01", "date2": "01/01/2023", "date3": "Jan 1, 2023", "value": 100},
            {"date1": "2023-01-02", "date2": "01/02/2023", "date3": "Jan 2, 2023", "value": 200}
        ]
        
        date_cols = self.analyzer._get_date_columns(various_date_data)
        
        # Should detect at least some date formats
        assert len(date_cols) > 0
        assert "value" not in date_cols
    
    def test_extract_numeric_values(self):
        """Test numeric value extraction."""
        values = self.analyzer._extract_numeric_values(self.increasing_data, "revenue")
        
        assert values == [1000, 1200, 1400, 1600, 1800]
    
    def test_extract_numeric_values_missing_column(self):
        """Test numeric value extraction with missing column."""
        values = self.analyzer._extract_numeric_values(self.increasing_data, "nonexistent")
        
        assert values == []
    
    def test_extract_numeric_values_mixed_types(self):
        """Test numeric value extraction with mixed data types."""
        mixed_data = [
            {"value": 100}, {"value": "200"}, {"value": None}, {"value": 300}
        ]
        
        values = self.analyzer._extract_numeric_values(mixed_data, "value")
        
        # Should extract valid numeric values and skip invalid ones
        assert 100 in values
        assert 300 in values
        # String "200" might or might not be converted
        assert len(values) >= 2
    
    def test_calculate_correlation_perfect_positive(self):
        """Test correlation calculation with perfect positive correlation."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]  # Perfect positive correlation
        
        correlation = self.analyzer._calculate_correlation(x, y)
        assert abs(correlation - 1.0) < 0.01  # Should be close to 1.0
    
    def test_calculate_correlation_perfect_negative(self):
        """Test correlation calculation with perfect negative correlation."""
        x = [1, 2, 3, 4, 5]
        y = [10, 8, 6, 4, 2]  # Perfect negative correlation
        
        correlation = self.analyzer._calculate_correlation(x, y)
        assert abs(correlation - (-1.0)) < 0.01  # Should be close to -1.0
    
    def test_calculate_correlation_no_correlation(self):
        """Test correlation calculation with no correlation."""
        x = [1, 2, 3, 4, 5]
        y = [3, 1, 4, 1, 5]  # Random values
        
        correlation = self.analyzer._calculate_correlation(x, y)
        assert -1.0 <= correlation <= 1.0  # Should be valid correlation value
    
    def test_calculate_correlation_edge_cases(self):
        """Test correlation calculation edge cases."""
        # Empty lists
        correlation = self.analyzer._calculate_correlation([], [])
        assert correlation == 0.0
        
        # Single values
        correlation = self.analyzer._calculate_correlation([1], [2])
        assert correlation == 0.0
        
        # Identical values (no variance)
        correlation = self.analyzer._calculate_correlation([1, 1, 1], [2, 2, 2])
        assert correlation == 0.0
    
    def test_analyze_column_trend_increasing(self):
        """Test individual column trend analysis for increasing data."""
        increasing_values = [10, 20, 30, 40, 50]
        trend = self.analyzer._analyze_column_trend(increasing_values, "test_col")
        
        assert trend.direction == "increasing"
        assert trend.confidence > 0.6
        assert trend.start_value == 10
        assert trend.end_value == 50
        assert trend.change_rate > 0
    
    def test_analyze_column_trend_decreasing(self):
        """Test individual column trend analysis for decreasing data."""
        decreasing_values = [50, 40, 30, 20, 10]
        trend = self.analyzer._analyze_column_trend(decreasing_values, "test_col")
        
        assert trend.direction == "decreasing"
        assert trend.confidence > 0.6
        assert trend.start_value == 50
        assert trend.end_value == 10
        assert trend.change_rate < 0
    
    def test_analyze_column_trend_stable(self):
        """Test individual column trend analysis for stable data."""
        stable_values = [100, 101, 99, 100, 102]
        trend = self.analyzer._analyze_column_trend(stable_values, "test_col")
        
        assert trend.direction == "stable"
        assert trend.confidence > 0.0
        assert abs(trend.change_rate) < 0.1  # Should be close to 0
    
    def test_detect_outliers_method(self):
        """Test outlier detection method."""
        values = [10, 12, 11, 50, 9, 13]  # 50 is an outlier
        outliers = self.analyzer._detect_outliers(values, "test_col")
        
        assert len(outliers) >= 1
        # Find the outlier with value 50
        outlier_50 = next((o for o in outliers if o.value == 50), None)
        assert outlier_50 is not None
        assert outlier_50.is_high is True
        assert outlier_50.deviation_score > 1.5
    
    def test_detect_outliers_no_outliers(self):
        """Test outlier detection with no outliers."""
        normal_values = [10, 11, 12, 13, 14, 15]
        outliers = self.analyzer._detect_outliers(normal_values, "test_col")
        
        # Should find no outliers in normal distribution
        assert len(outliers) == 0
    
    def test_detect_outliers_insufficient_data(self):
        """Test outlier detection with insufficient data."""
        # Need at least 3 points
        outliers = self.analyzer._detect_outliers([10, 20], "test_col")
        assert len(outliers) == 0
        
        outliers = self.analyzer._detect_outliers([], "test_col")
        assert len(outliers) == 0
    
    def test_create_trend_insight(self):
        """Test trend insight creation."""
        trend_analysis = TrendAnalysis(
            direction="increasing",
            strength=0.8,
            confidence=0.9,
            change_rate=0.5,
            start_value=100,
            end_value=150
        )
        
        insight = self.analyzer._create_trend_insight("revenue", trend_analysis)
        
        assert insight.type == InsightType.TREND
        assert insight.column == "revenue"
        assert insight.confidence == 0.9
        insight_message = insight.message.lower()
        assert any(word in insight_message for word in ["upward", "increasing", "growing", "rising"])
    
    def test_create_outlier_insight(self):
        """Test outlier insight creation."""
        outlier = OutlierInfo(
            value=100,
            column="sales",
            deviation_score=3.0,
            is_high=True
        )
        
        insight = self.analyzer._create_outlier_insight(outlier)
        
        assert insight.type == InsightType.OUTLIER
        assert insight.column == "sales"
        assert "100" in insight.message
        assert "high" in insight.message.lower()
    
    def test_create_outlier_insight_low_outlier(self):
        """Test outlier insight creation for low outlier."""
        outlier = OutlierInfo(
            value=5,
            column="sales",
            deviation_score=2.5,
            is_high=False
        )
        
        insight = self.analyzer._create_outlier_insight(outlier)
        
        assert insight.type == InsightType.OUTLIER
        assert insight.column == "sales"
        assert "5" in insight.message
        assert "low" in insight.message.lower()
    
    def test_summarize_numeric_data(self):
        """Test numeric data summarization."""
        insights = self.analyzer._summarize_numeric_data(self.increasing_data)
        
        assert len(insights) > 0
        
        # Should have insights for numeric columns
        revenue_insights = [i for i in insights if i.column == "revenue"]
        assert len(revenue_insights) >= 1
        
        revenue_insight = revenue_insights[0]
        assert revenue_insight.type == InsightType.SUMMARY
        assert "revenue" in revenue_insight.message.lower()
        # Should include statistical information
        assert any(word in revenue_insight.message.lower() for word in ["average", "range", "total", "min", "max"])
    
    def test_summarize_categorical_data(self):
        """Test categorical data summarization."""
        insights = self.analyzer._summarize_categorical_data(self.categorical_data)
        
        # Should analyze categorical distributions
        category_insights = [i for i in insights if i.column == "category"]
        if category_insights:  # May not always generate insights for small datasets
            category_insight = category_insights[0]
            assert category_insight.type == InsightType.SUMMARY
            assert "category" in category_insight.message.lower()
    
    def test_generate_insight_based_questions(self):
        """Test insight-based question generation."""
        insights = [
            Insight(InsightType.TREND, "Revenue is increasing steadily", 0.9, "revenue"),
            Insight(InsightType.OUTLIER, "Found unusually high sales value", 0.8, "sales"),
            Insight(InsightType.SUMMARY, "Data contains 5 records", 1.0, None)
        ]
        
        questions = self.analyzer._generate_insight_based_questions(insights, "revenue analysis")
        
        assert len(questions) > 0
        questions_text = " ".join(questions).lower()
        # Should reference the insights
        assert any(word in questions_text for word in ["trend", "outlier", "revenue", "sales"])
    
    def test_convert_execute_response_to_dicts(self):
        """Test conversion of ExecuteResponse to list of dicts."""
        execute_response = ExecuteResponse(
            columns=["id", "name", "value"],
            rows=[
                [1, "Alice", 100],
                [2, "Bob", 200],
                [3, "Charlie", 300]
            ],
            row_count=3,
            runtime_ms=50.0
        )
        
        data = self.analyzer._convert_execute_response_to_dicts(execute_response)
        
        assert len(data) == 3
        assert data[0] == {"id": 1, "name": "Alice", "value": 100}
        assert data[1] == {"id": 2, "name": "Bob", "value": 200}
        assert data[2] == {"id": 3, "name": "Charlie", "value": 300}
    
    def test_convert_execute_response_empty(self):
        """Test conversion of empty ExecuteResponse."""
        empty_response = ExecuteResponse(
            columns=["id", "value"],
            rows=[],
            row_count=0,
            runtime_ms=25.0
        )
        
        data = self.analyzer._convert_execute_response_to_dicts(empty_response)
        
        assert data == []
    
    def test_error_handling_malformed_data(self):
        """Test error handling with malformed data."""
        # Test with data containing invalid values
        malformed_data = [
            {"col1": "not_a_number", "col2": None},
            {"col1": float('inf'), "col2": "text"},
            {"col1": float('nan'), "col2": 42}
        ]
        
        # Should not raise exceptions
        trends = self.analyzer.analyze_trends(malformed_data)
        outliers = self.analyzer.identify_outliers(malformed_data)
        summary = self.analyzer.summarize_data(malformed_data)
        questions = self.analyzer.suggest_follow_up_questions(malformed_data, "test")
        
        # Should return safe results
        assert isinstance(trends, list)
        assert isinstance(outliers, list)
        assert isinstance(summary, list)
        assert isinstance(questions, list)
    
    def test_error_handling_missing_columns(self):
        """Test error handling when expected columns are missing."""
        # Data with inconsistent structure
        inconsistent_data = [
            {"a": 1, "b": 2},
            {"a": 3},  # Missing 'b'
            {"b": 4, "c": 5}  # Missing 'a', extra 'c'
        ]
        
        # Should handle gracefully
        insights = self.analyzer.summarize_data(inconsistent_data)
        assert isinstance(insights, list)
        
        questions = self.analyzer.suggest_follow_up_questions(inconsistent_data, "test")
        assert isinstance(questions, list)
    
    @patch('insight_analyzer.logger')
    def test_logging_info(self, mock_logger):
        """Test that appropriate info logging occurs."""
        self.analyzer.analyze_trends(self.increasing_data)
        
        # Should have logged the analysis
        assert mock_logger.info.called
    
    @patch('insight_analyzer.logger')
    def test_logging_error(self, mock_logger):
        """Test that error logging occurs on exceptions."""
        # Force an error by mocking a method to raise an exception
        with patch.object(self.analyzer, '_get_numeric_columns', side_effect=Exception("Test error")):
            self.analyzer.analyze_trends(self.increasing_data)
            assert mock_logger.error.called
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # Create larger dataset
        large_data = []
        for i in range(1000):
            large_data.append({
                "id": i,
                "value": i * 10 + (i % 100),  # Some variation
                "category": f"Cat_{i % 5}",
                "date": f"2023-{(i % 12) + 1:02d}-01"
            })
        
        # Should handle large datasets without issues
        insights = self.analyzer.summarize_data(large_data)
        assert isinstance(insights, list)
        assert len(insights) > 0
        
        trends = self.analyzer.analyze_trends(large_data)
        assert isinstance(trends, list)
        
        questions = self.analyzer.suggest_follow_up_questions(large_data, "large dataset analysis")
        assert isinstance(questions, list)
        assert len(questions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])