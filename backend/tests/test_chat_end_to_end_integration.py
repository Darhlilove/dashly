"""
Comprehensive end-to-end integration tests for chat functionality.

Tests cover the complete flow from natural language question to conversational response,
including all service integrations and error scenarios as specified in requirements.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import shutil

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from chat_service import ChatService
from models import ChatRequest, ConversationalResponse, ChartConfig, ExecuteResponse
from exceptions import SQLSchemaError, TableNotFoundError, QueryTimeoutError


class TestChatEndToEndIntegration:
    """End-to-end integration tests for complete chat functionality."""
    
    def setup_method(self):
        """Set up test fixtures with realistic service mocks."""
        # Create temporary directory for conversation storage
        self.temp_dir = tempfile.mkdtemp()
        
        # Create realistic mock services
        self.setup_mock_services()
        
        # Create ChatService with all dependencies
        self.chat_service = ChatService(
            query_executor=self.mock_query_executor,
            llm_service=self.mock_llm_service,
            response_generator=self.mock_response_generator,
            insight_analyzer=self.mock_insight_analyzer,
            chart_recommendation_service=self.mock_chart_service,
            conversation_history_manager=self.mock_conversation_manager,
            proactive_exploration_service=self.mock_proactive_service,
            db_manager=self.mock_db_manager,
            schema_service=self.mock_schema_service
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def setup_mock_services(self):
        """Set up realistic mock services for integration testing."""
        # Mock Query Executor
        self.mock_query_executor = Mock()
        self.mock_execute_response = ExecuteResponse(
            columns=["product", "sales", "date", "region"],
            rows=[
                ["Product A", 15000, "2023-01-01", "North"],
                ["Product B", 25000, "2023-01-02", "South"],
                ["Product C", 18000, "2023-01-03", "East"],
                ["Product D", 22000, "2023-01-04", "West"]
            ],
            row_count=4,
            runtime_ms=125.5,
            truncated=False
        )
        self.mock_query_executor.execute_query.return_value = self.mock_execute_response
        
        # Mock LLM Service
        self.mock_llm_service = Mock()
        self.mock_llm_service.translate_to_sql.return_value = "SELECT product, sales, date, region FROM sales_data ORDER BY sales DESC"
        self.mock_llm_service.generate_conversational_explanation.return_value = (
            "Great question! I found your top-performing products. Product B is leading with $25,000 in sales, "
            "followed by Product D at $22,000. Your sales are distributed across all regions, which shows good "
            "market coverage. The data spans from January 1st to 4th, giving us a nice snapshot of recent performance."
        )
        self.mock_llm_service.generate_data_insights.return_value = [
            "Product B is your top performer with 39% higher sales than the average",
            "All four regions are represented, showing good geographic distribution",
            "Sales range from $15K to $25K, indicating consistent product performance"
        ]
        self.mock_llm_service.generate_follow_up_questions.return_value = [
            "Which region is performing best overall?",
            "How do these sales compare to last month?",
            "What factors might be driving Product B's success?"
        ]
        
        # Mock Response Generator
        self.mock_response_generator = Mock()
        self.mock_response_generator.generate_conversational_response.return_value = ConversationalResponse(
            message="I've analyzed your product sales data and found some interesting patterns!",
            chart_config=ChartConfig(type="bar", x_axis="product", y_axis="sales"),
            insights=["Sales performance varies significantly across products"],
            follow_up_questions=["Would you like to see regional breakdowns?"],
            processing_time_ms=100.0,
            conversation_id="test_conv"
        )
        
        # Mock Insight Analyzer
        self.mock_insight_analyzer = Mock()
        self.mock_insight_analyzer.analyze_query_results.return_value = {
            "trends": [Mock(message="Sales show upward trend", type="trend", confidence=0.8)],
            "outliers": [Mock(message="Product B is an outlier", type="outlier", confidence=0.9)],
            "summary": [Mock(message="Found 4 products", type="summary", confidence=1.0)],
            "all_insights": [
                Mock(message="Sales show upward trend"),
                Mock(message="Product B is an outlier"),
                Mock(message="Found 4 products")
            ],
            "follow_up_questions": ["What drives the sales differences?", "Are there seasonal patterns?"],
            "data_quality": {
                "row_count": 4,
                "column_count": 4,
                "has_numeric_data": True,
                "completeness": 1.0
            }
        }
        
        # Mock Chart Recommendation Service
        self.mock_chart_service = Mock()
        self.mock_chart_config = ChartConfig(
            type="bar",
            x_axis="product",
            y_axis="sales",
            title="Product Sales Performance"
        )
        self.mock_chart_service.recommend_chart_config.return_value = self.mock_chart_config
        
        # Mock Conversation History Manager
        self.mock_conversation_manager = Mock()
        self.mock_conversation_manager.create_conversation.return_value = "conv_12345"
        self.mock_conversation_manager.add_message.return_value = None
        self.mock_conversation_manager.get_conversation_history.return_value = []
        self.mock_conversation_manager.get_conversation_context.return_value = {
            "user_questions": [],
            "topics": [],
            "recent_context": ""
        }
        
        # Mock Proactive Exploration Service
        self.mock_proactive_service = Mock()
        self.mock_proactive_service.detect_proactive_insights.return_value = [
            Mock(
                message="I notice Product B significantly outperforms others - this could indicate a successful marketing campaign or product feature",
                insight_type="business_opportunity",
                confidence=0.85,
                suggested_actions=["Analyze Product B's success factors", "Apply learnings to other products"]
            )
        ]
        self.mock_proactive_service.generate_initial_questions.return_value = [
            Mock(question="What are your best-selling products?"),
            Mock(question="How are sales distributed across regions?"),
            Mock(question="What trends do you see in recent sales data?")
        ]
        
        # Mock Database and Schema Services
        self.mock_db_manager = Mock()
        self.mock_schema_service = Mock()
    
    @pytest.mark.asyncio
    async def test_complete_chat_flow_new_conversation(self):
        """Test complete chat flow from question to response with new conversation."""
        # Test the full flow: question → SQL → execution → analysis → response
        request = ChatRequest(
            message="Show me my top-selling products",
            conversation_id=None
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Verify complete response structure
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id is not None
        assert len(response.message) > 0
        assert response.chart_config is not None
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        assert response.processing_time_ms > 0
        
        # Verify service integration calls
        self.mock_llm_service.translate_to_sql.assert_called_once()
        self.mock_query_executor.execute_query.assert_called_once()
        self.mock_llm_service.generate_conversational_explanation.assert_called_once()
        self.mock_llm_service.generate_data_insights.assert_called_once()
        self.mock_llm_service.generate_follow_up_questions.assert_called_once()
        self.mock_insight_analyzer.analyze_query_results.assert_called_once()
        self.mock_chart_service.recommend_chart_config.assert_called_once()
        self.mock_conversation_manager.add_message.assert_called()
        
        # Verify conversation was created
        self.mock_conversation_manager.create_conversation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_chat_flow_existing_conversation(self):
        """Test complete chat flow with existing conversation context."""
        conversation_id = "existing_conv_789"
        
        # Setup existing conversation context
        self.mock_conversation_manager.get_conversation_context.return_value = {
            "user_questions": ["What are my sales numbers?"],
            "topics": ["sales", "products"],
            "recent_context": "User previously asked about sales data"
        }
        
        request = ChatRequest(
            message="Break that down by region",
            conversation_id=conversation_id
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Verify response uses existing conversation
        assert response.conversation_id == conversation_id
        
        # Verify context was retrieved and used
        self.mock_conversation_manager.get_conversation_context.assert_called_with(conversation_id)
        
        # Verify LLM services received context
        explanation_call = self.mock_llm_service.generate_conversational_explanation.call_args
        assert "context" in explanation_call[1]
        assert "previous_questions" in explanation_call[1]["context"]
        
        followup_call = self.mock_llm_service.generate_follow_up_questions.call_args
        assert "conversation_context" in followup_call[1]
    
    @pytest.mark.asyncio
    async def test_chat_flow_with_chart_generation(self):
        """Test chat flow that generates dashboard charts."""
        request = ChatRequest(
            message="Show me sales by product in a chart",
            conversation_id=None
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Verify chart was generated and included
        assert response.chart_config is not None
        assert response.chart_config.type == "bar"
        assert response.chart_config.x_axis == "product"
        assert response.chart_config.y_axis == "sales"
        
        # Verify chart recommendation service was called with correct data
        self.mock_chart_service.recommend_chart_config.assert_called_once()
        chart_call_args = self.mock_chart_service.recommend_chart_config.call_args
        assert chart_call_args[0][0] == self.mock_execute_response  # Query results
        assert "chart" in chart_call_args[0][1].lower()  # User message
    
    @pytest.mark.asyncio
    async def test_chat_flow_with_proactive_insights(self):
        """Test chat flow that generates proactive insights."""
        request = ChatRequest(
            message="Analyze my product performance",
            conversation_id=None
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Verify proactive insights were included
        assert len(response.insights) > 0
        
        # Should include both LLM insights and proactive insights
        insights_text = " ".join(response.insights).lower()
        assert "product b" in insights_text or "outperform" in insights_text
        
        # Verify proactive service was called
        self.mock_proactive_service.detect_proactive_insights.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_flow_error_handling_sql_error(self):
        """Test chat flow error handling for SQL errors."""
        # Setup SQL error
        self.mock_llm_service.translate_to_sql.side_effect = SQLSchemaError(
            "Column 'invalid_column' does not exist",
            missing_object="invalid_column"
        )
        
        request = ChatRequest(
            message="Show me invalid_column data",
            conversation_id="error_test_conv"
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Should return error response, not raise exception
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == "error_test_conv"
        
        # Error response should be beginner-friendly
        error_message = response.message.lower()
        assert any(word in error_message for word in ["couldn't find", "trouble", "issue", "sorry"])
        assert "invalid_column" not in error_message  # Should hide technical details
        
        # Should provide helpful suggestions
        assert len(response.follow_up_questions) > 0
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in ["available", "columns", "data", "try"])
    
    @pytest.mark.asyncio
    async def test_chat_flow_error_handling_timeout(self):
        """Test chat flow error handling for query timeouts."""
        # Setup timeout error
        self.mock_query_executor.execute_query.side_effect = QueryTimeoutError(
            "Query execution timed out after 30 seconds",
            timeout_seconds=30
        )
        
        request = ChatRequest(
            message="Show me all data with complex calculations",
            conversation_id="timeout_test_conv"
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Should handle timeout gracefully
        assert isinstance(response, ConversationalResponse)
        
        # Error message should be conversational
        error_message = response.message.lower()
        assert any(phrase in error_message for phrase in ["taking too long", "bit slow", "try simpler"])
        
        # Should suggest alternatives
        assert len(response.follow_up_questions) > 0
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in ["simpler", "smaller", "subset"])
    
    @pytest.mark.asyncio
    async def test_chat_flow_no_data_found(self):
        """Test chat flow when no data is found."""
        # Setup empty results
        empty_response = ExecuteResponse(
            columns=["product", "sales"],
            rows=[],
            row_count=0,
            runtime_ms=50.0,
            truncated=False
        )
        self.mock_query_executor.execute_query.return_value = empty_response
        
        # Update LLM service for empty data scenario
        self.mock_llm_service.generate_conversational_explanation.return_value = (
            "I looked for that data but couldn't find any results matching your criteria. "
            "This might mean the data doesn't exist or we need to adjust the search parameters."
        )
        self.mock_llm_service.generate_data_insights.return_value = [
            "No matching records found in the current dataset"
        ]
        self.mock_llm_service.generate_follow_up_questions.return_value = [
            "Would you like to see what data is available?",
            "Should we try a different search approach?",
            "Are you looking for data from a specific time period?"
        ]
        
        request = ChatRequest(
            message="Show me sales for non-existent product",
            conversation_id=None
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Should handle empty results gracefully
        assert isinstance(response, ConversationalResponse)
        
        # Message should explain no data found
        message_lower = response.message.lower()
        assert any(phrase in message_lower for phrase in ["couldn't find", "no results", "no data"])
        
        # Should provide helpful alternatives
        assert len(response.follow_up_questions) > 0
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in ["available", "different", "try"])
        
        # Should not recommend chart for empty data
        assert response.chart_config is None
    
    @pytest.mark.asyncio
    async def test_chat_flow_conversation_context_building(self):
        """Test that conversation context builds up over multiple interactions."""
        conversation_id = "context_building_conv"
        
        # First interaction
        request1 = ChatRequest(
            message="Show me sales data",
            conversation_id=conversation_id
        )
        
        response1 = await self.chat_service.process_chat_message(request1)
        assert response1.conversation_id == conversation_id
        
        # Update context for second interaction
        self.mock_conversation_manager.get_conversation_context.return_value = {
            "user_questions": ["Show me sales data"],
            "topics": ["sales", "data"],
            "recent_context": "User asked about sales data"
        }
        
        # Second interaction with context
        request2 = ChatRequest(
            message="Break it down by month",
            conversation_id=conversation_id
        )
        
        response2 = await self.chat_service.process_chat_message(request2)
        
        # Verify context was used in second interaction
        assert response2.conversation_id == conversation_id
        
        # Verify conversation manager was called to get context
        context_calls = self.mock_conversation_manager.get_conversation_context.call_args_list
        assert len(context_calls) >= 2
        assert all(call[0][0] == conversation_id for call in context_calls)
        
        # Verify messages were added to conversation
        add_message_calls = self.mock_conversation_manager.add_message.call_args_list
        assert len(add_message_calls) >= 4  # 2 user messages + 2 assistant responses
    
    @pytest.mark.asyncio
    async def test_chat_flow_performance_optimization(self):
        """Test chat flow performance optimizations (caching, streaming)."""
        request = ChatRequest(
            message="Show me quick sales summary",
            conversation_id=None
        )
        
        # First request - should process normally
        response1 = await self.chat_service.process_chat_message(request)
        assert isinstance(response1, ConversationalResponse)
        assert response1.processing_time_ms > 0
        
        # Mock cache hit for second identical request
        with patch.object(self.chat_service.response_cache, 'get_chat_response') as mock_cache_get:
            cached_response = ConversationalResponse(
                message="Cached response for quick sales summary",
                insights=["Cached insight"],
                follow_up_questions=["Cached question?"],
                processing_time_ms=5.0,
                conversation_id="cached_conv"
            )
            mock_cache_get.return_value = cached_response
            
            # Second identical request - should use cache
            response2 = await self.chat_service.process_chat_message(request)
            
            # Should return cached response
            assert response2.message == "Cached response for quick sales summary"
            assert response2.processing_time_ms == 5.0
            
            # Cache should have been checked
            mock_cache_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_flow_with_streaming(self):
        """Test chat flow with streaming support."""
        request = ChatRequest(
            message="Analyze complex sales patterns",
            conversation_id=None
        )
        stream_id = "test_stream_456"
        
        # Mock streaming processor
        mock_streamed_response = ConversationalResponse(
            message="Streamed analysis of your sales patterns shows interesting trends...",
            insights=["Streaming insight 1", "Streaming insight 2"],
            follow_up_questions=["Streamed question 1?", "Streamed question 2?"],
            processing_time_ms=200.0,
            conversation_id="streamed_conv"
        )
        
        with patch.object(self.chat_service.stream_processor, 'process_with_streaming', new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = mock_streamed_response
            
            response = await self.chat_service.process_chat_message_with_streaming(request, stream_id)
            
            # Should use streaming processor
            assert response == mock_streamed_response
            mock_stream.assert_called_once()
            
            # Verify streaming processor was called with correct arguments
            call_args = mock_stream.call_args
            assert call_args[0][0] == stream_id
            assert call_args[0][2] == request  # The request object
    
    @pytest.mark.asyncio
    async def test_chat_flow_fallback_mode(self):
        """Test chat flow fallback when services are unavailable."""
        # Create service without query executor and LLM service
        fallback_service = ChatService(
            query_executor=None,
            llm_service=None
        )
        
        request = ChatRequest(
            message="Show me some data insights",
            conversation_id=None
        )
        
        response = await fallback_service.process_chat_message(request)
        
        # Should return mock response in fallback mode
        assert isinstance(response, ConversationalResponse)
        assert len(response.message) > 0
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        assert response.conversation_id is not None
        
        # Should not have chart config in fallback mode
        assert response.chart_config is None
    
    def test_chat_service_initialization_integration(self):
        """Test ChatService initialization with all components."""
        # Verify all components are properly initialized
        assert self.chat_service.query_executor is not None
        assert self.chat_service.llm_service is not None
        assert self.chat_service.response_generator is not None
        assert self.chat_service.insight_analyzer is not None
        assert self.chat_service.chart_recommendation_service is not None
        assert self.chat_service.conversation_history_manager is not None
        assert self.chat_service.proactive_exploration_service is not None
        assert self.chat_service.error_handler is not None
        assert self.chat_service.response_cache is not None
        assert self.chat_service.streaming_manager is not None
    
    def test_conversation_management_integration(self):
        """Test conversation management integration."""
        conversation_id = "mgmt_test_conv"
        
        # Test getting conversation history
        mock_history = [
            {"role": "user", "message": "Test question"},
            {"role": "assistant", "message": "Test response"}
        ]
        self.mock_conversation_manager.get_conversation_history.return_value = mock_history
        
        history = self.chat_service.get_conversation_history(conversation_id)
        assert history == mock_history
        
        # Test clearing conversation
        self.mock_conversation_manager.clear_conversation.return_value = True
        result = self.chat_service.clear_conversation_history(conversation_id)
        assert result is True
        
        # Test getting conversation summary
        mock_summary = {"id": conversation_id, "message_count": 2}
        self.mock_conversation_manager.get_conversation_summary.return_value = mock_summary
        summary = self.chat_service.get_conversation_summary(conversation_id)
        assert summary == mock_summary
    
    def test_proactive_exploration_integration(self):
        """Test proactive exploration service integration."""
        # Test initial question generation
        mock_initial_questions = [
            Mock(question="What does your data look like?"),
            Mock(question="What patterns can we find?")
        ]
        self.mock_proactive_service.generate_initial_questions.return_value = mock_initial_questions
        
        questions = self.chat_service.generate_initial_data_questions("sales")
        assert len(questions) == 2
        assert "What does your data look like?" in questions
        
        # Test contextual suggestions
        mock_contextual = [
            Mock(question="How about regional analysis?"),
            Mock(question="What about time trends?")
        ]
        self.mock_proactive_service.generate_contextual_suggestions.return_value = mock_contextual
        
        suggestions = self.chat_service.get_contextual_suggestions("test_conv")
        assert len(suggestions) == 2
        assert "How about regional analysis?" in suggestions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])