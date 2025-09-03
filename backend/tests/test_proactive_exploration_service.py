"""
Tests for ProactiveExplorationService.

Tests the proactive data exploration features including:
- Automatic initial question suggestions when data is uploaded
- Logic to suggest interesting questions based on available data structure
- Proactive insights when interesting patterns are detected in responses
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any

try:
    from ..src.proactive_exploration_service import (
        ProactiveExplorationService,
        DataCharacteristics,
        QuestionSuggestion,
        ProactiveInsight
    )
    from ..src.models import ExecuteResponse, ColumnInfo
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from proactive_exploration_service import (
        ProactiveExplorationService,
        DataCharacteristics,
        QuestionSuggestion,
        ProactiveInsight
    )
    from models import ExecuteResponse, ColumnInfo


class TestProactiveExplorationService:
    """Test cases for ProactiveExplorationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_schema_service = Mock()
        self.mock_llm_service = Mock()
        
        self.service = ProactiveExplorationService(
            db_manager=self.mock_db_manager,
            schema_service=self.mock_schema_service,
            llm_service=self.mock_llm_service
        )
    
    def test_generate_initial_questions_with_financial_data(self):
        """Test generating initial questions for financial data."""
        # Mock schema with financial data
        self.mock_schema_service.get_all_tables_schema.return_value = {
            "tables": {
                "sales_data": {
                    "columns": [
                        {"name": "date", "type": "date"},
                        {"name": "revenue", "type": "decimal"},
                        {"name": "customer_id", "type": "int"}
                    ],
                    "row_count": 1000
                }
            }
        }
        
        suggestions = self.service.generate_initial_questions("sales_data")
        
        assert len(suggestions) > 0
        assert any("revenue" in suggestion.question.lower() or "sales" in suggestion.question.lower() 
                  for suggestion in suggestions)
        assert any("time" in suggestion.question.lower() or "trend" in suggestion.question.lower() 
                  for suggestion in suggestions)
    
    def test_generate_initial_questions_with_user_data(self):
        """Test generating initial questions for user data."""
        # Mock schema with user data
        self.mock_schema_service.get_all_tables_schema.return_value = {
            "tables": {
                "user_activity": {
                    "columns": [
                        {"name": "user_id", "type": "int"},
                        {"name": "activity_date", "type": "date"},
                        {"name": "page_views", "type": "int"}
                    ],
                    "row_count": 5000
                }
            }
        }
        
        suggestions = self.service.generate_initial_questions("user_activity")
        
        assert len(suggestions) > 0
        assert any("user" in suggestion.question.lower() or "customer" in suggestion.question.lower() 
                  for suggestion in suggestions)
    
    def test_suggest_questions_from_structure(self):
        """Test suggesting questions based on data structure."""
        schema_info = {
            "tables": {
                "products": {
                    "columns": [
                        {"name": "product_id", "type": "int"},
                        {"name": "category", "type": "varchar"},
                        {"name": "price", "type": "decimal"}
                    ],
                    "sample_rows": [
                        {"product_id": 1, "category": "Electronics", "price": 299.99}
                    ]
                }
            }
        }
        
        suggestions = self.service.suggest_questions_from_structure(schema_info)
        
        assert len(suggestions) > 0
        assert any("category" in suggestion.question.lower() or "breakdown" in suggestion.question.lower() 
                  for suggestion in suggestions)
    
    def test_detect_proactive_insights_with_outliers(self):
        """Test detecting proactive insights with outlier data."""
        # Create mock query results with outliers
        query_results = ExecuteResponse(
            columns=["revenue", "month"],
            rows=[
                [1000, "Jan"],
                [1100, "Feb"], 
                [1050, "Mar"],
                [5000, "Apr"],  # Outlier
                [1200, "May"]
            ],
            row_count=5,
            runtime_ms=100
        )
        
        insights = self.service.detect_proactive_insights(query_results, "monthly revenue")
        
        assert len(insights) > 0
        assert any(insight.insight_type == "anomaly" for insight in insights)
        assert any("unusually high" in insight.message.lower() for insight in insights)
    
    def test_detect_proactive_insights_with_trends(self):
        """Test detecting proactive insights with trend data."""
        # Create mock query results with increasing trend
        query_results = ExecuteResponse(
            columns=["sales", "quarter"],
            rows=[
                [1000, "Q1"],
                [1200, "Q2"],
                [1400, "Q3"],
                [1600, "Q4"],
                [1800, "Q5"]
            ],
            row_count=5,
            runtime_ms=100
        )
        
        insights = self.service.detect_proactive_insights(query_results, "quarterly sales")
        
        assert len(insights) > 0
        assert any(insight.insight_type == "trend" for insight in insights)
        assert any("upward trend" in insight.message.lower() for insight in insights)
    
    def test_generate_contextual_suggestions(self):
        """Test generating contextual suggestions from conversation history."""
        conversation_history = [
            {
                "message_type": "user",
                "content": "What are my total sales?",
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "message_type": "assistant", 
                "content": "Your total sales are $50,000",
                "timestamp": "2024-01-01T10:00:01"
            }
        ]
        
        suggestions = self.service.generate_contextual_suggestions(conversation_history)
        
        assert len(suggestions) > 0
        # Check that suggestions are QuestionSuggestion objects with the expected content
        assert any("break down" in suggestion.question.lower() or "breakdown" in suggestion.question.lower() or 
                  "category" in suggestion.question.lower() or "categories" in suggestion.question.lower()
                  for suggestion in suggestions)
    
    def test_analyze_data_characteristics_financial(self):
        """Test analyzing data characteristics for financial data."""
        # Mock schema service
        self.mock_schema_service.get_all_tables_schema.return_value = {
            "tables": {
                "financial_data": {
                    "columns": [
                        {"name": "revenue", "type": "decimal"},
                        {"name": "date", "type": "date"},
                        {"name": "category", "type": "varchar"}
                    ],
                    "row_count": 1000
                }
            }
        }
        
        characteristics = self.service._analyze_data_characteristics()
        
        assert characteristics.has_financial_data is True
        assert characteristics.has_time_data is True
        assert characteristics.has_categorical_data is True
        assert characteristics.row_count == 1000
        assert "revenue" in characteristics.numeric_columns
    
    def test_generate_fallback_questions(self):
        """Test generating fallback questions when analysis fails."""
        # Mock schema service to raise exception
        self.mock_schema_service.get_all_tables_schema.side_effect = Exception("Schema error")
        
        suggestions = self.service.generate_initial_questions()
        
        # Should return fallback questions
        assert len(suggestions) > 0
        assert all(isinstance(suggestion, QuestionSuggestion) for suggestion in suggestions)
        assert any("overall" in suggestion.question.lower() for suggestion in suggestions)
    
    def test_detect_opportunity_patterns(self):
        """Test detecting opportunity patterns in data."""
        # Create data with imbalanced distribution
        data = [
            {"category": "A", "sales": 1000},
            {"category": "A", "sales": 1100},
            {"category": "A", "sales": 1200},
            {"category": "A", "sales": 1050},
            {"category": "A", "sales": 1150},
            {"category": "B", "sales": 200},  # Much lower performance
            {"category": "C", "sales": 150}   # Much lower performance
        ]
        
        insights = self.service._detect_opportunity_patterns(data, "sales by category")
        
        assert len(insights) > 0
        assert any(insight.insight_type == "opportunity" for insight in insights)
        assert any("untapped potential" in insight.message.lower() for insight in insights)
    
    def test_extract_conversation_topics(self):
        """Test extracting topics from conversation history."""
        conversation_history = [
            {
                "content": "What are my sales and revenue trends?",
                "message_type": "user"
            },
            {
                "content": "How many users visited last month?",
                "message_type": "user"
            }
        ]
        
        topics = self.service._extract_conversation_topics(conversation_history)
        
        assert "financial" in topics
        assert "temporal" in topics
        assert "users" in topics
    
    def test_deduplicate_suggestions(self):
        """Test deduplicating suggestion lists."""
        suggestions = [
            QuestionSuggestion("What are my sales?", "overview", 5, "test"),
            QuestionSuggestion("What are my sales?", "overview", 4, "test"),  # Duplicate
            QuestionSuggestion("How are trends?", "trends", 3, "test")
        ]
        
        unique_suggestions = self.service._deduplicate_suggestions(suggestions)
        
        assert len(unique_suggestions) == 2
        assert unique_suggestions[0].question == "What are my sales?"
        assert unique_suggestions[1].question == "How are trends?"


