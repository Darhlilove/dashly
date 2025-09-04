"""
Chat-specific error handling for beginner-friendly conversational responses.

This module provides specialized error handling for the chat interface,
converting technical errors into conversational, helpful responses that
guide users toward successful interactions.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    from .models import ConversationalResponse
    from .exceptions import (
        QueryExecutionError, SQLSyntaxError, SQLSecurityError, 
        QueryTimeoutError, ResultSetTooLargeError, SQLSchemaError,
        TableNotFoundError, DatabaseConnectionError, FileUploadError,
        ValidationError
    )
    from .logging_config import get_logger
except ImportError:
    from models import ConversationalResponse
    from exceptions import (
        QueryExecutionError, SQLSyntaxError, SQLSecurityError, 
        QueryTimeoutError, ResultSetTooLargeError, SQLSchemaError,
        TableNotFoundError, DatabaseConnectionError, FileUploadError,
        ValidationError
    )
    from logging_config import get_logger

logger = get_logger(__name__)


class ChatErrorHandler:
    """
    Specialized error handler for chat interactions that converts technical
    errors into beginner-friendly conversational responses.
    """
    
    def __init__(self):
        """Initialize the chat error handler."""
        self.error_patterns = self._initialize_error_patterns()
        logger.info("ChatErrorHandler initialized")
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize patterns for recognizing and handling different types of errors.
        
        Returns:
            Dict mapping error patterns to response templates
        """
        return {
            "no_data": {
                "keywords": ["no data", "empty", "no results", "0 rows", "no rows returned"],
                "message": "I couldn't find any data that matches what you're looking for. This might mean the criteria are too specific or the data doesn't contain that information.",
                "insights": ["No data matches your specific criteria."],
                "suggestions": [
                    "Try asking about a broader time period or category",
                    "Would you like to see what data is available?",
                    "Can we look at the overall summary instead?"
                ]
            },
            "column_not_found": {
                "keywords": ["column", "not found", "does not exist", "unknown column"],
                "message": "I couldn't find that specific information in your data. It looks like you're asking about something that might not be available in the dataset.",
                "insights": ["The data doesn't contain the specific field you're looking for."],
                "suggestions": [
                    "Try asking about different columns or fields in your data",
                    "What columns or fields are available in the data?",
                    "Can you show me what information is in the dataset?"
                ]
            },
            "table_not_found": {
                "keywords": ["table", "not found", "no such table"],
                "message": "It looks like there's no data loaded yet. You'll need to upload some data before I can help you analyze it.",
                "insights": ["No data has been uploaded to analyze."],
                "suggestions": [
                    "Would you like to upload a CSV file?",
                    "Should we use some demo data to get started?",
                    "What kind of data are you planning to analyze?"
                ]
            },
            "timeout": {
                "keywords": ["timeout", "time limit", "too long", "cancelled"],
                "message": "That question is taking a bit too long to process. Let's try something simpler or more specific.",
                "insights": ["The query is too complex or the dataset is very large."],
                "suggestions": [
                    "Try asking a simpler question about your data",
                    "Can you ask about a smaller subset of the data?",
                    "Would you like to see a summary first?"
                ]
            },
            "too_large": {
                "keywords": ["too large", "limit exceeded", "too many rows"],
                "message": "That question would return too much data to display easily. Let me help you narrow it down to something more manageable.",
                "insights": ["The result would be too large to display effectively."],
                "suggestions": [
                    "Would you like to see just the top results?",
                    "Can we filter this by a specific category or time period?",
                    "Should we look at a summary instead of all the details?"
                ]
            },
            "syntax_error": {
                "keywords": ["syntax error", "parse error", "invalid sql"],
                "message": "I had trouble understanding exactly what you're looking for. Could you try asking in a different way?",
                "insights": ["The question might be too complex or unclear for me to process."],
                "suggestions": [
                    "Try using simpler language",
                    "Can you be more specific about what you want to see?",
                    "What aspect of the data interests you most?"
                ]
            },
            "connection_error": {
                "keywords": ["connection", "database", "unavailable", "service"],
                "message": "I'm having trouble accessing the data right now. This is usually temporary - please try again in a moment.",
                "insights": ["There's a temporary issue with the data connection."],
                "suggestions": [
                    "Try asking your question again",
                    "Would you like to try a different question while we wait?",
                    "Is there something else I can help you with?"
                ]
            },
            "network_error": {
                "keywords": ["network", "connection failed", "request failed"],
                "message": "I'm having trouble connecting right now. Please check your internet connection and try again.",
                "insights": ["There seems to be a network connectivity issue."],
                "suggestions": [
                    "Try refreshing the page",
                    "Check your internet connection",
                    "Try asking again in a moment"
                ]
            },
            "vague_question": {
                "keywords": [],  # Detected by question analysis, not error message
                "message": "I'd love to help, but I need a bit more detail about what you're looking for. What specific information about your data would you like to see?",
                "insights": ["Your question might need more specific details for me to understand."],
                "suggestions": [
                    "What specific data would you like to explore?",
                    "Are you looking for totals, averages, or trends?",
                    "Would you like to see a summary of what data is available?"
                ]
            },
            "data_processing_failed": {
                "keywords": ["processing failed", "analysis failed", "computation error"],
                "message": "I ran into an issue while processing your data. This sometimes happens with complex queries or large datasets.",
                "insights": ["The data processing encountered an unexpected issue."],
                "suggestions": [
                    "Try asking a simpler question first",
                    "Would you like to see a basic summary of your data?",
                    "Can we break this down into smaller parts?"
                ]
            },
            "invalid_query": {
                "keywords": ["invalid query", "malformed", "cannot parse"],
                "message": "I'm having trouble understanding your question. Could you try rephrasing it in a different way?",
                "insights": ["The question format might be unclear or too complex."],
                "suggestions": [
                    "Try using simpler, more direct language",
                    "Ask about one thing at a time",
                    "Example: 'Show me total sales by month'"
                ]
            },
            "service_unavailable": {
                "keywords": ["service unavailable", "temporarily unavailable", "maintenance"],
                "message": "The data analysis service is temporarily unavailable. This is usually brief - please try again in a moment.",
                "insights": ["The service is experiencing temporary issues."],
                "suggestions": [
                    "Try again in a few moments",
                    "Check if there are any system notifications",
                    "Contact support if the issue persists"
                ]
            },
            "rate_limit": {
                "keywords": ["rate limit", "too many requests", "quota exceeded"],
                "message": "You're asking questions a bit too quickly! Please wait a moment before trying again.",
                "insights": ["Request rate limit has been exceeded."],
                "suggestions": [
                    "Wait a few seconds before asking another question",
                    "Try combining multiple questions into one",
                    "Consider the complexity of your questions"
                ]
            },
            "data_format_error": {
                "keywords": ["format error", "parsing error", "invalid format"],
                "message": "There seems to be an issue with how your data is formatted. Some values might not be in the expected format.",
                "insights": ["The data contains formatting issues that prevent analysis."],
                "suggestions": [
                    "Check if your CSV file has consistent formatting",
                    "Try uploading the data again",
                    "Ask about specific columns that might work better"
                ]
            },
            "memory_limit": {
                "keywords": ["memory", "out of memory", "resource limit"],
                "message": "Your query is trying to process too much data at once. Let's try a more focused approach.",
                "insights": ["The query requires too much memory to process."],
                "suggestions": [
                    "Try filtering to a smaller date range",
                    "Ask about specific categories instead of all data",
                    "Break your question into smaller parts"
                ]
            }
        }
    
    def handle_chat_error(
        self, 
        error: Exception, 
        user_message: str, 
        conversation_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ConversationalResponse:
        """
        Convert an error into a beginner-friendly conversational response.
        
        Args:
            error: The exception that occurred
            user_message: The user's original message
            conversation_id: Conversation identifier
            context: Optional additional context about the error
            
        Returns:
            ConversationalResponse: User-friendly error response with suggestions
        """
        logger.info(f"Handling chat error: {type(error).__name__} for message: '{user_message[:50]}...'")
        
        # Determine error type and get appropriate response
        error_type = self._classify_error(error, user_message)
        response_template = self.error_patterns.get(error_type, self.error_patterns["syntax_error"])
        
        # Customize the response based on the specific error and context
        customized_response = self._customize_response(
            response_template, 
            error, 
            user_message, 
            context
        )
        
        # Add conversation context if available
        if context and "conversation_history" in context:
            customized_response = self._add_conversation_context(
                customized_response, 
                context["conversation_history"]
            )
        
        logger.info(f"Generated {error_type} error response for chat")
        
        return ConversationalResponse(
            message=customized_response["message"],
            chart_config=None,
            insights=customized_response["insights"],
            follow_up_questions=customized_response["suggestions"],
            processing_time_ms=0.0,
            conversation_id=conversation_id
        )
    
    def _classify_error(self, error: Exception, user_message: str) -> str:
        """
        Classify the error type based on the exception and user message.
        
        Args:
            error: The exception that occurred
            user_message: The user's original message
            
        Returns:
            str: Error type key for response template lookup
        """
        error_message = str(error).lower()
        
        # Check for specific exception types first
        if isinstance(error, SQLSchemaError):
            return "column_not_found"
        elif isinstance(error, TableNotFoundError):
            return "table_not_found"
        elif isinstance(error, QueryTimeoutError):
            return "timeout"
        elif isinstance(error, ResultSetTooLargeError):
            return "too_large"
        elif isinstance(error, SQLSyntaxError):
            return "syntax_error"
        elif isinstance(error, DatabaseConnectionError):
            return "connection_error"
        elif isinstance(error, (FileUploadError, ValidationError)):
            return "syntax_error"  # Treat as user input issue
        
        # Check error message patterns
        for error_type, pattern in self.error_patterns.items():
            if any(keyword in error_message for keyword in pattern["keywords"]):
                return error_type
        
        # Check for vague questions (not based on error message)
        if self._is_vague_question(user_message):
            return "vague_question"
        
        # Default to syntax error for unknown issues
        return "syntax_error"
    
    def _is_vague_question(self, user_message: str) -> bool:
        """
        Determine if a user question is too vague to process effectively.
        
        Args:
            user_message: The user's message
            
        Returns:
            bool: True if the question appears vague
        """
        message_lower = user_message.lower().strip()
        
        # Very short messages
        if len(message_lower.split()) < 3:
            return True
        
        # Messages without clear data analysis intent
        analysis_words = [
            "show", "what", "how", "when", "where", "which", "total", "count", 
            "average", "sum", "trend", "compare", "analyze", "breakdown", "list"
        ]
        
        if not any(word in message_lower for word in analysis_words):
            return True
        
        # Very generic questions
        generic_patterns = [
            "tell me about", "what about", "show me", "how about", "what is"
        ]
        
        if any(pattern in message_lower for pattern in generic_patterns) and len(message_lower.split()) < 5:
            return True
        
        return False
    
    def _customize_response(
        self, 
        template: Dict[str, Any], 
        error: Exception, 
        user_message: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Customize the response template based on specific error details.
        
        Args:
            template: Base response template
            error: The exception that occurred
            user_message: User's original message
            context: Optional additional context
            
        Returns:
            Dict with customized message, insights, and suggestions
        """
        customized = {
            "message": template["message"],
            "insights": template["insights"].copy(),
            "suggestions": template["suggestions"].copy()
        }
        
        # Add specific details based on error type
        if isinstance(error, QueryTimeoutError) and hasattr(error, 'timeout_seconds'):
            customized["insights"].append(f"The query timed out after {error.timeout_seconds} seconds.")
        
        elif isinstance(error, ResultSetTooLargeError) and hasattr(error, 'actual_rows'):
            if error.actual_rows:
                customized["insights"].append(f"The query would return {error.actual_rows:,} rows.")
        
        elif isinstance(error, SQLSchemaError) and hasattr(error, 'missing_object'):
            if error.missing_object:
                customized["message"] = f"I couldn't find '{error.missing_object}' in your data. {customized['message']}"
        
        # Customize suggestions based on user message content
        if "sales" in user_message.lower():
            customized["suggestions"].insert(0, "Try asking about revenue, orders, or customer data")
        elif "time" in user_message.lower() or "date" in user_message.lower():
            customized["suggestions"].insert(0, "Try asking about trends over months or years")
        elif "customer" in user_message.lower():
            customized["suggestions"].insert(0, "Try asking about customer counts or customer behavior")
        
        return customized
    
    def _add_conversation_context(
        self, 
        response: Dict[str, Any], 
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add conversation context to make the error response more relevant.
        
        Args:
            response: Current response dictionary
            conversation_history: Previous conversation messages
            
        Returns:
            Dict with context-aware response
        """
        if not conversation_history:
            return response
        
        # Look at recent user questions to provide better suggestions
        recent_questions = [
            msg["message"] for msg in conversation_history[-3:] 
            if msg.get("role") == "user"
        ]
        
        if recent_questions:
            # If user has been asking similar questions, suggest a different approach
            if len(recent_questions) > 1:
                response["suggestions"].insert(0, "Maybe we should try a completely different approach")
            
            # If user mentioned specific topics, reference them
            all_questions = " ".join(recent_questions).lower()
            if "total" in all_questions or "sum" in all_questions:
                response["suggestions"].append("Would you like to see totals or summaries?")
            elif "trend" in all_questions or "over time" in all_questions:
                response["suggestions"].append("Are you interested in trends over time?")
        
        return response
    
    def generate_data_not_found_response(
        self, 
        user_message: str, 
        conversation_id: str,
        available_tables: Optional[List[str]] = None
    ) -> ConversationalResponse:
        """
        Generate a specific response when no data is available.
        
        Args:
            user_message: User's original message
            conversation_id: Conversation identifier
            available_tables: List of available table names
            
        Returns:
            ConversationalResponse: Helpful response about data availability
        """
        if available_tables and len(available_tables) > 0:
            message = f"I can see you have data available, but I couldn't find results for your specific question. The available data includes: {', '.join(available_tables)}."
            insights = [f"Available data: {', '.join(available_tables)}"]
            suggestions = [
                "What specific information would you like to see from this data?",
                "Would you like a summary of what's available?",
                "Try asking about the main categories in your data"
            ]
        else:
            message = "It looks like there's no data loaded yet. You'll need to upload some data before I can help you analyze it."
            insights = ["No data has been uploaded to analyze."]
            suggestions = [
                "Would you like to upload a CSV file?",
                "Should we use some demo data to get started?",
                "What kind of data are you planning to analyze?"
            ]
        
        return ConversationalResponse(
            message=message,
            chart_config=None,
            insights=insights,
            follow_up_questions=suggestions,
            processing_time_ms=0.0,
            conversation_id=conversation_id
        )
    
    def generate_alternative_questions(
        self, 
        failed_question: str, 
        available_data_info: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate alternative question suggestions when a query fails.
        
        Args:
            failed_question: The question that failed
            available_data_info: Information about available data structure
            
        Returns:
            List[str]: Alternative question suggestions
        """
        alternatives = []
        question_lower = failed_question.lower()
        
        # Generate alternatives based on the failed question content
        if "total" in question_lower or "sum" in question_lower:
            alternatives.extend([
                "What are the overall totals in the data?",
                "Can you show me a summary of the main numbers?",
                "What are the key metrics I should know about?"
            ])
        
        elif "trend" in question_lower or "over time" in question_lower:
            alternatives.extend([
                "How has this changed over the last few months?",
                "What does the data look like by month or year?",
                "Are there any patterns over time?"
            ])
        
        elif "compare" in question_lower or "vs" in question_lower:
            alternatives.extend([
                "What are the top categories in the data?",
                "How do different groups compare?",
                "Which items perform best?"
            ])
        
        else:
            # Generic alternatives
            alternatives.extend([
                "What are the main insights from this data?",
                "Can you show me an overview of what's available?",
                "What would be interesting to explore in this dataset?"
            ])
        
        # Add data-specific alternatives if we have schema information
        if available_data_info and "columns" in available_data_info:
            columns = available_data_info["columns"]
            
            # Suggest questions based on available columns
            if any("date" in col.lower() for col in columns):
                alternatives.append("How does this data break down by time period?")
            
            if any("amount" in col.lower() or "price" in col.lower() or "revenue" in col.lower() for col in columns):
                alternatives.append("What are the financial totals or averages?")
            
            if any("category" in col.lower() or "type" in col.lower() for col in columns):
                alternatives.append("How does this break down by category?")
        
        return alternatives[:5]  # Limit to 5 alternatives
    
    def generate_contextual_error_response(
        self,
        error: Exception,
        user_message: str,
        conversation_id: str,
        context: Optional[Dict[str, Any]] = None,
        data_info: Optional[Dict[str, Any]] = None
    ) -> ConversationalResponse:
        """
        Generate a contextual error response that takes into account user history and data availability.
        
        Args:
            error: The exception that occurred
            user_message: The user's original message
            conversation_id: Conversation identifier
            context: Optional conversation context
            data_info: Optional information about available data
            
        Returns:
            ConversationalResponse: Contextual error response with personalized suggestions
        """
        # Start with the base error response
        base_response = self.handle_chat_error(error, user_message, conversation_id, context)
        
        # Enhance with contextual information
        enhanced_insights = list(base_response.insights)
        enhanced_suggestions = list(base_response.follow_up_questions)
        
        # Add data-specific context if available
        if data_info:
            if "tables" in data_info and data_info["tables"]:
                table_names = list(data_info["tables"].keys())
                enhanced_insights.append(f"Available data tables: {', '.join(table_names)}")
                
            if "row_count" in data_info:
                enhanced_insights.append(f"Your dataset contains {data_info['row_count']:,} rows of data")
        
        # Add conversation-specific context
        if context and "conversation_history" in context:
            history = context["conversation_history"]
            if len(history) > 3:
                enhanced_suggestions.insert(0, "Based on our conversation, maybe we should try a different approach")
            
            # Look for patterns in previous questions
            recent_questions = [msg.get("message", "") for msg in history[-3:] if msg.get("role") == "user"]
            if recent_questions:
                all_text = " ".join(recent_questions).lower()
                if "sales" in all_text or "revenue" in all_text:
                    enhanced_suggestions.append("Would you like to explore sales data in a different way?")
                elif "customer" in all_text:
                    enhanced_suggestions.append("Should we look at customer data from another angle?")
        
        # Generate alternative questions based on the failed question and available data
        alternatives = self.generate_alternative_questions(user_message, data_info)
        if alternatives:
            enhanced_suggestions.extend(alternatives[:2])  # Add top 2 alternatives
        
        # Limit suggestions to avoid overwhelming the user
        enhanced_suggestions = enhanced_suggestions[:5]
        enhanced_insights = enhanced_insights[:4]
        
        return ConversationalResponse(
            message=base_response.message,
            chart_config=None,
            insights=enhanced_insights,
            follow_up_questions=enhanced_suggestions,
            processing_time_ms=0.0,
            conversation_id=conversation_id
        )
    
    def handle_no_data_uploaded_error(self, user_message: str, conversation_id: str) -> ConversationalResponse:
        """
        Handle the specific case where user asks questions but no data has been uploaded.
        
        Args:
            user_message: The user's original message
            conversation_id: Conversation identifier
            
        Returns:
            ConversationalResponse: Helpful response about uploading data
        """
        message = "I'd love to help you analyze that data, but it looks like you haven't uploaded any data yet. Once you upload a CSV file, I'll be able to answer questions about it!"
        
        insights = [
            "No data has been uploaded to analyze yet.",
            "Upload a CSV file to get started with data analysis."
        ]
        
        suggestions = [
            "Click the upload button to add your CSV file",
            "Try the demo data to see how the system works",
            "What kind of data are you planning to analyze?"
        ]
        
        return ConversationalResponse(
            message=message,
            chart_config=None,
            insights=insights,
            follow_up_questions=suggestions,
            processing_time_ms=0.0,
            conversation_id=conversation_id
        )
    
    def handle_data_quality_error(
        self, 
        user_message: str, 
        conversation_id: str,
        quality_issues: List[str]
    ) -> ConversationalResponse:
        """
        Handle errors related to data quality issues.
        
        Args:
            user_message: The user's original message
            conversation_id: Conversation identifier
            quality_issues: List of specific data quality issues found
            
        Returns:
            ConversationalResponse: Response explaining data quality issues and solutions
        """
        message = "I found some issues with your data that are preventing me from answering your question properly. Let me explain what I found and how we can work around it."
        
        insights = ["Data quality issues detected:"] + quality_issues[:3]
        
        suggestions = [
            "Try asking about columns that have cleaner data",
            "Would you like to see a summary of data quality issues?",
            "Should we focus on a subset of the data that's more complete?"
        ]
        
        return ConversationalResponse(
            message=message,
            chart_config=None,
            insights=insights,
            follow_up_questions=suggestions,
            processing_time_ms=0.0,
            conversation_id=conversation_id
        )