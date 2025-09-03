"""
Conversation History Manager for persistent chat history storage and retrieval.

This module handles conversation persistence, context management, and session state
to support the beginner-friendly chat interface requirements.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from .models import ConversationalResponse
    from .logging_config import get_logger
    from .exceptions import DatabaseError
except ImportError:
    from models import ConversationalResponse
    from logging_config import get_logger
    from exceptions import DatabaseError

logger = get_logger(__name__)


class ConversationHistoryManager:
    """
    Manages persistent conversation history storage and retrieval.
    
    Provides functionality for:
    - Storing conversation messages persistently
    - Retrieving conversation history by ID
    - Managing conversation context for follow-up questions
    - Session management across user interactions
    """
    
    def __init__(self, storage_path: str = "data/conversations"):
        """
        Initialize the conversation history manager.
        
        Args:
            storage_path: Directory path for storing conversation files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for active conversations
        self._conversation_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Configuration
        self.max_history_length = 50  # Maximum messages per conversation
        self.max_context_messages = 10  # Messages to include in context
        self.conversation_timeout_hours = 24  # Hours before conversation expires
        
        logger.info(f"ConversationHistoryManager initialized with storage: {self.storage_path}")
    
    def create_conversation(self) -> str:
        """
        Create a new conversation and return its ID.
        
        Returns:
            str: Unique conversation ID
        """
        conversation_id = str(uuid.uuid4())
        
        # Initialize empty conversation
        conversation_data = {
            "id": conversation_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "messages": []
        }
        
        # Store in cache
        self._conversation_cache[conversation_id] = conversation_data["messages"]
        
        # Persist to disk
        self._save_conversation(conversation_id, conversation_data)
        
        logger.info(f"Created new conversation: {conversation_id}")
        return conversation_id
    
    def add_message(
        self, 
        conversation_id: str, 
        message_type: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            message_type: Type of message ("user" or "assistant")
            content: Message content
            metadata: Optional metadata (insights, follow-up questions, etc.)
        """
        if not conversation_id:
            conversation_id = self.create_conversation()
        
        message = {
            "id": str(uuid.uuid4()),
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Add to cache
        if conversation_id not in self._conversation_cache:
            self._load_conversation_to_cache(conversation_id)
        
        self._conversation_cache[conversation_id].append(message)
        
        # Trim conversation if too long
        if len(self._conversation_cache[conversation_id]) > self.max_history_length:
            self._conversation_cache[conversation_id] = self._conversation_cache[conversation_id][-self.max_history_length:]
        
        # Persist to disk
        self._persist_conversation(conversation_id)
        
        logger.debug(f"Added {message_type} message to conversation {conversation_id}")
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get the full conversation history.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List[Dict[str, Any]]: List of messages in the conversation
        """
        if not conversation_id:
            return []
        
        # Check cache first
        if conversation_id in self._conversation_cache:
            return self._conversation_cache[conversation_id].copy()
        
        # Load from disk
        try:
            conversation_data = self._load_conversation(conversation_id)
            if conversation_data:
                self._conversation_cache[conversation_id] = conversation_data["messages"]
                return conversation_data["messages"].copy()
        except Exception as e:
            logger.error(f"Failed to load conversation {conversation_id}: {e}")
        
        return []
    
    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation context for follow-up questions and LLM processing.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Dict[str, Any]: Context information including recent messages and patterns
        """
        history = self.get_conversation_history(conversation_id)
        
        if not history:
            return {
                "recent_messages": [],
                "user_questions": [],
                "assistant_responses": [],
                "topics": [],
                "conversation_length": 0
            }
        
        # Get recent messages for context (limited to max_context_messages)
        recent_messages = history[-self.max_context_messages:] if len(history) > self.max_context_messages else history
        
        # Extract user questions and assistant responses
        user_questions = [msg["content"] for msg in history if msg["type"] == "user"]
        assistant_responses = [msg["content"] for msg in history if msg["type"] == "assistant"]
        
        # Extract topics/keywords from user questions (simple keyword extraction)
        topics = self._extract_topics(user_questions)
        
        return {
            "recent_messages": recent_messages,
            "user_questions": user_questions[-5:],  # Last 5 questions
            "assistant_responses": assistant_responses[-5:],  # Last 5 responses
            "topics": topics,
            "conversation_length": len(history)
        }
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear a conversation's history.
        
        Args:
            conversation_id: ID of the conversation to clear
            
        Returns:
            bool: True if conversation was cleared, False if not found
        """
        if not conversation_id:
            return False
        
        # Remove from cache
        if conversation_id in self._conversation_cache:
            del self._conversation_cache[conversation_id]
        
        # Remove from disk
        conversation_file = self.storage_path / f"{conversation_id}.json"
        if conversation_file.exists():
            try:
                conversation_file.unlink()
                logger.info(f"Cleared conversation: {conversation_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete conversation file {conversation_id}: {e}")
        
        return False
    
    def cleanup_expired_conversations(self) -> int:
        """
        Clean up expired conversations based on timeout.
        
        Returns:
            int: Number of conversations cleaned up
        """
        cleaned_count = 0
        cutoff_time = datetime.now() - timedelta(hours=self.conversation_timeout_hours)
        
        # Check all conversation files
        for conversation_file in self.storage_path.glob("*.json"):
            try:
                conversation_data = self._load_conversation_file(conversation_file)
                if conversation_data:
                    last_updated = datetime.fromisoformat(conversation_data["last_updated"])
                    if last_updated < cutoff_time:
                        # Remove expired conversation
                        conversation_id = conversation_data["id"]
                        if self.clear_conversation(conversation_id):
                            cleaned_count += 1
            except Exception as e:
                logger.warning(f"Error checking conversation file {conversation_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired conversations")
        
        return cleaned_count
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get a summary of the conversation for display purposes.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Dict[str, Any]: Summary information about the conversation
        """
        history = self.get_conversation_history(conversation_id)
        
        if not history:
            return {
                "id": conversation_id,
                "message_count": 0,
                "created_at": None,
                "last_updated": None,
                "first_question": None
            }
        
        # Find first user question
        first_question = None
        for msg in history:
            if msg["type"] == "user":
                first_question = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                break
        
        return {
            "id": conversation_id,
            "message_count": len(history),
            "created_at": history[0]["timestamp"] if history else None,
            "last_updated": history[-1]["timestamp"] if history else None,
            "first_question": first_question
        }
    
    def _extract_topics(self, user_questions: List[str]) -> List[str]:
        """
        Extract topics/keywords from user questions for context.
        
        Args:
            user_questions: List of user questions
            
        Returns:
            List[str]: List of extracted topics/keywords
        """
        # Simple keyword extraction - look for common data analysis terms
        data_keywords = [
            "sales", "revenue", "profit", "customer", "product", "order", "date",
            "month", "year", "quarter", "total", "average", "count", "sum",
            "trend", "growth", "decline", "comparison", "analysis", "report"
        ]
        
        topics = set()
        for question in user_questions:
            question_lower = question.lower()
            for keyword in data_keywords:
                if keyword in question_lower:
                    topics.add(keyword)
        
        return list(topics)[:10]  # Limit to 10 topics
    
    def _load_conversation_to_cache(self, conversation_id: str) -> None:
        """Load a conversation from disk to cache."""
        conversation_data = self._load_conversation(conversation_id)
        if conversation_data:
            self._conversation_cache[conversation_id] = conversation_data["messages"]
        else:
            # If conversation doesn't exist on disk, create empty list in cache
            self._conversation_cache[conversation_id] = []
    
    def _persist_conversation(self, conversation_id: str) -> None:
        """Persist a conversation from cache to disk."""
        if conversation_id not in self._conversation_cache:
            return
        
        conversation_data = {
            "id": conversation_id,
            "created_at": datetime.now().isoformat(),  # Will be overwritten if loading existing
            "last_updated": datetime.now().isoformat(),
            "messages": self._conversation_cache[conversation_id]
        }
        
        # Try to preserve original created_at if conversation exists
        try:
            existing_data = self._load_conversation(conversation_id)
            if existing_data and "created_at" in existing_data:
                conversation_data["created_at"] = existing_data["created_at"]
        except Exception:
            pass  # Use new created_at if can't load existing
        
        self._save_conversation(conversation_id, conversation_data)
    
    def _save_conversation(self, conversation_id: str, conversation_data: Dict[str, Any]) -> None:
        """Save conversation data to disk."""
        conversation_file = self.storage_path / f"{conversation_id}.json"
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save conversation {conversation_id}: {e}")
            raise DatabaseError(f"Failed to save conversation: {e}")
    
    def _load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load conversation data from disk."""
        conversation_file = self.storage_path / f"{conversation_id}.json"
        return self._load_conversation_file(conversation_file)
    
    def _load_conversation_file(self, conversation_file: Path) -> Optional[Dict[str, Any]]:
        """Load conversation data from a specific file."""
        if not conversation_file.exists():
            return None
        
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conversation file {conversation_file}: {e}")
            return None