class TestDataCharacteristics:
    """Test cases for DataCharacteristics dataclass."""
    
    def test_data_characteristics_creation(self):
        """Test creating DataCharacteristics instance."""
        characteristics = DataCharacteristics(
            has_time_data=True,
            has_financial_data=True,
            has_categorical_data=False,
            has_user_data=True,
            has_geographic_data=False,
            row_count=1000,
            column_count=5,
            numeric_columns=["revenue", "count"],
            date_columns=["created_date"],
            categorical_columns=["category"],
            primary_entities=["users", "products"]
        )
        
        assert characteristics.has_time_data is True
        assert characteristics.has_financial_data is True
        assert characteristics.row_count == 1000
        assert len(characteristics.numeric_columns) == 2
        assert "revenue" in characteristics.numeric_columns


class TestQuestionSuggestion:
    """Test cases for QuestionSuggestion dataclass."""
    
    def test_question_suggestion_creation(self):
        """Test creating QuestionSuggestion instance."""
        suggestion = QuestionSuggestion(
            question="What are my total sales?",
            category="overview",
            priority=5,
            reasoning="Financial data detected"
        )
        
        assert suggestion.question == "What are my total sales?"
        assert suggestion.category == "overview"
        assert suggestion.priority == 5
        assert "financial" in suggestion.reasoning.lower()


class TestProactiveInsight:
    """Test cases for ProactiveInsight dataclass."""
    
    def test_proactive_insight_creation(self):
        """Test creating ProactiveInsight instance."""
        insight = ProactiveInsight(
            message="Revenue shows strong growth",
            insight_type="trend",
            confidence=0.9,
            suggested_actions=["Analyze growth drivers", "Plan for scaling"]
        )
        
        assert insight.message == "Revenue shows strong growth"
        assert insight.insight_type == "trend"
        assert insight.confidence == 0.9
        assert len(insight.suggested_actions) == 2


if __name__ == "__main__":
    pytest.main([__file__])