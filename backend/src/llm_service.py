"""
LLM Service for natural language to SQL translation and conversational responses using OpenRouter.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from dataclasses import dataclass

try:
    from .logging_config import get_logger
    from .exceptions import ValidationError, ConfigurationError
    from .response_cache import get_response_cache
except ImportError:
    from logging_config import get_logger
    from exceptions import ValidationError, ConfigurationError
    from response_cache import get_response_cache

logger = get_logger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM service."""
    api_key: str
    model: str
    base_url: str
    timeout: int = 30
    max_tokens: int = 1000
    temperature: float = 0.1  # Low temperature for consistent SQL generation
    conversational_temperature: float = 0.3  # Higher temperature for conversational responses


class LLMService:
    """Service for interacting with OpenRouter LLM API."""
    
    def __init__(self):
        """Initialize LLM service with OpenRouter configuration."""
        self.config = self._load_config()
        self.client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://dashly.app",  # Optional: for OpenRouter analytics
                "X-Title": "Dashly - Dashboard Auto-Designer"  # Optional: for OpenRouter analytics
            }
        )
        
        # Performance optimization: response caching (Requirements 6.1)
        self.response_cache = get_response_cache()
        
        logger.info(f"LLM service initialized with model: {self.config.model} and response caching")
    
    def _load_config(self) -> LLMConfig:
        """Load LLM configuration from environment variables."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key or api_key == "your_openrouter_api_key_here":
            raise ConfigurationError(
                "OPENROUTER_API_KEY environment variable must be set with a valid API key"
            )
        
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet:beta")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        
        return LLMConfig(
            api_key=api_key,
            model=model,
            base_url=base_url
        )
    
    async def translate_to_sql(self, question: str, schema_info: Dict[str, Any]) -> str:
        """
        Translate natural language question to SQL query.
        
        Args:
            question: Natural language question about the data
            schema_info: Database schema information including tables and columns
            
        Returns:
            str: Generated SQL query
            
        Raises:
            ValidationError: If question is invalid
            Exception: If LLM API call fails
        """
        if not question or not question.strip():
            raise ValidationError("Question cannot be empty")
        
        # Build schema context for the LLM
        schema_context = self._build_schema_context(schema_info)
        
        # Create the prompt for SQL generation
        prompt = self._build_sql_prompt(question.strip(), schema_context)
        
        try:
            logger.info(f"Translating question to SQL: {question[:100]}...")
            
            # Check cache first for performance optimization (Requirements 6.1)
            cache_key = f"sql_translation:{question}:{schema_context[:100]}"
            cached_sql = self.response_cache.get_llm_response(cache_key, self.config.model)
            if cached_sql:
                logger.info("Cache hit for SQL translation")
                return cached_sql
            
            # Make API call to OpenRouter
            response = await self.client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert SQL query generator. Generate only valid SQL queries based on the provided schema and question. Return only the SQL query without any explanation or formatting."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "stop": [";", "\n\n"]  # Stop at semicolon or double newline
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract SQL from response
            sql_query = result["choices"][0]["message"]["content"].strip()
            
            # Clean up the SQL query
            sql_query = self._clean_sql_query(sql_query)
            
            # Cache the result for future use (Requirements 6.1)
            self.response_cache.cache_llm_response(
                cache_key, 
                sql_query, 
                self.config.model,
                ttl=600  # 10 minutes TTL for SQL translations
            )
            
            logger.info(f"Generated SQL: {sql_query}")
            return sql_query
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM API error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"OpenRouter request error: {str(e)}")
            raise Exception("Failed to connect to LLM service")
        except (KeyError, IndexError) as e:
            logger.error(f"Invalid LLM response format: {str(e)}")
            raise Exception("Invalid response from LLM service")
        except Exception as e:
            logger.error(f"Unexpected LLM error: {str(e)}")
            raise Exception(f"LLM translation failed: {str(e)}")
    
    def _build_schema_context(self, schema_info: Dict[str, Any]) -> str:
        """Build schema context string for the LLM prompt."""
        if not schema_info or "tables" not in schema_info:
            return "No schema information available."
        
        context_parts = ["Database Schema:"]
        
        for table_name, table_info in schema_info["tables"].items():
            context_parts.append(f"\nTable: {table_name}")
            
            if "columns" in table_info:
                context_parts.append("Columns:")
                for col in table_info["columns"]:
                    col_name = col.get("name", "unknown")
                    col_type = col.get("type", "unknown")
                    context_parts.append(f"  - {col_name} ({col_type})")
            
            if "sample_data" in table_info and table_info["sample_data"]:
                context_parts.append("Sample data:")
                sample_rows = table_info["sample_data"][:3]  # Show first 3 rows
                for row in sample_rows:
                    context_parts.append(f"  {row}")
        
        return "\n".join(context_parts)
    
    def _build_sql_prompt(self, question: str, schema_context: str) -> str:
        """Build the complete prompt for SQL generation."""
        return f"""Given the following database schema, generate a SQL query to answer the question.

