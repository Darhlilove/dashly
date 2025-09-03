"""
Comprehensive unit tests for ChatService class.

Tests cover all core functionality including message processing, conversation management,
error handling, and integration with various services as specified in requirements.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from chat_service import ChatService
from models import ChatRequest, ConversationalResponse, ChartConfig, ExecuteResponse
from exceptions import SQLSchemaError, TableNotFoundError, QueryTimeoutError


class TestChatServiceUnit:
    """Comprehensive unit tests for ChatService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mocked dependencies
        self.mock_query_executor = Mock()
        self.mock_llm_service = Mock()
        self.mock_response_generator = Mock()
        self.mock_insight_analyzer = Mock()
        self.mock_chart_service = Mock()
        self.mock_conversation_manager = Mock()
        self.mock_proactive_service = Mock()
        self.mock_db_manager = Mock()
        self.mock_schema_service = Mock()
        
        # Create ChatService instance with mocked dependencies
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
    
    def test_initialization(self):
        """Test ChatService initialization with all dependencies."""
        assert self.chat_service.query_executor == self.mock_query_executor
        assert self.chat_service.llm_service == self.mock_llm_service
        assert self.chat_service.response_generator == self.mock_response_generator
        assert self.chat_service.insight_analyzer == self.mock_insight_analyzer
        assert self.chat_service.chart_recommendation_service == self.mock_chart_service
        assert self.chat_service.conversation_history_manager == self.mock_conversation_manager
        assert self.chat_service.proactive_exploration_service == self.mock_proactive_service
        assert self.chat_service.error_handler is not None
        assert self.chat_service.response_cache is not None
        assert self.chat_service.streaming_manager is not None
    
    def test_initialization_with_defaults(self):
        """Test ChatService initialization with default dependencies."""
        service = ChatService()
        assert service.response_generator is not None
        assert service.insight_analyzer is not None
        assert service.chart_recommendation_service is not None
        assert service.conversation_history_manager is not None
        assert service.error_handler is not None
    
    @pytest.mark.asyncio
    async def test_process_chat_message_new_conversation(self):
        """Test processing chat message with new conversation creation."""
        # Setup mocks
        self.mock_conversation_manager.create_conversation.return_value = "new_conv_123"
        self.mock_conversation_manager.add_message.return_value = None
        self.mock_conversation_manager.get_conversation_context.return_value = {
            "user_questions": [],
            "topics": []
        }
        
        # Mock LLM service methods
        self.mock_llm_service.translate_to_sql.return_value = "SELECT * FROM sales"
        self.mock_llm_service.generate_conversational_explanation.return_value = "Here are your sales results!"
        self.mock_llm_service.generate_data_insights.return_value = ["Sales are trending upward"]
        self.mock_llm_service.generate_follow_up_questions.return_value = ["What about quarterly data?"]
        
        # Mock query executor
        mock_execute_response = ExecuteResponse(
            columns=["sales", "month"],
            rows=[["1000", "January"]],
            row_count=1,
            runtime_ms=50.0
        )
        self.mock_query_executor.execute_query.return_value = mock_execute_response
        
        # Mock insight analyzer
        self.mock_insight_analyzer.analyze_query_results.return_value = {
            "all_insights": [Mock(message="Data insight")],
            "follow_up_questions": ["Analyzer question?"]
        }
        
        # Mock chart service
        mock_chart_config = ChartConfig(type="bar", x_axis="month", y_axis="sales")
        self.mock_chart_service.recommend_chart_config.return_value = mock_chart_config
        
        # Mock proactive service
        self.mock_proactive_service.detect_proactive_insights.return_value = [
            Mock(message="Proactive insight", insight_type="trend", confidence=0.8, suggested_actions=[])
        ]
        
        request = ChatRequest(message="Show me sales data", conversation_id=None)
        response = await self.chat_service.process_chat_message(request)
        
        # Verify response
        assert isinstance(response, ConversationalResponse)
        assert response.message == "Here are your sales results!"
        assert "Sales are trending upward" in response.insights
        assert "What about quarterly data?" in response.follow_up_questions
        assert response.chart_config == mock_chart_config
        assert response.conversation_id is not None
        
        # Verify conversation was created and messages added
        self.mock_conversation_manager.add_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_chat_message_existing_conversation(self):
        """Test processing chat message with existing conversation."""
        conversation_id = "existing_conv_456"
        
        # Setup mocks for existing conversation
        self.mock_conversation_manager.get_conversation_context.return_value = {
            "user_questions": ["Previous question"],
            "topics": ["sales"]
        }
        
        # Mock services
        self.mock_llm_service.translate_to_sql.return_value = "SELECT * FROM sales WHERE month = 'January'"
        self.mock_llm_service.generate_conversational_explanation.return_value = "January sales look great!"
        self.mock_llm_service.generate_data_insights.return_value = ["January showed strong performance"]
        self.mock_llm_service.generate_follow_up_questions.return_value = ["How about February?"]
        
        mock_execute_response = ExecuteResponse(
            columns=["sales"], rows=[["1500"]], row_count=1, runtime_ms=75.0
        )
        self.mock_query_executor.execute_query.return_value = mock_execute_response
        
        self.mock_insight_analyzer.analyze_query_results.return_value = {
            "all_insights": [],
            "follow_up_questions": []
        }
        
        self.mock_chart_service.recommend_chart_config.return_value = None
        self.mock_proactive_service.detect_proactive_insights.return_value = []
        
        request = ChatRequest(message="Show me January sales", conversation_id=conversation_id)
        response = await self.chat_service.process_chat_message(request)
        
        # Verify response uses existing conversation
        assert response.conversation_id == conversation_id
        assert response.message == "January sales look great!"
        
        # Verify context was retrieved for existing conversation
        self.mock_conversation_manager.get_conversation_context.assert_called_with(conversation_id)
    
    @pytest.mark.asyncio
    async def test_process_chat_message_fallback_mode(self):
        """Test processing chat message without query executor (fallback mode)."""
        # Create service without query executor
        service = ChatService(llm_service=None, query_executor=None)
        
        request = ChatRequest(message="Show me sales data", conversation_id=None)
        response = await service.process_chat_message(request)
        
        # Should return mock response
        assert isinstance(response, ConversationalResponse)
        assert len(response.message) > 0
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        assert response.conversation_id is not None
    
    @pytest.mark.asyncio
    async def test_process_chat_message_error_handling(self):
        """Test error handling during chat message processing."""
        # Setup to cause an error
        self.mock_llm_service.translate_to_sql.side_effect = SQLSchemaError("Column not found")
        
        # Mock conversation manager
        self.mock_conversation_manager.add_message.return_value = None
        self.mock_conversation_manager.get_conversation_history.return_value = []
        
        request = ChatRequest(message="Show me invalid_column", conversation_id="test_conv")
        response = await self.chat_service.process_chat_message(request)
        
        # Should return error response, not raise exception
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == "test_conv"
        # Error handler should have been used
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
    
    def test_generate_mock_response_sales_keywords(self):
        """Test mock response generation for sales-related keywords."""
        response = self.chat_service._generate_mock_response("Show me sales revenue")
        assert "sales" in response.lower()
        assert len(response) > 0
    
    def test_generate_mock_response_customer_keywords(self):
        """Test mock response generation for customer-related keywords."""
        response = self.chat_service._generate_mock_response("Show me customer data")
        assert "customer" in response.lower()
        assert len(response) > 0
    
    def test_generate_mock_response_trend_keywords(self):
        """Test mock response generation for trend-related keywords."""
        response = self.chat_service._generate_mock_response("Show me trends over time")
        assert "trend" in response.lower() or "pattern" in response.lower()
        assert len(response) > 0
    
    def test_generate_mock_response_generic(self):
        """Test mock response generation for generic questions."""
        response = self.chat_service._generate_mock_response("What is this about?")
        assert len(response) > 0
        assert "question" in response.lower()
    
    def test_generate_mock_insights(self):
        """Test mock insights generation."""
        insights = self.chat_service._generate_mock_insights()
        assert isinstance(insights, list)
        assert len(insights) == 3
        assert all(isinstance(insight, str) for insight in insights)
        assert any("trend" in insight.lower() for insight in insights)
    
    def test_generate_mock_follow_up_questions(self):
        """Test mock follow-up questions generation."""
        questions = self.chat_service._generate_mock_follow_up_questions()
        assert isinstance(questions, list)
        assert len(questions) == 3
        assert all(isinstance(q, str) for q in questions)
        assert all("?" in q for q in questions)
    
    def test_get_conversation_history_persistent(self):
        """Test getting conversation history from persistent storage."""
        conversation_id = "test_conv_123"
        mock_history = [
            {"role": "user", "message": "Hello"},
            {"role": "assistant", "message": "Hi there!"}
        ]
        
        self.mock_conversation_manager.get_conversation_history.return_value = mock_history
        
        history = self.chat_service.get_conversation_history(conversation_id)
        
        assert history == mock_history
        self.mock_conversation_manager.get_conversation_history.assert_called_with(conversation_id)
    
    def test_get_conversation_history_fallback(self):
        """Test getting conversation history fallback to in-memory storage."""
        conversation_id = "test_conv_456"
        
        # Mock persistent storage returns empty
        self.mock_conversation_manager.get_conversation_history.return_value = []
        
        # Add to in-memory storage
        self.chat_service.conversation_history[conversation_id] = [
            {"role": "user", "message": "Test message"}
        ]
        
        history = self.chat_service.get_conversation_history(conversation_id)
        
        assert len(history) == 1
        assert history[0]["message"] == "Test message"
    
    def test_clear_conversation_history_success(self):
        """Test successful conversation history clearing."""
        conversation_id = "test_conv_789"
        
        # Setup mocks
        self.mock_conversation_manager.clear_conversation.return_value = True
        
        # Add to in-memory storage
        self.chat_service.conversation_history[conversation_id] = [{"role": "user", "message": "Test"}]
        
        result = self.chat_service.clear_conversation_history(conversation_id)
        
        assert result is True
        assert conversation_id not in self.chat_service.conversation_history
        self.mock_conversation_manager.clear_conversation.assert_called_with(conversation_id)
    
    def test_clear_conversation_history_not_found(self):
        """Test conversation history clearing when conversation not found."""
        conversation_id = "nonexistent_conv"
        
        self.mock_conversation_manager.clear_conversation.return_value = False
        
        result = self.chat_service.clear_conversation_history(conversation_id)
        
        assert result is False
    
    def test_get_conversation_context(self):
        """Test getting conversation context."""
        conversation_id = "test_conv_context"
        mock_context = {
            "user_questions": ["Question 1", "Question 2"],
            "topics": ["sales", "revenue"]
        }
        
        self.mock_conversation_manager.get_conversation_context.return_value = mock_context
        
        context = self.chat_service.get_conversation_context(conversation_id)
        
        assert context == mock_context
        self.mock_conversation_manager.get_conversation_context.assert_called_with(conversation_id)
    
    def test_get_conversation_context_empty_id(self):
        """Test getting conversation context with empty ID."""
        context = self.chat_service.get_conversation_context("")
        assert context == {}
        
        context = self.chat_service.get_conversation_context(None)
        assert context == {}
    
    def test_get_conversation_summary(self):
        """Test getting conversation summary."""
        conversation_id = "test_conv_summary"
        mock_summary = {
            "id": conversation_id,
            "message_count": 5,
            "first_question": "What is my data about?"
        }
        
        self.mock_conversation_manager.get_conversation_summary.return_value = mock_summary
        
        summary = self.chat_service.get_conversation_summary(conversation_id)
        
        assert summary == mock_summary
        self.mock_conversation_manager.get_conversation_summary.assert_called_with(conversation_id)
    
    def test_cleanup_expired_conversations(self):
        """Test cleanup of expired conversations."""
        self.mock_conversation_manager.cleanup_expired_conversations.return_value = 3
        
        cleaned_count = self.chat_service.cleanup_expired_conversations()
        
        assert cleaned_count == 3
        self.mock_conversation_manager.cleanup_expired_conversations.assert_called_once()
    
    def test_generate_initial_data_questions_success(self):
        """Test successful generation of initial data questions."""
        mock_suggestions = [
            Mock(question="What does my sales data look like?"),
            Mock(question="How many records do I have?")
        ]
        
        self.mock_proactive_service.generate_initial_questions.return_value = mock_suggestions
        
        questions = self.chat_service.generate_initial_data_questions("sales")
        
        assert len(questions) == 2
        assert "What does my sales data look like?" in questions
        assert "How many records do I have?" in questions
        self.mock_proactive_service.generate_initial_questions.assert_called_with("sales")
    
    def test_generate_initial_data_questions_error(self):
        """Test generation of initial data questions with error fallback."""
        self.mock_proactive_service.generate_initial_questions.side_effect = Exception("Service error")
        
        questions = self.chat_service.generate_initial_data_questions()
        
        # Should return fallback questions
        assert len(questions) == 3
        assert any("overall" in q.lower() for q in questions)
    
    def test_suggest_questions_from_data_structure_success(self):
        """Test successful question suggestions from data structure."""
        schema_info = {"tables": {"sales": {"columns": ["date", "amount", "customer"]}}}
        mock_suggestions = [
            Mock(question="What are the sales trends over time?"),
            Mock(question="Who are the top customers?")
        ]
        
        self.mock_proactive_service.suggest_questions_from_structure.return_value = mock_suggestions
        
        questions = self.chat_service.suggest_questions_from_data_structure(schema_info)
        
        assert len(questions) == 2
        assert "What are the sales trends over time?" in questions
        self.mock_proactive_service.suggest_questions_from_structure.assert_called_with(schema_info)
    
    def test_suggest_questions_from_data_structure_error(self):
        """Test question suggestions from data structure with error fallback."""
        self.mock_proactive_service.suggest_questions_from_structure.side_effect = Exception("Error")
        
        questions = self.chat_service.suggest_questions_from_data_structure({})
        
        # Should return fallback questions
        assert len(questions) == 3
        assert any("insights" in q.lower() for q in questions)
    
    def test_get_proactive_insights_success(self):
        """Test successful proactive insights generation."""
        mock_query_results = Mock()
        mock_insights = [
            Mock(
                message="Detected unusual spike in sales",
                insight_type="anomaly",
                confidence=0.9,
                suggested_actions=["Investigate cause"]
            )
        ]
        
        self.mock_proactive_service.detect_proactive_insights.return_value = mock_insights
        
        insights = self.chat_service.get_proactive_insights(mock_query_results, "sales question")
        
        assert len(insights) == 1
        assert insights[0]["message"] == "Detected unusual spike in sales"
        assert insights[0]["type"] == "anomaly"
        assert insights[0]["confidence"] == 0.9
    
    def test_get_proactive_insights_error(self):
        """Test proactive insights generation with error handling."""
        self.mock_proactive_service.detect_proactive_insights.side_effect = Exception("Error")
        
        insights = self.chat_service.get_proactive_insights(Mock(), "test question")
        
        # Should return empty list on error
        assert insights == []
    
    def test_get_contextual_suggestions_success(self):
        """Test successful contextual suggestions generation."""
        conversation_id = "test_conv"
        mock_history = [{"role": "user", "message": "Show me sales"}]
        mock_suggestions = [
            Mock(question="What about sales by region?"),
            Mock(question="How do sales compare to last year?")
        ]
        
        self.chat_service.get_conversation_history = Mock(return_value=mock_history)
        self.mock_proactive_service.generate_contextual_suggestions.return_value = mock_suggestions
        
        suggestions = self.chat_service.get_contextual_suggestions(conversation_id)
        
        assert len(suggestions) == 2
        assert "What about sales by region?" in suggestions
        self.mock_proactive_service.generate_contextual_suggestions.assert_called_with(mock_history)
    
    def test_get_contextual_suggestions_error(self):
        """Test contextual suggestions generation with error handling."""
        self.chat_service.get_conversation_history = Mock(side_effect=Exception("Error"))
        
        suggestions = self.chat_service.get_contextual_suggestions("test_conv")
        
        # Should return fallback suggestions
        assert len(suggestions) == 3
        assert any("explore" in s.lower() for s in suggestions)
    
    def test_analyze_data_insights(self):
        """Test public method for analyzing data insights."""
        mock_query_results = Mock()
        mock_analysis = {
            "trends": [],
            "outliers": [],
            "summary": [],
            "all_insights": [Mock(message="Test insight")],
            "follow_up_questions": ["Test question?"]
        }
        
        self.mock_insight_analyzer.analyze_query_results.return_value = mock_analysis
        
        result = self.chat_service.analyze_data_insights(mock_query_results, "test question")
        
        assert result == mock_analysis
        self.mock_insight_analyzer.analyze_query_results.assert_called_with(mock_query_results, "test question")
    
    def test_generate_context_hash_success(self):
        """Test successful context hash generation."""
        conversation_id = "test_conv"
        mock_history = [
            {"role": "user", "message": "First question about sales data"},
            {"role": "assistant", "message": "Here are your sales results"}
        ]
        
        self.chat_service.get_conversation_history = Mock(return_value=mock_history)
        
        hash_value = self.chat_service._generate_context_hash(conversation_id)
        
        assert isinstance(hash_value, str)
        assert len(hash_value) == 8  # MD5 hash truncated to 8 characters
    
    def test_generate_context_hash_error(self):
        """Test context hash generation with error fallback."""
        self.chat_service.get_conversation_history = Mock(side_effect=Exception("Error"))
        
        hash_value = self.chat_service._generate_context_hash("test_conv")
        
        assert hash_value == "default"
    
    @pytest.mark.asyncio
    async def test_process_chat_message_with_streaming_success(self):
        """Test chat message processing with streaming."""
        request = ChatRequest(message="Test message", conversation_id=None)
        stream_id = "test_stream_123"
        
        # Mock the stream processor
        mock_response = ConversationalResponse(
            message="Streamed response",
            insights=["Streamed insight"],
            follow_up_questions=["Streamed question?"],
            processing_time_ms=100.0,
            conversation_id="stream_conv"
        )
        
        self.chat_service.stream_processor.process_with_streaming = AsyncMock(return_value=mock_response)
        
        response = await self.chat_service.process_chat_message_with_streaming(request, stream_id)
        
        assert response == mock_response
        self.chat_service.stream_processor.process_with_streaming.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_chat_message_with_streaming_fallback(self):
        """Test chat message processing without streaming (fallback)."""
        request = ChatRequest(message="Test message", conversation_id=None)
        
        # Mock the regular process_chat_message method
        mock_response = ConversationalResponse(
            message="Regular response",
            insights=[],
            follow_up_questions=[],
            processing_time_ms=50.0,
            conversation_id="regular_conv"
        )
        
        with patch.object(self.chat_service, 'process_chat_message', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_response
            
            response = await self.chat_service.process_chat_message_with_streaming(request, None)
            
            assert response == mock_response
            mock_process.assert_called_once_with(request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])