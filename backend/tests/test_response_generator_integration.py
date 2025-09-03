"""
Integration tests for ResponseGenerator with existing system components.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from response_generator import ResponseGenerator
from models import ExecuteResponse, ChartConfig


class TestResponseGeneratorIntegration:
    """Integration tests for ResponseGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ResponseGenerator()
    
    def test_integration_with_execute_response(self):
        """Test integration with actual ExecuteResponse objects."""
        # Create a realistic ExecuteResponse as would come from QueryExecutor
        query_results = ExecuteResponse(
            columns=["product_name", "total_sales", "order_date", "region"],
            rows=[
                ["Widget A", 15000.50, "2023-01-15", "North"],
                ["Widget B", 22000.75, "2023-01-16", "South"],
                ["Widget C", 8500.25, "2023-01-17", "East"],
                ["Widget A", 18000.00, "2023-02-15", "West"],
                ["Widget B", 25000.00, "2023-02-16", "North"]
            ],
            row_count=5,
            runtime_ms=245.7,
            truncated=False
        )
        
        # Test with chart configuration
        chart_config = ChartConfig(
            type="bar",
            x_axis="product_name",
            y_axis="total_sales",
            title="Product Sales Analysis"
        )
        
        response = self.generator.generate_conversational_response(
            query_results,
            "Show me the sales by product",
            chart_config
        )
        
        # Verify response structure
        assert response.message is not None
        assert len(response.message) > 20  # Should be a substantial response
        assert response.chart_config == chart_config
        assert response.processing_time_ms == 245.7
        
        # Verify conversational tone
        assert any(word in response.message.lower() for word in ["found", "here", "looking", "shows"])
        
        # Verify insights are generated
        assert len(response.insights) > 0
        assert any("5 results" in insight or "found" in insight.lower() for insight in response.insights)
        
        # Verify follow-up questions
        assert len(response.follow_up_questions) > 0
        assert all("?" in question for question in response.follow_up_questions)
    
    def test_integration_with_large_dataset(self):
        """Test with larger dataset to verify performance and truncation handling."""
        # Create a larger dataset
        rows = []
        for i in range(100):
            rows.append([
                f"Product {i}",
                1000 + (i * 100),
                f"2023-{(i % 12) + 1:02d}-01",
                ["North", "South", "East", "West"][i % 4]
            ])
        
        query_results = ExecuteResponse(
            columns=["product", "sales", "date", "region"],
            rows=rows,
            row_count=100,
            runtime_ms=1200.5,
            truncated=True  # Simulate truncation
        )
        
        response = self.generator.generate_conversational_response(
            query_results,
            "Show me all product sales data"
        )
        
        # Should handle large datasets gracefully
        assert response.message is not None
        assert len(response.insights) <= 5  # Should limit insights
        assert len(response.follow_up_questions) <= 3  # Should limit follow-ups
        
        # Should mention the large dataset
        assert any("100" in insight for insight in response.insights)
    
    def test_integration_with_financial_data(self):
        """Test with financial data to verify currency formatting."""
        query_results = ExecuteResponse(
            columns=["quarter", "revenue", "profit_margin"],
            rows=[
                ["Q1 2023", 1250000.00, 0.15],
                ["Q2 2023", 1450000.50, 0.18],
                ["Q3 2023", 1380000.25, 0.16],
                ["Q4 2023", 1650000.75, 0.22]
            ],
            row_count=4,
            runtime_ms=180.3,
            truncated=False
        )
        
        response = self.generator.generate_conversational_response(
            query_results,
            "What's our quarterly revenue and profit margins?"
        )
        
        # Should format financial numbers appropriately
        insights_text = " ".join(response.insights)
        
        # Should contain formatted currency (millions)
        assert "M" in insights_text or "million" in insights_text.lower()
        
        # Should handle percentage data
        assert "%" in insights_text or "percent" in insights_text.lower()
    
    def test_integration_with_time_series_data(self):
        """Test with time series data to verify date handling."""
        query_results = ExecuteResponse(
            columns=["date", "daily_users", "sessions"],
            rows=[
                ["2023-12-01", 1250, 3200],
                ["2023-12-02", 1180, 2950],
                ["2023-12-03", 1320, 3400],
                ["2023-12-04", 1290, 3150],
                ["2023-12-05", 1410, 3600]
            ],
            row_count=5,
            runtime_ms=95.2,
            truncated=False
        )
        
        response = self.generator.generate_conversational_response(
            query_results,
            "Show me daily user activity for the past week"
        )
        
        # Should identify temporal patterns
        insights_text = " ".join(response.insights)
        
        # Should mention time-related insights
        assert any(word in insights_text.lower() for word in ["days", "daily", "activity", "time"])
        
        # Should suggest time-related follow-ups
        follow_ups_text = " ".join(response.follow_up_questions)
        assert any(word in follow_ups_text.lower() for word in ["time", "trend", "over", "period"])
    
    def test_integration_error_recovery(self):
        """Test error recovery with malformed data."""
        # Create query results with mixed data types that might cause issues
        query_results = ExecuteResponse(
            columns=["mixed_col", "null_col", "weird_col"],
            rows=[
                ["text", None, {"nested": "object"}],
                [123, "", [1, 2, 3]],
                [None, "value", "normal"]
            ],
            row_count=3,
            runtime_ms=50.0,
            truncated=False
        )
        
        # Should not crash and should provide a reasonable response
        response = self.generator.generate_conversational_response(
            query_results,
            "Show me the mixed data"
        )
        
        assert response.message is not None
        assert len(response.message) > 0
        assert isinstance(response.insights, list)
        assert isinstance(response.follow_up_questions, list)
    
    def test_business_language_conversion(self):
        """Test that technical terms are converted to business language."""
        query_results = ExecuteResponse(
            columns=["customer_id", "total_order_value", "last_purchase_date"],
            rows=[
                ["CUST001", 2500.00, "2023-11-15"],
                ["CUST002", 1800.50, "2023-11-20"],
                ["CUST003", 3200.75, "2023-11-22"]
            ],
            row_count=3,
            runtime_ms=120.0,
            truncated=False
        )
        
        response = self.generator.generate_conversational_response(
            query_results,
            "Show me customer purchase data"
        )
        
        # Should use business-friendly language
        full_text = response.message + " " + " ".join(response.insights)
        
        # Should avoid technical jargon
        assert "customer_id" not in full_text.lower()
        assert "total_order_value" not in full_text.lower()
        
        # Should use conversational language
        assert any(word in full_text.lower() for word in ["customers", "purchases", "found", "shows"])
    
    def test_chart_integration(self):
        """Test integration with chart configuration."""
        query_results = ExecuteResponse(
            columns=["category", "count"],
            rows=[
                ["Electronics", 45],
                ["Clothing", 32],
                ["Books", 28],
                ["Home", 19]
            ],
            row_count=4,
            runtime_ms=85.0,
            truncated=False
        )
        
        chart_config = ChartConfig(
            type="pie",
            x_axis="category",
            y_axis="count",
            title="Sales by Category"
        )
        
        response = self.generator.generate_conversational_response(
            query_results,
            "What's the breakdown of sales by category?",
            chart_config
        )
        
        # Should reference the visualization
        assert "visualization" in response.message.lower() or "chart" in response.message.lower()
        assert response.chart_config == chart_config
        
        # Should provide context about what the chart shows
        assert any("category" in insight.lower() or "breakdown" in insight.lower() 
                  for insight in response.insights)


if __name__ == "__main__":
    pytest.main([__file__])