{schema_context}

Question: {question}

Requirements:
- Generate only a SELECT statement
- Use proper SQL syntax for DuckDB
- Include appropriate WHERE, GROUP BY, ORDER BY clauses as needed
- Limit results to reasonable numbers (use LIMIT if showing individual records)
- Use meaningful column aliases for calculated fields
- For date/time queries, use appropriate date functions
- For aggregations, group by relevant dimensions

SQL Query:"""
    
    def _clean_sql_query(self, sql_query: str) -> str:
        """Clean and validate the generated SQL query."""
        # Remove common prefixes/suffixes that LLMs sometimes add
        sql_query = sql_query.strip()
        
        # Remove markdown code blocks if present
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.startswith("```"):
            sql_query = sql_query[3:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        
        # Remove trailing semicolon if present
        if sql_query.endswith(";"):
            sql_query = sql_query[:-1]
        
        # Ensure it starts with SELECT (basic validation)
        sql_query = sql_query.strip()
        if not sql_query.upper().startswith("SELECT"):
            logger.warning(f"Generated query doesn't start with SELECT: {sql_query}")
            # Try to extract SELECT statement if it's embedded
            lines = sql_query.split("\n")
            for line in lines:
                if line.strip().upper().startswith("SELECT"):
                    sql_query = line.strip()
                    break
        
        return sql_query
    
    async def generate_conversational_explanation(
        self, 
        query_results: Dict[str, Any], 
        original_question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a conversational explanation of query results.
        
        Args:
            query_results: Results from SQL query execution
            original_question: The user's original question
            context: Additional context about the data or conversation
            
        Returns:
            str: Business-friendly conversational explanation
        """
        try:
            # Build context for the explanation
            explanation_prompt = self._build_explanation_prompt(
                query_results, original_question, context
            )
            
            logger.info("Generating conversational explanation for query results")
            
            # Check cache first (Requirements 6.1)
            cache_key = f"explanation:{original_question}:{str(query_results)[:200]}"
            cached_explanation = self.response_cache.get_llm_response(cache_key, self.config.model)
            if cached_explanation:
                logger.info("Cache hit for conversational explanation")
                return cached_explanation
            
            response = await self.client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a friendly data analyst who explains data insights in conversational, business-friendly language. 
                            
