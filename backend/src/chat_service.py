"""
Chat service for handling conversational interactions with data.

This service orchestrates the complete flow from natural language questions
to conversational responses, hiding technical complexity from users.
"""

import time
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from .models import ChatRequest, ConversationalResponse, ChartConfig
    from .logging_config import get_logger
    from .insight_analyzer import InsightAnalyzer
    from .response_generator import ResponseGenerator
    from .chat_error_handler import ChatErrorHandler
    from .chart_recommendation_service import ChartRecommendationService
    from .conversation_history_manager import ConversationHistoryManager
    from .proactive_exploration_service import ProactiveExplorationService
    from .response_cache import get_response_cache
    from .streaming_response import get_streaming_manager, ChatStreamProcessor
except ImportError:
    from models import ChatRequest, ConversationalResponse, ChartConfig
    from logging_config import get_logger
    from insight_analyzer import InsightAnalyzer
    from response_generator import ResponseGenerator
    from chat_error_handler import ChatErrorHandler
    from chart_recommendation_service import ChartRecommendationService
    from conversation_history_manager import ConversationHistoryManager
    from proactive_exploration_service import ProactiveExplorationService
    from response_cache import get_response_cache
    from streaming_response import get_streaming_manager, ChatStreamProcessor

logger = get_logger(__name__)


