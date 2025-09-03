"""
Tests for ConversationHistoryManager functionality.

Tests conversation persistence, context management, and session state handling.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json

from src.conversation_history_manager import ConversationHistoryManager


class TestConversationHistoryManager:
    """Test suite for ConversationHistoryManager."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def history_manager(self, temp_storage):
        """Create ConversationHistoryManager instance for testing."""
        return ConversationHistoryManager(storage_path=temp_storage)
    
    def test_create_conversation(self, history_manager):
        """Test creating a new conversation."""
        conversation_id = history_manager.create_conversation()
        
        assert conversation_id is not None
        assert len(conversation_id) > 0
        assert conversation_id in history_manager._conversation_cache
        assert len(history_manager._conversation_cache[conversation_id]) == 0
    
    def test_add_message(self, history_manager):
        """Test adding messages to a conversation."""
        conversation_id = history_manager.create_conversation()
        
        # Add user message
        history_manager.add_message(
            conversation_id=conversation_id,
            message_type="user",
            content="What are my total sales?",
            metadata=None
        )
        
        # Add assistant message
        history_manager.add_message(
            conversation_id=conversation_id,
            message_type="assistant",
            content="Your total sales are $50,000.",
            metadata={
                "insights": ["Sales are up 20% from last month"],
                "follow_up_questions": ["Would you like to see sales by region?"]
            }
        )
        
        messages = history_manager.get_conversation_history(conversation_id)
        assert len(messages) == 2
        assert messages[0]["type"] == "user"
        assert messages[0]["content"] == "What are my total sales?"
        assert messages[1]["type"] == "assistant"
        assert messages[1]["content"] == "Your total sales are $50,000."
        assert messages[1]["metadata"]["insights"] == ["Sales are up 20% from last month"]
    
    def test_conversation_persistence(self, history_manager, temp_storage):
        """Test that conversations are persisted to disk."""
        conversation_id = history_manager.create_conversation()
        
        history_manager.add_message(
            conversation_id=conversation_id,
            message_type="user",
            content="Test message"
        )
        
        # Check that file was created
        conversation_file = Path(temp_storage) / f"{conversation_id}.json"
        assert conversation_file.exists()
        
        # Check file content
        with open(conversation_file, 'r') as f:
            data = json.load(f)
        
        assert data["id"] == conversation_id
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Test message"
    
    def test_load_conversation_from_disk(self, history_manager, temp_storage):
        """Test loading conversation from disk."""
        # Create a conversation file manually
        conversation_id = "test-conversation-123"
        conversation_data = {
            "id": conversation_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "messages": [
                {
                    "id": "msg-1",
                    "type": "user",
                    "content": "Hello",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {}
                }
            ]
        }
        
        conversation_file = Path(temp_storage) / f"{conversation_id}.json"
        with open(conversation_file, 'w') as f:
            json.dump(conversation_data, f)
        
        # Load conversation
        messages = history_manager.get_conversation_history(conversation_id)
        
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello"
        assert messages[0]["type"] == "user"
    
    def test_conversation_context(self, history_manager):
        """Test getting conversation context."""
        conversation_id = history_manager.create_conversation()
        
        # Add several messages
        history_manager.add_message(conversation_id, "user", "Show me sales data")
        history_manager.add_message(conversation_id, "assistant", "Here's your sales data")
        history_manager.add_message(conversation_id, "user", "What about revenue trends?")
        history_manager.add_message(conversation_id, "assistant", "Revenue is trending upward")
        
        context = history_manager.get_conversation_context(conversation_id)
        
        assert context["conversation_length"] == 4
        assert len(context["user_questions"]) == 2
        assert len(context["assistant_responses"]) == 2
        assert "sales" in context["topics"]
        assert "revenue" in context["topics"]
    
    def test_clear_conversation(self, history_manager, temp_storage):
        """Test clearing a conversation."""
        conversation_id = history_manager.create_conversation()
        history_manager.add_message(conversation_id, "user", "Test message")
        
        # Verify conversation exists
        assert len(history_manager.get_conversation_history(conversation_id)) == 1
        conversation_file = Path(temp_storage) / f"{conversation_id}.json"
        assert conversation_file.exists()
        
        # Clear conversation
        result = history_manager.clear_conversation(conversation_id)
        
        assert result is True
        assert len(history_manager.get_conversation_history(conversation_id)) == 0
        assert not conversation_file.exists()
        assert conversation_id not in history_manager._conversation_cache
    
    def test_conversation_summary(self, history_manager):
        """Test getting conversation summary."""
        conversation_id = history_manager.create_conversation()
        
        # Add messages
        history_manager.add_message(conversation_id, "user", "What are my sales for this quarter?")
        history_manager.add_message(conversation_id, "assistant", "Your Q4 sales are $75,000")
        
        summary = history_manager.get_conversation_summary(conversation_id)
        
        assert summary["id"] == conversation_id
        assert summary["message_count"] == 2
        assert summary["first_question"] == "What are my sales for this quarter?"
        assert summary["created_at"] is not None
        assert summary["last_updated"] is not None
    
    def test_max_history_length(self, history_manager):
        """Test that conversation history is trimmed when it exceeds max length."""
        # Set a small max length for testing
        history_manager.max_history_length = 3
        
        conversation_id = history_manager.create_conversation()
        
        # Add more messages than the limit
        for i in range(5):
            history_manager.add_message(conversation_id, "user", f"Message {i}")
        
        messages = history_manager.get_conversation_history(conversation_id)
        
        # Should only keep the last 3 messages
        assert len(messages) == 3
        assert messages[0]["content"] == "Message 2"
        assert messages[2]["content"] == "Message 4"
    
    def test_cleanup_expired_conversations(self, history_manager, temp_storage):
        """Test cleanup of expired conversations."""
        # Set short timeout for testing
        history_manager.conversation_timeout_hours = 1
        
        # Create conversation with old timestamp
        conversation_id = "old-conversation"
        old_time = datetime.now() - timedelta(hours=2)
        conversation_data = {
            "id": conversation_id,
            "created_at": old_time.isoformat(),
            "last_updated": old_time.isoformat(),
            "messages": []
        }
        
        conversation_file = Path(temp_storage) / f"{conversation_id}.json"
        with open(conversation_file, 'w') as f:
            json.dump(conversation_data, f)
        
        # Create recent conversation
        recent_id = history_manager.create_conversation()
        
        # Run cleanup
        cleaned_count = history_manager.cleanup_expired_conversations()
        
        assert cleaned_count == 1
        assert not conversation_file.exists()
        
        # Recent conversation should still exist
        recent_file = Path(temp_storage) / f"{recent_id}.json"
        assert recent_file.exists()
    
    def test_topic_extraction(self, history_manager):
        """Test topic extraction from user questions."""
        conversation_id = history_manager.create_conversation()
        
        # Add messages with various data analysis terms
        history_manager.add_message(conversation_id, "user", "Show me sales revenue by month")
        history_manager.add_message(conversation_id, "assistant", "Here's your monthly revenue")
        history_manager.add_message(conversation_id, "user", "What about customer growth trends?")
        history_manager.add_message(conversation_id, "assistant", "Customer growth is positive")
        
        context = history_manager.get_conversation_context(conversation_id)
        topics = context["topics"]
        
        assert "sales" in topics
        assert "revenue" in topics
        assert "customer" in topics
        assert "growth" in topics
        assert "month" in topics
    
    def test_empty_conversation_context(self, history_manager):
        """Test getting context for empty conversation."""
        context = history_manager.get_conversation_context("nonexistent-id")
        
        assert context["recent_messages"] == []
        assert context["user_questions"] == []
        assert context["assistant_responses"] == []
        assert context["topics"] == []
        assert context["conversation_length"] == 0
    
    def test_add_message_creates_conversation(self, history_manager):
        """Test that adding a message to non-existent conversation creates it."""
        # Add message without creating conversation first
        history_manager.add_message(
            conversation_id="",  # Empty ID should create new conversation
            message_type="user",
            content="Test message"
        )
        
        # Should have created a conversation
        assert len(history_manager._conversation_cache) == 1
        
        # Get the conversation ID
        conversation_id = list(history_manager._conversation_cache.keys())[0]
        messages = history_manager.get_conversation_history(conversation_id)
        
        assert len(messages) == 1
        assert messages[0]["content"] == "Test message"