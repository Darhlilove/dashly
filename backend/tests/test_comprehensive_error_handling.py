"""
Comprehensive tests for error handling and user guidance improvements.

Tests the implementation of task 6: Add comprehensive error handling and user guidance
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chat_error_handler import ChatErrorHandler
from response_generator import ResponseGenerator
from models import ConversationalResponse, ExecuteResponse, ChartConfig
from exceptions import (
    QueryExecutionError, SQLSyntaxError, SQLSecurityError, 
    QueryTimeoutError, ResultSetTooLargeError, SQLSchemaError,
    TableNotFoundError, DatabaseConnectionError
)


class TestChatErrorHandler:
    """Test the enhanced ChatErrorHandler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ChatErrorHandler()
    
    def test_no_data_error_handling(self):
        """Test handling of no data scenarios."""
        error = TableNotFoundError("Table 'data' not found")
        user_message = "Show me sales data"
        conversation_id = "test_conv_1"
        
        response = self.error_handler.handle_chat_error(
            error, user_message, conversation_id
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "no data" in response.message.lower() or "upload" in response.message.lower()
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        assert "upload" in " ".join(response.follow_up_questions).lower()
    
    def test_column_not_found_error_handling(self):
        """Test handling of column not found errors."""
        error = SQLSchemaError("Column 'revenue' not found", missing_object="revenue")
        user_message = "Show me revenue by month"
        conversation_id = "test_conv_2"
        
        response = self.error_handler.handle_chat_error(
            error, user_message, conversation_id
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "revenue" in response.message or "column" in response.message.lower()
        assert any("different" in suggestion.lower() for suggestion in response.follow_up_questions)
    
    def test_timeout_error_handling(self):
        """Test handling of timeout errors."""
        error = QueryTimeoutError("Query timed out after 30 seconds", timeout_seconds=30)
        user_message = "Show me all data with complex calculations"
        conversation_id = "test_conv_3"
        
        response = self.error_handler.handle_chat_error(
            error, user_message, conversation_id
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "timeout" in response.message.lower() or "long" in response.message.lower()
        assert any("simpler" in suggestion.lower() for suggestion in response.follow_up_questions)
    
    def test_contextual_error_response(self):
        """Test contextual error responses with data info."""
        error = SQLSchemaError("Column not found")
        user_message = "Show me customer data"
        conversation_id = "test_conv_4"
        
        context = {
            "conversation_history": [
                {"role": "user", "message": "What data do I have?"},
                {"role": "assistant", "message": "You have sales and product data."}
            ]
        }
        
        data_info = {
            "tables": {"sales": {}, "products": {}},
            "columns": ["id", "date", "amount", "product_name"],
            "row_count": 1000
        }
        
        response = self.error_handler.generate_contextual_error_response(
            error, user_message, conversation_id, context, data_info
        )
        
        assert isinstance(response, ConversationalResponse)
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        # Should include information about available data
        insights_text = " ".join(response.insights).lower()
        assert "available" in insights_text or "columns" in insights_text
    
    def test_no_data_uploaded_response(self):
        """Test specific response for no data uploaded scenario."""
        user_message = "Show me my sales trends"
        conversation_id = "test_conv_5"
        
        response = self.error_handler.handle_no_data_uploaded_error(
            user_message, conversation_id
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "upload" in response.message.lower()
        assert any("csv" in suggestion.lower() for suggestion in response.follow_up_questions)
        assert any("demo" in suggestion.lower() for suggestion in response.follow_up_questions)
    
    def test_data_quality_error_response(self):
        """Test response for data quality issues."""
        user_message = "Analyze my customer data"
        conversation_id = "test_conv_6"
        quality_issues = [
            "Missing values in 'customer_id' column",
            "Invalid date formats in 'purchase_date'",
            "Duplicate entries found"
        ]
        
        response = self.error_handler.handle_data_quality_error(
            user_message, conversation_id, quality_issues
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "quality" in response.message.lower() or "issues" in response.message.lower()
        assert len(response.insights) > 1  # Should include quality issues
        assert "Missing values" in response.insights[1]  # First quality issue
    
    def test_alternative_questions_generation(self):
        """Test generation of alternative questions."""
        failed_question = "Show me total sales revenue"
        available_data_info = {
            "columns": ["date", "amount", "product_category", "customer_id"]
        }
        
        alternatives = self.error_handler.generate_alternative_questions(
            failed_question, available_data_info
        )
        
        assert len(alternatives) > 0
        assert len(alternatives) <= 5  # Should be limited to 5
        # Should include data-specific suggestions
        alternatives_text = " ".join(alternatives).lower()
        assert "time" in alternatives_text or "category" in alternatives_text
    
    def test_vague_question_detection(self):
        """Test detection of vague questions."""
        # Test vague questions
        assert self.error_handler._is_vague_question("hi")
        assert self.error_handler._is_vague_question("tell me about data")
        assert self.error_handler._is_vague_question("what is")
        
        # Test specific questions
        assert not self.error_handler._is_vague_question("show me total sales by month")
        assert not self.error_handler._is_vague_question("how many customers do I have")
        assert not self.error_handler._is_vague_question("what are my top products")


class TestResponseGeneratorErrorHandling:
    """Test the enhanced ResponseGenerator error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.response_generator = ResponseGenerator()
    
    def test_fallback_response_no_data(self):
        """Test fallback response when no data is found."""
        query_results = Mock(spec=ExecuteResponse)
        query_results.row_count = 0
        query_results.runtime_ms = 100
        query_results.columns = ["id", "name"]
        query_results.rows = []
        
        error = Exception("No data found")
        original_question = "Show me customer data"
        
        response = self.response_generator._generate_fallback_response(
            query_results, original_question, None, error
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "no results" in response.message.lower() or "couldn't find" in response.message.lower()
        assert len(response.follow_up_questions) > 0
    
    def test_fallback_response_timeout(self):
        """Test fallback response for timeout errors."""
        query_results = Mock(spec=ExecuteResponse)
        query_results.row_count = 1000
        query_results.runtime_ms = 30000
        
        error = Exception("Query timeout after 30 seconds")
        original_question = "Show me complex analysis"
        
        response = self.response_generator._generate_fallback_response(
            query_results, original_question, None, error
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "timeout" in response.message.lower() or "longer" in response.message.lower()
        assert any("simpler" in suggestion.lower() for suggestion in response.follow_up_questions)
    
    def test_fallback_response_column_not_found(self):
        """Test fallback response for column not found errors."""
        query_results = Mock(spec=ExecuteResponse)
        query_results.row_count = 0
        query_results.runtime_ms = 100
        
        error = Exception("Column 'revenue' does not exist")
        original_question = "Show me revenue trends"
        
        response = self.response_generator._generate_fallback_response(
            query_results, original_question, None, error
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "column" in response.message.lower() or "fields" in response.message.lower()
        assert any("available" in suggestion.lower() for suggestion in response.follow_up_questions)
    
    def test_error_guidance_response_no_data_uploaded(self):
        """Test error guidance for no data uploaded scenario."""
        response = self.response_generator.generate_error_guidance_response(
            "no_data_uploaded", 
            "Show me sales data"
        )
        
        assert isinstance(response, ConversationalResponse)
        assert "upload" in response.message.lower()
        assert any("csv" in suggestion.lower() for suggestion in response.follow_up_questions)
    
    def test_error_guidance_response_with_data_info(self):
        """Test error guidance with available data information."""
        available_data_info = {
            "columns": ["date", "amount", "customer_id", "product_name"]
        }
        
        response = self.response_generator.generate_error_guidance_response(
            "column_not_found", 
            "Show me revenue data",
            available_data_info
        )
        
        assert isinstance(response, ConversationalResponse)
        assert len(response.insights) > 1  # Should include column info
        insights_text = " ".join(response.insights)
        assert "date" in insights_text and "amount" in insights_text


class TestErrorHandlingIntegration:
    """Test integration of error handling components."""
    
    def test_error_flow_no_data_to_guidance(self):
        """Test complete error flow from no data to user guidance."""
        error_handler = ChatErrorHandler()
        
        # Simulate no data scenario
        error = TableNotFoundError("No table found")
        user_message = "Show me my data"
        conversation_id = "test_integration"
        
        # Should get guidance response
        response = error_handler.handle_no_data_uploaded_error(user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        assert "upload" in response.message.lower()
        assert len(response.follow_up_questions) >= 2
        
        # Should suggest both upload and demo options
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert "upload" in suggestions_text
        assert "demo" in suggestions_text
    
    def test_error_context_preservation(self):
        """Test that error responses preserve conversation context."""
        error_handler = ChatErrorHandler()
        
        # Create conversation context
        context = {
            "conversation_history": [
                {"role": "user", "message": "What sales data do I have?"},
                {"role": "assistant", "message": "I can help with sales analysis."},
                {"role": "user", "message": "Show me revenue by product"}
            ]
        }
        
        error = SQLSchemaError("Column 'revenue' not found")
        user_message = "Show me revenue by product"
        conversation_id = "test_context"
        
        response = error_handler.handle_chat_error(
            error, user_message, conversation_id, context
        )
        
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == conversation_id
        # Should provide contextual suggestions based on conversation
        assert len(response.follow_up_questions) > 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])