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
except ImportError:
    from models import ChatRequest, ConversationalResponse, ChartConfig
    from logging_config import get_logger
    from insight_analyzer import InsightAnalyzer
    from response_generator import ResponseGenerator

logger = get_logger(__name__)


class ChatService:
    """
    Main orchestrator for chat interactions, handling the complete flow
    from question to conversational response.
    """
    
    def __init__(self, query_executor=None, llm_service=None, response_generator=None, insight_analyzer=None):
        """
        Initialize ChatService with required dependencies.
        
        Args:
            query_executor: QueryExecutor instance for SQL execution
            llm_service: LLMService instance for natural language processing
            response_generator: ResponseGenerator instance for conversational responses
            insight_analyzer: InsightAnalyzer instance for pattern detection
        """
        self.query_executor = query_executor
        self.llm_service = llm_service
        self.response_generator = response_generator or ResponseGenerator()
        self.insight_analyzer = insight_analyzer or InsightAnalyzer()
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("ChatService initialized with InsightAnalyzer and ResponseGenerator")
    
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
        
        try:
            # Initialize conversation history if needed
            if conversation_id not in self.conversation_history:
                self.conversation_history[conversation_id] = []
            
            # Add user message to history
            self.conversation_history[conversation_id].append({
                "role": "user",
                "message": request.message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Process the message with available services
            if self.query_executor and self.llm_service:
                # Full processing with query execution and analysis
                response = await self._process_with_query_execution(request.message, conversation_id)
                response_message = response.message
                insights = response.insights
                follow_up_questions = response.follow_up_questions
            else:
                # Fallback to mock responses for demonstration
                response_message = self._generate_mock_response(request.message)
                insights = self._generate_mock_insights()
                follow_up_questions = self._generate_mock_follow_up_questions()
            
            # Add assistant response to history
            self.conversation_history[conversation_id].append({
                "role": "assistant", 
                "message": response_message,
                "timestamp": datetime.now().isoformat()
            })
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(f"Chat message processed successfully in {processing_time:.2f}ms")
            
            return ConversationalResponse(
                message=response_message,
                chart_config=None,  # TODO: Implement chart recommendation
                insights=insights,
                follow_up_questions=follow_up_questions,
                processing_time_ms=processing_time,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"Error processing chat message: {str(e)}")
            
            # Return user-friendly error response
            return ConversationalResponse(
                message="I'm having trouble understanding your question right now. Could you try rephrasing it or asking something else about your data?",
                chart_config=None,
                insights=[],
                follow_up_questions=["What data do you have available?", "Can you show me a summary of the data?"],
                processing_time_ms=processing_time,
                conversation_id=conversation_id
            )
    
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
            conversation_history = self.get_conversation_history(conversation_id)
            previous_questions = [
                msg["message"] for msg in conversation_history[-5:] 
                if msg["role"] == "user"
            ]
            
            # Step 1: Convert natural language to SQL using LLM service
            # Note: Using translate_to_sql method which should exist in LLMService
            # This will need to be updated when the schema info is available
            schema_info = {"tables": {}}  # TODO: Get actual schema info
            sql_query = await self.llm_service.translate_to_sql(user_message, schema_info)
            
            # Step 2: Execute the SQL query
            query_results = await self.query_executor.execute_query(sql_query)
            
            # Step 3: Generate conversational explanation using enhanced LLM service
            conversational_explanation = await self.llm_service.generate_conversational_explanation(
                query_results, 
                user_message,
                context={"previous_questions": previous_questions}
            )
            
            # Step 4: Generate business insights using enhanced LLM service
            llm_insights = await self.llm_service.generate_data_insights(
                query_results, 
                user_message
            )
            
            # Step 5: Generate follow-up questions using enhanced LLM service
            llm_follow_ups = await self.llm_service.generate_follow_up_questions(
                query_results, 
                user_message,
                conversation_context=previous_questions
            )
            
            # Step 6: Analyze the results for additional insights using InsightAnalyzer
            analysis_results = self.insight_analyzer.analyze_query_results(query_results, user_message)
            
            # Step 7: Combine insights from LLM and analyzer
            combined_insights = []
            combined_insights.extend(llm_insights)
            combined_insights.extend([insight.message for insight in analysis_results["all_insights"][:2]])
            
            # Step 8: Combine follow-up questions, prioritizing LLM-generated ones
            combined_follow_ups = llm_follow_ups
            if len(combined_follow_ups) < 3:
                analyzer_questions = analysis_results.get("follow_up_questions", [])
                combined_follow_ups.extend(analyzer_questions[:3 - len(combined_follow_ups)])
            
            return ConversationalResponse(
                message=conversational_explanation,
                chart_config=None,  # TODO: Add chart recommendation logic
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
        if conversation_id in self.conversation_history:
            del self.conversation_history[conversation_id]
            logger.info(f"Cleared conversation history for: {conversation_id}")
            return True
        return False