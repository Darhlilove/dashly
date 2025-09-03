"""
Demonstration script for proactive data exploration features.

This script demonstrates the three main proactive exploration features:
1. Automatic initial question suggestions when data is uploaded
2. Logic to suggest interesting questions based on available data structure
3. Proactive insights when interesting patterns are detected in responses
"""

import asyncio
from typing import Dict, Any, List

try:
    from .proactive_exploration_service import ProactiveExplorationService
    from .models import ExecuteResponse
    from .logging_config import get_logger
except ImportError:
    from proactive_exploration_service import ProactiveExplorationService
    from models import ExecuteResponse
    from logging_config import get_logger

logger = get_logger(__name__)


def demo_initial_question_suggestions():
    """Demonstrate automatic initial question suggestions when data is uploaded."""
    print("\n" + "="*60)
    print("DEMO 1: Initial Question Suggestions When Data is Uploaded")
    print("="*60)
    
    service = ProactiveExplorationService()
    
    # Simulate different types of data uploads
    test_scenarios = [
        {
            "name": "E-commerce Sales Data",
            "schema": {
                "tables": {
                    "sales_data": {
                        "columns": [
                            {"name": "order_date", "type": "date"},
                            {"name": "revenue", "type": "decimal"},
                            {"name": "customer_id", "type": "int"},
                            {"name": "product_category", "type": "varchar"}
                        ],
                        "row_count": 10000
                    }
                }
            }
        },
        {
            "name": "User Activity Data",
            "schema": {
                "tables": {
                    "user_activity": {
                        "columns": [
                            {"name": "user_id", "type": "int"},
                            {"name": "activity_date", "type": "date"},
                            {"name": "page_views", "type": "int"},
                            {"name": "session_duration", "type": "int"}
                        ],
                        "row_count": 50000
                    }
                }
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📊 Scenario: {scenario['name']}")
        print("-" * 40)
        
        # Mock the schema service
        service.schema_service = type('MockSchemaService', (), {
            'get_all_tables_schema': lambda: scenario['schema']
        })()
        
        suggestions = service.generate_initial_questions()
        
        print(f"Generated {len(suggestions)} initial question suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.question}")
            print(f"     Category: {suggestion.category} | Priority: {suggestion.priority}")
            print(f"     Reasoning: {suggestion.reasoning}")
            print()


def demo_structure_based_suggestions():
    """Demonstrate suggesting questions based on data structure."""
    print("\n" + "="*60)
    print("DEMO 2: Structure-Based Question Suggestions")
    print("="*60)
    
    service = ProactiveExplorationService()
    
    # Example schema with different data patterns
    schema_info = {
        "tables": {
            "financial_data": {
                "columns": [
                    {"name": "transaction_date", "type": "date"},
                    {"name": "amount", "type": "decimal"},
                    {"name": "transaction_type", "type": "varchar"},
                    {"name": "account_id", "type": "int"}
                ],
                "sample_rows": [
                    {"transaction_date": "2024-01-01", "amount": 1500.00, "transaction_type": "deposit", "account_id": 123}
                ]
            },
            "customer_data": {
                "columns": [
                    {"name": "customer_id", "type": "int"},
                    {"name": "signup_date", "type": "date"},
                    {"name": "country", "type": "varchar"},
                    {"name": "subscription_tier", "type": "varchar"}
                ],
                "sample_rows": [
                    {"customer_id": 456, "signup_date": "2024-01-15", "country": "USA", "subscription_tier": "Premium"}
                ]
            }
        }
    }
    
    print("📋 Analyzing database schema:")
    for table_name, table_info in schema_info["tables"].items():
        print(f"  • {table_name}: {len(table_info['columns'])} columns, sample data available")
    
    suggestions = service.suggest_questions_from_structure(schema_info)
    
    print(f"\n🤔 Generated {len(suggestions)} structure-based questions:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {suggestion.question}")
        print(f"     Category: {suggestion.category} | Priority: {suggestion.priority}")
        print()


def demo_proactive_insights():
    """Demonstrate proactive insights from query results."""
    print("\n" + "="*60)
    print("DEMO 3: Proactive Insights from Query Results")
    print("="*60)
    
    service = ProactiveExplorationService()
    
    # Test different types of data patterns
    test_cases = [
        {
            "name": "Revenue Growth Trend",
            "query_results": ExecuteResponse(
                columns=["month", "revenue"],
                rows=[
                    ["Jan", 10000],
                    ["Feb", 12000],
                    ["Mar", 14500],
                    ["Apr", 17000],
                    ["May", 19500]
                ],
                row_count=5,
                runtime_ms=150
            ),
            "question": "monthly revenue trends"
        },
        {
            "name": "Sales with Outlier",
            "query_results": ExecuteResponse(
                columns=["product", "sales"],
                rows=[
                    ["Product A", 1000],
                    ["Product B", 1100],
                    ["Product C", 950],
                    ["Product D", 5000],  # Outlier
                    ["Product E", 1050]
                ],
                row_count=5,
                runtime_ms=120
            ),
            "question": "product sales comparison"
        },
        {
            "name": "Category Distribution",
            "query_results": ExecuteResponse(
                columns=["category", "count"],
                rows=[
                    ["Electronics", 500],
                    ["Electronics", 520],
                    ["Electronics", 480],
                    ["Books", 50],      # Much lower
                    ["Clothing", 45],   # Much lower
                    ["Sports", 40]      # Much lower
                ],
                row_count=6,
                runtime_ms=100
            ),
            "question": "category distribution analysis"
        }
    ]
    
    for case in test_cases:
        print(f"\n📈 Scenario: {case['name']}")
        print(f"Question: '{case['question']}'")
        print("-" * 50)
        
        insights = service.detect_proactive_insights(case['query_results'], case['question'])
        
        if insights:
            print(f"🔍 Detected {len(insights)} proactive insights:")
            for i, insight in enumerate(insights, 1):
                print(f"\n  {i}. {insight.message}")
                print(f"     Type: {insight.insight_type} | Confidence: {insight.confidence:.1%}")
                print(f"     Suggested Actions:")
                for action in insight.suggested_actions:
                    print(f"       • {action}")
        else:
            print("   No significant patterns detected in this data.")


def demo_contextual_suggestions():
    """Demonstrate contextual suggestions based on conversation history."""
    print("\n" + "="*60)
    print("DEMO 4: Contextual Suggestions from Conversation History")
    print("="*60)
    
    service = ProactiveExplorationService()
    
    # Simulate conversation history
    conversation_history = [
        {
            "message_type": "user",
            "content": "What are my total sales for this quarter?",
            "timestamp": "2024-01-01T10:00:00"
        },
        {
            "message_type": "assistant",
            "content": "Your total sales for this quarter are $125,000, which represents a 15% increase from last quarter.",
            "timestamp": "2024-01-01T10:00:01"
        },
        {
            "message_type": "user",
            "content": "How many customers do I have?",
            "timestamp": "2024-01-01T10:05:00"
        },
        {
            "message_type": "assistant",
            "content": "You currently have 1,250 active customers.",
            "timestamp": "2024-01-01T10:05:01"
        }
    ]
    
    print("💬 Conversation History:")
    for msg in conversation_history:
        role = "👤 User" if msg["message_type"] == "user" else "🤖 Assistant"
        print(f"  {role}: {msg['content']}")
    
    suggestions = service.generate_contextual_suggestions(conversation_history)
    
    print(f"\n💡 Generated {len(suggestions)} contextual suggestions:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {suggestion.question}")
        print(f"     Category: {suggestion.category} | Priority: {suggestion.priority}")
        print(f"     Reasoning: {suggestion.reasoning}")
        print()


def main():
    """Run all demonstration scenarios."""
    print("🚀 Proactive Data Exploration Features Demonstration")
    print("This demo showcases the three main proactive exploration capabilities:")
    print("1. Initial question suggestions when data is uploaded")
    print("2. Structure-based question suggestions")
    print("3. Proactive insights from query results")
    print("4. Contextual suggestions from conversation history")
    
    try:
        demo_initial_question_suggestions()
        demo_structure_based_suggestions()
        demo_proactive_insights()
        demo_contextual_suggestions()
        
        print("\n" + "="*60)
        print("✅ DEMONSTRATION COMPLETE")
        print("="*60)
        print("All proactive exploration features are working correctly!")
        print("These features help users:")
        print("• Discover relevant questions to ask about their data")
        print("• Identify interesting patterns and anomalies automatically")
        print("• Get contextual suggestions based on their exploration journey")
        print("• Maximize insights from their data analysis sessions")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {str(e)}")
        logger.error(f"Demo error: {str(e)}")


if __name__ == "__main__":
    main()