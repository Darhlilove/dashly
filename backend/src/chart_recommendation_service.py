"""
Chart recommendation service for automatic dashboard updates.

This service analyzes query results and determines appropriate chart configurations
for automatic dashboard visualization during chat interactions.
"""

from typing import Optional, Dict, Any, List, Set
from datetime import datetime
import re

try:
    from .models import ExecuteResponse, ChartConfig
    from .logging_config import get_logger
except ImportError:
    from models import ExecuteResponse, ChartConfig
    from logging_config import get_logger

logger = get_logger(__name__)


class ChartRecommendationService:
    """
    Service for analyzing query results and recommending appropriate chart types
    for automatic dashboard updates during chat interactions.
    """
    
    def __init__(self):
        """Initialize the chart recommendation service."""
        logger.info("ChartRecommendationService initialized")
    
    def should_create_visualization(self, query_results: ExecuteResponse, user_question: str) -> bool:
        """
        Determine if a visualization should be created based on query results and user question.
        
        Args:
            query_results: Results from SQL query execution
            user_question: The user's original natural language question
            
        Returns:
            bool: True if a visualization should be created, False otherwise
        """
        try:
            # Don't create visualizations for empty results
            if not query_results.rows or len(query_results.rows) == 0:
                logger.debug("No visualization: Empty results")
                return False
            
            # Don't create visualizations for single-value results (unless it's a meaningful metric)
            if len(query_results.rows) == 1 and len(query_results.columns) == 1:
                # Check if it's a meaningful single metric
                question_lower = user_question.lower()
                metric_keywords = ['total', 'sum', 'count', 'average', 'avg', 'max', 'min', 'revenue', 'sales']
                if any(keyword in question_lower for keyword in metric_keywords):
                    logger.debug("Single metric detected, creating visualization")
                    return True
                else:
                    logger.debug("No visualization: Single non-metric value")
                    return False
            
            # Don't create visualizations for very large result sets (table view is better)
            if len(query_results.rows) > 100:
                logger.debug("No visualization: Too many rows for effective charting")
                return False
            
            # Check if the question implies visualization intent
            question_lower = user_question.lower()
            visualization_keywords = [
                'show', 'display', 'chart', 'graph', 'plot', 'visualize',
                'trend', 'over time', 'by month', 'by year', 'by category',
                'compare', 'comparison', 'breakdown', 'distribution'
            ]
            
            has_viz_intent = any(keyword in question_lower for keyword in visualization_keywords)
            
            # Analyze data structure to determine if it's suitable for visualization
            column_analysis = self._analyze_columns(query_results)
            has_suitable_structure = self._has_suitable_structure_for_charts(column_analysis)
            
            # Create visualization if either there's explicit intent or suitable structure
            should_create = has_viz_intent or has_suitable_structure
            
            logger.debug(f"Visualization decision: intent={has_viz_intent}, structure={has_suitable_structure}, result={should_create}")
            return should_create
            
        except Exception as e:
            logger.error(f"Error determining visualization need: {str(e)}")
            return False
    
    def recommend_chart_config(self, query_results: ExecuteResponse, user_question: str) -> Optional[ChartConfig]:
        """
        Recommend an appropriate chart configuration based on query results and user question.
        
        Args:
            query_results: Results from SQL query execution
            user_question: The user's original natural language question
            
        Returns:
            Optional[ChartConfig]: Recommended chart configuration, or None if no chart is suitable
        """
        try:
            if not self.should_create_visualization(query_results, user_question):
                return None
            
            # Analyze the data structure
            column_analysis = self._analyze_columns(query_results)
            
            # Generate chart title from user question
            chart_title = self._generate_chart_title(user_question, query_results)
            
            # Apply chart selection rules
            chart_config = self._select_chart_type(column_analysis, query_results, user_question)
            
            if chart_config:
                chart_config.title = chart_title
                logger.info(f"Recommended chart: {chart_config.type} with title '{chart_title}'")
            
            return chart_config
            
        except Exception as e:
            logger.error(f"Error recommending chart config: {str(e)}")
            return None
    
    def _analyze_columns(self, query_results: ExecuteResponse) -> List[Dict[str, Any]]:
        """
        Analyze column types and characteristics from query results.
        
        Args:
            query_results: Results from SQL query execution
            
        Returns:
            List[Dict[str, Any]]: Analysis of each column including type and characteristics
        """
        analysis = []
        
        for i, column_name in enumerate(query_results.columns):
            # Extract column values
            column_values = [row[i] for row in query_results.rows if row[i] is not None]
            
            if not column_values:
                analysis.append({
                    'name': column_name,
                    'type': 'empty',
                    'unique_count': 0,
                    'sample_values': []
                })
                continue
            
            # Determine column type
            column_type = self._determine_column_type(column_values)
            unique_values = set(column_values)
            
            analysis.append({
                'name': column_name,
                'type': column_type,
                'unique_count': len(unique_values),
                'sample_values': list(unique_values)[:10],
                'total_values': len(column_values)
            })
        
        return analysis
    
    def _determine_column_type(self, values: List[Any]) -> str:
        """
        Determine the type of a column based on its values.
        
        Args:
            values: List of column values
            
        Returns:
            str: Column type ('numeric', 'datetime', 'categorical', 'text')
        """
        if not values:
            return 'empty'
        
        # Check for datetime
        if self._is_datetime_column(values):
            return 'datetime'
        
        # Check for numeric
        if self._is_numeric_column(values):
            return 'numeric'
        
        # Check for categorical (limited unique values or string values that repeat)
        unique_values = set(values)
        
        # If we have string values and reasonable number of unique values, treat as categorical
        if len(unique_values) <= 20:
            # Check if values are mostly strings (non-numeric)
            string_count = sum(1 for v in values if isinstance(v, str) and not self._is_numeric_string(v))
            if string_count / len(values) >= 0.5:  # At least 50% are non-numeric strings
                return 'categorical'
        
        # Also check for repeated values (even if more than 20 unique)
        if len(unique_values) < len(values) and len(unique_values) <= 50:
            return 'categorical'
        
        return 'text'
    
    def _is_numeric_string(self, value: str) -> bool:
        """Check if a string value represents a number."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _is_datetime_column(self, values: List[Any]) -> bool:
        """Check if column contains datetime values."""
        if not values:
            return False
        
        sample_size = min(len(values), 10)
        date_count = 0
        
        for value in values[:sample_size]:
            if isinstance(value, str):
                # Check common date patterns
                date_patterns = [
                    r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                    r'^\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                    r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO datetime
                    r'^\d{4}-\d{2}',  # YYYY-MM
                ]
                
                if any(re.match(pattern, value) for pattern in date_patterns):
                    date_count += 1
                    continue
                
                # Try parsing as date
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                    date_count += 1
                except:
                    try:
                        datetime.strptime(value, '%Y-%m-%d')
                        date_count += 1
                    except:
                        pass
        
        return date_count / sample_size >= 0.8
    
    def _is_numeric_column(self, values: List[Any]) -> bool:
        """Check if column contains numeric values."""
        if not values:
            return False
        
        sample_size = min(len(values), 10)
        numeric_count = 0
        
        for value in values[:sample_size]:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_count += 1
            elif isinstance(value, str):
                try:
                    float(value)
                    numeric_count += 1
                except ValueError:
                    pass
        
        return numeric_count / sample_size >= 0.8
    
    def _has_suitable_structure_for_charts(self, column_analysis: List[Dict[str, Any]]) -> bool:
        """
        Determine if the data structure is suitable for chart visualization.
        
        Args:
            column_analysis: Analysis of columns from _analyze_columns
            
        Returns:
            bool: True if data structure is suitable for charts
        """
        if len(column_analysis) < 2:
            return False
        
        numeric_cols = [col for col in column_analysis if col['type'] == 'numeric']
        categorical_cols = [col for col in column_analysis if col['type'] == 'categorical']
        datetime_cols = [col for col in column_analysis if col['type'] == 'datetime']
        
        # Good for charts if we have:
        # - At least one numeric column AND (one categorical OR one datetime)
        # - OR multiple numeric columns
        return (
            (len(numeric_cols) >= 1 and (len(categorical_cols) >= 1 or len(datetime_cols) >= 1)) or
            len(numeric_cols) >= 2
        )
    
    def _select_chart_type(self, column_analysis: List[Dict[str, Any]], query_results: ExecuteResponse, user_question: str) -> Optional[ChartConfig]:
        """
        Select appropriate chart type based on column analysis and user question.
        
        Args:
            column_analysis: Analysis of columns
            query_results: Query results
            user_question: User's original question
            
        Returns:
            Optional[ChartConfig]: Chart configuration or None
        """
        numeric_cols = [col for col in column_analysis if col['type'] == 'numeric']
        categorical_cols = [col for col in column_analysis if col['type'] == 'categorical']
        datetime_cols = [col for col in column_analysis if col['type'] == 'datetime']
        
        question_lower = user_question.lower()
        
        # Rule 1: Line chart for time series data
        if len(datetime_cols) >= 1 and len(numeric_cols) >= 1:
            return ChartConfig(
                type="line",
                x_axis=datetime_cols[0]['name'],
                y_axis=numeric_cols[0]['name']
            )
        
        # Rule 2: Pie chart for distribution questions with small categories
        if ('distribution' in question_lower or 'breakdown' in question_lower or 'share' in question_lower):
            suitable_categorical = [col for col in categorical_cols if col['unique_count'] <= 8]
            if suitable_categorical and numeric_cols:
                return ChartConfig(
                    type="pie",
                    x_axis=suitable_categorical[0]['name'],
                    y_axis=numeric_cols[0]['name']
                )
        
        # Rule 3: Bar chart for categorical comparisons
        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            # Prefer categorical columns with reasonable number of categories
            best_categorical = min(categorical_cols, key=lambda x: x['unique_count'] if x['unique_count'] <= 20 else 100)
            if best_categorical['unique_count'] <= 20:
                # Additional check: make sure we're not charting text descriptions
                if not self._is_text_description_column(best_categorical):
                    # Also check that we're not using ID columns as categorical
                    if not self._is_id_column(best_categorical):
                        return ChartConfig(
                            type="bar",
                            x_axis=best_categorical['name'],
                            y_axis=numeric_cols[0]['name']
                        )
        
        # Rule 4: Line chart for numeric trends (even without explicit datetime)
        if len(numeric_cols) >= 2:
            # Avoid using ID columns for charting
            suitable_numeric = [col for col in numeric_cols if not self._is_id_column(col)]
            if len(suitable_numeric) >= 2:
                return ChartConfig(
                    type="line",
                    x_axis=suitable_numeric[0]['name'],
                    y_axis=suitable_numeric[1]['name']
                )
        
        # Rule 5: Single metric display for aggregated results
        if len(query_results.rows) == 1 and len(numeric_cols) == 1:
            metric_keywords = ['total', 'sum', 'count', 'average', 'avg', 'max', 'min']
            if any(keyword in question_lower for keyword in metric_keywords):
                return ChartConfig(
                    type="bar",  # Single bar for metric display
                    x_axis=query_results.columns[0] if len(query_results.columns) == 1 else "Metric",
                    y_axis=numeric_cols[0]['name']
                )
        
        # Default: table view
        return None
    
    def _generate_chart_title(self, user_question: str, query_results: ExecuteResponse) -> str:
        """
        Generate an appropriate chart title based on the user question.
        
        Args:
            user_question: User's original question
            query_results: Query results for context
            
        Returns:
            str: Generated chart title
        """
        # Clean up the question to make it title-like
        title = user_question.strip()
        
        # Remove question words from the beginning, but preserve meaningful questions
        question_starters = ['show me', 'what is', 'what are', 'can you show', 'display']
        title_lower = title.lower()
        
        # Don't remove "how much" or "how many" as they are meaningful for chart titles
        for starter in question_starters:
            if title_lower.startswith(starter):
                title = title[len(starter):].strip()
                break
        
        # Remove "the" from the beginning if present
        if title.lower().startswith('the '):
            title = title[4:]
        
        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]
        
        # Remove trailing question mark only for certain question types
        if title.endswith('?') and not title.lower().startswith(('how much', 'how many')):
            title = title[:-1]
        
        # Limit length
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title or "Data Visualization"
    
    def _is_text_description_column(self, column_analysis: Dict[str, Any]) -> bool:
        """
        Check if a column appears to contain text descriptions rather than categorical data.
        
        Args:
            column_analysis: Column analysis dictionary
            
        Returns:
            bool: True if column appears to be text descriptions
        """
        column_name = column_analysis['name'].lower()
        
        # Check for common description column names
        description_indicators = ['description', 'comment', 'note', 'detail', 'summary', 'text']
        if any(indicator in column_name for indicator in description_indicators):
            return True
        
        # Check sample values for description-like content
        sample_values = column_analysis.get('sample_values', [])
        if sample_values:
            # If values are long strings (likely descriptions)
            string_values = [str(val) for val in sample_values if isinstance(val, str)]
            if string_values:
                avg_length = sum(len(val) for val in string_values) / len(string_values)
                if avg_length > 15:  # Average length > 15 characters suggests descriptions
                    return True
        
        return False
    
    def _is_id_column(self, column_analysis: Dict[str, Any]) -> bool:
        """
        Check if a column appears to be an ID column.
        
        Args:
            column_analysis: Column analysis dictionary
            
        Returns:
            bool: True if column appears to be an ID column
        """
        column_name = column_analysis['name'].lower()
        
        # Check for common ID column names
        id_indicators = ['id', 'key', 'index', 'pk', 'primary']
        if any(indicator in column_name for indicator in id_indicators):
            return True
        
        return False