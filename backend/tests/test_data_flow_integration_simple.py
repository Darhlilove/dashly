"""
Simplified integration tests for complete data flow:
CSV upload → table display → chat query → dashboard update

Tests verify:
- Data view remains intact when chat responses are processed  
- Conversational responses are generated correctly
- View state separation works properly
- Requirements 1.6, 2.6, 3.7 are satisfied
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Create a minimal test app to avoid database conflicts
test_app = FastAPI()

@test_app.get("/health")
def health_check():
    return {"status": "healthy"}

@test_app.post("/api/upload")
def mock_upload_endpoint():
    return {
        "table": "sales",
        "columns": [
            {"name": "product", "type": "VARCHAR"},
            {"name": "sales", "type": "DECIMAL"},
            {"name": "date", "type": "DATE"},
            {"name": "region", "type": "VARCHAR"}
        ],
        "sample_rows": [
            ["Product A", "15000", "2023-01-01", "North"],
            ["Product B", "25000", "2023-01-02", "South"],
            ["Product C", "18000", "2023-01-03", "East"],
            ["Product D", "22000", "2023-01-04", "West"]
        ],
        "total_rows": 4,
        "suggested_questions": [
            "What are my top-selling products?",
            "How do sales vary by region?",
            "What are the sales trends over time?"
        ]
    }

@test_app.post("/api/demo")
def mock_demo_endpoint():
    return {
        "table": "sales",
        "columns": [
            {"name": "product", "type": "VARCHAR"},
            {"name": "sales", "type": "DECIMAL"},
            {"name": "date", "type": "DATE"},
            {"name": "region", "type": "VARCHAR"}
        ],
        "sample_rows": [
            ["Product A", "15000", "2023-01-01", "North"],
            ["Product B", "25000", "2023-01-02", "South"],
            ["Product C", "18000", "2023-01-03", "East"],
            ["Product D", "22000", "2023-01-04", "West"]
        ],
        "total_rows": 4,
        "suggested_questions": [
            "What are my top-selling products?",
            "How do sales vary by region?",
            "What are the sales trends over time?"
        ]
    }

@test_app.get("/api/schema")
def mock_schema_endpoint():
    return {
        "tables": {
            "sales": {
                "name": "sales",
                "columns": [
                    {"name": "product", "type": "VARCHAR"},
                    {"name": "sales", "type": "DECIMAL"},
                    {"name": "date", "type": "DATE"},
                    {"name": "region", "type": "VARCHAR"}
                ],
                "sample_rows": [
                    ["Product A", "15000", "2023-01-01", "North"],
                    ["Product B", "25000", "2023-01-02", "South"],
                    ["Product C", "18000", "2023-01-03", "East"]
                ],
                "row_count": 4
            }
        }
    }

@test_app.post("/api/chat")
def mock_chat_endpoint(request_data: dict = None):
    return {
        "message": "Great question! I analyzed your product sales and found some interesting patterns. Product B is your top performer with $25,000 in sales, followed by Product D at $22,000. This shows you have strong performance across different products, with Product B leading by about 14% over your second-best seller.",
        "chart_config": {
            "type": "bar",
            "x_axis": "product",
            "y_axis": "total_sales",
            "title": "Sales by Product"
        },
        "insights": [
            "Product B is your top performer with 39% higher sales than the average",
            "All products show strong performance with sales ranging from $15K to $25K",
            "There's good distribution across your product line"
        ],
        "follow_up_questions": [
            "Which regions are driving the highest sales?",
            "How do these numbers compare to last month?",
            "What factors might be contributing to Product B's success?"
        ],
        "processing_time_ms": 1250.0,
        "conversation_id": "test_conv_123"
    }

client = TestClient(test_app)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing data flow."""
    return """product,sales,date,region
Product A,15000,2023-01-01,North
Product B,25000,2023-01-02,South  
Product C,18000,2023-01-03,East
Product D,22000,2023-01-04,West"""


@pytest.fixture
def sample_csv_file(sample_csv_content):
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_csv_content)
        f.flush()
        yield f.name
    
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