Your responses should:
- Use natural, conversational tone like you're talking to a colleague
- Explain data in business terms, not technical jargon
- Highlight key insights and what they mean for the business
- Be encouraging and supportive
- Avoid technical database or SQL terminology
- Focus on actionable insights when possible
- Keep explanations concise but informative"""
                        },
                        {
                            "role": "user", 
                            "content": explanation_prompt
                        }
                    ],
                    "max_tokens": 500,
                    "temperature": self.config.conversational_temperature
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            explanation = result["choices"][0]["message"]["content"].strip()
            
            # Cache the result (Requirements 6.1)
            self.response_cache.cache_llm_response(
                cache_key,
                explanation,
                self.config.model,
                ttl=300  # 5 minutes TTL for explanations
            )
            
            logger.info("Generated conversational explanation successfully")
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating conversational explanation: {str(e)}")
            # Return a fallback explanation
            return self._generate_fallback_explanation(query_results, original_question)
    
    async def generate_data_insights(
        self, 
        query_results: Dict[str, Any], 
        original_question: str
    ) -> List[str]:
        """
        Generate business-friendly insights from query results.
        
        Args:
            query_results: Results from SQL query execution
            original_question: The user's original question
            
        Returns:
            List[str]: List of business insights
        """
        try:
            insights_prompt = self._build_insights_prompt(query_results, original_question)
            
            logger.info("Generating data insights from query results")
            
            response = await self.client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a business analyst who identifies key insights from data. 
                            
Generate 2-4 concise, actionable insights that:
- Highlight important patterns, trends, or outliers
- Explain what the data means for business decisions
- Use business-friendly language
- Focus on actionable information
- Are specific and concrete
- Each insight should be one clear sentence

Return insights as a JSON array of strings."""
                        },
                        {
                            "role": "user",
                            "content": insights_prompt
                        }
                    ],
                    "max_tokens": 300,
                    "temperature": self.config.conversational_temperature
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            insights_text = result["choices"][0]["message"]["content"].strip()
            
            # Try to parse as JSON, fallback to text parsing
            try:
                insights = json.loads(insights_text)
                if isinstance(insights, list):
                    return insights[:4]  # Limit to 4 insights
            except json.JSONDecodeError:
                # Fallback: split by lines and clean up
                insights = [
                    line.strip().lstrip('- ').lstrip('• ')
                    for line in insights_text.split('\n')
                    if line.strip() and not line.strip().startswith('[') and not line.strip().endswith(']')
                ]
                return insights[:4]
            
            logger.info(f"Generated {len(insights)} data insights")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating data insights: {str(e)}")
            return self._generate_fallback_insights(query_results)
    
    async def generate_follow_up_questions(
        self, 
        query_results: Dict[str, Any], 
        original_question: str,
        conversation_context: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate context-aware follow-up question suggestions.
        
        Args:
            query_results: Results from SQL query execution
            original_question: The user's original question
            conversation_context: Previous questions in the conversation
            
        Returns:
            List[str]: List of suggested follow-up questions
        """
        try:
            followup_prompt = self._build_followup_prompt(
                query_results, original_question, conversation_context
            )
            
            logger.info("Generating follow-up question suggestions")
            
            response = await self.client.post(
                f"{self.config.base_url}/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a helpful data assistant who suggests relevant follow-up questions.
                            
Generate 2-3 natural follow-up questions that:
- Build on the current analysis
- Help users explore related aspects of their data
- Are phrased in natural, conversational language
- Avoid technical jargon
- Lead to actionable insights
- Are specific to the data and context provided

Return questions as a JSON array of strings."""
                        },
                        {
                            "role": "user",
                            "content": followup_prompt
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": self.config.conversational_temperature
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            questions_text = result["choices"][0]["message"]["content"].strip()
            
            # Try to parse as JSON, fallback to text parsing
            try:
                questions = json.loads(questions_text)
                if isinstance(questions, list):
                    return questions[:3]  # Limit to 3 questions
            except json.JSONDecodeError:
                # Fallback: split by lines and clean up
                questions = [
                    line.strip().lstrip('- ').lstrip('• ').rstrip('?') + '?'
                    for line in questions_text.split('\n')
                    if line.strip() and '?' in line
                ]
                return questions[:3]
            
            logger.info(f"Generated {len(questions)} follow-up questions")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
            return self._generate_fallback_questions(original_question)
    
    def _build_explanation_prompt(
        self, 
        query_results: Dict[str, Any], 
        original_question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for generating conversational explanations."""
        data_summary = self._summarize_query_results(query_results)
        
        prompt_parts = [
            f"Original question: {original_question}",
            f"Data results: {data_summary}",
        ]
        
        if context and context.get("previous_questions"):
            prompt_parts.append(f"Previous questions in conversation: {context['previous_questions']}")
        
        prompt_parts.append(
            "Please provide a conversational, business-friendly explanation of these results. "
            "Focus on what the data means and why it matters, using natural language that "
            "anyone can understand."
        )
        
        return "\n\n".join(prompt_parts)
    
    def _build_insights_prompt(self, query_results: Dict[str, Any], original_question: str) -> str:
        """Build prompt for generating data insights."""
        data_summary = self._summarize_query_results(query_results)
        
        return f"""Original question: {original_question}

Data results: {data_summary}

Analyze this data and identify the most important business insights. Focus on:
- Key patterns or trends
- Notable numbers or changes
- What this means for business decisions
- Opportunities or concerns revealed by the data

Provide insights as actionable, business-focused observations."""
    
    def _build_followup_prompt(
        self, 
        query_results: Dict[str, Any], 
        original_question: str,
        conversation_context: Optional[List[str]] = None
    ) -> str:
        """Build prompt for generating follow-up questions."""
        data_summary = self._summarize_query_results(query_results)
        
        prompt_parts = [
            f"Original question: {original_question}",
            f"Data results: {data_summary}",
        ]
        
        if conversation_context:
            prompt_parts.append(f"Previous questions: {', '.join(conversation_context[-3:])}")
        
        prompt_parts.append(
            "Based on this analysis, suggest natural follow-up questions that would help "
            "the user explore related aspects of their data or dive deeper into these findings."
        )
        
        return "\n\n".join(prompt_parts)
    
    def _summarize_query_results(self, query_results: Dict[str, Any]) -> str:
        """Create a concise summary of query results for LLM prompts."""
        if not query_results or "data" not in query_results:
            return "No data returned"
        
        data = query_results["data"]
        if not data:
            return "Empty result set"
        
        # Get basic info about the results
        row_count = len(data)
        if row_count == 0:
            return "No rows returned"
        
        # Get column names
        columns = list(data[0].keys()) if data else []
        
        # Sample a few rows for context
        sample_size = min(3, row_count)
        sample_data = data[:sample_size]
        
        summary_parts = [
            f"Returned {row_count} rows with columns: {', '.join(columns)}",
        ]
        
        if sample_data:
            summary_parts.append("Sample data:")
            for i, row in enumerate(sample_data):
                row_summary = ", ".join([f"{k}: {v}" for k, v in row.items()])
                summary_parts.append(f"  Row {i+1}: {row_summary}")
        
        return "\n".join(summary_parts)
    
    def _generate_fallback_explanation(self, query_results: Dict[str, Any], original_question: str) -> str:
        """Generate a fallback explanation when LLM call fails."""
        if not query_results or "data" not in query_results:
            return "I found some information related to your question, but I'm having trouble explaining it right now. Let me know if you'd like to try a different approach!"
        
        data = query_results["data"]
        row_count = len(data) if data else 0
        
        if row_count == 0:
            return "I looked for data matching your question, but didn't find any results. This might mean the data doesn't exist, or we might need to ask the question differently."
        
        return f"I found {row_count} records that match your question. The data shows some interesting patterns that could be valuable for your analysis."
    
    def _generate_fallback_insights(self, query_results: Dict[str, Any]) -> List[str]:
        """Generate fallback insights when LLM call fails."""
        if not query_results or "data" not in query_results:
            return ["The data contains information that could provide valuable insights for your business."]
        
        data = query_results["data"]
        row_count = len(data) if data else 0
        
        if row_count == 0:
            return ["No data was found matching your criteria - this might indicate an opportunity to explore different aspects of your data."]
        
        insights = [f"Your query returned {row_count} records, indicating there's substantial data to analyze."]
        
        if data and len(data) > 1:
            insights.append("The data shows multiple data points that could reveal important patterns.")
        
        return insights
    
    def _generate_fallback_questions(self, original_question: str) -> List[str]:
        """Generate fallback follow-up questions when LLM call fails."""
        return [
            "Would you like to see this data broken down differently?",
            "Are you interested in comparing this to other time periods?",
            "Should we look at this from a different angle?"
        ]
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def cleanup_llm_service():
    """Cleanup the global LLM service instance."""
    global _llm_service
    if _llm_service is not None:
        await _llm_service.close()
        _llm_service = None