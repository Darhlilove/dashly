"""
Integration tests for complete data flow:
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
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app

client = TestClient(app)


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
                assert chart_config['x_axis'] in column_names
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
        
        # Skip test if demo data not available
        if demo_response.status_code == 404:
            pytest.skip("Demo data not available")
        
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

    def test_multiple_chat_queries_preserve_data_view(self, sample_csv_file):
        """
        Test that multiple chat queries don't interfere with data view
        Verifies Requirements 2.4, 2.5
        """
        # Step 1: Upload data
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('sales.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        assert upload_response.status_code == 200
        
        # Get initial schema state
        initial_schema = client.get('/api/schema')
        assert initial_schema.status_code == 200
        initial_data = initial_schema.json()
        
        # Step 2: First chat query
        chat_request_1 = {
            'message': 'Show me sales by product',
            'conversation_id': None
        }
        
        chat_response_1 = client.post('/api/chat', json=chat_request_1)
        assert chat_response_1.status_code == 200
        chat_data_1 = chat_response_1.json()
        
        # Verify first response
        assert 'message' in chat_data_1
        assert 'conversation_id' in chat_data_1
        conversation_id = chat_data_1['conversation_id']
        
        # Step 3: Second chat query in same conversation
        chat_request_2 = {
            'message': 'Now show me sales by region',
            'conversation_id': conversation_id
        }
        
        chat_response_2 = client.post('/api/chat', json=chat_request_2)
        assert chat_response_2.status_code == 200
        chat_data_2 = chat_response_2.json()
        
        # Verify second response
        assert 'message' in chat_data_2
        assert chat_data_2['conversation_id'] == conversation_id
        
        # Step 4: Verify data view is unchanged
        final_schema = client.get('/api/schema')
        assert final_schema.status_code == 200
        final_data = final_schema.json()
        
        # Data should be identical to initial state
        assert final_data['tables']['sales']['row_count'] == initial_data['tables']['sales']['row_count']
        assert final_data['tables']['sales']['columns'] == initial_data['tables']['sales']['columns']
        assert len(final_data['tables']['sales']['sample_rows']) == len(initial_data['tables']['sales']['sample_rows'])

    def test_error_handling_preserves_data_view(self, sample_csv_file):
        """
        Test that chat errors don't corrupt data view
        Verifies Requirements 2.4, 3.6
        """
        # Step 1: Upload data successfully
        with open(sample_csv_file, 'rb') as f:
            files = {'file': ('sales.csv', f, 'text/csv')}
            upload_response = client.post('/api/upload', files=files)
        
        assert upload_response.status_code == 200
        
        # Get initial schema state
        initial_schema = client.get('/api/schema')
        assert initial_schema.status_code == 200
        initial_data = initial_schema.json()
        
        # Step 2: Send invalid chat query
        chat_request = {
            'message': 'Show me data from nonexistent_column that does not exist',
            'conversation_id': None
        }
        
        chat_response = client.post('/api/chat', json=chat_request)
        
        # Chat might return error or user-friendly message
        if chat_response.status_code == 200:
            # If successful, should contain user-friendly error explanation
            chat_data = chat_response.json()
            message = chat_data['message'].lower()
            
            # Should explain error in user-friendly terms (Requirement 3.6)
            user_friendly_indicators = [
                "couldn't find", "doesn't exist", "not available", 
                "try", "instead", "available columns", "help"
            ]
            assert any(indicator in message for indicator in user_friendly_indicators), \
                f"Error should be user-friendly, got: {chat_data['message']}"
            
            # Should NOT expose technical details
            technical_terms = ["column not found", "sql error", "exception", "stack trace"]
            assert not any(term in message for term in technical_terms), \
                f"Error should not expose technical details, got: {chat_data['message']}"
        
        # Step 3: Verify data view is still intact
        final_schema = client.get('/api/schema')
        assert final_schema.status_code == 200
        final_data = final_schema.json()
        
        # Data should be unchanged despite the error
        assert final_data['tables']['sales']['row_count'] == initial_data['tables']['sales']['row_count']
        assert final_data['tables']['sales']['columns'] == initial_data['tables']['sales']['columns']

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
                
                # Should be conversational
                conversational_starters = [
                    'would you like', 'how about', 'what about', 'are you interested',
                    'should we', 'do you want', 'would it help'
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
            
            # Should explain what the chart reveals
            revelation_phrases = [
                'shows that', 'reveals', 'indicates', 'demonstrates', 
                'you can see', 'clearly shows', 'highlights'
            ]
            assert any(phrase in message for phrase in revelation_phrases), \
                f"Should explain what chart reveals, got: {chat_data['message']}"

    def test_no_data_scenario_conversational_handling(self):
        """
        Test conversational handling when no data matches query
        Verifies Requirement 3.7
        """
        # Use demo data first
        demo_response = client.post('/api/demo')
        if demo_response.status_code == 404:
            pytest.skip("Demo data not available")
        
        assert demo_response.status_code == 200
        
        # Ask for data that doesn't exist
        chat_request = {
            'message': 'Show me sales for products that do not exist in my data',
            'conversation_id': None
        }
        
        chat_response = client.post('/api/chat', json=chat_request)
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        
        message = chat_data['message'].lower()
        
        # Should acknowledge no data found (Requirement 3.7)
        no_data_phrases = [
            "couldn't find", "no data", "no results", "not found", 
            "doesn't exist", "no matching", "empty"
        ]
        assert any(phrase in message for phrase in no_data_phrases), \
            f"Should acknowledge no data found, got: {chat_data['message']}"
        
        # Should suggest alternatives (Requirement 3.7)
        suggestion_phrases = [
            "try", "instead", "available", "different", "alternative", 
            "what about", "you might want", "consider"
        ]
        assert any(phrase in message for phrase in suggestion_phrases), \
            f"Should suggest alternatives, got: {chat_data['message']}"
        
        # Should provide helpful follow-up questions
        follow_ups = chat_data.get('follow_up_questions', [])
        assert len(follow_ups) > 0, "Should provide follow-up questions when no data found"
        
        # Follow-ups should be helpful
        for question in follow_ups:
            helpful_indicators = [
                'available', 'see', 'show', 'try', 'different', 'what', 'how'
            ]
            assert any(indicator in question.lower() for indicator in helpful_indicators), \
                f"Follow-up should be helpful: {question}"

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