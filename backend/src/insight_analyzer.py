"""
Insight Analyzer for automatically detecting patterns in query results.

This module implements automatic pattern detection, trend analysis, outlier identification,
and contextual follow-up question generation as specified in requirements 2.3, 4.1, 4.2, and 4.3.
"""

import statistics
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum

try:
    from .models import ExecuteResponse
    from .logging_config import get_logger
except ImportError:
    from models import ExecuteResponse
    from logging_config import get_logger

logger = get_logger(__name__)


class InsightType(Enum):
    """Types of insights that can be detected."""
    TREND = "trend"
    OUTLIER = "outlier"
    SUMMARY = "summary"
    PATTERN = "pattern"
    COMPARISON = "comparison"
    DISTRIBUTION = "distribution"


@dataclass
class Insight:
    """Represents a data insight discovered through analysis."""
    type: InsightType
    message: str
    confidence: float  # 0.0 to 1.0
    column: Optional[str] = None
    supporting_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.supporting_data is None:
            self.supporting_data = {}


@dataclass
class TrendAnalysis:
    """Results of trend analysis on numeric data."""
    direction: str  # "increasing", "decreasing", "stable", "volatile"
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    change_rate: Optional[float] = None
    start_value: Optional[float] = None
    end_value: Optional[float] = None


@dataclass
class OutlierInfo:
    """Information about detected outliers."""
    value: Any
    column: str
    deviation_score: float  # How many standard deviations from mean
    is_high: bool  # True if above mean, False if below