class ChatService:
    """
    Main orchestrator for chat interactions, handling the complete flow
    from question to conversational response.
    """
    
    def __init__(self, query_executor=None, llm_service=None, response_generator=None, insight_analyzer=None, chart_recommendation_service=None, conversation_history_manager=None, proactive_exploration_service=None, db_manager=None, schema_service=None):
        """
        Initialize ChatService with required dependencies.
        
        Args:
            query_executor: QueryExecutor instance for SQL execution
            llm_service: LLMService instance for natural language processing
            response_generator: ResponseGenerator instance for conversational responses
            insight_analyzer: InsightAnalyzer instance for pattern detection
            chart_recommendation_service: ChartRecommendationService for automatic dashboard updates
            conversation_history_manager: ConversationHistoryManager for persistent history
            proactive_exploration_service: ProactiveExplorationService for data exploration suggestions
            db_manager: DatabaseManager instance for data access
            schema_service: SchemaService instance for schema analysis
        """
        self.query_executor = query_executor
        self.llm_service = llm_service
        self.response_generator = response_generator or ResponseGenerator()
        self.insight_analyzer = insight_analyzer or InsightAnalyzer()
        self.chart_recommendation_service = chart_recommendation_service or ChartRecommendationService()
        self.error_handler = ChatErrorHandler()
        self.conversation_history_manager = conversation_history_manager or ConversationHistoryManager()
        self.proactive_exploration_service = proactive_exploration_service or ProactiveExplorationService(
            db_manager=db_manager,
            schema_service=schema_service,
            llm_service=llm_service
        )
        
        # Performance optimization components
        self.response_cache = get_response_cache()
        self.streaming_manager = get_streaming_manager()
        self.stream_processor = ChatStreamProcessor(self.streaming_manager)
        
        # Keep the old in-memory conversation history for backward compatibility
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("ChatService initialized with performance optimizations: caching, streaming, and enhanced processing")
    
    async def process_chat_message(
        self, 
        request: ChatRequest
    ) -> ConversationalResponse:
        """
        Process a chat message and return a conversational response.
        
        Args:
            request: ChatRequest containing the user's message
            
        Returns:
            ConversationalResponse: Conversational response with insights and suggestions
        """
        start_time = time.time()
        
        # Generate or use existing conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        logger.info(f"Processing chat message: '{request.message[:50]}...' (conversation: {conversation_id})")
        
        # Check cache first for performance optimization (Requirements 6.1)
        context_hash = self._generate_context_hash(conversation_id)
        cached_response = self.response_cache.get_chat_response(request.message, context_hash)
        if cached_response:
            logger.info(f"Cache hit for chat message: {request.message[:50]}...")
            cached_response.conversation_id = conversation_id
            return cached_response
        
        try:
            # Create conversation if needed
            if not conversation_id:
                conversation_id = self.conversation_history_manager.create_conversation()
            
            # Add user message to persistent history
            try:
                self.conversation_history_manager.add_message(
                    conversation_id=conversation_id,
                    message_type="user",
                    content=request.message
                )
                logger.debug(f"Successfully added user message to conversation {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to add user message to conversation {conversation_id}: {e}")
                raise
            
            # Also maintain backward compatibility with in-memory history
            try:
                if conversation_id not in self.conversation_history:
                    self.conversation_history[conversation_id] = []
                
                self.conversation_history[conversation_id].append({
                    "role": "user",
                    "message": request.message,
                    "timestamp": datetime.now().isoformat()
                })
                logger.debug(f"Successfully added user message to in-memory history for {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to add user message to in-memory history for {conversation_id}: {e}")
                raise
            
            # Process the message with available services
            if self.query_executor and self.llm_service:
                # Full processing with query execution and analysis
                response = await self._process_with_query_execution(request.message, conversation_id)
                response_message = response.message
                insights = response.insights
                follow_up_questions = response.follow_up_questions
                chart_config = response.chart_config  # Preserve chart config from full processing
            else:
                # Fallback to mock responses for demonstration
                response_message = self._generate_mock_response(request.message)
                insights = self._generate_mock_insights()
                follow_up_questions = self._generate_mock_follow_up_questions()
                chart_config = None  # No chart for mock responses since we don't have real data
            
            # Add assistant response to persistent history
            chart_config_dict = None
            if chart_config:
                try:
                    # Try to convert ChartConfig to dict (handle both Pydantic v1 and v2)
                    if hasattr(chart_config, 'model_dump'):
                        chart_config_dict = chart_config.model_dump()
                    elif hasattr(chart_config, 'dict'):
                        chart_config_dict = chart_config.dict()
                    elif hasattr(chart_config, '__dict__'):
                        chart_config_dict = chart_config.__dict__
                    else:
                        chart_config_dict = str(chart_config)
                except Exception as e:
                    logger.warning(f"Failed to serialize chart_config: {e}")
                    chart_config_dict = None
            
            # Calculate processing time first
            processing_time = (time.time() - start_time) * 1000
            
            self.conversation_history_manager.add_message(
                conversation_id=conversation_id,
                message_type="assistant",
                content=response_message,
                metadata={
                    "insights": insights,
                    "follow_up_questions": follow_up_questions,
                    "chart_config": chart_config_dict,
                    "processing_time_ms": processing_time
                }
            )
            
            # Also maintain backward compatibility with in-memory history
            try:
                self.conversation_history[conversation_id].append({
                    "role": "assistant", 
                    "message": response_message,
                    "timestamp": datetime.now().isoformat()
                })
                logger.debug(f"Successfully added assistant message to in-memory history for {conversation_id}")
            except Exception as e:
                logger.error(f"Failed to add assistant message to in-memory history for {conversation_id}: {e}")
                # Don't raise here as this is just backward compatibility
            
            logger.info(f"Chat message processed successfully in {processing_time:.2f}ms")
            
            final_response = ConversationalResponse(
                message=response_message,
                chart_config=chart_config,
                insights=insights,
                follow_up_questions=follow_up_questions,
                processing_time_ms=processing_time,
                conversation_id=conversation_id
            )
            
            # Cache the response for future use (Requirements 6.1)
            if processing_time < 5000:  # Only cache responses that processed quickly
                self.response_cache.cache_chat_response(
                    request.message, 
                    final_response, 
                    context_hash,
                    ttl=300  # 5 minutes TTL
                )
            
            return final_response
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Error processing chat message: {str(e)}")
            
            # Generate beginner-friendly error response using ChatErrorHandler
            conversation_context = {
                "conversation_history": self.get_conversation_history(conversation_id)
            }
            
            # Try to get data information for better error context
            data_info = None
            try:
                if hasattr(self, 'db_manager') and self.db_manager:
                    # Get available tables and basic info
                    data_info = {
                        "tables": {},  # Could be populated with actual table info
                        "has_data": True  # Basic check
                    }
            except Exception:
                pass  # Ignore errors when getting data info
            
            # Use contextual error response if we have data info
            if data_info:
                error_response = self.error_handler.generate_contextual_error_response(
                    e, request.message, conversation_id, conversation_context, data_info
                )
            else:
                error_response = self.error_handler.handle_chat_error(
                    e, request.message, conversation_id, conversation_context
                )
            
            error_response.processing_time_ms = processing_time
            return error_response
    
    def _generate_mock_response(self, user_message: str) -> str:
        """
        Generate a mock conversational response.
        
        Args:
            user_message: The user's original message
            
        Returns:
            str: Mock conversational response
        """
        # Simple keyword-based mock responses
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["sales", "revenue", "money"]):
            return "I can see you're interested in sales data! Based on what I'm seeing, your sales have been showing some interesting patterns. Let me break that down for you in a way that's easy to understand."
        
        elif any(word in message_lower for word in ["customer", "client", "buyer"]):
            return "Great question about customers! Looking at your customer data, there are some insights that might be really valuable for your business decisions."
        
        elif any(word in message_lower for word in ["trend", "pattern", "over time"]):
            return "You're asking about trends - that's smart! I can see some clear patterns in your data that tell an interesting story about how things have been changing."
        
        else:
            return "That's an interesting question! Let me look at your data and see what insights I can share with you. I'll explain everything in plain English so it's easy to understand."
    
    def _generate_mock_insights(self) -> List[str]:
        """
        Generate mock insights for the response.
        
        Returns:
            List[str]: Mock insights
        """
        return [
            "Your data shows a clear upward trend in the last quarter",
            "There's an interesting pattern on weekends that might be worth exploring",
            "The numbers suggest there's room for growth in certain areas"
        ]
    
    def _generate_mock_follow_up_questions(self) -> List[str]:
        """
        Generate mock follow-up questions.
        
        Returns:
            List[str]: Mock follow-up questions
        """
        return [
            "Would you like to see how this compares to last year?",
            "Are you interested in breaking this down by category?",
            "Should we look at the top performers in more detail?"
        ]
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history for a specific conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List[Dict[str, Any]]: Conversation history
        """
        # Try to get from persistent storage first
        if conversation_id:
            persistent_history = self.conversation_history_manager.get_conversation_history(conversation_id)
            if persistent_history:
                return persistent_history
        
        # Fall back to in-memory history for backward compatibility
        return self.conversation_history.get(conversation_id, [])
    
    async def _process_with_query_execution(self, user_message: str, conversation_id: str) -> ConversationalResponse:
        """
        Process message with full query execution and insight analysis.
        
        Args:
            user_message: The user's message
            conversation_id: Conversation identifier
            
        Returns:
            ConversationalResponse: Complete response with insights
        """
        try:
            # Get conversation context for better LLM responses
            conversation_context = self.conversation_history_manager.get_conversation_context(conversation_id)
            previous_questions = conversation_context.get("user_questions", [])
            conversation_topics = conversation_context.get("topics", [])
            
            # Step 1: Convert natural language to SQL using LLM service
            # Note: Using translate_to_sql method which should exist in LLMService
            # This will need to be updated when the schema info is available
            schema_info = {"tables": {}}  # TODO: Get actual schema info
            
            # Check if translate_to_sql is async or sync
            translate_result = self.llm_service.translate_to_sql(user_message, schema_info)
            if hasattr(translate_result, '__await__'):
                sql_query = await translate_result
            else:
                sql_query = translate_result
            
            # Step 2: Execute the SQL query
            execute_result = self.query_executor.execute_query(sql_query)
            if hasattr(execute_result, '__await__'):
                query_results = await execute_result
            else:
                query_results = execute_result
            
            # Step 3: Generate chart recommendation for dashboard updates
            chart_config = self.chart_recommendation_service.recommend_chart_config(
                query_results, user_message
            )
            
            if chart_config:
                logger.info(f"Generated chart recommendation: {chart_config.type} chart for dashboard update")
            else:
                logger.debug("No chart recommendation generated - data not suitable for visualization")
            
            # Step 4: Use enhanced ResponseGenerator for conversational response
            conversational_response = self.response_generator.generate_conversational_response(
                query_results, 
                user_message,
                chart_config=chart_config
            )
            
            # Extract components from the response
            conversational_explanation = conversational_response.message
            combined_insights = list(conversational_response.insights)  # Make a copy
            combined_follow_ups = list(conversational_response.follow_up_questions)  # Make a copy
            
            # Step 5: Analyze the results for additional insights using InsightAnalyzer
            analysis_results = self.insight_analyzer.analyze_query_results(query_results, user_message)
            
            # Step 6: Enhance insights with analyzer results (add up to 2 additional insights)
            analyzer_insights = [insight.message for insight in analysis_results.get("all_insights", [])[:2]]
            combined_insights.extend(analyzer_insights)
            
            # Step 7: Generate proactive insights from the query results
            proactive_insights = self.get_proactive_insights(query_results, user_message)
            
            # Add proactive insight messages to combined insights (limit to 2)
            for proactive_insight in proactive_insights[:2]:
                combined_insights.append(proactive_insight["message"])
            
            # Step 8: Enhance follow-up questions with analyzer and contextual suggestions
            if len(combined_follow_ups) < 3:
                analyzer_questions = analysis_results.get("follow_up_questions", [])
                combined_follow_ups.extend(analyzer_questions[:3 - len(combined_follow_ups)])
            
            # Add contextual suggestions if we still need more follow-up questions
            if len(combined_follow_ups) < 3:
                contextual_suggestions = self.get_contextual_suggestions(conversation_id)
                combined_follow_ups.extend(contextual_suggestions[:3 - len(combined_follow_ups)])
            
            return ConversationalResponse(
                message=conversational_explanation,
                chart_config=chart_config,
                insights=combined_insights[:5],  # Limit to 5 insights
                follow_up_questions=combined_follow_ups[:3],  # Limit to 3 questions
                processing_time_ms=0.0,  # Will be calculated by caller
                conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Error in query execution processing: {str(e)}")
            # Fallback to mock response
            return ConversationalResponse(
                message="I encountered an issue processing your question. Let me try a different approach or you can rephrase your question.",
                chart_config=None,
                insights=["There was a technical issue with the data analysis."],
                follow_up_questions=["Could you try asking your question differently?", "What other data would you like to explore?"],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
    
    def analyze_data_insights(self, query_results, original_question: str) -> Dict[str, Any]:
        """
        Public method to analyze query results and generate insights.
        
        Args:
            query_results: ExecuteResponse from query execution
            original_question: The user's original question
            
        Returns:
            Dict containing analysis results with trends, outliers, and suggestions
        """
        return self.insight_analyzer.analyze_query_results(query_results, original_question)
    
    def clear_conversation_history(self, conversation_id: str) -> bool:
        """
        Clear conversation history for a specific conversation.
        
        Args:
            conversation_id: ID of the conversation to clear
            
        Returns:
            bool: True if conversation was found and cleared, False otherwise
        """
        # Clear from persistent storage
        persistent_cleared = False
        if conversation_id:
            persistent_cleared = self.conversation_history_manager.clear_conversation(conversation_id)
        
        # Clear from in-memory storage for backward compatibility
        memory_cleared = False
        if conversation_id in self.conversation_history:
            del self.conversation_history[conversation_id]
            memory_cleared = True
        
        if persistent_cleared or memory_cleared:
            logger.info(f"Cleared conversation history for: {conversation_id}")
            return True
        return False
    
    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get conversation context for enhanced follow-up question processing.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Dict[str, Any]: Context information including recent messages and topics
        """
        if not conversation_id:
            return {}
        
        return self.conversation_history_manager.get_conversation_context(conversation_id)
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get a summary of the conversation for display purposes.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Dict[str, Any]: Summary information about the conversation
        """
        if not conversation_id:
            return {}
        
        return self.conversation_history_manager.get_conversation_summary(conversation_id)
    
    def cleanup_expired_conversations(self) -> int:
        """
        Clean up expired conversations.
        
        Returns:
            int: Number of conversations cleaned up
        """
        return self.conversation_history_manager.cleanup_expired_conversations()
    
    def generate_initial_data_questions(self, table_name: str = None) -> List[str]:
        """
        Generate initial question suggestions when data is uploaded.
        
        Args:
            table_name: Optional specific table name to analyze
            
        Returns:
            List[str]: List of suggested questions for initial exploration
        """
        try:
            suggestions = self.proactive_exploration_service.generate_initial_questions(table_name)
            return [suggestion.question for suggestion in suggestions]
        except Exception as e:
            logger.error(f"Error generating initial data questions: {str(e)}")
            return [
                "What does my data look like overall?",
                "How much data do I have to work with?",
                "What are the main patterns in my data?"
            ]
    
    def suggest_questions_from_data_structure(self, schema_info: Dict[str, Any]) -> List[str]:
        """
        Suggest interesting questions based on available data structure.
        
        Args:
            schema_info: Database schema information
            
        Returns:
            List[str]: Questions suggested based on data structure
        """
        try:
            suggestions = self.proactive_exploration_service.suggest_questions_from_structure(schema_info)
            return [suggestion.question for suggestion in suggestions]
        except Exception as e:
            logger.error(f"Error suggesting questions from data structure: {str(e)}")
            return [
                "What insights can I discover in this data?",
                "What patterns should I look for?",
                "How can I best explore this dataset?"
            ]
    
    def get_proactive_insights(self, query_results, original_question: str) -> List[Dict[str, Any]]:
        """
        Get proactive insights when interesting patterns are detected in responses.
        
        Args:
            query_results: Results from query execution
            original_question: The user's original question
            
        Returns:
            List[Dict[str, Any]]: Proactive insights with suggested actions
        """
        try:
            insights = self.proactive_exploration_service.detect_proactive_insights(query_results, original_question)
            return [
                {
                    "message": insight.message,
                    "type": insight.insight_type,
                    "confidence": insight.confidence,
                    "suggested_actions": insight.suggested_actions
                }
                for insight in insights
            ]
        except Exception as e:
            logger.error(f"Error getting proactive insights: {str(e)}")
            return []
    
    def get_contextual_suggestions(self, conversation_id: str) -> List[str]:
        """
        Generate contextual question suggestions based on conversation history.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            List[str]: Contextual question suggestions
        """
        try:
            conversation_history = self.get_conversation_history(conversation_id)
            suggestions = self.proactive_exploration_service.generate_contextual_suggestions(conversation_history)
            return [suggestion.question for suggestion in suggestions]
        except Exception as e:
            logger.error(f"Error getting contextual suggestions: {str(e)}")
            return [
                "What would you like to explore next?",
                "Are there specific aspects of this data that interest you?",
                "Would you like to see this data from a different angle?"
            ]
    
    async def process_chat_message_with_streaming(
        self, 
        request: ChatRequest,
        stream_id: Optional[str] = None
    ) -> ConversationalResponse:
        """
        Process chat message with streaming updates for better perceived performance.
        
        Args:
            request: ChatRequest containing the user's message
            stream_id: Optional stream ID for streaming updates
            
        Returns:
            ConversationalResponse: Conversational response with insights and suggestions
        """
        if stream_id:
            # Use streaming processor for better UX (Requirements 6.2)
            return await self.stream_processor.process_with_streaming(
                stream_id,
                self.process_chat_message,
                request
            )
        else:
            # Fall back to regular processing
            return await self.process_chat_message(request)
    
    def _generate_context_hash(self, conversation_id: str) -> str:
        """
        Generate hash of conversation context for caching.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            str: Hash of conversation context
        """
        try:
            # Get recent conversation history for context
            recent_history = self.get_conversation_history(conversation_id)[-5:]  # Last 5 messages
            
            # Create context string from recent messages
            context_parts = []
            for msg in recent_history:
                if isinstance(msg, dict):
                    role = msg.get('role', 'unknown')
                    message = msg.get('message', '')
                    context_parts.append(f"{role}:{message[:50]}")
            
            context_string = "|".join(context_parts)
            
            # Generate hash
            import hashlib
            return hashlib.md5(context_string.encode('utf-8')).hexdigest()[:8]
            
        except Exception as e:
            logger.warning(f"Failed to generate context hash: {e}")
            return "default"
    
    def _generate_error_response(self, error: Exception, user_message: str, conversation_id: str) -> ConversationalResponse:
        """
        Generate beginner-friendly error responses with recovery suggestions.
        
        Args:
            error: The exception that occurred
            user_message: The user's original message
            conversation_id: Conversation identifier
            
        Returns:
            ConversationalResponse: User-friendly error response with suggestions
        """
        # Import exceptions here to avoid circular imports
        try:
            from .exceptions import (
                QueryExecutionError, SQLSyntaxError, SQLSecurityError, 
                QueryTimeoutError, ResultSetTooLargeError, SQLSchemaError,
                TableNotFoundError, DatabaseConnectionError
            )
        except ImportError:
            from exceptions import (
                QueryExecutionError, SQLSyntaxError, SQLSecurityError, 
                QueryTimeoutError, ResultSetTooLargeError, SQLSchemaError,
                TableNotFoundError, DatabaseConnectionError
            )
        
        error_message = str(error).lower()
        
        # Handle specific error types with conversational messages
        if isinstance(error, SQLSchemaError) or "column" in error_message and ("not found" in error_message or "does not exist" in error_message):
            return ConversationalResponse(
                message="I couldn't find that information in your data. It looks like you're asking about something that might not be available in the dataset.",
                chart_config=None,
                insights=["The data doesn't contain the specific field or information you're looking for."],
                follow_up_questions=[
                    "What data do you have available?",
                    "Can you show me what columns are in the data?",
                    "What would you like to explore instead?"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        elif isinstance(error, TableNotFoundError) or "table" in error_message and ("not found" in error_message or "does not exist" in error_message):
            return ConversationalResponse(
                message="It looks like there's no data loaded yet. You'll need to upload some data before I can help you analyze it.",
                chart_config=None,
                insights=["No data has been uploaded to analyze."],
                follow_up_questions=[
                    "Would you like to upload a CSV file?",
                    "Should we use some demo data to get started?",
                    "What kind of data are you planning to analyze?"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        elif isinstance(error, QueryTimeoutError) or "timeout" in error_message or "time limit" in error_message:
            return ConversationalResponse(
                message="That question is taking a bit too long to process. Let's try something simpler or more specific.",
                chart_config=None,
                insights=["The query is too complex or the dataset is very large."],
                follow_up_questions=[
                    "Can you ask about a smaller subset of the data?",
                    "Would you like to see a summary first?",
                    "Try asking about a specific time period or category"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        elif isinstance(error, ResultSetTooLargeError) or "too large" in error_message or "limit" in error_message:
            return ConversationalResponse(
                message="That question would return too much data to display easily. Let me help you narrow it down to something more manageable.",
                chart_config=None,
                insights=["The result would be too large to display effectively."],
                follow_up_questions=[
                    "Would you like to see just the top results?",
                    "Can we filter this by a specific category or time period?",
                    "Should we look at a summary instead of all the details?"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        elif isinstance(error, SQLSyntaxError) or "syntax" in error_message or "parse" in error_message:
            return ConversationalResponse(
                message="I had trouble understanding exactly what you're looking for. Could you try asking in a different way?",
                chart_config=None,
                insights=["The question might be too complex or unclear for me to process."],
                follow_up_questions=[
                    "Try using simpler language",
                    "Can you be more specific about what you want to see?",
                    "What aspect of the data interests you most?"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        elif isinstance(error, DatabaseConnectionError) or "connection" in error_message or "database" in error_message:
            return ConversationalResponse(
                message="I'm having trouble accessing the data right now. This is usually temporary - please try again in a moment.",
                chart_config=None,
                insights=["There's a temporary issue with the data connection."],
                follow_up_questions=[
                    "Try asking your question again",
                    "Would you like to try a different question while we wait?",
                    "Is there something else I can help you with?"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        # Handle network/translation errors
        elif "network" in error_message or "connection" in error_message:
            return ConversationalResponse(
                message="I'm having trouble connecting right now. Please check your internet connection and try again.",
                chart_config=None,
                insights=["There seems to be a network connectivity issue."],
                follow_up_questions=[
                    "Try refreshing the page",
                    "Check your internet connection",
                    "Try asking again in a moment"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        # Handle vague or unclear questions
        elif len(user_message.split()) < 3 or not any(word in user_message.lower() for word in ["show", "what", "how", "when", "where", "which", "total", "count", "average", "sum"]):
            return ConversationalResponse(
                message="I'd love to help, but I need a bit more detail about what you're looking for. What specific information about your data would you like to see?",
                chart_config=None,
                insights=["Your question might need more specific details for me to understand."],
                follow_up_questions=[
                    "What specific data would you like to explore?",
                    "Are you looking for totals, averages, or trends?",
                    "Would you like to see a summary of what data is available?"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )
        
        # Default friendly error response
        else:
            return ConversationalResponse(
                message="I ran into an issue while processing your question. Let me suggest some other ways we can explore your data together.",
                chart_config=None,
                insights=["Something unexpected happened while analyzing your question."],
                follow_up_questions=[
                    "What would you like to know about your data?",
                    "Should we start with a simple overview?",
                    "Try asking about totals, trends, or comparisons"
                ],
                processing_time_ms=0.0,
                conversation_id=conversation_id
            )