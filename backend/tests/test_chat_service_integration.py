"""
Test integration between ChatService and enhanced LLMService.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

try:
    from src.chat_service import ChatService
    from src.models import ChatRequest
    from src.llm_service import LLMService
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from src.chat_service import ChatService
    from src.models import ChatRequest
    from src.llm_service import LLMService


class TestChatServiceIntegration:
    """Test ChatService integration with enhanced LLMService."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Mock enhanced LLM service."""
        llm_service = Mock(spec=LLMService)
        llm_service.translate_to_sql = AsyncMock(return_value="SELECT * FROM sales")
        llm_service.generate_conversational_explanation = AsyncMock(
            return_value="Your sales data shows great growth this quarter! Revenue increased by 25% compared to last quarter."
        )
        llm_service.generate_data_insights = AsyncMock(
            return_value=[
                "Sales growth of 25% indicates strong market demand",
                "Customer acquisition is accelerating",
                "Revenue per customer is increasing"
            ]
        )
        llm_service.generate_follow_up_questions = AsyncMock(
            return_value=[
                "What products are driving this growth?",
                "How does this compare to last year?",
                "Which regions are performing best?"
            ]
        )
        return llm_service
    
    @pytest.fixture
    def mock_query_executor(self):
        """Mock query executor."""
        executor = Mock()
        executor.execute_query = AsyncMock(return_value={
            "data": [
                {"month": "Q1", "sales": 100000, "customers": 500},
                {"month": "Q2", "sales": 125000, "customers": 625}
            ],
            "columns": ["month", "sales", "customers"]
        })
        return executor
    
    @pytest.fixture
    def mock_insight_analyzer(self):
        """Mock insight analyzer."""
        analyzer = Mock()
        analyzer.analyze_query_results = Mock(return_value={
            "all_insights": [
                Mock(message="Trend analysis shows consistent growth"),
                Mock(message="Seasonal patterns detected")
            ],
            "follow_up_questions": ["What about seasonal trends?"]
        })
        return analyzer
    
    @pytest.fixture
    def chat_service(self, mock_llm_service, mock_query_executor, mock_insight_analyzer):
        """Create ChatService with mocked dependencies."""
        return ChatService(
            query_executor=mock_query_executor,
            llm_service=mock_llm_service,
            insight_analyzer=mock_insight_analyzer
        )
    
    @pytest.mark.asyncio
    async def test_enhanced_chat_processing(self, chat_service, mock_llm_service):
        """Test that ChatService uses enhanced LLM service methods."""
        request = ChatRequest(
            message="Show me quarterly sales growth",
            conversation_id="test_conv_123"
        )
        
        response = await chat_service.process_chat_message(request)
        
        # Verify enhanced LLM methods were called
        mock_llm_service.translate_to_sql.assert_called_once()
        mock_llm_service.generate_conversational_explanation.assert_called_once()
        mock_llm_service.generate_data_insights.assert_called_once()
        mock_llm_service.generate_follow_up_questions.assert_called_once()
        
        # Verify response contains conversational content
        assert "great growth" in response.message.lower()
        assert "25%" in response.message
        
        # Verify insights are business-focused
        assert len(response.insights) > 0
        assert "market demand" in response.insights[0].lower()
        
        # Verify follow-up questions are natural
        assert len(response.follow_up_questions) > 0
        assert "products" in response.follow_up_questions[0].lower()
    
    @pytest.mark.asyncio
    async def test_conversation_context_usage(self, chat_service, mock_llm_service):
        """Test that conversation context is passed to LLM service."""
        # First message
        request1 = ChatRequest(
            message="Show me sales data",
            conversation_id="test_conv_456"
        )
        await chat_service.process_chat_message(request1)
        
        # Second message with context
        request2 = ChatRequest(
            message="Break it down by region",
            conversation_id="test_conv_456"
        )
        await chat_service.process_chat_message(request2)
        
        # Verify context was passed to LLM methods
        explanation_call = mock_llm_service.generate_conversational_explanation.call_args_list[-1]
        context_arg = explanation_call[1]["context"]
        assert "previous_questions" in context_arg
        assert "Show me sales data" in context_arg["previous_questions"]
        
        followup_call = mock_llm_service.generate_follow_up_questions.call_args_list[-1]
        conversation_context = followup_call[1]["conversation_context"]
        assert "Show me sales data" in conversation_context


if __name__ == "__main__":
    # Run a simple integration test
    async def run_integration_test():
        print("Testing ChatService integration with enhanced LLMService...")
        
        # Create mocks
        llm_service = Mock(spec=LLMService)
        llm_service.translate_to_sql = AsyncMock(return_value="SELECT * FROM test")
        llm_service.generate_conversational_explanation = AsyncMock(
            return_value="This is a conversational explanation of your data."
        )
        llm_service.generate_data_insights = AsyncMock(
            return_value=["Insight 1", "Insight 2"]
        )
        llm_service.generate_follow_up_questions = AsyncMock(
            return_value=["Question 1?", "Question 2?"]
        )
        
        query_executor = Mock()
        query_executor.execute_query = AsyncMock(return_value={
            "data": [{"test": "value"}],
            "columns": ["test"]
        })
        
        # Create chat service
        chat_service = ChatService(
            query_executor=query_executor,
            llm_service=llm_service
        )
        
        # Test processing
        request = ChatRequest(
            message="Test question",
            conversation_id="test_123"
        )
        
        response = await chat_service.process_chat_message(request)
        
        print(f"Response message: {response.message}")
        print(f"Insights: {response.insights}")
        print(f"Follow-up questions: {response.follow_up_questions}")
        
        # Verify methods were called
        assert llm_service.generate_conversational_explanation.called
        assert llm_service.generate_data_insights.called
        assert llm_service.generate_follow_up_questions.called
        
        print("✅ Integration test passed!")
    
    asyncio.run(run_integration_test())