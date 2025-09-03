"""
Demonstration of enhanced LLM service conversational capabilities.
"""

import asyncio
from unittest.mock import Mock, patch

try:
    from src.llm_service import LLMService, LLMConfig
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    from llm_service import LLMService, LLMConfig


async def demo_enhanced_llm_service():
    """Demonstrate the enhanced LLM service capabilities."""
    print("🚀 Enhanced LLM Service Demo")
    print("=" * 50)
    
    # Mock configuration for demo
    config = LLMConfig(
        api_key="demo_key",
        model="demo_model",
        base_url="https://demo.api",
        conversational_temperature=0.3
    )
    
    # Create service with mocked config
    with patch.object(LLMService, '_load_config', return_value=config):
        service = LLMService()
        
        # Sample query results
        sample_results = {
            "data": [
                {"month": "January", "sales": 45000, "customers": 320, "avg_order": 140.63},
                {"month": "February", "sales": 52000, "customers": 380, "avg_order": 136.84},
                {"month": "March", "sales": 61000, "customers": 425, "avg_order": 143.53},
                {"month": "April", "sales": 58000, "customers": 410, "avg_order": 141.46}
            ],
            "columns": ["month", "sales", "customers", "avg_order"]
        }
        
        print("📊 Sample Data:")
        for row in sample_results["data"]:
            print(f"  {row['month']}: ${row['sales']:,} sales, {row['customers']} customers, ${row['avg_order']:.2f} avg order")
        print()
        
        # Test 1: Query Results Summarization
        print("1️⃣ Query Results Summarization")
        print("-" * 30)
        summary = service._summarize_query_results(sample_results)
        print(summary)
        print()
        
        # Test 2: Fallback Explanation
        print("2️⃣ Fallback Conversational Explanation")
        print("-" * 40)
        explanation = service._generate_fallback_explanation(sample_results, "Show me monthly sales trends")
        print(explanation)
        print()
        
        # Test 3: Fallback Insights
        print("3️⃣ Fallback Business Insights")
        print("-" * 30)
        insights = service._generate_fallback_insights(sample_results)
        for i, insight in enumerate(insights, 1):
            print(f"  • {insight}")
        print()
        
        # Test 4: Fallback Follow-up Questions
        print("4️⃣ Fallback Follow-up Questions")
        print("-" * 35)
        questions = service._generate_fallback_questions("Show me monthly sales trends")
        for i, question in enumerate(questions, 1):
            print(f"  {i}. {question}")
        print()
        
        # Test 5: Prompt Building
        print("5️⃣ Prompt Building Examples")
        print("-" * 30)
        
        explanation_prompt = service._build_explanation_prompt(
            sample_results, 
            "Show me monthly sales trends",
            context={"previous_questions": ["What are my total sales?"]}
        )
        print("Explanation Prompt:")
        print(explanation_prompt[:200] + "..." if len(explanation_prompt) > 200 else explanation_prompt)
        print()
        
        insights_prompt = service._build_insights_prompt(sample_results, "Show me monthly sales trends")
        print("Insights Prompt:")
        print(insights_prompt[:200] + "..." if len(insights_prompt) > 200 else insights_prompt)
        print()
        
        followup_prompt = service._build_followup_prompt(
            sample_results, 
            "Show me monthly sales trends",
            conversation_context=["What are my total sales?", "Show me customer data"]
        )
        print("Follow-up Prompt:")
        print(followup_prompt[:200] + "..." if len(followup_prompt) > 200 else followup_prompt)
        print()
        
        print("✅ Enhanced LLM Service Demo Complete!")
        print("\n🎯 Key Features Demonstrated:")
        print("  • Conversational explanation generation")
        print("  • Business-friendly insight analysis")
        print("  • Context-aware question suggestions")
        print("  • Robust fallback mechanisms")
        print("  • Intelligent prompt building")
        print("  • Query result summarization")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_llm_service())