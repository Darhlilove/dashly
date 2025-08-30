"""
LLM Service for natural language to SQL translation using OpenRouter.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
import httpx
from dataclasses import dataclass

try:
    from .logging_config import get_logger
    from .exceptions import ValidationError, ConfigurationError
except ImportError:
    from logging_config import get_logger
    from exceptions import ValidationError, ConfigurationError

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
        logger.info(f"LLM service initialized with model: {self.config.model}")
    
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