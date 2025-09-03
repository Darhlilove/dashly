"""
Comprehensive error handling and edge case tests for chat functionality.

Tests cover all error scenarios, edge cases, and recovery mechanisms
as specified in requirements 1.4, 2.4 for beginner-friendly error handling.
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
from chat_error_handler import ChatErrorHandler
from models import ChatRequest, ConversationalResponse, ExecuteResponse
from exceptions import (
    SQLSchemaError, TableNotFoundError, QueryTimeoutError,
    ResultSetTooLargeError, SQLSyntaxError, DatabaseConnectionError
)


class TestChatErrorScenariosComprehensive:
    """Comprehensive error handling and edge case tests."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ChatErrorHandler()
        self.chat_service = ChatService()
        
        # Setup mock services for error testing
        self.mock_query_executor = Mock()
        self.mock_llm_service = Mock()
        self.mock_conversation_manager = Mock()
        
        self.chat_service.query_executor = self.mock_query_executor
        self.chat_service.llm_service = self.mock_llm_service
        self.chat_service.conversation_history_manager = self.mock_conversation_manager
        
        # Default mock setup
        self.mock_conversation_manager.create_conversation.return_value = "error_test_conv"
        self.mock_conversation_manager.add_message.return_value = None
        self.mock_conversation_manager.get_conversation_context.return_value = {
            "user_questions": [],
            "topics": []
        }
    
    def test_error_handler_column_not_found_detailed(self):
        """Test detailed handling of column not found errors."""
        error = SQLSchemaError(
            "Column 'revenue_2024' does not exist in table 'sales'",
            missing_object="revenue_2024"
        )
        user_message = "Show me revenue_2024 by region"
        conversation_id = "col_error_conv"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        
        # Should provide beginner-friendly explanation
        message_lower = response.message.lower()
        assert any(phrase in message_lower for phrase in [
            "couldn't find", "don't see", "not available", "doesn't exist"
        ])
        
        # Should not expose technical SQL details
        assert "column" not in message_lower
        assert "table" not in message_lower
        assert "sql" not in message_lower
        
        # Should provide helpful suggestions
        assert len(response.follow_up_questions) > 0
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in [
            "available", "columns", "fields", "data", "what"
        ])
        
        # Should include insights about the error
        assert len(response.insights) > 0
        insights_text = " ".join(response.insights).lower()
        assert any(word in insights_text for word in [
            "field", "data", "available", "try"
        ])
    
    def test_error_handler_table_not_found_detailed(self):
        """Test detailed handling of table not found errors."""
        error = TableNotFoundError("Table 'customer_analytics' does not exist")
        user_message = "Show me customer analytics data"
        conversation_id = "table_error_conv"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        
        # Should explain in business terms
        message_lower = response.message.lower()
        assert any(phrase in message_lower for phrase in [
            "no data loaded", "haven't uploaded", "data not available"
        ])
        
        # Should suggest data upload or demo data
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in [
            "upload", "demo", "sample", "load"
        ])
    
    def test_error_handler_query_timeout_detailed(self):
        """Test detailed handling of query timeout errors."""
        error = QueryTimeoutError(
            "Query execution timed out after 45 seconds",
            timeout_seconds=45
        )
        user_message = "Show me detailed analysis of all customer transactions with complex calculations"
        conversation_id = "timeout_error_conv"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        
        # Should explain timeout in user-friendly terms
        message_lower = response.message.lower()
        assert any(phrase in message_lower for phrase in [
            "taking too long", "bit slow", "complex request", "try simpler"
        ])
        
        # Should suggest simpler alternatives
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(phrase in suggestions_text for phrase in [
            "simpler question", "smaller subset", "specific time period", "fewer details"
        ])
        
        # Should provide actionable insights
        insights_text = " ".join(response.insights).lower()
        assert any(word in insights_text for word in [
            "complex", "large", "simplify", "break down"
        ])
    
    def test_error_handler_result_too_large_detailed(self):
        """Test detailed handling of result set too large errors."""
        error = ResultSetTooLargeError(
            "Result set contains 500,000 rows, exceeds limit of 10,000",
            max_rows=10000,
            actual_rows=500000
        )
        user_message = "Show me all customer transactions ever"
        conversation_id = "large_result_conv"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        
        # Should explain size limitation in friendly terms
        message_lower = response.message.lower()
        assert any(phrase in message_lower for phrase in [
            "too much data", "very large", "manageable amount", "overwhelming"
        ])
        
        # Should suggest filtering options
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(phrase in suggestions_text for phrase in [
            "recent data", "specific period", "top results", "filter"
        ])
    
    def test_error_handler_sql_syntax_detailed(self):
        """Test detailed handling of SQL syntax errors."""
        error = SQLSyntaxError("Syntax error near 'SELCT' at line 1")
        user_message = "Show me sales data with some complex filtering"
        conversation_id = "syntax_error_conv"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        
        # Should not expose SQL syntax details
        message_lower = response.message.lower()
        assert "syntax" not in message_lower
        assert "sql" not in message_lower
        assert "selct" not in message_lower
        
        # Should explain in user terms
        assert any(phrase in message_lower for phrase in [
            "trouble understanding", "different way", "rephrase"
        ])
        
        # Should suggest rephrasing
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(phrase in suggestions_text for phrase in [
            "simpler language", "different words", "rephrase", "try asking"
        ])
    
    def test_error_handler_database_connection_detailed(self):
        """Test detailed handling of database connection errors."""
        error = DatabaseConnectionError("Connection to database failed: timeout")
        user_message = "Show me my sales dashboard"
        conversation_id = "connection_error_conv"
        
        response = self.error_handler.handle_chat_error(error, user_message, conversation_id)
        
        assert isinstance(response, ConversationalResponse)
        
        # Should explain connection issue in user terms
        message_lower = response.message.lower()
        assert any(phrase in message_lower for phrase in [
            "trouble accessing", "temporary issue", "connection problem"
        ])
        
        # Should suggest retry
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(phrase in suggestions_text for phrase in [
            "try again", "moment", "refresh", "retry"
        ])
    
    def test_error_handler_vague_question_detection(self):
        """Test detection and handling of vague questions."""
        error = Exception("Generic processing error")
        vague_messages = [
            "show me",
            "what about",
            "data",
            "tell me something",
            "analyze"
        ]
        
        for vague_message in vague_messages:
            response = self.error_handler.handle_chat_error(
                error, vague_message, "vague_test_conv"
            )
            
            assert isinstance(response, ConversationalResponse)
            
            # Should detect vagueness and ask for clarification
            message_lower = response.message.lower()
            assert any(phrase in message_lower for phrase in [
                "need more detail", "bit more specific", "what specifically"
            ])
            
            # Should provide specific examples
            suggestions_text = " ".join(response.follow_up_questions).lower()
            assert any(word in suggestions_text for word in [
                "sales", "customers", "revenue", "products", "time period"
            ])
    
    def test_error_handler_context_aware_responses(self):
        """Test that error responses are customized based on context."""
        error = SQLSchemaError("Column not found")
        
        # Test with sales context
        sales_context = {
            "conversation_history": [
                {"role": "user", "message": "Show me sales data"},
                {"role": "assistant", "message": "Here's your sales information"}
            ]
        }
        
        response = self.error_handler.handle_chat_error(
            error, "Show me revenue by quarter", "sales_context_conv", sales_context
        )
        
        # Should include sales-specific suggestions
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in ["sales", "revenue", "quarterly"])
        
        # Test with customer context
        customer_context = {
            "conversation_history": [
                {"role": "user", "message": "Tell me about customers"},
                {"role": "assistant", "message": "Here's customer data"}
            ]
        }
        
        response = self.error_handler.handle_chat_error(
            error, "Show me customer segments", "customer_context_conv", customer_context
        )
        
        # Should include customer-specific suggestions
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in ["customer", "segment", "client"])
    
    def test_error_handler_alternative_questions_generation(self):
        """Test generation of alternative questions when queries fail."""
        failed_questions = [
            "Show me total revenue by customer segment over time with growth rates",
            "Analyze product performance across all regions with statistical significance",
            "Display customer lifetime value trends by acquisition channel"
        ]
        
        available_data = {
            "columns": ["date", "amount", "customer_type", "region", "product_id", "customer_id"]
        }
        
        for failed_question in failed_questions:
            alternatives = self.error_handler.generate_alternative_questions(
                failed_question, available_data
            )
            
            assert len(alternatives) > 0
            assert len(alternatives) <= 5  # Should limit alternatives
            
            # Should be based on available columns
            alternatives_text = " ".join(alternatives).lower()
            assert any(col in alternatives_text for col in ["date", "amount", "customer", "region", "product"])
            
            # Should be simpler than original
            for alt in alternatives:
                assert len(alt.split()) < len(failed_question.split())  # Simpler questions
    
    def test_error_handler_data_not_found_with_suggestions(self):
        """Test response when no data matches but alternatives exist."""
        user_message = "Show me product sales for 2025"
        conversation_id = "no_data_conv"
        available_tables = ["sales_2023", "sales_2024", "products", "customers"]
        
        response = self.error_handler.generate_data_not_found_response(
            user_message, conversation_id, available_tables
        )
        
        assert isinstance(response, ConversationalResponse)
        
        # Should mention available data
        message_lower = response.message.lower()
        assert "2023" in response.message or "2024" in response.message
        assert any(table in response.message.lower() for table in available_tables)
        
        # Should suggest available alternatives
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(year in suggestions_text for year in ["2023", "2024"])
    
    def test_error_handler_data_not_found_no_alternatives(self):
        """Test response when no data is available at all."""
        user_message = "Show me any business data"
        conversation_id = "empty_db_conv"
        available_tables = []
        
        response = self.error_handler.generate_data_not_found_response(
            user_message, conversation_id, available_tables
        )
        
        assert isinstance(response, ConversationalResponse)
        
        # Should explain no data is loaded
        message_lower = response.message.lower()
        assert any(phrase in message_lower for phrase in [
            "no data loaded", "haven't uploaded", "empty database"
        ])
        
        # Should suggest data upload
        suggestions_text = " ".join(response.follow_up_questions).lower()
        assert any(word in suggestions_text for word in ["upload", "import", "demo", "sample"])
    
    @pytest.mark.asyncio
    async def test_chat_service_error_integration_comprehensive(self):
        """Test comprehensive error handling integration in ChatService."""
        # Test various error scenarios through ChatService
        
        # 1. SQL Schema Error
        self.mock_llm_service.translate_to_sql.side_effect = SQLSchemaError("Column not found")
        
        request = ChatRequest(
            message="Show me invalid_field data",
            conversation_id="integration_error_1"
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        assert isinstance(response, ConversationalResponse)
        assert response.conversation_id == "integration_error_1"
        assert len(response.insights) > 0
        assert len(response.follow_up_questions) > 0
        
        # Reset for next test
        self.mock_llm_service.translate_to_sql.side_effect = None
        self.mock_llm_service.translate_to_sql.return_value = "SELECT * FROM sales"
        
        # 2. Query Execution Error
        self.mock_query_executor.execute_query.side_effect = QueryTimeoutError("Timeout")
        
        request = ChatRequest(
            message="Complex analysis request",
            conversation_id="integration_error_2"
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        assert isinstance(response, ConversationalResponse)
        assert "timeout" not in response.message.lower()  # Should hide technical details
        assert any(word in response.message.lower() for word in ["slow", "long", "complex"])
    
    @pytest.mark.asyncio
    async def test_chat_service_fallback_error_handling(self):
        """Test ChatService fallback error handling when services fail."""
        # Test when all services fail
        self.mock_llm_service.translate_to_sql.side_effect = Exception("LLM service down")
        self.mock_query_executor.execute_query.side_effect = Exception("Database down")
        self.mock_conversation_manager.add_message.side_effect = Exception("Storage down")
        
        request = ChatRequest(
            message="Show me data despite all failures",
            conversation_id="fallback_test"
        )
        
        response = await self.chat_service.process_chat_message(request)
        
        # Should still return a response, not crash
        assert isinstance(response, ConversationalResponse)
        assert len(response.message) > 0
        assert len(response.follow_up_questions) > 0
        
        # Should be apologetic and helpful
        message_lower = response.message.lower()
        assert any(word in message_lower for word in ["sorry", "issue", "trouble", "problem"])
    
    def test_error_message_tone_and_language(self):
        """Test that error messages maintain appropriate tone and language."""
        errors_and_messages = [
            (SQLSchemaError("Column error"), "Show me invalid data"),
            (QueryTimeoutError("Timeout"), "Complex query request"),
            (TableNotFoundError("Table missing"), "Show me missing table"),
            (DatabaseConnectionError("Connection failed"), "Access my data")
        ]
        
        for error, message in errors_and_messages:
            response = self.error_handler.handle_chat_error(
                error, message, "tone_test_conv"
            )
            
            # Check tone is friendly and supportive
            message_lower = response.message.lower()
            
            # Should not be harsh or technical
            harsh_words = ["error", "failed", "invalid", "wrong", "bad"]
            assert not any(word in message_lower for word in harsh_words)
            
            # Should be supportive and helpful
            supportive_phrases = [
                "let me help", "i can help", "try this", "here's what",
                "no problem", "that's okay", "i understand"
            ]
            # At least one supportive element should be present
            has_supportive_tone = (
                any(phrase in message_lower for phrase in supportive_phrases) or
                len(response.follow_up_questions) > 0 or
                len(response.insights) > 0
            )
            assert has_supportive_tone
    
    def test_error_recovery_suggestions_quality(self):
        """Test quality and relevance of error recovery suggestions."""
        error_scenarios = [
            {
                "error": SQLSchemaError("Column 'profit_margin' not found"),
                "message": "Show me profit margins by product",
                "expected_suggestions": ["profit", "margin", "product", "financial"]
            },
            {
                "error": QueryTimeoutError("Query too complex"),
                "message": "Analyze all customer behavior patterns with machine learning",
                "expected_suggestions": ["simpler", "specific", "recent", "subset"]
            },
            {
                "error": TableNotFoundError("Table 'inventory' not found"),
                "message": "Show me inventory levels",
                "expected_suggestions": ["upload", "data", "available", "demo"]
            }
        ]
        
        for scenario in error_scenarios:
            response = self.error_handler.handle_chat_error(
                scenario["error"],
                scenario["message"],
                "quality_test_conv"
            )
            
            # Check suggestion quality
            assert len(response.follow_up_questions) >= 2
            assert len(response.follow_up_questions) <= 5
            
            # All suggestions should be questions
            assert all("?" in q for q in response.follow_up_questions)
            
            # Should be relevant to the context
            suggestions_text = " ".join(response.follow_up_questions).lower()
            relevant_words = scenario["expected_suggestions"]
            assert any(word in suggestions_text for word in relevant_words)
            
            # Should be actionable (contain action words)
            action_words = ["show", "try", "look", "see", "find", "explore", "check"]
            assert any(word in suggestions_text for word in action_words)
    
    def test_edge_case_empty_or_null_inputs(self):
        """Test handling of empty or null inputs."""
        edge_cases = [
            ("", "empty_message_conv"),
            (None, "null_message_conv"),
            ("   ", "whitespace_message_conv"),
            ("?", "question_mark_conv"),
            ("show", "single_word_conv")
        ]
        
        for message, conv_id in edge_cases:
            if message is None:
                # Skip None message as it would be caught by request validation
                continue
                
            response = self.error_handler.handle_chat_error(
                Exception("Generic error"),
                message,
                conv_id
            )
            
            assert isinstance(response, ConversationalResponse)
            assert len(response.message) > 0
            assert len(response.follow_up_questions) > 0
            
            # Should ask for clarification
            message_lower = response.message.lower()
            assert any(word in message_lower for word in [
                "specific", "detail", "clarify", "help", "what"
            ])
    
    def test_error_handling_performance(self):
        """Test that error handling doesn't significantly impact performance."""
        import time
        
        error = SQLSchemaError("Performance test error")
        message = "Performance test message"
        
        # Measure error handling time
        start_time = time.time()
        
        for _ in range(100):  # Test 100 error responses
            response = self.error_handler.handle_chat_error(
                error, message, "perf_test_conv"
            )
            assert isinstance(response, ConversationalResponse)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_error = total_time / 100
        
        # Error handling should be fast (under 10ms per error on average)
        assert avg_time_per_error < 0.01, f"Error handling too slow: {avg_time_per_error:.4f}s per error"
    
    def test_error_consistency_across_similar_scenarios(self):
        """Test that similar errors produce consistent response patterns."""
        # Test multiple column not found errors
        column_errors = [
            SQLSchemaError("Column 'revenue' not found"),
            SQLSchemaError("Column 'profit' not found"),
            SQLSchemaError("Column 'sales' not found")
        ]
        
        responses = []
        for error in column_errors:
            response = self.error_handler.handle_chat_error(
                error, "Show me financial data", "consistency_test"
            )
            responses.append(response)
        
        # All responses should have similar structure
        for response in responses:
            assert isinstance(response, ConversationalResponse)
            assert len(response.insights) > 0
            assert len(response.follow_up_questions) > 0
            
        # Should have consistent messaging patterns
        messages = [r.message.lower() for r in responses]
        # All should mention not finding the data
        assert all(any(phrase in msg for phrase in ["couldn't find", "don't see", "not available"]) for msg in messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])