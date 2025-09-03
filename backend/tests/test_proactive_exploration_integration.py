"""
Integration tests for proactive exploration API endpoints.

Tests the API endpoints for proactive data exploration features.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

try:
    from ..src.main import app
    from ..src.chat_service import ChatService
    from ..src.proactive_exploration_service import ProactiveExplorationService
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from main import app
    from chat_service import ChatService
    from proactive_exploration_service import ProactiveExplorationService


class TestProactiveExplorationAPI:
    """Test cases for proactive exploration API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        
        # Mock authentication
        self.auth_patcher = patch('main.verify_api_key')
        self.mock_auth = self.auth_patcher.start()
        self.mock_auth.return_value = True
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.auth_patcher.stop()
    
    @patch('main.chat_service')
    def test_get_initial_question_suggestions(self, mock_chat_service):
        """Test the initial question suggestions endpoint."""
        # Mock the chat service response
        mock_chat_service.generate_initial_data_questions.return_value = [
            "What does my data look like overall?",
            "How much data do I have to work with?",
            "What are the main patterns in my data?"
        ]
        
        response = self.client.get("/api/suggestions/initial")
        
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        assert "What does my data look like overall?" in data["suggestions"]
        assert data["suggestion_type"] == "initial_exploration"
    
    @patch('main.chat_service')
    @patch('main.schema_service')
    def test_get_structure_based_suggestions(self, mock_schema_service, mock_chat_service):
        """Test the structure-based suggestions endpoint."""
        # Mock schema service response
        mock_schema_service.get_all_tables_schema.return_value = {
            "tables": {
                "sales_data": {
                    "columns": [{"name": "revenue", "type": "decimal"}]
                }
            }
        }
        
        # Mock chat service response
        mock_chat_service.suggest_questions_from_data_structure.return_value = [
            "What are my total sales?",
            "How do sales break down by category?"
        ]
        
        response = self.client.get("/api/suggestions/structure")
        
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 2
        assert data["suggestion_type"] == "structure_based"
        assert "tables_analyzed" in data
    
    @patch('main.chat_service')
    def test_get_contextual_suggestions(self, mock_chat_service):
        """Test the contextual suggestions endpoint."""
        # Mock chat service response
        mock_chat_service.get_contextual_suggestions.return_value = [
            "How does this break down by different categories?",
            "What are the top performers?"
        ]
        
        conversation_id = "test-conversation-123"
        response = self.client.get(f"/api/suggestions/contextual/{conversation_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) == 2
        assert data["conversation_id"] == conversation_id
        assert data["suggestion_type"] == "contextual"
    
    @patch('main.chat_service')
    def test_get_proactive_insights(self, mock_chat_service):
        """Test the proactive insights endpoint."""
        # Mock chat service response
        mock_chat_service.get_proactive_insights.return_value = [
            {
                "message": "Revenue shows strong growth trend",
                "type": "trend",
                "confidence": 0.9,
                "suggested_actions": ["Analyze growth drivers"]
            }
        ]
        
        request_data = {
            "query_results": {
                "columns": ["revenue", "month"],
                "rows": [[1000, "Jan"], [1200, "Feb"]],
                "row_count": 2
            },
            "original_question": "monthly revenue"
        }
        
        response = self.client.post("/api/insights/proactive", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert len(data["insights"]) == 1
        assert data["insights"][0]["type"] == "trend"
        assert data["original_question"] == "monthly revenue"
    
    def test_get_proactive_insights_missing_data(self):
        """Test proactive insights endpoint with missing query_results."""
        request_data = {
            "original_question": "test question"
            # Missing query_results
        }
        
        response = self.client.post("/api/insights/proactive", json=request_data)
        
        assert response.status_code == 400
        assert "query_results is required" in response.json()["detail"]
    
    @patch('main.chat_service')
    def test_get_initial_suggestions_with_table_name(self, mock_chat_service):
        """Test initial suggestions with specific table name."""
        mock_chat_service.generate_initial_data_questions.return_value = [
            "What does the sales_data table show?",
            "How much sales data do I have?"
        ]
        
        response = self.client.get("/api/suggestions/initial?table_name=sales_data")
        
        assert response.status_code == 200
        data = response.json()
        assert data["table_name"] == "sales_data"
        assert len(data["suggestions"]) == 2
        
        # Verify the chat service was called with the correct table name
        mock_chat_service.generate_initial_data_questions.assert_called_once_with("sales_data")
    
    @patch('main.chat_service')
    def test_api_error_handling(self, mock_chat_service):
        """Test API error handling when service raises exception."""
        # Mock chat service to raise exception
        mock_chat_service.generate_initial_data_questions.side_effect = Exception("Service error")
        
        response = self.client.get("/api/suggestions/initial")
        
        assert response.status_code == 500
        assert "Failed to generate initial question suggestions" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])