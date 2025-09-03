"""
Integration tests for InsightAnalyzer with ChatService and other components.

Tests the integration of InsightAnalyzer with the broader chat system
to ensure insights are properly generated and integrated into responses.
"""

import pytest
from unittest.mock import Mock, AsyncMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from insight_analyzer import InsightAnalyzer
from chat_service import ChatService
from models import ExecuteResponse, ChatRequest, ConversationalResponse


class TestInsightAnalyzerIntegration:
    """Integration tests for InsightAnalyzer with other services."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.insight_analyzer = InsightAnalyzer()
        
        # Mock dependencies
        self.mock_query_executor = Mock()
        self.mock_llm_service = Mock()
        
        # Create ChatService with InsightAnalyzer
        self.chat_service = ChatService(
            query_executor=self.mock_query_executor,
            llm_service=self.mock_llm_service,
            insight_analyzer=self.insight_analyzer
        )
        
        # Sample query results for testing
        self.sample_query_results = ExecuteResponse(
            columns=["month", "revenue", "customers", "region"],
            rows=[
                ["2023-01", 10000, 100, "North"],
                ["2023-02", 12000, 120, "North"],
                ["2023-03", 15000, 150, "North"],
                ["2023-04", 18000, 180, "South"],
                ["2023-05", 22000, 220, "South"]
            ],
            row_count=5,
            runtime_ms=150.0
        )
    
    def test_analyze_data_insights_public_method(self):
        """Test the public analyze_data_insights method in ChatService."""
        results = self.chat_service.analyze_data_insights(
            self.sample_query_results, 
            "Show me monthly revenue trends"
        )
        
        # Verify all expected components are present
        assert "trends" in results
        assert "outliers" in results
        assert "summary" in results
        assert "all_insights" in results
        assert "follow_up_questions" in results
        assert "data_quality" in results
        
        # Verify data quality metrics
        assert results["data_quality"]["row_count"] == 5
        assert results["data_quality"]["column_count"] == 4
        assert results["data_quality"]["has_numeric_data"] is True
        
        # Should have detected trends in revenue (increasing pattern)
        trend_insights = results["trends"]
        revenue_trends = [t for t in trend_insights if t.column == "revenue"]
        assert len(revenue_trends) >= 1
        
        # Should have some insights
        assert len(results["all_insights"]) > 0
        
        # Should have follow-up questions
        assert len(results["follow_up_questions"]) > 0
    
    @pytest.mark.asyncio
    async def test_chat_service_with_insight_analyzer_mock_mode(self):
        """Test ChatService with InsightAnalyzer in mock mode (no query execution)."""
        # Test without query executor (mock mode)
        chat_service_mock = ChatService(insight_analyzer=self.insight_analyzer)
        
        request = ChatRequest(
            message="What are my sales trends?",
            conversation_id="test-123"
        )
        
        response = await chat_service_mock.process_chat_message(request)
        
        # Should return a valid response even in mock mode
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == "test-123"
        assert len(response.message) > 0
        assert isinstance(response.insights, list)
        assert isinstance(response.follow_up_questions, list)
    
    @pytest.mark.asyncio
    async def test_chat_service_with_full_processing_flow(self):
        """Test ChatService with full processing flow including InsightAnalyzer."""
        # Mock the LLM service to return SQL
        self.mock_llm_service.generate_sql = AsyncMock(return_value="SELECT * FROM sales")
        
        # Mock the query executor to return results
        self.mock_query_executor.execute_query = AsyncMock(return_value=self.sample_query_results)
        
        request = ChatRequest(
            message="Show me revenue trends by month",
            conversation_id="test-456"
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Verify the response includes insights from InsightAnalyzer
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == "test-456"
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        
        # Verify that LLM and query executor were called
        self.mock_llm_service.generate_sql.assert_called_once()
        self.mock_query_executor.execute_query.assert_called_once()
    
    def test_insight_analyzer_with_different_data_types(self):
        """Test InsightAnalyzer with various data types and patterns."""
        # Test with categorical data
        categorical_results = ExecuteResponse(
            columns=["category", "count"],
            rows=[
                ["Electronics", 150],
                ["Clothing", 200],
                ["Books", 75],
                ["Sports", 125]
            ],
            row_count=4,
            runtime_ms=80.0
        )
        
        analysis = self.insight_analyzer.analyze_query_results(
            categorical_results, 
            "Show me sales by category"
        )
        
        assert len(analysis["summary"]) > 0
        assert analysis["data_quality"]["row_count"] == 4
        
        # Test with time series data
        time_series_results = ExecuteResponse(
            columns=["date", "daily_users"],
            rows=[
                ["2023-01-01", 100],
                ["2023-01-02", 110],
                ["2023-01-03", 105],
                ["2023-01-04", 120],
                ["2023-01-05", 115]
            ],
            row_count=5,
            runtime_ms=90.0
        )
        
        time_analysis = self.insight_analyzer.analyze_query_results(
            time_series_results,
            "Show me daily user activity"
        )
        
        assert len(time_analysis["all_insights"]) > 0
        assert "daily" in " ".join(time_analysis["follow_up_questions"]).lower() or \
               "time" in " ".join(time_analysis["follow_up_questions"]).lower()
    
    def test_insight_analyzer_error_handling_integration(self):
        """Test InsightAnalyzer error handling in integration context."""
        # Test with malformed data
        malformed_results = ExecuteResponse(
            columns=["col1", "col2"],
            rows=[
                [None, "invalid"],
                ["text", None]
            ],
            row_count=2,
            runtime_ms=50.0
        )
        
        # Should not raise exceptions
        analysis = self.insight_analyzer.analyze_query_results(
            malformed_results,
            "Test question"
        )
        
        # Should return valid structure even with bad data
        assert "trends" in analysis
        assert "outliers" in analysis
        assert "summary" in analysis
        assert "follow_up_questions" in analysis
        assert isinstance(analysis["follow_up_questions"], list)
    
    def test_insight_analyzer_performance_with_large_dataset(self):
        """Test InsightAnalyzer performance with larger datasets."""
        # Create a larger dataset
        large_rows = []
        for i in range(100):
            large_rows.append([f"2023-{i//30 + 1:02d}-{i%30 + 1:02d}", i * 100 + 1000, i % 10])
        
        large_results = ExecuteResponse(
            columns=["date", "revenue", "category_id"],
            rows=large_rows,
            row_count=100,
            runtime_ms=200.0
        )
        
        import time
        start_time = time.time()
        
        analysis = self.insight_analyzer.analyze_query_results(
            large_results,
            "Show me revenue trends over time"
        )
        
        analysis_time = time.time() - start_time
        
        # Should complete analysis in reasonable time (< 1 second for 100 rows)
        assert analysis_time < 1.0
        
        # Should still produce meaningful results
        assert len(analysis["all_insights"]) > 0
        assert analysis["data_quality"]["row_count"] == 100
        
        # Should detect trends in the increasing revenue pattern
        trend_insights = analysis["trends"]
        revenue_trends = [t for t in trend_insights if t.column == "revenue"]
        assert len(revenue_trends) >= 1
    
    def test_follow_up_question_contextual_relevance(self):
        """Test that follow-up questions are contextually relevant to the data and question."""
        # Test with sales data
        sales_results = ExecuteResponse(
            columns=["product", "sales_amount", "profit_margin"],
            rows=[
                ["Product A", 10000, 0.25],
                ["Product B", 15000, 0.30],
                ["Product C", 8000, 0.20]
            ],
            row_count=3,
            runtime_ms=75.0
        )
        
        analysis = self.insight_analyzer.analyze_query_results(
            sales_results,
            "Which products are most profitable?"
        )
        
        follow_ups = analysis["follow_up_questions"]
        follow_up_text = " ".join(follow_ups).lower()
        
        # Should suggest relevant business questions
        assert any(word in follow_up_text for word in [
            "product", "profit", "sales", "performance", "compare", "category", "trend"
        ])
        
        # Test with user activity data
        activity_results = ExecuteResponse(
            columns=["user_id", "login_count", "last_login_date"],
            rows=[
                [1, 25, "2023-05-01"],
                [2, 30, "2023-05-02"],
                [3, 15, "2023-04-28"]
            ],
            row_count=3,
            runtime_ms=60.0
        )
        
        activity_analysis = self.insight_analyzer.analyze_query_results(
            activity_results,
            "Show me user activity patterns"
        )
        
        activity_follow_ups = activity_analysis["follow_up_questions"]
        activity_text = " ".join(activity_follow_ups).lower()
        
        # Should suggest user-related questions
        assert any(word in activity_text for word in [
            "user", "activity", "login", "engagement", "time", "pattern"
        ])


if __name__ == "__main__":
    pytest.main([__file__])