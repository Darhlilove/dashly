"""
Tests for chat error handling functionality.

This module tests the beginner-friendly error handling implementation
for the chat interface, ensuring errors are converted to conversational
responses with helpful suggestions.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chat_error_handler import ChatErrorHandler
from chat_service import ChatService
from models import ChatRequest, ConversationalResponse
from exceptions import (
    SQLSchemaError, TableNotFoundError, QueryTimeoutError,
    ResultSetTooLargeError, SQLSyntaxError, DatabaseConnectionError
)


class TestChatErrorHandler:
    """Test the ChatErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ChatErrorHandler()
    
    def test_column_not_found_error(self):
        """Test handling of column not found errors."""
        error = SQLSchemaError("Column 'invalid_column' does not exist", missing_object="invalid_column")
        user_message = "Show me the invalid_column data"
        conversation_id = "test_conv_1"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "couldn't find" in response.message.lower()
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        assert "What columns or fields are available" in str(response.follow_up_questions)
        assert response.conversation_id == conversation_id
    
    def test_table_not_found_error(self):
        """Test handling of table not found errors."""
        error = TableNotFoundError("Table 'sales' does not exist")
        user_message = "Show me sales data"
        conversation_id = "test_conv_2"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "no data loaded yet" in response.message.lower()
        assert "upload" in str(response.follow_up_questions).lower()
        assert "demo data" in str(response.follow_up_questions).lower()
    
    def test_timeout_error(self):
        """Test handling of query timeout errors."""
        error = QueryTimeoutError("Query execution timed out after 30 seconds", timeout_seconds=30)
        user_message = "Show me all data with complex calculations"
        conversation_id = "test_conv_3"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "taking a bit too long" in response.message.lower()
        assert "simpler" in response.message.lower()
        assert "smaller subset" in str(response.follow_up_questions).lower()
    
    def test_result_too_large_error(self):
        """Test handling of result set too large errors."""
        error = ResultSetTooLargeError("Result set too large", max_rows=1000, actual_rows=50000)
        user_message = "Show me all customer data"
        conversation_id = "test_conv_4"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "too much data" in response.message.lower()
        assert "manageable" in response.message.lower()
        assert "top results" in str(response.follow_up_questions).lower()
    
    def test_syntax_error(self):
        """Test handling of SQL syntax errors."""
        error = SQLSyntaxError("Syntax error in SQL query")
        user_message = "Show me the data where something complex"
        conversation_id = "test_conv_5"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "trouble understanding" in response.message.lower()
        assert "different way" in response.message.lower()
        assert "simpler language" in str(response.follow_up_questions).lower()
    
    def test_connection_error(self):
        """Test handling of database connection errors."""
        error = DatabaseConnectionError("Failed to connect to database")
        user_message = "Show me sales data"
        conversation_id = "test_conv_6"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "trouble accessing the data" in response.message.lower()
        assert "temporary" in response.message.lower()
        assert "try asking your question again" in str(response.follow_up_questions).lower()
    
    def test_vague_question_detection(self):
        """Test detection and handling of vague questions."""
        error = Exception("Generic error")
        user_message = "show me"  # Very vague
        conversation_id = "test_conv_7"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "need a bit more detail" in response.message.lower()
        assert "specific" in response.message.lower()
    
    def test_error_customization_with_context(self):
        """Test error response customization based on user message content."""
        error = SQLSchemaError("Column not found")
        user_message = "Show me sales revenue by month"
        conversation_id = "test_conv_8"
        context = {
            "conversation_history": [
                {"role": "user", "message": "What sales data do you have?"},
                {"role": "assistant", "message": "I can help with sales analysis."}
            ]
        }
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id, context)
        
        assert isinstance(response, ConversationalResponse)
        # Should include sales-specific suggestion
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert "revenue" in suggestions_text or "sales" in suggestions_text
    
    def test_alternative_questions_generation(self):
        """Test generation of alternative questions when queries fail."""
        failed_question = "Show me total revenue by customer segment over time"
        available_data = {"columns": ["date", "amount", "customer_type", "region"]}
        
        alternatives = self.error_handler.generate_alternative_questions(
            failed_question, available_data
        )
        
        assert len(alternatives) > 0
        assert len(alternatives) <= 5  # Should limit to 5 alternatives
        
        # Should include data-specific alternatives based on available columns
        alternatives_text = " ".join(alternatives).lower()
        assert "time" in alternatives_text or "date" in alternatives_text
        assert "amount" in alternatives_text or "financial" in alternatives_text
    
    def test_data_not_found_response_with_available_tables(self):
        """Test response when no data matches but tables are available."""
        user_message = "Show me product sales"
        conversation_id = "test_conv_9"
        available_tables = ["customers", "orders", "inventory"]
        
        response = self.error_handler.generate_data_not_found_response(
            user_message, conversation_id, available_tables
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "customers" in response.message
        assert "orders" in response.message
        assert "inventory" in response.message
        assert "available data includes" in response.message.lower()
    
    def test_data_not_found_response_no_tables(self):
        """Test response when no data is available at all."""
        user_message = "Show me any data"
        conversation_id = "test_conv_10"
        available_tables = []
        
        response = self.error_handler.generate_data_not_found_response(
            user_message, conversation_id, available_tables
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "no data loaded yet" in response.message.lower()
        assert "upload" in str(response.follow_up_questions).lower()


class TestChatServiceErrorIntegration:
    """Test error handling integration in ChatService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.chat_service = ChatService()
    
    @pytest.mark.asyncio
    async def test_chat_service_error_handling(self):
        """Test that ChatService properly handles errors using ChatErrorHandler."""
        request = ChatRequest(
            message="Show me invalid data",
            conversation_id="test_integration"
        )
        
        # Mock the query executor to raise an error
        mock_query_executor = Mock()
        mock_query_executor.execute_query.side_effect = SQLSchemaError("Column not found")
        
        # Mock the LLM service
        mock_llm_service = Mock()
        mock_llm_service.translate_to_sql.return_value = "SELECT invalid_column FROM sales"
        
        # Set up the chat service with mocked dependencies
        self.chat_service.query_executor = mock_query_executor
        self.chat_service.llm_service = mock_llm_service
        
        # Process the chat message
        response = await self.chat_service.process_chat_message(request)
        
        # Should return a conversational error response, not raise an exception
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == "test_integration"
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        assert "issue" in response.message.lower() or "trouble" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_chat_service_fallback_error_handling(self):
        """Test ChatService fallback when no specific services are available."""
        request = ChatRequest(
            message="What is my data about?",
            conversation_id="test_fallback"
        )
        
        # Don't set query_executor or llm_service (they should be None)
        response = await self.chat_service.process_chat_message(request)
        
        # Should return a mock response, not an error
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == "test_fallback"
        assert len(response.message) > 0
        assert len(response.follow_up_questions) > 0
    
    @pytest.mark.asyncio
    async def test_conversation_history_in_error_context(self):
        """Test that conversation history is included in error context."""
        # First message
        request1 = ChatRequest(
            message="Show me sales data",
            conversation_id="test_history"
        )
        
        response1 = await self.chat_service.process_chat_message(request1)
        
        # Second message that will cause an error
        request2 = ChatRequest(
            message="Show me invalid_column",
            conversation_id="test_history"
        )
        
        # Mock services to cause an error
        mock_query_executor = Mock()
        mock_query_executor.execute_query.side_effect = SQLSchemaError("Column not found")
        mock_llm_service = Mock()
        mock_llm_service.translate_to_sql.return_value = "SELECT invalid_column FROM sales"
        
        self.chat_service.query_executor = mock_query_executor
        self.chat_service.llm_service = mock_llm_service
        
        response2 = await self.chat_service.process_chat_message(request2)
        
        # Should have conversation history available for context
        assert isinstance(response2, ConversationalResponse)
        assert response2.conversation_id == "test_history"
        
        # Check that conversation history was maintained
        history = self.chat_service.get_conversation_history("test_history")
        assert len(history) >= 2  # Should have both user messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])