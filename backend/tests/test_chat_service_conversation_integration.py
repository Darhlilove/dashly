"""
Integration tests for ChatService with ConversationHistoryManager.

Tests the integration between chat service and conversation history functionality.
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock

from src.chat_service import ChatService
from src.conversation_history_manager import ConversationHistoryManager
from src.models import ChatRequest, ConversationalResponse


class TestChatServiceConversationIntegration:
    """Test suite for ChatService conversation history integration."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def conversation_history_manager(self, temp_storage):
        """Create ConversationHistoryManager instance for testing."""
        return ConversationHistoryManager(storage_path=temp_storage)
    
    @pytest.fixture
    def mock_query_executor(self):
        """Create mock query executor."""
        mock = Mock()
        mock.execute_query = Mock(return_value=Mock(
            columns=["sales", "month"],
            rows=[["1000", "January"], ["1200", "February"]],
            row_count=2,
            runtime_ms=50.0
        ))
        return mock
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        mock = Mock()
        mock.translate_to_sql = Mock(return_value="SELECT * FROM sales")
        mock.generate_conversational_explanation = Mock(return_value="Here are your sales results.")
        mock.generate_data_insights = Mock(return_value=["Sales are trending upward"])
        mock.generate_follow_up_questions = Mock(return_value=["Would you like to see quarterly data?"])
        return mock
    
    @pytest.fixture
    def chat_service(self, conversation_history_manager, mock_query_executor, mock_llm_service):
        """Create ChatService instance with mocked dependencies."""
        return ChatService(
            query_executor=mock_query_executor,
            llm_service=mock_llm_service,
            conversation_history_manager=conversation_history_manager
        )
    
    @pytest.mark.asyncio
    async def test_conversation_history_persistence(self, chat_service, conversation_history_manager):
        """Test that conversation history is persisted across chat interactions."""
        # First message
        request1 = ChatRequest(message="What are my sales?", conversation_id=None)
        response1 = await chat_service.process_chat_message(request1)
        
        conversation_id = response1.conversation_id
        assert conversation_id is not None
        
        # Second message in same conversation
        request2 = ChatRequest(message="Show me by month", conversation_id=conversation_id)
        response2 = await chat_service.process_chat_message(request2)
        
        assert response2.conversation_id == conversation_id
        
        # Check that history is persisted
        history = conversation_history_manager.get_conversation_history(conversation_id)
        assert len(history) == 4  # 2 user messages + 2 assistant responses
        
        # Check message content
        assert history[0]["type"] == "user"
        assert history[0]["content"] == "What are my sales?"
        assert history[1]["type"] == "assistant"
        assert history[2]["type"] == "user"
        assert history[2]["content"] == "Show me by month"
        assert history[3]["type"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_conversation_context_usage(self, chat_service, conversation_history_manager):
        """Test that conversation context is used for follow-up questions."""
        # Create conversation with some history
        conversation_id = conversation_history_manager.create_conversation()
        conversation_history_manager.add_message(conversation_id, "user", "Show me sales data")
        conversation_history_manager.add_message(conversation_id, "assistant", "Here's your sales data")
        
        # Send follow-up message
        request = ChatRequest(message="What about last month?", conversation_id=conversation_id)
        response = await chat_service.process_chat_message(request)
        
        # Verify context was available
        context = conversation_history_manager.get_conversation_context(conversation_id)
        assert len(context["user_questions"]) >= 2
        assert "sales" in context["topics"]
    
    def test_get_conversation_history_integration(self, chat_service, conversation_history_manager):
        """Test getting conversation history through chat service."""
        # Create conversation with messages
        conversation_id = conversation_history_manager.create_conversation()
        conversation_history_manager.add_message(conversation_id, "user", "Test message")
        
        # Get history through chat service
        history = chat_service.get_conversation_history(conversation_id)
        
        assert len(history) == 1
        assert history[0]["content"] == "Test message"
    
    def test_clear_conversation_integration(self, chat_service, conversation_history_manager):
        """Test clearing conversation through chat service."""
        # Create conversation with messages
        conversation_id = conversation_history_manager.create_conversation()
        conversation_history_manager.add_message(conversation_id, "user", "Test message")
        
        # Verify conversation exists
        assert len(chat_service.get_conversation_history(conversation_id)) == 1
        
        # Clear conversation
        result = chat_service.clear_conversation_history(conversation_id)
        
        assert result is True
        assert len(chat_service.get_conversation_history(conversation_id)) == 0
    
    def test_conversation_summary_integration(self, chat_service, conversation_history_manager):
        """Test getting conversation summary through chat service."""
        # Create conversation with messages
        conversation_id = conversation_history_manager.create_conversation()
        conversation_history_manager.add_message(conversation_id, "user", "What are my sales?")
        conversation_history_manager.add_message(conversation_id, "assistant", "Your sales are $50,000")
        
        # Get summary through chat service
        summary = chat_service.get_conversation_summary(conversation_id)
        
        assert summary["id"] == conversation_id
        assert summary["message_count"] == 2
        assert summary["first_question"] == "What are my sales?"
    
    @pytest.mark.asyncio
    async def test_conversation_creation_on_first_message(self, chat_service):
        """Test that a new conversation is created when no conversation_id is provided."""
        request = ChatRequest(message="Hello", conversation_id=None)
        response = await chat_service.process_chat_message(request)
        
        assert response.conversation_id is not None
        assert len(response.conversation_id) > 0
        
        # Verify conversation was created in history manager
        history = chat_service.get_conversation_history(response.conversation_id)
        assert len(history) >= 2  # User message + assistant response
    
    def test_cleanup_expired_conversations_integration(self, chat_service):
        """Test cleanup of expired conversations through chat service."""
        # This test verifies the method exists and can be called
        # The actual cleanup logic is tested in the ConversationHistoryManager tests
        cleaned_count = chat_service.cleanup_expired_conversations()
        
        # Should return a number (even if 0)
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0