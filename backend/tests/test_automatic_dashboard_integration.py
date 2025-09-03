"""
Integration tests for automatic dashboard updates functionality.
Tests the complete workflow from chat message to dashboard update.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chat_service import ChatService
from chart_recommendation_service import ChartRecommendationService
from models import ChatRequest, ConversationalResponse, ExecuteResponse, ChartConfig


class TestAutomaticDashboardIntegration:
    """Integration tests for automatic dashboard updates."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_query_executor = Mock()
        self.mock_llm_service = Mock()
        
        # Create real services
        self.chart_service = ChartRecommendationService()
        self.chat_service = ChatService(
            query_executor=self.mock_query_executor,
            llm_service=self.mock_llm_service,
            chart_recommendation_service=self.chart_service
        )
    
    @pytest.mark.asyncio
    async def test_automatic_dashboard_update_workflow(self):
        """Test the complete workflow from chat message to automatic dashboard update."""
        
        # Mock query results that should generate a chart
        mock_query_results = ExecuteResponse(
            columns=["month", "sales"],
            rows=[
                ["January", 10000],
                ["February", 12000],
                ["March", 11000],
            ],
            row_count=3,
            runtime_ms=50.0,
            truncated=False
        )
        
        # Mock LLM service responses
        self.mock_llm_service.translate_to_sql.return_value = "SELECT month, sales FROM sales_data"
        self.mock_llm_service.generate_conversational_explanation.return_value = "Here are your monthly sales trends. I can see steady growth from January to February, with a slight dip in March."
        self.mock_llm_service.generate_data_insights.return_value = ["Sales increased 20% from January to February", "March showed a 8% decrease from February"]
        self.mock_llm_service.generate_follow_up_questions.return_value = ["Would you like to see quarterly totals?", "Should we compare this to last year?"]
        
        # Mock query executor
        self.mock_query_executor.execute_query.return_value = mock_query_results
        
        # Create chat request
        chat_request = ChatRequest(
            message="Show me monthly sales trends",
            conversation_id="test-conversation"
        )
        
        # Process the chat message
        response = await self.chat_service.process_chat_message(chat_request)
        
        # Verify response structure
        assert isinstance(response, ConversationalResponse)
        assert response.message is not None
        assert len(response.message) > 0
        
        # Verify automatic chart recommendation was generated
        assert response.chart_config is not None, "Should generate chart config for automatic dashboard update"
        assert isinstance(response.chart_config, ChartConfig)
        
        # Verify chart configuration is appropriate for the data
        assert response.chart_config.type in ["line", "bar"], "Should recommend appropriate chart type for time series data"
        assert response.chart_config.x_axis == "month", "Should use month as x-axis"
        assert response.chart_config.y_axis == "sales", "Should use sales as y-axis"
        assert response.chart_config.title is not None, "Should include chart title"
        
        # Verify insights and follow-up questions are included
        assert len(response.insights) > 0, "Should include insights"
        assert len(response.follow_up_questions) > 0, "Should include follow-up questions"
        
        # Verify conversation ID is maintained
        assert response.conversation_id == "test-conversation"
    
    @pytest.mark.asyncio
    async def test_no_chart_for_unsuitable_data(self):
        """Test that no chart is generated for data unsuitable for visualization."""
        
        # Mock query results that should NOT generate a chart
        mock_query_results = ExecuteResponse(
            columns=["description", "notes"],
            rows=[
                ["Long text description here", "Additional notes"],
                ["Another description", "More notes"],
            ],
            row_count=2,
            runtime_ms=30.0,
            truncated=False
        )
        
        # Mock LLM service responses
        self.mock_llm_service.translate_to_sql.return_value = "SELECT description, notes FROM customer_info"
        self.mock_llm_service.generate_conversational_explanation.return_value = "Here is the customer information you requested."
        self.mock_llm_service.generate_data_insights.return_value = ["Found 2 customer records"]
        self.mock_llm_service.generate_follow_up_questions.return_value = ["Would you like to see specific customer details?"]
        
        # Mock query executor
        self.mock_query_executor.execute_query.return_value = mock_query_results
        
        # Create chat request
        chat_request = ChatRequest(
            message="Show me customer descriptions",
            conversation_id="test-conversation-2"
        )
        
        # Process the chat message
        response = await self.chat_service.process_chat_message(chat_request)
        
        # Verify response structure
        assert isinstance(response, ConversationalResponse)
        assert response.message is not None
        
        # Verify NO chart recommendation was generated
        assert response.chart_config is None, "Should not generate chart config for text-heavy data"
        
        # Verify other response elements are still present
        assert len(response.insights) > 0, "Should still include insights"
        assert len(response.follow_up_questions) > 0, "Should still include follow-up questions"
    
    @pytest.mark.asyncio
    async def test_chart_recommendation_for_single_metric(self):
        """Test that appropriate chart is recommended for single metric queries."""
        
        # Mock query results for a single metric
        mock_query_results = ExecuteResponse(
            columns=["total_revenue"],
            rows=[[150000]],
            row_count=1,
            runtime_ms=20.0,
            truncated=False
        )
        
        # Mock LLM service responses
        self.mock_llm_service.translate_to_sql.return_value = "SELECT SUM(revenue) as total_revenue FROM sales"
        self.mock_llm_service.generate_conversational_explanation.return_value = "Your total revenue is $150,000."
        self.mock_llm_service.generate_data_insights.return_value = ["Total revenue reached $150,000"]
        self.mock_llm_service.generate_follow_up_questions.return_value = ["How does this compare to last quarter?"]
        
        # Mock query executor
        self.mock_query_executor.execute_query.return_value = mock_query_results
        
        # Create chat request with metric-focused question
        chat_request = ChatRequest(
            message="What is our total revenue?",
            conversation_id="test-conversation-3"
        )
        
        # Process the chat message
        response = await self.chat_service.process_chat_message(chat_request)
        
        # Verify response structure
        assert isinstance(response, ConversationalResponse)
        
        # Verify chart recommendation was generated for the metric
        assert response.chart_config is not None, "Should generate chart config for meaningful single metrics"
        assert response.chart_config.type == "bar", "Should recommend bar chart for single metric display"
    
    def test_chart_recommendation_service_integration(self):
        """Test that the chart recommendation service integrates correctly with chat service."""
        
        # Verify the chat service has the chart recommendation service
        assert self.chat_service.chart_recommendation_service is not None
        assert isinstance(self.chat_service.chart_recommendation_service, ChartRecommendationService)
        
        # Test direct chart recommendation
        mock_query_results = ExecuteResponse(
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
        
        # Test that chart recommendation works
        should_create = self.chart_service.should_create_visualization(mock_query_results, user_question)
        assert should_create is True
        
        chart_config = self.chart_service.recommend_chart_config(mock_query_results, user_question)
        assert chart_config is not None
        assert chart_config.type == "bar"
        assert chart_config.x_axis == "category"
        assert chart_config.y_axis == "count"
    
    @pytest.mark.asyncio
    async def test_error_handling_preserves_chat_functionality(self):
        """Test that errors in chart recommendation don't break chat functionality."""
        
        # Mock query results
        mock_query_results = ExecuteResponse(
            columns=["data"],
            rows=[["test"]],
            row_count=1,
            runtime_ms=10.0,
            truncated=False
        )
        
        # Mock LLM service responses
        self.mock_llm_service.translate_to_sql.return_value = "SELECT data FROM test_table"
        self.mock_llm_service.generate_conversational_explanation.return_value = "Here is your data."
        self.mock_llm_service.generate_data_insights.return_value = ["Found test data"]
        self.mock_llm_service.generate_follow_up_questions.return_value = ["What else would you like to see?"]
        
        # Mock query executor
        self.mock_query_executor.execute_query.return_value = mock_query_results
        
        # Mock chart recommendation service to raise an exception
        with patch.object(self.chat_service.chart_recommendation_service, 'recommend_chart_config', side_effect=Exception("Chart error")):
            
            # Create chat request
            chat_request = ChatRequest(
                message="Show me test data",
                conversation_id="test-conversation-error"
            )
            
            # Process the chat message - should not fail even if chart recommendation fails
            response = await self.chat_service.process_chat_message(chat_request)
            
            # Verify chat functionality still works
            assert isinstance(response, ConversationalResponse)
            assert response.message is not None
            assert len(response.message) > 0
            
            # Chart config should be None due to error, but chat should still work
            assert response.chart_config is None
            
            # Other functionality should be preserved
            assert len(response.insights) > 0
            assert len(response.follow_up_questions) > 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])