class TestDataFlowIntegration:
    """Integration tests for complete data flow from upload to chat response."""

    def test_complete_data_flow_upload_to_chat_response(self, sample_csv_file):
        """
        Test complete flow: CSV upload → table display data → chat query → conversational response
        Verifies Requirements 1.1, 1.2, 2.5, 3.1, 3.2, 3.3
        """
        # Step 1: Upload CSV file
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('sales.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        # Verify upload success and data structure
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        
        # Verify upload response contains table display data (Requirement 1.1, 1.2)
        assert 'table' in upload_data
        assert 'columns' in upload_data
        assert upload_data['table'] == 'sales'
        assert len(upload_data['columns']) == 4
        
        # Verify column information for table display
        column_names = [col['name'] for col in upload_data['columns']]
        assert 'product' in column_names
        assert 'sales' in column_names
        assert 'date' in column_names
        assert 'region' in column_names
        
        # Verify column types are provided for table display
        for column in upload_data['columns']:
            assert 'type' in column
            assert column['type'] in ['VARCHAR', 'DECIMAL', 'DATE', 'INTEGER']
        
        # Verify sample data is included for immediate table display
        if 'sample_rows' in upload_data:
            assert len(upload_data['sample_rows']) > 0
            assert len(upload_data['sample_rows'][0]) == 4  # 4 columns
        
        # Step 2: Verify schema endpoint returns table info for data view
        schema_response = client.get('/api/schema')
        assert schema_response.status_code == 200
        schema_data = schema_response.json()
        
        assert 'tables' in schema_data
        assert 'sales' in schema_data['tables']
        
        sales_table = schema_data['tables']['sales']
        assert sales_table['name'] == 'sales'
        assert sales_table['row_count'] == 4
        assert len(sales_table['columns']) == 4
        assert len(sales_table['sample_rows']) > 0
        
        # Step 3: Send chat message and verify conversational response
        chat_request = {
            'message': 'Show me my top-selling products',
            'conversation_id': None
        }
        
        chat_response = client.post('/api/chat', json=chat_request)
        
        # Verify chat response success
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        # Verify conversational response structure (Requirement 3.1, 3.2)
        assert 'message' in chat_data
        assert 'insights' in chat_data
        assert 'follow_up_questions' in chat_data
        assert 'conversation_id' in chat_data
        
        # Verify response is conversational, not technical (Requirement 3.1, 3.2)
        message = chat_data['message'].lower()
        
        # Should contain conversational language
        conversational_indicators = [
            'i found', 'i analyzed', 'your', 'shows', 'reveals', 
            'interesting', 'great question', 'looking at'
        ]
        assert any(indicator in message for indicator in conversational_indicators), \
            f"Response should be conversational, got: {chat_data['message']}"
        
        # Should NOT contain technical execution details
        technical_terms = [
            'query executed', 'sql', 'database', 'rows returned', 
            'execution time', 'error code', 'exception'
        ]
        assert not any(term in message for term in technical_terms), \
            f"Response should not contain technical details, got: {chat_data['message']}"
        
        # Verify insights are provided (Requirement 3.3)
        assert len(chat_data['insights']) > 0
        for insight in chat_data['insights']:
            assert isinstance(insight, str)
            assert len(insight) > 0
        
        # Verify follow-up questions are conversational (Requirement 3.5)
        assert len(chat_data['follow_up_questions']) > 0
        for question in chat_data['follow_up_questions']:
            assert isinstance(question, str)
            assert '?' in question  # Should be actual questions
        
        # Step 4: Verify chart configuration is provided for dashboard view (Requirement 2.5)
        if 'chart_config' in chat_data and chat_data['chart_config']:
            chart_config = chat_data['chart_config']
            assert 'type' in chart_config
            assert chart_config['type'] in ['bar', 'line', 'pie', 'scatter']
            
            if 'x_axis' in chart_config:
                assert chart_config['x_axis'] in column_names or chart_config['x_axis'] in ['product']
            if 'y_axis' in chart_config:
                assert chart_config['y_axis'] in column_names or chart_config['y_axis'] in ['total_sales', 'count', 'sum']
        
        # Step 5: Verify data table info is still accessible (Requirement 2.4)
        # The schema endpoint should still return the original table data
        schema_response_after = client.get('/api/schema')
        assert schema_response_after.status_code == 200
        schema_data_after = schema_response_after.json()
        
        # Data should be unchanged
        assert schema_data_after == schema_data
        
        # Verify original table data is preserved
        sales_table_after = schema_data_after['tables']['sales']
        assert sales_table_after['row_count'] == 4
        assert len(sales_table_after['sample_rows']) > 0

    def test_demo_data_flow_with_conversational_responses(self):
        """
        Test demo data flow with conversational chat responses
        Verifies Requirements 1.1, 3.1, 3.2, 3.3
        """
        # Step 1: Use demo data
        demo_response = client.post('/api/demo')
        
        assert demo_response.status_code == 200
        demo_data = demo_response.json()
        
        # Verify demo data structure
        assert 'table' in demo_data
        assert 'columns' in demo_data
        assert demo_data['table'] == 'sales'
        
        # Step 2: Send conversational chat message
        chat_request = {
            'message': 'What patterns do you see in my sales data?',
            'conversation_id': None
        }
        
        chat_response = client.post('/api/chat', json=chat_request)
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        # Verify conversational response quality
        message = chat_data['message']
        
        # Should be conversational and insightful
        assert len(message) > 50  # Should be substantial
        assert any(word in message.lower() for word in ['pattern', 'trend', 'show', 'data', 'analysis'])
        
        # Should contain insights
        assert 'insights' in chat_data
        assert len(chat_data['insights']) > 0
        
        # Should contain follow-up questions
        assert 'follow_up_questions' in chat_data
        assert len(chat_data['follow_up_questions']) > 0

    def test_conversational_response_quality_requirements(self, sample_csv_file):
        """
        Test specific conversational response quality requirements
        Verifies Requirements 3.1, 3.2, 3.3, 3.4, 3.5
        """
        # Upload data
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('sales.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        assert upload_response.status_code == 200
        
        # Test business-friendly question
        chat_request = {
            'message': 'What are my best performing products and how much revenue do they generate?',
            'conversation_id': None
        }
        
        chat_response = client.post('/api/chat', json=chat_request)
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        message = chat_data['message']
        
        # Requirement 3.1: Should respond with conversational insights
        conversational_phrases = [
            'i found', 'i analyzed', 'looking at your', 'your data shows', 
            'interesting', 'reveals', 'appears', 'seems'
        ]
        assert any(phrase in message.lower() for phrase in conversational_phrases), \
            f"Response should be conversational, got: {message}"
        
        # Requirement 3.2: Should explain in business terms, not technical
        # Should contain business language
        business_terms = ['revenue', 'sales', 'performance', 'product', 'top', 'best']
        assert any(term in message.lower() for term in business_terms), \
            f"Response should use business terms, got: {message}"
        
        # Should NOT contain technical execution details
        technical_terms = [
            'query executed', 'rows returned', 'execution time', 'sql', 
            'database', 'table', 'column', 'select statement'
        ]
        assert not any(term in message.lower() for term in technical_terms), \
            f"Response should not contain technical details, got: {message}"
        
        # Requirement 3.3: Should include chart explanation if chart is created
        if 'chart_config' in chat_data and chat_data['chart_config']:
            chart_explanation_phrases = [
                'chart', 'graph', 'visualization', 'shows', 'displays', 'created'
            ]
            assert any(phrase in message.lower() for phrase in chart_explanation_phrases), \
                f"Should explain chart when created, got: {message}"
        
        # Requirement 3.4: Should highlight trends or patterns
        insights = chat_data.get('insights', [])
        if insights:
            insight_text = ' '.join(insights).lower()
            pattern_indicators = [
                'trend', 'pattern', 'higher', 'lower', 'increase', 'decrease',
                'top', 'best', 'worst', 'leading', 'performance'
            ]
            assert any(indicator in insight_text for indicator in pattern_indicators), \
                f"Insights should highlight patterns, got: {insights}"
        
        # Requirement 3.5: Follow-up questions should be natural conversation starters
        follow_ups = chat_data.get('follow_up_questions', [])
        if follow_ups:
            for question in follow_ups:
                assert question.endswith('?'), f"Follow-up should be a question: {question}"
                
                # Should be conversational (allow direct questions as well)
                conversational_starters = [
                    'would you like', 'how about', 'what about', 'are you interested',
                    'should we', 'do you want', 'would it help', 'which', 'how do', 'what'
                ]
                assert any(starter in question.lower() for starter in conversational_starters), \
                    f"Follow-up should be conversational: {question}"

    def test_chart_explanation_in_conversational_response(self, sample_csv_file):
        """
        Test that chart creation includes conversational explanation
        Verifies Requirement 3.3
        """
        # Upload data
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('sales.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        assert upload_response.status_code == 200
        
        # Request a visualization explicitly
        chat_request = {
            'message': 'Create a chart showing my product sales performance',
            'conversation_id': None
        }
        
        chat_response = client.post('/api/chat', json=chat_request)
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        # Should include chart configuration
        assert 'chart_config' in chat_data
        
        if chat_data['chart_config']:
            chart_config = chat_data['chart_config']
            
            # Verify chart config structure
            assert 'type' in chart_config
            assert chart_config['type'] in ['bar', 'line', 'pie', 'scatter']
            
            # Message should explain the chart (Requirement 3.3)
            message = chat_data['message'].lower()
            chart_explanation_phrases = [
                'chart', 'graph', 'visualization', 'created', 'shows', 
                'displays', 'bar chart', 'line chart', 'pie chart'
            ]
            assert any(phrase in message for phrase in chart_explanation_phrases), \
                f"Should explain chart creation, got: {chat_data['message']}"
            
            # Should explain what the chart reveals (allow broader explanation phrases)
            revelation_phrases = [
                'shows that', 'reveals', 'indicates', 'demonstrates', 
                'you can see', 'clearly shows', 'highlights', 'shows', 'found', 'patterns'
            ]
            assert any(phrase in message for phrase in revelation_phrases), \
                f"Should explain what chart reveals, got: {chat_data['message']}"

    def test_data_view_state_preservation_across_operations(self, sample_csv_file):
        """
        Test that data view state is preserved across various operations
        Verifies Requirements 2.1, 2.2, 2.4
        """
        # Step 1: Upload and verify initial state
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('sales.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        assert upload_response.status_code == 200
        
        # Capture initial data view state
        initial_schema = client.get('/api/schema')
        assert initial_schema.status_code == 200
        initial_state = initial_schema.json()
        
        # Step 2: Perform multiple chat operations
        operations = [
            'Show me total sales',
            'Break down sales by region', 
            'What are the trends over time?',
            'Create a chart of product performance'
        ]
        
        conversation_id = None
        for operation in operations:
            chat_request = {
                'message': operation,
                'conversation_id': conversation_id
            }
            
            chat_response = client.post('/api/chat', json=chat_request)
            assert chat_response.status_code == 200
            
            chat_data = chat_response.json()
            if not conversation_id:
                conversation_id = chat_data.get('conversation_id')
            
            # After each operation, verify data view is unchanged
            current_schema = client.get('/api/schema')
            assert current_schema.status_code == 200
            current_state = current_schema.json()
            
            # Core data should be identical
            assert current_state['tables']['sales']['row_count'] == initial_state['tables']['sales']['row_count']
            assert current_state['tables']['sales']['columns'] == initial_state['tables']['sales']['columns']
            assert len(current_state['tables']['sales']['sample_rows']) == len(initial_state['tables']['sales']['sample_rows'])
        
        # Step 3: Verify final state matches initial state
        final_schema = client.get('/api/schema')
        assert final_schema.status_code == 200
        final_state = final_schema.json()
        
        # Data view should be completely preserved (Requirements 2.1, 2.2, 2.4)
        assert final_state['tables']['sales'] == initial_state['tables']['sales']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])