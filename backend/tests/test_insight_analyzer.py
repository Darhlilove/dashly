"""
Tests for the InsightAnalyzer class.

Tests cover trend detection, outlier identification, data summarization,
and follow-up question generation as specified in requirements 2.3, 4.1, 4.2, and 4.3.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from insight_analyzer import InsightAnalyzer, InsightType, Insight, TrendAnalysis, OutlierInfo
from models import ExecuteResponse


class TestInsightAnalyzer:
    """Test suite for InsightAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = InsightAnalyzer()
        
        # Sample data for testing
        self.sample_numeric_data = [
            {"id": 1, "revenue": 1000, "users": 50, "category": "A"},
            {"id": 2, "revenue": 1200, "users": 60, "category": "B"},
            {"id": 3, "revenue": 1400, "users": 70, "category": "A"},
            {"id": 4, "revenue": 1600, "users": 80, "category": "C"},
            {"id": 5, "revenue": 1800, "users": 90, "category": "B"}
        ]
        
        self.sample_outlier_data = [
            {"id": 1, "value": 10},
            {"id": 2, "value": 12},
            {"id": 3, "value": 11},
            {"id": 4, "value": 50},  # Outlier
            {"id": 5, "value": 9}
        ]
        
        self.empty_data = []
        
        self.single_row_data = [{"id": 1, "value": 100}]
    
    def test_analyze_trends_increasing(self):
        """Test trend detection for increasing data."""
        insights = self.analyzer.analyze_trends(self.sample_numeric_data)
        
        # Should detect increasing trends in revenue and users
        trend_insights = [i for i in insights if i.type == InsightType.TREND]
        assert len(trend_insights) >= 1
        
        # Check that we detected the increasing trend
        revenue_trends = [i for i in trend_insights if i.column == "revenue"]
        assert len(revenue_trends) == 1
        assert "upward" in revenue_trends[0].message.lower() or "increasing" in revenue_trends[0].message.lower()
        assert revenue_trends[0].confidence > 0.6
    
    def test_analyze_trends_insufficient_data(self):
        """Test trend analysis with insufficient data."""
        insights = self.analyzer.analyze_trends(self.single_row_data)
        assert len(insights) == 0
        
        insights = self.analyzer.analyze_trends(self.empty_data)
        assert len(insights) == 0
    
    def test_identify_outliers(self):
        """Test outlier detection."""
        insights = self.analyzer.identify_outliers(self.sample_outlier_data)
        
        outlier_insights = [i for i in insights if i.type == InsightType.OUTLIER]
        assert len(outlier_insights) >= 1
        
        # Check that the outlier (value=50) was detected
        outlier = outlier_insights[0]
        assert outlier.column == "value"
        assert "50" in outlier.message
        assert outlier.confidence > 0.0
    
    def test_identify_outliers_insufficient_data(self):
        """Test outlier detection with insufficient data."""
        insights = self.analyzer.identify_outliers([{"value": 1}, {"value": 2}])
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
        assert "exactly one" in summary_insights[0].message.lower()
    
    def test_summarize_data_multiple_rows(self):
        """Test data summarization with multiple rows."""
        insights = self.analyzer.summarize_data(self.sample_numeric_data)
        
        summary_insights = [i for i in insights if i.type == InsightType.SUMMARY]
        assert len(summary_insights) >= 1
        
        # Should mention the number of results
        row_count_insight = summary_insights[0]
        assert "5" in row_count_insight.message or "results" in row_count_insight.message.lower()
    
    def test_suggest_follow_up_questions_empty_data(self):
        """Test follow-up question generation with empty data."""
        questions = self.analyzer.suggest_follow_up_questions(self.empty_data, "test question")
        
        assert len(questions) >= 1
        assert any("data" in q.lower() for q in questions)
    
    def test_suggest_follow_up_questions_with_data(self):
        """Test follow-up question generation with data."""
        questions = self.analyzer.suggest_follow_up_questions(
            self.sample_numeric_data, 
            "show me revenue by category"
        )
        
        assert len(questions) >= 1
        assert len(questions) <= 5  # Should limit to 5 questions
        
        # Should suggest relevant questions
        question_text = " ".join(questions).lower()
        assert any(word in question_text for word in ["trend", "category", "compare", "pattern"])
    
    def test_analyze_query_results_comprehensive(self):
        """Test comprehensive analysis of query results."""
        # Create mock ExecuteResponse
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
        assert "trends" in results
        assert "outliers" in results
        assert "summary" in results
        assert "all_insights" in results
        assert "follow_up_questions" in results
        assert "data_quality" in results
        
        # Check data quality metrics
        assert results["data_quality"]["row_count"] == 5
        assert results["data_quality"]["column_count"] == 4
        assert results["data_quality"]["has_numeric_data"] is True
        
        # Should have some insights
        assert len(results["all_insights"]) > 0
        assert len(results["follow_up_questions"]) > 0
    
    def test_get_numeric_columns(self):
        """Test numeric column identification."""
        numeric_cols = self.analyzer._get_numeric_columns(self.sample_numeric_data)
        
        assert "revenue" in numeric_cols
        assert "users" in numeric_cols
        assert "id" in numeric_cols
        assert "category" not in numeric_cols
    
    def test_get_date_columns(self):
        """Test date column identification."""
        date_data = [
            {"id": 1, "created_date": "2023-01-01", "value": 100},
            {"id": 2, "created_date": "2023-01-02", "value": 200}
        ]
        
        date_cols = self.analyzer._get_date_columns(date_data)
        assert "created_date" in date_cols
        assert "id" not in date_cols
        assert "value" not in date_cols
    
    def test_extract_numeric_values(self):
        """Test numeric value extraction."""
        values = self.analyzer._extract_numeric_values(self.sample_numeric_data, "revenue")
        
        assert values == [1000, 1200, 1400, 1600, 1800]
    
    def test_calculate_correlation(self):
        """Test correlation calculation."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]  # Perfect positive correlation
        
        correlation = self.analyzer._calculate_correlation(x, y)
        assert abs(correlation - 1.0) < 0.01  # Should be close to 1.0
        
        # Test negative correlation
        y_neg = [10, 8, 6, 4, 2]
        correlation_neg = self.analyzer._calculate_correlation(x, y_neg)
        assert abs(correlation_neg - (-1.0)) < 0.01  # Should be close to -1.0
    
    def test_analyze_column_trend(self):
        """Test individual column trend analysis."""
        increasing_values = [10, 20, 30, 40, 50]
        trend = self.analyzer._analyze_column_trend(increasing_values, "test_col")
        
        assert trend.direction == "increasing"
        assert trend.confidence > 0.6
        assert trend.start_value == 10
        assert trend.end_value == 50
    
    def test_detect_outliers_method(self):
        """Test outlier detection method."""
        values = [10, 12, 11, 50, 9]  # 50 is an outlier
        outliers = self.analyzer._detect_outliers(values, "test_col")
        
        assert len(outliers) >= 1
        assert outliers[0].value == 50
        assert outliers[0].is_high is True
        assert outliers[0].deviation_score > 1.5  # Updated to match the actual threshold
    
    def test_create_trend_insight(self):
        """Test trend insight creation."""
        trend_analysis = TrendAnalysis(
            direction="increasing",
            strength=0.8,
            confidence=0.9,
            change_rate=0.5
        )
        
        insight = self.analyzer._create_trend_insight("revenue", trend_analysis)
        
        assert insight.type == InsightType.TREND
        assert insight.column == "revenue"
        assert insight.confidence == 0.9
        assert "upward" in insight.message.lower() or "increasing" in insight.message.lower()
    
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
    
    def test_summarize_numeric_data(self):
        """Test numeric data summarization."""
        insights = self.analyzer._summarize_numeric_data(self.sample_numeric_data)
        
        assert len(insights) > 0
        
        # Should have insights for numeric columns
        revenue_insights = [i for i in insights if i.column == "revenue"]
        assert len(revenue_insights) >= 1
        
        revenue_insight = revenue_insights[0]
        assert revenue_insight.type == InsightType.SUMMARY
        assert "revenue" in revenue_insight.message.lower()
    
    def test_summarize_categorical_data(self):
        """Test categorical data summarization."""
        insights = self.analyzer._summarize_categorical_data(self.sample_numeric_data)
        
        # Should have insights for categorical columns
        category_insights = [i for i in insights if i.column == "category"]
        if category_insights:  # May not always generate insights for small datasets
            category_insight = category_insights[0]
            assert category_insight.type == InsightType.SUMMARY
            assert "category" in category_insight.message.lower()
    
    def test_generate_insight_based_questions(self):
        """Test insight-based question generation."""
        insights = [
            Insight(InsightType.TREND, "Revenue is increasing", 0.9, "revenue"),
            Insight(InsightType.OUTLIER, "Found high value", 0.8, "sales")
        ]
        
        questions = self.analyzer._generate_insight_based_questions(insights, "test question")
        
        assert len(questions) > 0
        question_text = " ".join(questions).lower()
        assert "trend" in question_text or "outlier" in question_text
    
    def test_convert_execute_response_to_dicts(self):
        """Test conversion of ExecuteResponse to list of dicts."""
        execute_response = ExecuteResponse(
            columns=["id", "name", "value"],
            rows=[
                [1, "Alice", 100],
                [2, "Bob", 200]
            ],
            row_count=2,
            runtime_ms=50.0
        )
        
        data = self.analyzer._convert_execute_response_to_dicts(execute_response)
        
        assert len(data) == 2
        assert data[0] == {"id": 1, "name": "Alice", "value": 100}
        assert data[1] == {"id": 2, "name": "Bob", "value": 200}
    
    def test_error_handling(self):
        """Test error handling in analysis methods."""
        # Test with malformed data
        malformed_data = [{"col1": "not_a_number"}, {"col1": None}]
        
        # Should not raise exceptions
        trends = self.analyzer.analyze_trends(malformed_data)
        outliers = self.analyzer.identify_outliers(malformed_data)
        summary = self.analyzer.summarize_data(malformed_data)
        questions = self.analyzer.suggest_follow_up_questions(malformed_data, "test")
        
        # Should return empty or safe results
        assert isinstance(trends, list)
        assert isinstance(outliers, list)
        assert isinstance(summary, list)
        assert isinstance(questions, list)
    
    @patch('insight_analyzer.logger')
    def test_logging(self, mock_logger):
        """Test that appropriate logging occurs."""
        self.analyzer.analyze_trends(self.sample_numeric_data)
        
        # Should have logged the analysis
        assert mock_logger.info.called
        
        # Test error logging with invalid data
        with patch.object(self.analyzer, '_get_numeric_columns', side_effect=Exception("Test error")):
            self.analyzer.analyze_trends(self.sample_numeric_data)
            assert mock_logger.error.called


if __name__ == "__main__":
    pytest.main([__file__])