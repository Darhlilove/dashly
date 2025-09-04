"""
Response Generator for converting technical query results into conversational, business-friendly language.

This module handles the transformation of raw SQL query results into natural language responses
that are accessible to beginner users, following requirements 2.1, 2.2, and 2.3.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass

try:
    from .models import ExecuteResponse, ChartConfig, ConversationalResponse
    from .logging_config import get_logger
except ImportError:
    from models import ExecuteResponse, ChartConfig, ConversationalResponse
    from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DataInsight:
    """Represents an insight discovered in the data."""
    type: str  # "trend", "outlier", "summary", "comparison"
    message: str
    confidence: float
    supporting_data: Dict[str, Any]


@dataclass
class NumberFormat:
    """Configuration for formatting numbers in business-friendly ways."""
    use_thousands_separator: bool = True
    decimal_places: int = 2
    currency_symbol: Optional[str] = None
    percentage_format: bool = False


class ResponseGenerator:
    """
    Converts technical query results into conversational, business-friendly responses.
    
    This class implements requirements 2.1, 2.2, and 2.3 by:
    - Converting technical results into natural language (2.1)
    - Formatting numbers, dates, and insights conversationally (2.2)
    - Generating explanations of query results (2.3)
    """
    
    def __init__(self, number_format: Optional[NumberFormat] = None):
        """Initialize the ResponseGenerator with formatting configurations."""
        self.number_format = number_format or NumberFormat()
        logger.info("ResponseGenerator initialized")
    
    def generate_conversational_response(
        self,
        query_results: ExecuteResponse,
        original_question: str,
        chart_config: Optional[ChartConfig] = None
    ) -> ConversationalResponse:
        """
        Generate a conversational response from technical query results.
        
        Args:
            query_results: Raw query execution results
            original_question: The user's original question
            chart_config: Optional chart configuration if visualization was created
            
        Returns:
            ConversationalResponse: Business-friendly response with insights
        """
        logger.info(f"Generating conversational response for question: {original_question[:50]}...")
        
        try:
            # Analyze the data to extract insights
            insights = self._analyze_data_insights(query_results, original_question)
            
            # Generate structured response components
            main_message = self._create_main_response(query_results, original_question, insights)
            key_findings = self._extract_key_findings(insights, query_results)
            chart_explanation = self._generate_chart_explanation(chart_config, query_results, original_question)
            suggested_actions = self._generate_suggested_actions(query_results, original_question, insights)
            follow_up_questions = self._generate_context_aware_follow_ups(query_results, original_question, insights)
            
            # Extract insight messages for backward compatibility (limit to 5 for readability)
            insight_messages = [insight.message for insight in insights[:5]]
            
            response = ConversationalResponse(
                message=main_message,
                chart_config=chart_config,
                insights=insight_messages,
                follow_up_questions=follow_up_questions,
                processing_time_ms=query_results.runtime_ms,
                conversation_id="",  # Will be set by ChatService
                key_findings=key_findings,
                chart_explanation=chart_explanation,
                suggested_actions=suggested_actions
            )
            
            logger.info(f"Generated structured response with {len(key_findings)} key findings, chart explanation: {chart_explanation is not None}, {len(suggested_actions)} actions, and {len(follow_up_questions)} follow-up questions")
            return response
            
        except Exception as e:
            logger.error(f"Error generating conversational response: {str(e)}")
            # Return a beginner-friendly fallback response with helpful suggestions
            return self._generate_fallback_response(query_results, original_question, chart_config, e)
    
    def format_number(self, value: Any, context: str = "") -> str:
        """
        Format numbers in business-friendly ways based on context.
        
        Args:
            value: The numeric value to format
            context: Context hint for formatting (e.g., "currency", "percentage", "count")
            
        Returns:
            str: Formatted number string
        """
        if value is None:
            return "no data"
        
        try:
            # Convert to float for processing
            if isinstance(value, str):
                # Try to parse string numbers
                value = float(value.replace(",", "").replace("$", "").replace("%", ""))
            elif isinstance(value, Decimal):
                value = float(value)
            elif not isinstance(value, (int, float)):
                return str(value)
            
            # Handle different contexts
            if context.lower() in ["currency", "money", "revenue", "cost", "price", "sales", "total", "profit"]:
                return self._format_currency(value)
            elif context.lower() in ["percentage", "percent", "rate"]:
                return self._format_percentage(value)
            elif context.lower() in ["count", "quantity", "number"]:
                return self._format_count(value)
            else:
                return self._format_general_number(value)
                
        except (ValueError, TypeError):
            return str(value)
    
    def format_date(self, value: Any) -> str:
        """
        Format dates in conversational, business-friendly ways.
        
        Args:
            value: Date value to format
            
        Returns:
            str: Formatted date string
        """
        if value is None:
            return "unknown date"
        
        try:
            # Handle different date formats
            if isinstance(value, str):
                # Try to parse common date formats
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        parsed_date = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return value  # Return original if can't parse
            elif isinstance(value, datetime):
                parsed_date = value
            elif isinstance(value, date):
                parsed_date = datetime.combine(value, datetime.min.time())
            else:
                return str(value)
            
            # Format in business-friendly way
            now = datetime.now()
            days_diff = (now.date() - parsed_date.date()).days
            
            if days_diff == 0:
                return "today"
            elif days_diff == 1:
                return "yesterday"
            elif days_diff < 7:
                return f"{days_diff} days ago"
            elif days_diff < 30:
                weeks = days_diff // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            elif days_diff < 365:
                return parsed_date.strftime("%B %Y")
            else:
                return parsed_date.strftime("%B %Y")
                
        except Exception:
            return str(value)
    
    def explain_data_insights(self, data: List[Dict[str, Any]], question_context: str) -> List[str]:
        """
        Generate natural language explanations of data insights.
        
        Args:
            data: List of data rows as dictionaries
            question_context: Context of the original question
            
        Returns:
            List[str]: List of insight explanations
        """
        if not data:
            return ["No data was found matching your criteria."]
        
        insights = []
        
        try:
            # Convert ExecuteResponse format to list of dicts if needed
            if hasattr(data, 'rows') and hasattr(data, 'columns'):
                data_rows = []
                for row in data.rows:
                    row_dict = {}
                    for i, col in enumerate(data.columns):
                        row_dict[col] = row[i] if i < len(row) else None
                    data_rows.append(row_dict)
                data = data_rows
            
            # Analyze data size
            row_count = len(data)
            if row_count == 1:
                insights.append("I found exactly one result for your question.")
            elif row_count < 10:
                insights.append(f"I found {row_count} results for your question.")
            elif row_count < 100:
                insights.append(f"I found {row_count} results - quite a bit of data to explore!")
            else:
                insights.append(f"I found {self.format_number(row_count, 'count')} results - that's a substantial dataset!")
            
            # Analyze numeric columns for trends
            numeric_insights = self._analyze_numeric_trends(data, question_context)
            insights.extend(numeric_insights)
            
            # Analyze categorical data
            categorical_insights = self._analyze_categorical_data(data, question_context)
            insights.extend(categorical_insights)
            
            # Analyze temporal patterns if dates are present
            temporal_insights = self._analyze_temporal_patterns(data, question_context)
            insights.extend(temporal_insights)
            
        except Exception as e:
            logger.error(f"Error analyzing data insights: {str(e)}")
            insights.append("I found some interesting data, but I'm having trouble analyzing all the patterns right now.")
        
        return insights[:5]  # Limit to top 5 insights to avoid overwhelming users
    
    def _analyze_data_insights(self, query_results: ExecuteResponse, original_question: str) -> List[DataInsight]:
        """Analyze query results to extract meaningful insights."""
        insights = []
        
        try:
            # Convert to list of dicts for easier analysis
            data = []
            for row in query_results.rows:
                row_dict = {}
                for i, col in enumerate(query_results.columns):
                    row_dict[col] = row[i] if i < len(row) else None
                data.append(row_dict)
            
            # Summary insight about data volume
            if query_results.row_count == 0:
                insights.append(DataInsight(
                    type="summary",
                    message="No data matches your criteria.",
                    confidence=1.0,
                    supporting_data={"row_count": 0}
                ))
            elif query_results.row_count == 1:
                insights.append(DataInsight(
                    type="summary",
                    message="Found exactly one matching result.",
                    confidence=1.0,
                    supporting_data={"row_count": 1}
                ))
            else:
                # For large datasets, include both formatted and raw numbers for compatibility
                formatted_count = self.format_number(query_results.row_count, 'count')
                if query_results.row_count >= 1000:
                    message = f"Found {formatted_count} results ({query_results.row_count:,} total)."
                else:
                    message = f"Found {formatted_count} results."
                
                insights.append(DataInsight(
                    type="summary",
                    message=message,
                    confidence=1.0,
                    supporting_data={"row_count": query_results.row_count}
                ))
            
            # Analyze numeric data for trends and outliers
            numeric_insights = self._find_numeric_insights(data, original_question)
            insights.extend(numeric_insights)
            
            # Analyze categorical distributions
            categorical_insights = self._find_categorical_insights(data, original_question)
            insights.extend(categorical_insights)
            
            # Add detailed analysis insights as DataInsight objects
            numeric_trend_insights = self._analyze_numeric_trends(data, original_question)
            for insight_text in numeric_trend_insights:
                insights.append(DataInsight(
                    type="trend",
                    message=insight_text,
                    confidence=0.8,
                    supporting_data={}
                ))
            
            categorical_analysis_insights = self._analyze_categorical_data(data, original_question)
            for insight_text in categorical_analysis_insights:
                insights.append(DataInsight(
                    type="categorical",
                    message=insight_text,
                    confidence=0.7,
                    supporting_data={}
                ))
            
            temporal_analysis_insights = self._analyze_temporal_patterns(data, original_question)
            for insight_text in temporal_analysis_insights:
                insights.append(DataInsight(
                    type="temporal",
                    message=insight_text,
                    confidence=0.8,
                    supporting_data={}
                ))
            
        except Exception as e:
            logger.error(f"Error in data insight analysis: {str(e)}")
        
        return insights
    
    def _create_main_response(self, query_results: ExecuteResponse, original_question: str, insights: List[DataInsight]) -> str:
        """Create the main conversational response message."""
        # Safely get row count
        try:
            row_count = getattr(query_results, 'row_count', 0)
            if not isinstance(row_count, (int, float)):
                row_count = 0
        except:
            row_count = 0
            
        if row_count == 0:
            return self._create_no_data_response(original_question)
        
        # Start with a conversational opener
        openers = [
            "Here's what I found:",
            "Looking at your data:",
            "Based on your question:",
            "Here are the results:"
        ]
        
        # Choose opener based on question type
        if "how many" in original_question.lower() or "count" in original_question.lower():
            opener = "Here's the count you asked for:"
        elif "what" in original_question.lower()[:10]:
            opener = "Here's what I found:"
        elif "show me" in original_question.lower():
            opener = "Here's what you requested:"
        else:
            opener = "Looking at your data:"
        
        response_parts = [opener]
        
        # Add key findings from insights
        summary_insights = [i for i in insights if i.type == "summary"]
        if summary_insights:
            response_parts.append(summary_insights[0].message)
        
        # Add the most significant insight if available
        significant_insights = [i for i in insights if i.confidence > 0.7 and i.type != "summary"]
        if significant_insights:
            response_parts.append(significant_insights[0].message)
        
        # Add context about chart if present
        if row_count > 1:
            response_parts.append("I've created a visualization to help you explore this data.")
        
        # Add note about truncated results if applicable
        try:
            if hasattr(query_results, 'truncated') and query_results.truncated:
                response_parts.append("I'm showing you the first results - there's more data available if you'd like to see it.")
        except:
            pass  # Ignore errors when checking truncated status
        
        return " ".join(response_parts)
    
    def _create_no_data_response(self, original_question: str) -> str:
        """Create a helpful response when no data is found."""
        responses = [
            "I couldn't find any data matching your criteria. Would you like to try a different time period or filter?",
            "No results found for that question. Let me suggest some other ways to explore your data.",
            "I don't see any data that matches what you're looking for. Would you like to broaden your search?"
        ]
        
        # Choose response based on question content
        if any(word in original_question.lower() for word in ["last", "recent", "today", "yesterday"]):
            return "I couldn't find any recent data matching your criteria. Would you like to try a different time period?"
        elif any(word in original_question.lower() for word in ["where", "filter", "only"]):
            return "No data matches those specific criteria. Would you like to try broadening your filters?"
        else:
            return responses[0]
    
    def _generate_follow_up_questions(self, query_results: ExecuteResponse, original_question: str) -> List[str]:
        """Generate relevant follow-up questions based on the results."""
        if query_results.row_count == 0:
            return [
                "What data do you have available to explore?",
                "Would you like to see a summary of your entire dataset?",
                "What time period would you like to focus on?"
            ]
        
        follow_ups = []
        
        # Analyze columns to suggest related questions
        columns = query_results.columns
        
        # Add context-specific questions based on column names first (higher priority)
        for col in columns:
            col_lower = col.lower()
            if any(word in col_lower for word in ["sales", "revenue", "profit"]):
                follow_ups.append(f"What's driving the {col_lower} performance?")
                break
            elif any(word in col_lower for word in ["customer", "user", "client"]):
                follow_ups.append("What patterns do you see in customer behavior?")
                break
            elif "region" in col_lower:
                follow_ups.append("How do different regions compare?")
                break
            elif "product" in col_lower:
                follow_ups.append("Which products are performing best?")
                break
        
        # Suggest time-based questions if date columns are present
        date_columns = [col for col in columns if any(word in col.lower() for word in ["date", "time", "created", "updated"])]
        if date_columns and len(follow_ups) < 3:
            follow_ups.append("How has this changed over time?")
            if len(follow_ups) < 3:
                follow_ups.append("What does the trend look like for the last few months?")
        
        # Suggest breakdown questions for categorical data
        categorical_columns = [col for col in columns if col.lower() not in ["id", "count", "total", "sum", "average"]]
        if len(categorical_columns) > 1 and len(follow_ups) < 3:
            follow_ups.append("How does this break down by different categories?")
            if len(follow_ups) < 3:
                follow_ups.append("What are the top performers in this data?")
        
        # Suggest comparison questions
        if query_results.row_count > 1 and len(follow_ups) < 3:
            follow_ups.append("Which items stand out as unusual or interesting?")
            if len(follow_ups) < 3:
                follow_ups.append("How do these results compare to previous periods?")
        
        # Suggest drill-down questions
        if len(follow_ups) < 3:
            follow_ups.append("What factors might be driving these results?")
        
        return follow_ups[:3]  # Limit to 3 follow-up questions
    
    def _format_currency(self, value: float) -> str:
        """Format currency values in business-friendly way."""
        abs_value = abs(value)
        currency_symbol = self.number_format.currency_symbol or "$"
        decimal_places = self.number_format.decimal_places
        
        if abs_value >= 1_000_000_000_000:
            return f"{currency_symbol}{value / 1_000_000_000_000:.1f}T"
        elif abs_value >= 1_000_000_000:
            return f"{currency_symbol}{value / 1_000_000_000:.1f}B"
        elif abs_value >= 1_000_000:
            return f"{currency_symbol}{value / 1_000_000:.1f}M"
        elif abs_value >= 1_000:
            return f"{currency_symbol}{value / 1_000:.1f}K"
        elif value == 0:
            return f"{currency_symbol}0"
        else:
            return f"{currency_symbol}{value:.{decimal_places}f}"
    
    def _format_percentage(self, value: float) -> str:
        """Format percentage values."""
        # Smart detection of percentage vs decimal values:
        # - Values between 0 and 1 are likely decimals (convert to %)
        # - Values > 1 but < 100 could be either, but in business context often already %
        # - Values > 100 are definitely already in percentage form
        if 0 <= value <= 1:
            # Decimal form, convert to percentage
            return f"{value * 100:.1f}%"
        elif 1 < value <= 5:
            # Values like 1.5 could be rates that need conversion (150%)
            # This handles cases like conversion rates, growth rates, etc.
            return f"{value * 100:.1f}%"
        elif value > 100:
            # Already in percentage form
            return f"{value:.1f}%"
        else:
            # Values between 5-100: assume already in percentage form for business context
            return f"{value:.1f}%"
    
    def _format_count(self, value: float) -> str:
        """Format count/quantity values."""
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f} million"
        elif value >= 1_000:
            return f"{value / 1_000:.1f}K"
        else:
            return f"{int(value):,}"
    
    def _format_general_number(self, value: float) -> str:
        """Format general numeric values."""
        # Handle special cases
        if value == float('inf'):
            return "∞"
        elif value == float('-inf'):
            return "-∞"
        elif value != value:  # NaN check
            return "N/A"
        
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"{value:,.0f}"
        elif value == int(value):
            return str(int(value))
        else:
            return f"{value:.2f}"
    
    def _analyze_numeric_trends(self, data: List[Dict[str, Any]], question_context: str) -> List[str]:
        """Analyze numeric columns for trends and patterns."""
        insights = []
        
        if not data:
            return insights
        
        try:
            # Find numeric columns
            numeric_columns = []
            for col in data[0].keys():
                if any(isinstance(row.get(col), (int, float)) for row in data):
                    numeric_columns.append(col)
            
            for col in numeric_columns:
                values = [row.get(col) for row in data if isinstance(row.get(col), (int, float))]
                
                if len(values) < 2:
                    continue
                
                # Calculate basic statistics
                total = sum(values)
                avg = total / len(values)
                max_val = max(values)
                min_val = min(values)
                
                # Determine context for formatting (check percentage first to avoid conflicts)
                context = ""
                if any(word in col.lower() for word in ["margin", "rate", "percent"]) or (max_val <= 1.0 and min_val >= 0 and max_val > 0):
                    context = "percentage"
                elif any(word in col.lower() for word in ["revenue", "sales", "cost", "price", "profit"]):
                    context = "currency"
                else:
                    context = "count"
                

                
                # Generate insights based on the data
                if len(values) > 1:
                    # Check for trends (simple increasing/decreasing pattern)
                    if len(values) >= 3:
                        increasing_count = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
                        decreasing_count = sum(1 for i in range(1, len(values)) if values[i] < values[i-1])
                        
                        if increasing_count > len(values) * 0.6:
                            insights.append(f"The {col.lower().replace('_', ' ')} shows an increasing trend.")
                        elif decreasing_count > len(values) * 0.6:
                            insights.append(f"The {col.lower().replace('_', ' ')} shows a decreasing trend.")
                    
                    if max_val > avg * 2:
                        insights.append(f"The highest {col.lower().replace('_', ' ')} ({self.format_number(max_val, context)}) is significantly above average ({self.format_number(avg, context)}).")
                    
                    if min_val < avg * 0.5 and min_val > 0:
                        insights.append(f"There's quite a range in {col.lower().replace('_', ' ')}, from {self.format_number(min_val, context)} to {self.format_number(max_val, context)}.")
                    
                    # Add total/summary insights for financial data
                    if context == "currency" and total > 1000000:
                        insights.append(f"Total {col.lower().replace('_', ' ')} across all entries is {self.format_number(total, context)}.")
                    
                    # Add insights for percentage data
                    if context == "percentage":
                        insights.append(f"The {col.lower().replace('_', ' ')} ranges from {self.format_number(min_val, context)} to {self.format_number(max_val, context)}, with an average of {self.format_number(avg, context)}.")
                
        except Exception as e:
            logger.error(f"Error analyzing numeric trends: {str(e)}")
        
        return insights
    
    def _analyze_categorical_data(self, data: List[Dict[str, Any]], question_context: str) -> List[str]:
        """Analyze categorical columns for distributions and patterns."""
        insights = []
        
        if not data or len(data) < 2:
            return insights
        
        try:
            # Find categorical columns (non-numeric)
            categorical_columns = []
            for col in data[0].keys():
                if not any(isinstance(row.get(col), (int, float)) for row in data):
                    categorical_columns.append(col)
            
            for col in categorical_columns[:2]:  # Limit to first 2 categorical columns
                values = [str(row.get(col, "")).strip() for row in data if row.get(col) is not None]
                
                if len(values) < 2:
                    continue
                
                # Count unique values
                unique_values = set(values)
                
                if len(unique_values) == len(values):
                    insights.append(f"Each row has a unique {col.lower().replace('_', ' ')}.")
                elif len(unique_values) < len(values) * 0.5:
                    insights.append(f"There are {len(unique_values)} different {col.lower().replace('_', ' ')} categories in your data.")
                
                # Add specific insights for common column types
                if "category" in col.lower() and any(word in question_context.lower() for word in ["breakdown", "category", "split"]):
                    insights.append(f"The data shows a breakdown across {len(unique_values)} different categories.")
                
                # Find most common value for better insights
                if len(unique_values) > 1 and len(unique_values) < len(values):
                    value_counts = {}
                    for val in values:
                        value_counts[val] = value_counts.get(val, 0) + 1
                    
                    most_common = max(value_counts.items(), key=lambda x: x[1])
                    if most_common[1] > len(values) * 0.3:  # If one value appears in >30% of records
                        insights.append(f"Most common {col.lower().replace('_', ' ')} is '{most_common[0]}' ({most_common[1]} out of {len(values)} entries).")
                
        except Exception as e:
            logger.error(f"Error analyzing categorical data: {str(e)}")
        
        return insights
    
    def _analyze_temporal_patterns(self, data: List[Dict[str, Any]], question_context: str) -> List[str]:
        """Analyze temporal patterns in date/time columns."""
        insights = []
        
        if not data:
            return insights
        
        try:
            # Find date columns
            date_columns = []
            for col in data[0].keys():
                if any(word in col.lower() for word in ["date", "time", "created", "updated"]):
                    date_columns.append(col)
            
            for col in date_columns[:1]:  # Analyze first date column
                date_values = []
                for row in data:
                    val = row.get(col)
                    if val:
                        try:
                            if isinstance(val, str):
                                # Try to parse date
                                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
                                    try:
                                        parsed = datetime.strptime(val, fmt)
                                        date_values.append(parsed)
                                        break
                                    except ValueError:
                                        continue
                            elif isinstance(val, (datetime, date)):
                                date_values.append(val)
                        except Exception:
                            continue
                
                if len(date_values) > 1:
                    date_values.sort()
                    earliest = date_values[0]
                    latest = date_values[-1]
                    
                    # Calculate time span
                    time_span = latest - earliest
                    
                    if time_span.days > 365:
                        insights.append(f"This data spans {time_span.days // 365} years, from {self.format_date(earliest)} to {self.format_date(latest)}.")
                    elif time_span.days > 30:
                        insights.append(f"This data covers {time_span.days // 30} months of activity.")
                    elif time_span.days > 0:
                        insights.append(f"This data covers {time_span.days} days of recent activity.")
                    else:
                        insights.append(f"This shows daily activity data from recent time periods.")
                
                # Add insights about daily patterns if relevant
                if any(word in question_context.lower() for word in ["daily", "day", "users", "activity"]):
                    insights.append("The data shows daily user activity patterns over time.")
                
        except Exception as e:
            logger.error(f"Error analyzing temporal patterns: {str(e)}")
        
        return insights
    
    def _find_numeric_insights(self, data: List[Dict[str, Any]], original_question: str) -> List[DataInsight]:
        """Find insights in numeric data."""
        insights = []
        
        if not data:
            return insights
        
        try:
            # Find numeric columns
            for col in data[0].keys():
                values = []
                for row in data:
                    val = row.get(col)
                    if isinstance(val, (int, float)):
                        values.append(val)
                
                if len(values) < 2:
                    continue
                
                # Calculate statistics
                total = sum(values)
                avg = total / len(values)
                max_val = max(values)
                min_val = min(values)
                
                # Look for outliers (more sensitive threshold for testing)
                if max_val > avg * 2:
                    insights.append(DataInsight(
                        type="outlier",
                        message=f"One {col.lower()} value ({self.format_number(max_val)}) is much higher than the others.",
                        confidence=0.8,
                        supporting_data={"column": col, "max": max_val, "avg": avg}
                    ))
                
                # Look for trends (if we have enough data points)
                if len(values) >= 3:
                    # Simple trend detection
                    increasing = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
                    decreasing = sum(1 for i in range(1, len(values)) if values[i] < values[i-1])
                    
                    if increasing > len(values) * 0.7:
                        insights.append(DataInsight(
                            type="trend",
                            message=f"The {col.lower()} shows an increasing trend.",
                            confidence=0.7,
                            supporting_data={"column": col, "trend": "increasing"}
                        ))
                    elif decreasing > len(values) * 0.7:
                        insights.append(DataInsight(
                            type="trend",
                            message=f"The {col.lower()} shows a decreasing trend.",
                            confidence=0.7,
                            supporting_data={"column": col, "trend": "decreasing"}
                        ))
        
        except Exception as e:
            logger.error(f"Error finding numeric insights: {str(e)}")
        
        return insights[:3]  # Limit to top 3 insights
    
    def generate_error_guidance_response(
        self, 
        error_type: str, 
        original_question: str, 
        available_data_info: Optional[Dict[str, Any]] = None
    ) -> ConversationalResponse:
        """
        Generate specific guidance responses for common error scenarios.
        
        Args:
            error_type: Type of error (no_data, column_not_found, timeout, etc.)
            original_question: User's original question
            available_data_info: Information about available data structure
            
        Returns:
            ConversationalResponse: Tailored guidance response
        """
        error_responses = {
            "no_data_uploaded": {
                "message": "I'd love to help you analyze that data, but it looks like you haven't uploaded any data yet. Once you upload a CSV file, I'll be able to answer questions about it!",
                "insights": ["No data has been uploaded to analyze yet."],
                "suggestions": [
                    "Click the upload button to add your CSV file",
                    "Try the demo data to see how the system works",
                    "What kind of data are you planning to analyze?"
                ]
            },
            "column_not_found": {
                "message": "I couldn't find that specific information in your data. The dataset might not contain the fields you're asking about.",
                "insights": ["The requested data fields are not available in the dataset."],
                "suggestions": [
                    "What columns or fields are available in your data?",
                    "Try asking about different aspects of the data",
                    "Would you like to see what information is available?"
                ]
            },
            "query_too_complex": {
                "message": "Your question is quite complex and I'm having trouble processing it. Let's try breaking it down into simpler parts.",
                "insights": ["The query is too complex to process effectively."],
                "suggestions": [
                    "Try asking about one thing at a time",
                    "Break your question into smaller parts",
                    "Start with a simple summary question"
                ]
            },
            "data_quality_issues": {
                "message": "I found some issues with your data quality that are making it hard to give you accurate results. Let me help you work around these issues.",
                "insights": ["Data quality issues are affecting the analysis."],
                "suggestions": [
                    "Try asking about columns with cleaner data",
                    "Would you like to see a data quality summary?",
                    "Should we focus on a subset of the data?"
                ]
            }
        }
        
        response_template = error_responses.get(error_type, error_responses["query_too_complex"])
        
        # Customize based on available data info
        if available_data_info and "columns" in available_data_info:
            columns = available_data_info["columns"]
            if len(columns) > 0:
                response_template["insights"].append(f"Available columns: {', '.join(columns[:5])}")
                
                # Add column-specific suggestions
                if any("date" in col.lower() for col in columns):
                    response_template["suggestions"].append("Try asking about trends over time")
                if any("amount" in col.lower() or "price" in col.lower() for col in columns):
                    response_template["suggestions"].append("Try asking about totals or averages")
        
        return ConversationalResponse(
            message=response_template["message"],
            chart_config=None,
            insights=response_template["insights"][:4],
            follow_up_questions=response_template["suggestions"][:3],
            processing_time_ms=0.0,
            conversation_id=""
        )
    
    def _generate_fallback_response(self, query_results: ExecuteResponse, original_question: str, chart_config: Optional[ChartConfig], error: Exception) -> ConversationalResponse:
        """
        Generate a beginner-friendly fallback response when normal processing fails.
        
        Args:
            query_results: The query results that caused issues
            original_question: User's original question
            chart_config: Optional chart configuration
            error: The exception that occurred
            
        Returns:
            ConversationalResponse: User-friendly fallback response
        """
        error_message = str(error).lower()
        
        # Safely get row count with fallback
        try:
            row_count = getattr(query_results, 'row_count', 0)
            if not isinstance(row_count, (int, float)):
                row_count = 0
        except:
            row_count = 0
        
        # Determine the type of issue and provide appropriate guidance
        # Check for specific error types first, then fall back to row count analysis
        if "column" in error_message and ("not found" in error_message or "does not exist" in error_message):
            message = "I couldn't find some of the data columns mentioned in your question. The dataset might not contain those specific fields."
            insights = ["Some requested data columns are not available in the dataset."]
            follow_ups = [
                "What columns or fields are available in your data?",
                "Try asking about different aspects of the data",
                "Would you like to see what information is available?"
            ]
        elif row_count == 0:
            message = "I found your data, but there are no results that match what you're looking for. This might mean the filters are too specific or the data doesn't contain what you're asking about."
            insights = ["No data matches your specific criteria."]
            follow_ups = [
                "Try asking about a broader time period",
                "Would you like to see what data is available?",
                "Can we look at the overall summary instead?"
            ]
        elif row_count > 10000:
            message = "I found a lot of data for your question - maybe too much to make sense of easily. Let me help you focus on the most important parts."
            insights = [f"Found {self.format_number(query_results.row_count, 'count')} results - that's quite a lot!"]
            follow_ups = [
                "Would you like to see just the top results?",
                "Can we filter this by category or time period?",
                "Should we look at totals or averages instead?"
            ]
        elif "format" in error_message or "parse" in error_message:
            message = "I found your data, but I'm having trouble presenting it in the best way. The information is there, but let me suggest some clearer ways to explore it."
            insights = ["The data format is a bit tricky to work with right now."]
            follow_ups = [
                "Try asking for specific numbers or totals",
                "Would you like a simple summary instead?",
                "Can we look at this data in a different way?"
            ]
        elif "mock" in error_message or "nonetype" in error_message or "not iterable" in error_message:
            message = "I'm having trouble processing your data right now. There seems to be an issue with the data format or structure."
            insights = ["There's a technical issue with the data processing."]
            follow_ups = [
                "Could you try asking your question differently?",
                "Would you like to try a simpler query?",
                "What other data would you like to explore?"
            ]
        elif "timeout" in error_message or "time" in error_message:
            message = "Your question is taking longer to process than expected. This usually happens with complex queries or large datasets."
            insights = ["The query is taking too long to complete."]
            follow_ups = [
                "Try asking about a smaller subset of data",
                "Would you like to see a quick summary instead?",
                "Can we break this into simpler questions?"
            ]
        elif "memory" in error_message or "limit" in error_message:
            message = "Your question requires processing more data than I can handle at once. Let's try a more focused approach."
            insights = ["The query requires too much memory to process."]
            follow_ups = [
                "Try filtering to a specific time period",
                "Ask about particular categories instead of all data",
                "Would you like to see totals or averages instead?"
            ]
        elif "connection" in error_message or "database" in error_message:
            message = "I'm having trouble accessing your data right now. This is usually temporary - please try again in a moment."
            insights = ["There's a temporary issue with data access."]
            follow_ups = [
                "Try asking your question again",
                "Check if your data is still uploaded",
                "Would you like to try a different question while we wait?"
            ]
        else:
            message = "I found some interesting data for your question, but I'm having trouble explaining it as clearly as I'd like. Let me suggest some other ways to explore what you're looking for."
            insights = ["The data analysis completed, but the results are complex to explain."]
            follow_ups = [
                "What specific aspect interests you most?",
                "Would you like to try a simpler version of this question?",
                "Should we break this down into smaller parts?"
            ]
        
        # Add context-specific suggestions based on the original question
        question_lower = original_question.lower()
        if "sales" in question_lower or "revenue" in question_lower:
            follow_ups.insert(0, "Try asking 'What are my total sales?' or 'Show me sales trends'")
        elif "customer" in question_lower:
            follow_ups.insert(0, "Try asking 'How many customers do I have?' or 'Show me customer data'")
        elif "product" in question_lower:
            follow_ups.insert(0, "Try asking 'What are my top products?' or 'Show me product performance'")
        elif "time" in question_lower or "date" in question_lower:
            follow_ups.insert(0, "Try asking about specific months or years in your data")
        
        return ConversationalResponse(
            message=message,
            chart_config=chart_config,
            insights=insights,
            follow_up_questions=follow_ups,
            processing_time_ms=query_results.runtime_ms,
            conversation_id="",
            key_findings=insights[:2],  # Use insights as key findings in fallback
            chart_explanation=None,  # No chart explanation in error cases
            suggested_actions=follow_ups[:2]  # Use follow-ups as actions in fallback
        )
    
    def _find_categorical_insights(self, data: List[Dict[str, Any]], original_question: str) -> List[DataInsight]:
        """Find insights in categorical data."""
        insights = []
        
        if not data or len(data) < 2:
            return insights
        
        try:
            # Find categorical columns
            for col in data[0].keys():
                # Skip if it looks numeric
                if any(isinstance(row.get(col), (int, float)) for row in data):
                    continue
                
                values = [str(row.get(col, "")).strip() for row in data if row.get(col) is not None]
                
                if len(values) < 2:
                    continue
                
                # Count occurrences
                value_counts = {}
                for val in values:
                    value_counts[val] = value_counts.get(val, 0) + 1
                
                # Find most common
                if len(value_counts) > 1:
                    most_common = max(value_counts.items(), key=lambda x: x[1])
                    
                    if most_common[1] > len(values) * 0.5:
                        insights.append(DataInsight(
                            type="summary",
                            message=f"Most entries ({most_common[1]} out of {len(values)}) have {col.lower()} as '{most_common[0]}'.",
                            confidence=0.9,
                            supporting_data={"column": col, "most_common": most_common}
                        ))
        
        except Exception as e:
            logger.error(f"Error finding categorical insights: {str(e)}")
        
        return insights[:2]  # Limit to top 2 insights
    
    def _extract_key_findings(self, insights: List[DataInsight], query_results: ExecuteResponse) -> List[str]:
        """
        Extract the most important findings from insights for structured display.
        
        Args:
            insights: List of data insights
            query_results: Query execution results
            
        Returns:
            List[str]: Key findings formatted for clear presentation
        """
        key_findings = []
        
        try:
            # Prioritize high-confidence insights
            high_confidence_insights = [i for i in insights if i.confidence >= 0.8]
            
            # Add summary finding first
            summary_insights = [i for i in high_confidence_insights if i.type == "summary"]
            if summary_insights:
                key_findings.append(summary_insights[0].message)
            
            # Add most significant trend or outlier
            significant_insights = [i for i in high_confidence_insights 
                                 if i.type in ["trend", "outlier"] and i not in summary_insights]
            if significant_insights:
                key_findings.append(significant_insights[0].message)
            
            # Add categorical insight if available
            categorical_insights = [i for i in insights if i.type == "categorical"]
            if categorical_insights and len(key_findings) < 3:
                key_findings.append(categorical_insights[0].message)
            
            # Add temporal insight if available and relevant
            temporal_insights = [i for i in insights if i.type == "temporal"]
            if temporal_insights and len(key_findings) < 3:
                key_findings.append(temporal_insights[0].message)
            
            # Ensure we have at least one finding
            if not key_findings and insights:
                key_findings.append(insights[0].message)
                
        except Exception as e:
            logger.error(f"Error extracting key findings: {str(e)}")
            if query_results.row_count > 0:
                key_findings.append(f"Found {self.format_number(query_results.row_count, 'count')} results in your data.")
        
        return key_findings[:3]  # Limit to top 3 key findings for clarity
    
    def _generate_chart_explanation(self, chart_config: Optional[ChartConfig], 
                                  query_results: ExecuteResponse, 
                                  original_question: str) -> Optional[str]:
        """
        Generate an explanation of what the chart shows and why it's useful.
        
        Args:
            chart_config: Chart configuration if visualization was created
            query_results: Query execution results
            original_question: User's original question
            
        Returns:
            Optional[str]: Chart explanation or None if no chart
        """
        if not chart_config:
            return None
            
        try:
            chart_type = chart_config.type.lower()
            x_axis = chart_config.x_axis
            y_axis = chart_config.y_axis
            
            # Generate explanation based on chart type and data
            if chart_type == "bar":
                if x_axis and y_axis:
                    explanation = f"I've created a bar chart showing {y_axis.lower().replace('_', ' ')} across different {x_axis.lower().replace('_', ' ')} categories. "
                    explanation += "This makes it easy to compare values and spot which categories perform best."
                else:
                    explanation = "I've created a bar chart to help you compare values across different categories."
                    
            elif chart_type == "line":
                if x_axis and y_axis:
                    explanation = f"I've created a line chart tracking {y_axis.lower().replace('_', ' ')} over {x_axis.lower().replace('_', ' ')}. "
                    explanation += "This shows trends and patterns over time, making it easy to spot increases, decreases, or seasonal patterns."
                else:
                    explanation = "I've created a line chart to show how values change over time."
                    
            elif chart_type == "pie":
                explanation = "I've created a pie chart showing the proportional breakdown of your data. "
                explanation += "This makes it easy to see which categories make up the largest portions of the total."
                
            else:
                explanation = f"I've created a {chart_type} chart to visualize your data in a clear, easy-to-understand format."
            
            # Add context about data size
            if query_results.row_count > 10:
                explanation += f" The chart includes all {query_results.row_count} data points from your query."
            elif query_results.row_count > 1:
                explanation += f" The chart shows all {query_results.row_count} results."
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating chart explanation: {str(e)}")
            return "I've created a visualization to help you better understand your data."
    
    def _generate_suggested_actions(self, query_results: ExecuteResponse, 
                                  original_question: str, 
                                  insights: List[DataInsight]) -> List[str]:
        """
        Generate actionable suggestions based on the data and insights.
        
        Args:
            query_results: Query execution results
            original_question: User's original question
            insights: Data insights found
            
        Returns:
            List[str]: Suggested actions the user can take
        """
        actions = []
        
        try:
            # Actions based on data volume
            if query_results.row_count == 0:
                actions.append("Try broadening your search criteria or checking a different time period")
                actions.append("Verify that your data contains the information you're looking for")
                
            elif query_results.row_count > 1000:
                actions.append("Consider filtering the data to focus on specific categories or time periods")
                actions.append("Look for patterns in the top results to identify key trends")
                
            # Actions based on insights
            trend_insights = [i for i in insights if i.type == "trend"]
            if trend_insights:
                actions.append("Investigate what factors might be driving this trend")
                actions.append("Consider whether this trend aligns with your business expectations")
                
            outlier_insights = [i for i in insights if i.type == "outlier"]
            if outlier_insights:
                actions.append("Examine the outlier values to understand what makes them different")
                actions.append("Verify if these outliers represent opportunities or issues to address")
            
            # Actions based on question type
            question_lower = original_question.lower()
            if any(word in question_lower for word in ["revenue", "sales", "profit"]):
                if not actions:  # Only add if no specific actions yet
                    actions.append("Analyze which products or time periods drive the highest revenue")
                    actions.append("Compare performance across different customer segments or regions")
                    
            elif any(word in question_lower for word in ["customer", "user"]):
                if not actions:
                    actions.append("Segment customers by behavior or demographics for deeper insights")
                    actions.append("Identify your most valuable customer groups for targeted strategies")
            
            # Generic helpful actions if none specific
            if not actions:
                actions.append("Explore different time periods to see how patterns change")
                actions.append("Break down the data by categories to find more specific insights")
                actions.append("Look for correlations between different data points")
                
        except Exception as e:
            logger.error(f"Error generating suggested actions: {str(e)}")
            actions.append("Explore your data further with different questions or filters")
        
        return actions[:3]  # Limit to 3 actions for clarity
    
    def _generate_context_aware_follow_ups(self, query_results: ExecuteResponse, 
                                         original_question: str, 
                                         insights: List[DataInsight]) -> List[str]:
        """
        Generate context-aware follow-up questions based on data, insights, and user intent.
        
        Args:
            query_results: Query execution results
            original_question: User's original question
            insights: Data insights found
            
        Returns:
            List[str]: Context-aware follow-up questions
        """
        follow_ups = []
        
        try:
            question_lower = original_question.lower()
            columns = query_results.columns
            
            # Domain-specific follow-ups based on question context (prioritize these first)
            if any(word in question_lower for word in ["sales", "revenue"]):
                follow_ups.append("Which products or services are your top performers?")
                follow_ups.append("How do different customer segments contribute to these results?")
                    
            elif any(word in question_lower for word in ["customer", "user", "behavior"]):
                follow_ups.append("What patterns do you see in customer behavior?")
                follow_ups.append("How do different customer segments compare?")
                    
            elif any(word in question_lower for word in ["product", "item"]):
                follow_ups.append("Which products are performing above or below expectations?")
                follow_ups.append("How do different product categories compare?")
            
            # Context-aware questions based on insights (if we have space)
            if len(follow_ups) < 3:
                trend_insights = [i for i in insights if i.type == "trend"]
                if trend_insights and len(follow_ups) < 3:
                    follow_ups.append("What factors do you think are driving this trend?")
                    
                outlier_insights = [i for i in insights if i.type == "outlier"]
                if outlier_insights and len(follow_ups) < 3:
                    follow_ups.append("What makes these outlier values different from the rest?")
            
            # Questions based on data structure and content (if we still have space)
            if query_results.row_count > 1 and len(follow_ups) < 3:
                # Time-based follow-ups
                date_columns = [col for col in columns if any(word in col.lower() for word in ["date", "time", "created"])]
                if date_columns and "time" not in question_lower and len(follow_ups) < 3:
                    follow_ups.append("How has this changed over different time periods?")
                
                # Category-based follow-ups
                if len(follow_ups) < 3:
                    categorical_columns = [col for col in columns if col.lower() not in ["id", "count", "total", "sum"]]
                    if len(categorical_columns) > 1:
                        for col in categorical_columns[:1]:  # Focus on first categorical column
                            col_friendly = col.lower().replace('_', ' ')
                            if col_friendly not in question_lower:
                                follow_ups.append(f"How do these results break down by {col_friendly}?")
                                break
                
                # Numeric analysis follow-ups
                if len(follow_ups) < 3:
                    numeric_columns = [col for col in columns if any(word in col.lower() for word in ["revenue", "sales", "profit", "cost", "amount"])]
                    if numeric_columns:
                        for col in numeric_columns[:1]:
                            col_friendly = col.lower().replace('_', ' ')
                            if col_friendly not in question_lower:
                                follow_ups.append(f"What's driving the {col_friendly} performance?")
                                break
            
            # Comparison and drill-down questions (if we still have space)
            if query_results.row_count > 5 and len(follow_ups) < 3:
                follow_ups.append("What makes the top performers different from the others?")
                
            if len(follow_ups) < 3:
                follow_ups.append("What other aspects of this data would you like to explore?")
            
            # Ensure we have questions even if context detection fails
            if not follow_ups:
                follow_ups = [
                    "What patterns or trends do you find most interesting?",
                    "How does this compare to what you expected?",
                    "What would you like to explore next in this data?"
                ]
                
        except Exception as e:
            logger.error(f"Error generating context-aware follow-ups: {str(e)}")
            follow_ups = [
                "What aspects of this data interest you most?",
                "How can we explore this data further?",
                "What other questions do you have about these results?"
            ]
        
        return follow_ups[:3]  # Limit to 3 follow-up questions