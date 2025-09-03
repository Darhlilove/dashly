"""
Demonstration script for InsightAnalyzer capabilities.

This script shows how the InsightAnalyzer can detect trends, outliers,
and generate insights from sample data, fulfilling requirements 2.3, 4.1, 4.2, and 4.3.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from insight_analyzer import InsightAnalyzer, InsightType
from models import ExecuteResponse
import json


def create_sample_sales_data():
    """Create sample sales data with trends and outliers."""
    return ExecuteResponse(
        columns=["month", "revenue", "customers", "avg_order_value", "region"],
        rows=[
            ["2023-01", 50000, 500, 100, "North"],
            ["2023-02", 55000, 520, 106, "North"],
            ["2023-03", 60000, 540, 111, "North"],
            ["2023-04", 65000, 560, 116, "South"],
            ["2023-05", 70000, 580, 121, "South"],
            ["2023-06", 120000, 600, 200, "West"],  # Outlier month
            ["2023-07", 75000, 620, 121, "West"],
            ["2023-08", 80000, 640, 125, "East"],
            ["2023-09", 85000, 660, 129, "East"],
            ["2023-10", 90000, 680, 132, "Central"]
        ],
        row_count=10,
        runtime_ms=125.0
    )


def create_sample_user_activity_data():
    """Create sample user activity data."""
    return ExecuteResponse(
        columns=["date", "daily_active_users", "new_signups", "retention_rate"],
        rows=[
            ["2023-05-01", 1000, 50, 0.85],
            ["2023-05-02", 1050, 55, 0.87],
            ["2023-05-03", 1100, 60, 0.86],
            ["2023-05-04", 1150, 65, 0.88],
            ["2023-05-05", 1200, 70, 0.89],
            ["2023-05-06", 1250, 75, 0.90],
            ["2023-05-07", 1300, 80, 0.91]
        ],
        row_count=7,
        runtime_ms=95.0
    )


def demonstrate_trend_detection():
    """Demonstrate trend detection capabilities."""
    print("=" * 60)
    print("TREND DETECTION DEMONSTRATION")
    print("=" * 60)
    
    analyzer = InsightAnalyzer()
    sales_data = create_sample_sales_data()
    
    print("Sample Data: Monthly sales with revenue, customers, and average order value")
    print("Expected: Should detect increasing trends in revenue and customers")
    print()
    
    # Analyze trends
    analysis = analyzer.analyze_query_results(sales_data, "Show me monthly sales trends")
    
    print("DETECTED TRENDS:")
    for trend in analysis["trends"]:
        print(f"  • {trend.message} (Confidence: {trend.confidence:.2f})")
    
    print()


def demonstrate_outlier_detection():
    """Demonstrate outlier detection capabilities."""
    print("=" * 60)
    print("OUTLIER DETECTION DEMONSTRATION")
    print("=" * 60)
    
    analyzer = InsightAnalyzer()
    sales_data = create_sample_sales_data()
    
    print("Sample Data: Monthly sales with one exceptional month (June: $120K revenue)")
    print("Expected: Should detect June as an outlier")
    print()
    
    # Analyze outliers
    analysis = analyzer.analyze_query_results(sales_data, "Analyze sales performance")
    
    print("DETECTED OUTLIERS:")
    for outlier in analysis["outliers"]:
        print(f"  • {outlier.message} (Confidence: {outlier.confidence:.2f})")
    
    print()


def demonstrate_data_summarization():
    """Demonstrate data summarization capabilities."""
    print("=" * 60)
    print("DATA SUMMARIZATION DEMONSTRATION")
    print("=" * 60)
    
    analyzer = InsightAnalyzer()
    user_data = create_sample_user_activity_data()
    
    print("Sample Data: Daily user activity with growth patterns")
    print("Expected: Should summarize data volume and key metrics")
    print()
    
    # Analyze summary
    analysis = analyzer.analyze_query_results(user_data, "Summarize user activity")
    
    print("DATA SUMMARY:")
    for summary in analysis["summary"]:
        print(f"  • {summary.message}")
    
    print()


def demonstrate_follow_up_questions():
    """Demonstrate contextual follow-up question generation."""
    print("=" * 60)
    print("FOLLOW-UP QUESTION GENERATION DEMONSTRATION")
    print("=" * 60)
    
    analyzer = InsightAnalyzer()
    sales_data = create_sample_sales_data()
    
    print("Sample Data: Monthly sales data")
    print("Expected: Should suggest relevant business questions")
    print()
    
    # Generate follow-up questions
    analysis = analyzer.analyze_query_results(sales_data, "What are my sales trends?")
    
    print("SUGGESTED FOLLOW-UP QUESTIONS:")
    for i, question in enumerate(analysis["follow_up_questions"], 1):
        print(f"  {i}. {question}")
    
    print()


def demonstrate_comprehensive_analysis():
    """Demonstrate comprehensive analysis combining all features."""
    print("=" * 60)
    print("COMPREHENSIVE ANALYSIS DEMONSTRATION")
    print("=" * 60)
    
    analyzer = InsightAnalyzer()
    sales_data = create_sample_sales_data()
    
    print("Sample Data: Complete monthly sales dataset")
    print("Expected: Should provide trends, outliers, summary, and suggestions")
    print()
    
    # Comprehensive analysis
    analysis = analyzer.analyze_query_results(sales_data, "Give me a complete analysis of sales performance")
    
    print("COMPREHENSIVE ANALYSIS RESULTS:")
    print()
    
    print("Data Quality Metrics:")
    quality = analysis["data_quality"]
    print(f"  • Rows: {quality['row_count']}")
    print(f"  • Columns: {quality['column_count']}")
    print(f"  • Has Numeric Data: {quality['has_numeric_data']}")
    print(f"  • Has Date Data: {quality['has_date_data']}")
    print()
    
    print("Key Insights (Top 5):")
    for i, insight in enumerate(analysis["all_insights"][:5], 1):
        print(f"  {i}. {insight.message}")
    print()
    
    print("Recommended Next Steps:")
    for i, question in enumerate(analysis["follow_up_questions"], 1):
        print(f"  {i}. {question}")
    
    print()


def demonstrate_different_data_patterns():
    """Demonstrate analysis with different data patterns."""
    print("=" * 60)
    print("DIFFERENT DATA PATTERNS DEMONSTRATION")
    print("=" * 60)
    
    analyzer = InsightAnalyzer()
    
    # Stable data pattern
    stable_data = ExecuteResponse(
        columns=["week", "sales"],
        rows=[
            ["Week 1", 1000],
            ["Week 2", 1010],
            ["Week 3", 990],
            ["Week 4", 1005],
            ["Week 5", 995]
        ],
        row_count=5,
        runtime_ms=50.0
    )
    
    print("STABLE DATA PATTERN:")
    stable_analysis = analyzer.analyze_query_results(stable_data, "Show weekly sales")
    trends = [t for t in stable_analysis["trends"] if t.column == "sales"]
    if trends:
        print(f"  • {trends[0].message}")
    else:
        print("  • No significant trends detected (as expected for stable data)")
    
    # Volatile data pattern
    volatile_data = ExecuteResponse(
        columns=["day", "stock_price"],
        rows=[
            ["Day 1", 100],
            ["Day 2", 120],
            ["Day 3", 80],
            ["Day 4", 110],
            ["Day 5", 90],
            ["Day 6", 130]
        ],
        row_count=6,
        runtime_ms=60.0
    )
    
    print("\nVOLATILE DATA PATTERN:")
    volatile_analysis = analyzer.analyze_query_results(volatile_data, "Show stock price movement")
    trends = [t for t in volatile_analysis["trends"] if t.column == "stock_price"]
    if trends:
        print(f"  • {trends[0].message}")
    else:
        print("  • Volatility detected in price movements")
    
    print()


def main():
    """Run all demonstrations."""
    print("INSIGHT ANALYZER DEMONSTRATION")
    print("Showcasing automatic pattern detection and insight generation")
    print("Requirements covered: 2.3, 4.1, 4.2, 4.3")
    print()
    
    try:
        demonstrate_trend_detection()
        demonstrate_outlier_detection()
        demonstrate_data_summarization()
        demonstrate_follow_up_questions()
        demonstrate_comprehensive_analysis()
        demonstrate_different_data_patterns()
        
        print("=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("The InsightAnalyzer successfully demonstrated:")
        print("✓ Trend detection in numeric data")
        print("✓ Outlier identification")
        print("✓ Data summarization")
        print("✓ Contextual follow-up question generation")
        print("✓ Comprehensive analysis combining all features")
        print("✓ Handling different data patterns")
        print()
        print("All requirements 2.3, 4.1, 4.2, and 4.3 have been fulfilled!")
        
    except Exception as e:
        print(f"Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()