class InsightAnalyzer:
    """
    Analyzes query results to automatically detect patterns and generate insights.
    
    This class implements requirements 2.3, 4.1, 4.2, and 4.3 by:
    - Detecting trends and patterns in data (4.1)
    - Identifying outliers and anomalies (4.1)
    - Providing data summarization (2.3)
    - Generating contextual follow-up questions (4.2, 4.3)
    """
    
    def __init__(self):
        """Initialize the InsightAnalyzer."""
        self.outlier_threshold = 1.5  # Standard deviations for outlier detection (lowered for better detection)
        self.trend_threshold = 0.6  # Minimum correlation for trend detection
        logger.info("InsightAnalyzer initialized")
    
    def analyze_trends(self, data: List[Dict[str, Any]]) -> List[Insight]:
        """
        Detect trends in numeric data columns.
        
        Args:
            data: List of data rows as dictionaries
            
        Returns:
            List[Insight]: Detected trend insights
        """
        logger.info(f"Analyzing trends in {len(data)} data rows")
        insights = []
        
        if len(data) < 3:
            logger.info("Insufficient data for trend analysis")
            return insights
        
        try:
            # Find numeric columns
            numeric_columns = self._get_numeric_columns(data)
            
            for column in numeric_columns:
                values = self._extract_numeric_values(data, column)
                
                if len(values) < 3:
                    continue
                
                trend_analysis = self._analyze_column_trend(values, column)
                
                if trend_analysis.confidence > 0.6:
                    insight = self._create_trend_insight(column, trend_analysis)
                    insights.append(insight)
                    
        except Exception as e:
            logger.error(f"Error in trend analysis: {str(e)}")
        
        logger.info(f"Detected {len(insights)} trend insights")
        return insights
    
    def identify_outliers(self, data: List[Dict[str, Any]]) -> List[Insight]:
        """
        Identify outliers in numeric data columns.
        
        Args:
            data: List of data rows as dictionaries
            
        Returns:
            List[Insight]: Detected outlier insights
        """
        logger.info(f"Identifying outliers in {len(data)} data rows")
        insights = []
        
        if len(data) < 4:  # Need at least 4 points for meaningful outlier detection
            logger.info("Insufficient data for outlier detection")
            return insights
        
        try:
            numeric_columns = self._get_numeric_columns(data)
            
            for column in numeric_columns:
                values = self._extract_numeric_values(data, column)
                
                if len(values) < 4:
                    continue
                
                outliers = self._detect_outliers(values, column)
                
                for outlier in outliers:
                    insight = self._create_outlier_insight(outlier)
                    insights.append(insight)
                    
        except Exception as e:
            logger.error(f"Error in outlier detection: {str(e)}")
        
        logger.info(f"Detected {len(insights)} outlier insights")
        return insights
    
    def summarize_data(self, data: List[Dict[str, Any]]) -> List[Insight]:
        """
        Generate summary insights about the data.
        
        Args:
            data: List of data rows as dictionaries
            
        Returns:
            List[Insight]: Summary insights
        """
        logger.info(f"Summarizing data with {len(data)} rows")
        insights = []
        
        try:
            # Basic data summary
            row_count = len(data)
            if row_count == 0:
                insights.append(Insight(
                    type=InsightType.SUMMARY,
                    message="No data found matching your criteria.",
                    confidence=1.0
                ))
                return insights
            
            # Row count insight
            if row_count == 1:
                message = "Found exactly one result."
            elif row_count < 10:
                message = f"Found {row_count} results."
            elif row_count < 100:
                message = f"Found {row_count} results - a good amount of data to analyze."
            else:
                message = f"Found {row_count:,} results - quite a substantial dataset."
            
            insights.append(Insight(
                type=InsightType.SUMMARY,
                message=message,
                confidence=1.0,
                supporting_data={"row_count": row_count}
            ))
            
            # Column analysis
            if data:
                column_count = len(data[0].keys())
                insights.append(Insight(
                    type=InsightType.SUMMARY,
                    message=f"The data includes {column_count} different attributes.",
                    confidence=1.0,
                    supporting_data={"column_count": column_count}
                ))
            
            # Numeric data summary
            numeric_insights = self._summarize_numeric_data(data)
            insights.extend(numeric_insights)
            
            # Categorical data summary
            categorical_insights = self._summarize_categorical_data(data)
            insights.extend(categorical_insights)
            
        except Exception as e:
            logger.error(f"Error in data summarization: {str(e)}")
        
        logger.info(f"Generated {len(insights)} summary insights")
        return insights
    
    def suggest_follow_up_questions(
        self, 
        data: List[Dict[str, Any]], 
        original_question: str,
        detected_insights: List[Insight] = None
    ) -> List[str]:
        """
        Generate contextual follow-up question suggestions.
        
        Args:
            data: List of data rows as dictionaries
            original_question: The user's original question
            detected_insights: Previously detected insights (optional)
            
        Returns:
            List[str]: Suggested follow-up questions
        """
        logger.info(f"Generating follow-up questions for: {original_question[:50]}...")
        suggestions = []
        
        try:
            if not data:
                return [
                    "What data do you have available to explore?",
                    "Would you like to see a summary of your entire dataset?",
                    "What time period would you like to focus on?"
                ]
            
            # Analyze data structure for suggestions
            columns = list(data[0].keys()) if data else []
            numeric_columns = self._get_numeric_columns(data)
            date_columns = self._get_date_columns(data)
            categorical_columns = [col for col in columns if col not in numeric_columns and col not in date_columns]
            
            # Time-based suggestions
            if date_columns:
                suggestions.extend([
                    "How has this changed over time?",
                    "What does the trend look like for recent periods?"
                ])
            
            # Breakdown suggestions
            if len(categorical_columns) > 0:
                suggestions.extend([
                    "How does this break down by different categories?",
                    "What are the top performers in this data?"
                ])
            
            # Comparison suggestions
            if len(data) > 1:
                suggestions.extend([
                    "Which items stand out as unusual or interesting?",
                    "How do these results compare to other periods?"
                ])
            
            # Insight-based suggestions
            if detected_insights:
                insight_suggestions = self._generate_insight_based_questions(detected_insights, original_question)
                suggestions.extend(insight_suggestions)
            
            # Analysis depth suggestions
            suggestions.extend([
                "What factors might be driving these results?",
                "Are there any patterns or correlations I should know about?"
            ])
            
            # Remove duplicates and limit to 5 suggestions
            unique_suggestions = list(dict.fromkeys(suggestions))[:5]
            
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
            unique_suggestions = [
                "What would you like to explore next?",
                "Are there specific aspects of this data that interest you?",
                "Would you like to see this data from a different angle?"
            ]
        
        logger.info(f"Generated {len(unique_suggestions)} follow-up questions")
        return unique_suggestions
    
    def analyze_query_results(self, query_results: ExecuteResponse, original_question: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of query results combining all analysis methods.
        
        Args:
            query_results: Raw query execution results
            original_question: The user's original question
            
        Returns:
            Dict containing all analysis results
        """
        logger.info("Starting comprehensive query results analysis")
        
        try:
            # Convert ExecuteResponse to list of dicts
            data = self._convert_execute_response_to_dicts(query_results)
            
            # Run all analysis methods
            trends = self.analyze_trends(data)
            outliers = self.identify_outliers(data)
            summary = self.summarize_data(data)
            
            # Combine all insights
            all_insights = trends + outliers + summary
            
            # Generate follow-up questions based on insights
            follow_up_questions = self.suggest_follow_up_questions(data, original_question, all_insights)
            
            analysis_results = {
                "trends": trends,
                "outliers": outliers,
                "summary": summary,
                "all_insights": all_insights,
                "follow_up_questions": follow_up_questions,
                "data_quality": {
                    "row_count": len(data),
                    "column_count": len(data[0].keys()) if data else 0,
                    "has_numeric_data": len(self._get_numeric_columns(data)) > 0,
                    "has_date_data": len(self._get_date_columns(data)) > 0
                }
            }
            
            logger.info(f"Analysis complete: {len(all_insights)} total insights, {len(follow_up_questions)} follow-up questions")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {
                "trends": [],
                "outliers": [],
                "summary": [],
                "all_insights": [],
                "follow_up_questions": ["What would you like to explore next?"],
                "data_quality": {"error": str(e)}
            }
    
    # Private helper methods
    
    def _convert_execute_response_to_dicts(self, query_results: ExecuteResponse) -> List[Dict[str, Any]]:
        """Convert ExecuteResponse to list of dictionaries."""
        data = []
        for row in query_results.rows:
            row_dict = {}
            for i, col in enumerate(query_results.columns):
                row_dict[col] = row[i] if i < len(row) else None
            data.append(row_dict)
        return data
    
    def _get_numeric_columns(self, data: List[Dict[str, Any]]) -> List[str]:
        """Identify numeric columns in the data."""
        if not data:
            return []
        
        numeric_columns = []
        for col in data[0].keys():
            # Check if most values in this column are numeric
            numeric_count = sum(1 for row in data if isinstance(row.get(col), (int, float)))
            if numeric_count > len(data) * 0.5:  # More than 50% numeric
                numeric_columns.append(col)
        
        return numeric_columns
    
    def _get_date_columns(self, data: List[Dict[str, Any]]) -> List[str]:
        """Identify date/time columns in the data."""
        if not data:
            return []
        
        date_columns = []
        for col in data[0].keys():
            if any(word in col.lower() for word in ["date", "time", "created", "updated"]):
                date_columns.append(col)
        
        return date_columns
    
    def _extract_numeric_values(self, data: List[Dict[str, Any]], column: str) -> List[float]:
        """Extract numeric values from a specific column."""
        values = []
        for row in data:
            val = row.get(column)
            if isinstance(val, (int, float)):
                values.append(float(val))
        return values
    
    def _analyze_column_trend(self, values: List[float], column: str) -> TrendAnalysis:
        """Analyze trend in a column of numeric values."""
        if len(values) < 3:
            return TrendAnalysis("stable", 0.0, 0.0)
        
        # Calculate simple trend using correlation with index
        indices = list(range(len(values)))
        
        # Calculate correlation coefficient
        correlation = self._calculate_correlation(indices, values)
        
        # Determine trend direction and strength
        if abs(correlation) < 0.3:
            direction = "stable"
            strength = 0.0
        elif correlation > 0.6:
            direction = "increasing"
            strength = correlation
        elif correlation < -0.6:
            direction = "decreasing"
            strength = abs(correlation)
        else:
            direction = "volatile"
            strength = abs(correlation)
        
        # Calculate change rate
        change_rate = None
        if len(values) > 1:
            change_rate = (values[-1] - values[0]) / values[0] if values[0] != 0 else 0
        
        return TrendAnalysis(
            direction=direction,
            strength=strength,
            confidence=min(strength, 1.0),
            change_rate=change_rate,
            start_value=values[0],
            end_value=values[-1]
        )
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        try:
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(xi * xi for xi in x)
            sum_y2 = sum(yi * yi for yi in y)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
            
            if denominator == 0:
                return 0.0
            
            return numerator / denominator
        except Exception:
            return 0.0
    
    def _detect_outliers(self, values: List[float], column: str) -> List[OutlierInfo]:
        """Detect outliers using statistical methods."""
        if len(values) < 4:
            return []
        
        try:
            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values)
            
            if stdev_val == 0:
                return []
            
            outliers = []
            for i, value in enumerate(values):
                deviation_score = abs(value - mean_val) / stdev_val
                
                if deviation_score > self.outlier_threshold:
                    outliers.append(OutlierInfo(
                        value=value,
                        column=column,
                        deviation_score=deviation_score,
                        is_high=value > mean_val
                    ))
            
            return outliers
            
        except Exception:
            return []
    
    def _create_trend_insight(self, column: str, trend_analysis: TrendAnalysis) -> Insight:
        """Create an insight from trend analysis."""
        column_display = column.replace('_', ' ').title()
        
        if trend_analysis.direction == "increasing":
            message = f"{column_display} shows a clear upward trend."
        elif trend_analysis.direction == "decreasing":
            message = f"{column_display} shows a declining trend."
        elif trend_analysis.direction == "volatile":
            message = f"{column_display} shows significant variation."
        else:
            message = f"{column_display} remains relatively stable."
        
        return Insight(
            type=InsightType.TREND,
            message=message,
            confidence=trend_analysis.confidence,
            column=column,
            supporting_data={
                "direction": trend_analysis.direction,
                "strength": trend_analysis.strength,
                "change_rate": trend_analysis.change_rate
            }
        )
    
    def _create_outlier_insight(self, outlier: OutlierInfo) -> Insight:
        """Create an insight from outlier detection."""
        column_display = outlier.column.replace('_', ' ').title()
        direction = "high" if outlier.is_high else "low"
        
        message = f"Found an unusually {direction} {column_display.lower()} value: {outlier.value}."
        
        return Insight(
            type=InsightType.OUTLIER,
            message=message,
            confidence=min(outlier.deviation_score / 3.0, 1.0),  # Scale confidence
            column=outlier.column,
            supporting_data={
                "value": outlier.value,
                "deviation_score": outlier.deviation_score,
                "is_high": outlier.is_high
            }
        )
    
    def _summarize_numeric_data(self, data: List[Dict[str, Any]]) -> List[Insight]:
        """Generate summary insights for numeric columns."""
        insights = []
        numeric_columns = self._get_numeric_columns(data)
        
        for column in numeric_columns[:3]:  # Limit to first 3 numeric columns
            values = self._extract_numeric_values(data, column)
            
            if len(values) < 2:
                continue
            
            try:
                total = sum(values)
                avg = statistics.mean(values)
                max_val = max(values)
                min_val = min(values)
                
                column_display = column.replace('_', ' ').title()
                
                # Generate appropriate summary based on column name and values
                if "revenue" in column.lower() or "sales" in column.lower():
                    message = f"Total {column_display.lower()} is ${total:,.2f} with an average of ${avg:,.2f}."
                elif "count" in column.lower() or "quantity" in column.lower():
                    message = f"{column_display} ranges from {int(min_val)} to {int(max_val)}, averaging {avg:.1f}."
                else:
                    message = f"{column_display} ranges from {min_val:.2f} to {max_val:.2f}."
                
                insights.append(Insight(
                    type=InsightType.SUMMARY,
                    message=message,
                    confidence=0.9,
                    column=column,
                    supporting_data={
                        "min": min_val,
                        "max": max_val,
                        "avg": avg,
                        "total": total
                    }
                ))
                
            except Exception as e:
                logger.error(f"Error summarizing numeric column {column}: {str(e)}")
        
        return insights
    
    def _summarize_categorical_data(self, data: List[Dict[str, Any]]) -> List[Insight]:
        """Generate summary insights for categorical columns."""
        insights = []
        
        if not data:
            return insights
        
        numeric_columns = self._get_numeric_columns(data)
        date_columns = self._get_date_columns(data)
        categorical_columns = [col for col in data[0].keys() 
                             if col not in numeric_columns and col not in date_columns]
        
        for column in categorical_columns[:2]:  # Limit to first 2 categorical columns
            values = [str(row.get(column, "")).strip() for row in data if row.get(column) is not None]
            
            if len(values) < 2:
                continue
            
            unique_values = set(values)
            column_display = column.replace('_', ' ').title()
            
            if len(unique_values) == len(values):
                message = f"Each row has a unique {column_display.lower()}."
            elif len(unique_values) < len(values) * 0.5:
                message = f"Data includes {len(unique_values)} different {column_display.lower()} categories."
            else:
                message = f"{column_display} shows good variety with {len(unique_values)} different values."
            
            insights.append(Insight(
                type=InsightType.SUMMARY,
                message=message,
                confidence=0.8,
                column=column,
                supporting_data={
                    "unique_count": len(unique_values),
                    "total_count": len(values),
                    "uniqueness_ratio": len(unique_values) / len(values)
                }
            ))
        
        return insights
    
    def _generate_insight_based_questions(self, insights: List[Insight], original_question: str) -> List[str]:
        """Generate follow-up questions based on detected insights."""
        questions = []
        
        # Questions based on trends
        trend_insights = [i for i in insights if i.type == InsightType.TREND]
        if trend_insights:
            questions.append("What might be causing this trend?")
            questions.append("How does this trend compare to previous periods?")
        
        # Questions based on outliers
        outlier_insights = [i for i in insights if i.type == InsightType.OUTLIER]
        if outlier_insights:
            questions.append("What makes these outliers different from the rest?")
            questions.append("Are these outliers expected or concerning?")
        
        # Questions based on data patterns
        if len(insights) > 3:
            questions.append("Are there any correlations between these patterns?")
        
        return questions[:3]  # Limit to 3 insight-based questions