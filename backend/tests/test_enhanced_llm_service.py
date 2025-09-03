"""
Tests for enhanced LLM service conversational capabilities.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json

try:
    from src.llm_service import LLMService, LLMConfig
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from src.llm_service import LLMService, LLMConfig


class TestEnhancedLLMService:
    """Test enhanced LLM service conversational features."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock LLM configuration."""
        return LLMConfig(
            api_key="test_key",
            model="test_model",
            base_url="https://test.api",
            conversational_temperature=0.3
        )
    
    @pytest.fixture
    def sample_query_results(self):
        """Sample query results for testing."""
        return {
            "data": [
                {"month": "January", "sales": 10000, "customers": 150},
                {"month": "February", "sales": 12000, "customers": 180},
                {"month": "March", "sales": 15000, "customers": 200}
            ],
            "columns": ["month", "sales", "customers"]
        }
    
    @pytest.fixture
    def llm_service(self, mock_config):
        """Create LLM service with mocked config."""
        with patch.object(LLMService, '_load_config', return_value=mock_config):
            service = LLMService()
            service.client = AsyncMock()
            return service
    
    @pytest.mark.asyncio
    async def test_generate_conversational_explanation(self, llm_service, sample_query_results):
        """Test conversational explanation generation."""
        # Mock API response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Looking at your sales data, I can see some great growth happening! Your sales increased from $10,000 in January to $15,000 in March, which is a 50% increase. Your customer base is also growing steadily, from 150 to 200 customers."
                }
            }]
        }
        llm_service.client.post.return_value = mock_response
        
        # Test the method
        explanation = await llm_service.generate_conversational_explanation(
            sample_query_results,
            "Show me monthly sales and customer data"
        )
        
        # Verify the explanation is conversational
        assert "great growth" in explanation.lower()
        assert "50% increase" in explanation
        assert "$10,000" in explanation
        assert "$15,000" in explanation
        
        # Verify API was called with correct parameters
        llm_service.client.post.assert_called_once()
        call_args = llm_service.client.post.call_args
        assert call_args[1]["json"]["temperature"] == 0.3
        assert "conversational" in call_args[1]["json"]["messages"][0]["content"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_data_insights(self, llm_service, sample_query_results):
        """Test data insights generation."""
        # Mock API response with JSON array
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '["Sales growth of 50% indicates strong market demand", "Customer acquisition is accelerating month over month", "Revenue per customer is increasing from $67 to $75"]'
                }
            }]
        }
        llm_service.client.post.return_value = mock_response
        
        # Test the method
        insights = await llm_service.generate_data_insights(
            sample_query_results,
            "Show me monthly sales trends"
        )
        
        # Verify insights are business-focused
        assert len(insights) == 3
        assert "50%" in insights[0]
        assert "customer acquisition" in insights[1].lower()
        assert "revenue per customer" in insights[2].lower()
        
        # Verify API call
        llm_service.client.post.assert_called_once()
        call_args = llm_service.client.post.call_args
        assert "business analyst" in call_args[1]["json"]["messages"][0]["content"].lower()
    
    @pytest.mark.asyncio
    async def test_generate_follow_up_questions(self, llm_service, sample_query_results):
        """Test follow-up question generation."""
        # Mock API response with JSON array
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '["What products are driving this sales growth?", "How does this compare to the same period last year?", "Which customer segments are growing fastest?"]'
                }
            }]
        }
        llm_service.client.post.return_value = mock_response
        
        # Test the method
        questions = await llm_service.generate_follow_up_questions(
            sample_query_results,
            "Show me monthly sales trends",
            conversation_context=["What are my total sales?"]
        )
        
        # Verify questions are relevant and natural
        assert len(questions) == 3
        assert all(q.endswith("?") for q in questions)
        assert "products" in questions[0].lower()
        assert "last year" in questions[1].lower()
        assert "segments" in questions[2].lower()
        
        # Verify API call includes context
        llm_service.client.post.assert_called_once()
        call_args = llm_service.client.post.call_args
        request_content = call_args[1]["json"]["messages"][1]["content"]
        assert "Previous questions: What are my total sales?" in request_content
    
    @pytest.mark.asyncio
    async def test_fallback_handling(self, llm_service, sample_query_results):
        """Test fallback responses when API calls fail."""
        # Mock API failure
        llm_service.client.post.side_effect = Exception("API Error")
        
        # Test explanation fallback
        explanation = await llm_service.generate_conversational_explanation(
            sample_query_results,
            "Show me sales data"
        )
        assert "3 records" in explanation
        assert "interesting patterns" in explanation.lower()
        
        # Test insights fallback
        insights = await llm_service.generate_data_insights(
            sample_query_results,
            "Show me sales data"
        )
        assert len(insights) >= 1
        assert "3 records" in insights[0]
        
        # Test questions fallback
        questions = await llm_service.generate_follow_up_questions(
            sample_query_results,
            "Show me sales data"
        )
        assert len(questions) == 3
        assert all(q.endswith("?") for q in questions)
    
    def test_summarize_query_results(self, llm_service, sample_query_results):
        """Test query results summarization."""
        summary = llm_service._summarize_query_results(sample_query_results)
        
        assert "3 rows" in summary
        assert "month, sales, customers" in summary
        assert "January" in summary
        assert "10000" in summary
        
        # Test empty results
        empty_results = {"data": []}
        summary = llm_service._summarize_query_results(empty_results)
        assert "Empty result set" in summary
        
        # Test no data
        no_data = {}
        summary = llm_service._summarize_query_results(no_data)
        assert "No data returned" in summary
    
    @pytest.mark.asyncio
    async def test_json_parsing_fallback(self, llm_service, sample_query_results):
        """Test fallback when LLM returns non-JSON format."""
        # Mock API response with non-JSON format
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "- Sales are growing strongly\n- Customer base is expanding\n- Revenue per customer is improving"
                }
            }]
        }
        llm_service.client.post.return_value = mock_response
        
        # Test insights parsing
        insights = await llm_service.generate_data_insights(
            sample_query_results,
            "Show me sales trends"
        )
        
        assert len(insights) == 3
        assert "Sales are growing strongly" in insights[0]
        assert "Customer base is expanding" in insights[1]
        assert "Revenue per customer is improving" in insights[2]


if __name__ == "__main__":
    # Run a simple test
    async def run_test():
        config = LLMConfig(
            api_key="test_key",
            model="test_model", 
            base_url="https://test.api",
            conversational_temperature=0.3
        )
        
        with patch.object(LLMService, '_load_config', return_value=config):
            service = LLMService()
            
            # Test summarization
            sample_data = {
                "data": [
                    {"month": "Jan", "sales": 1000},
                    {"month": "Feb", "sales": 1200}
                ]
            }
            
            summary = service._summarize_query_results(sample_data)
            print("Summary:", summary)
            
            # Test fallback methods
            explanation = service._generate_fallback_explanation(sample_data, "Show sales")
            print("Fallback explanation:", explanation)
            
            insights = service._generate_fallback_insights(sample_data)
            print("Fallback insights:", insights)
            
            questions = service._generate_fallback_questions("Show sales")
            print("Fallback questions:", questions)
    
    asyncio.run(run_test())