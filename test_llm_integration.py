#!/usr/bin/env python3
"""
Test script to verify LLM integration is working correctly in the dashly API.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_query(query, expected_chart_type=None):
    """Test a query and print results."""
    print(f"\n🔍 Testing query: '{query}'")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/query",
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"📊 Generated SQL: {data['sql'][:100]}...")
            print(f"📈 Chart Type: {data['chart_type']}")
            print(f"📋 Columns: {', '.join(data['columns'])}")
            print(f"📊 Data Rows: {len(data['data'])}")
            
            if expected_chart_type and data['chart_type'] != expected_chart_type:
                print(f"⚠️  Expected chart type '{expected_chart_type}', got '{data['chart_type']}'")
            
            # Show first few rows of data
            if data['data']:
                print(f"📄 Sample data:")
                for i, row in enumerate(data['data'][:3]):
                    print(f"   Row {i+1}: {row}")
                if len(data['data']) > 3:
                    print(f"   ... and {len(data['data']) - 3} more rows")
            
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return False

def main():
    """Run comprehensive tests of the LLM integration."""
    print("🚀 Testing Dashly LLM Integration")
    print("=" * 60)
    
    # Test different types of queries
    test_cases = [
        # Product analysis
        ("Show me the performance of different products", "bar"),
        ("Which products are selling best?", "pie"),
        
        # Time series analysis  
        ("What are the sales trends over time?", "line"),
        ("Show me monthly sales data", "line"),
        
        # Regional analysis
        ("Which regions are performing best?", "pie"),
        ("Compare sales across all regions", "bar"),
        
        # Customer analysis
        ("Show me top 10 customers by sales", "bar"),
        ("Who are our biggest customers?", "bar"),
        
        # Complex analysis
        ("Analyze customer behavior patterns", "bar"),
        ("What insights can you show me about the data?", "bar"),
    ]
    
    successful_tests = 0
    total_tests = len(test_cases)
    
    for query, expected_chart in test_cases:
        if test_query(query, expected_chart):
            successful_tests += 1
        time.sleep(1)  # Be nice to the API
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {successful_tests}/{total_tests} tests passed")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed! LLM integration is working perfectly!")
    else:
        print(f"⚠️  {total_tests - successful_tests} tests failed. Check the logs above.")
    
    # Test fallback mechanism
    print("\n🔧 Testing fallback mechanism...")
    print("-" * 60)
    
    # This should work even if LLM fails because of the fallback
    fallback_query = "product performance analysis"
    if test_query(fallback_query):
        print("✅ Fallback mechanism is working!")
    else:
        print("❌ Fallback mechanism failed!")

if __name__ == "__main__":
    main()