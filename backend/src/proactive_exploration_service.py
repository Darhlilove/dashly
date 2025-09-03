"""
Proactive Data Exploration Service for generating automatic question suggestions and insights.

This service implements proactive data exploration features as specified in requirements 4.3, 4.4, and 7.3:
- Automatic initial question suggestions when data is uploaded
- Logic to suggest interesting questions based on available data structure
- Proactive insights when interesting patterns are detected in responses
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass

try:
    from .models import ExecuteResponse, DatabaseSchema, TableSchema, ColumnInfo
    from .logging_config import get_logger
    from .database_manager import DatabaseManager
    from .schema_service import SchemaService
    from .llm_service import LLMService
except ImportError:
    from models import ExecuteResponse, DatabaseSchema, TableSchema, ColumnInfo
    from logging_config import get_logger
    from database_manager import DatabaseManager
    from schema_service import SchemaService
    from llm_service import LLMService

logger = get_logger(__name__)


@dataclass
class DataCharacteristics:
    """Characteristics of a dataset for generating relevant questions."""
    has_time_data: bool
    has_financial_data: bool
    has_categorical_data: bool
    has_user_data: bool
    has_geographic_data: bool
    row_count: int
    column_count: int
    numeric_columns: List[str]
    date_columns: List[str]
    categorical_columns: List[str]
    primary_entities: List[str]  # Main business entities (customers, products, etc.)


@dataclass
class QuestionSuggestion:
    """A suggested question for data exploration."""
    question: str
    category: str  # "overview", "trends", "comparisons", "details"
    priority: int  # 1-5, higher is more important
    reasoning: str  # Why this question is suggested


@dataclass
class ProactiveInsight:
    """A proactive insight discovered in data patterns."""
    message: str
    insight_type: str  # "pattern", "anomaly", "trend", "opportunity"
    confidence: float  # 0.0 to 1.0
    suggested_actions: List[str]


class ProactiveExplorationService:
    """
    Service for generating proactive data exploration suggestions and insights.
    
    This service implements requirements 4.3, 4.4, and 7.3 by:
    - Generating initial question suggestions when data is uploaded (4.3)
    - Suggesting interesting questions based on data structure (4.4)
    - Creating proactive insights from response patterns (7.3)
    """
    
    def __init__(self, db_manager: DatabaseManager = None, schema_service: SchemaService = None, llm_service: LLMService = None):
        """
        Initialize ProactiveExplorationService.
        
        Args:
            db_manager: DatabaseManager instance for data access
            schema_service: SchemaService instance for schema analysis
            llm_service: LLMService instance for intelligent suggestions
        """
        self.db_manager = db_manager
        self.schema_service = schema_service
        self.llm_service = llm_service
        logger.info("ProactiveExplorationService initialized")
    
    def generate_initial_questions(self, table_name: str = None) -> List[QuestionSuggestion]:
        """
        Generate initial question suggestions when data is uploaded.
        
        Args:
            table_name: Optional specific table name to analyze
            
        Returns:
            List[QuestionSuggestion]: List of suggested questions for initial exploration
        """
        logger.info(f"Generating initial questions for table: {table_name or 'all tables'}")
        
        try:
            # Analyze data characteristics
            characteristics = self._analyze_data_characteristics(table_name)
            
            # Generate questions based on characteristics
            suggestions = []
            
            # Always include basic overview questions
            suggestions.extend(self._generate_overview_questions(characteristics))
            
            # Add specific questions based on data types
            if characteristics.has_time_data:
                suggestions.extend(self._generate_time_based_questions(characteristics))
            
            if characteristics.has_financial_data:
                suggestions.extend(self._generate_financial_questions(characteristics))
            
            if characteristics.has_categorical_data:
                suggestions.extend(self._generate_categorical_questions(characteristics))
            
            if characteristics.has_user_data:
                suggestions.extend(self._generate_user_analysis_questions(characteristics))
            
            # Sort by priority and limit to top suggestions
            suggestions.sort(key=lambda x: x.priority, reverse=True)
            top_suggestions = suggestions[:6]  # Limit to 6 initial questions
            
            # If no suggestions were generated, return fallback questions
            if not top_suggestions:
                top_suggestions = self._generate_fallback_questions()
            
            logger.info(f"Generated {len(top_suggestions)} initial question suggestions")
            return top_suggestions
            
        except Exception as e:
            logger.error(f"Error generating initial questions: {str(e)}")
            return self._generate_fallback_questions()
    
    def suggest_questions_from_structure(self, schema_info: Dict[str, Any]) -> List[QuestionSuggestion]:
        """
        Suggest interesting questions based on available data structure.
        
        Args:
            schema_info: Database schema information
            
        Returns:
            List[QuestionSuggestion]: Questions suggested based on data structure
        """
        logger.info("Generating questions based on data structure")
        
        try:
            suggestions = []
            
            if "tables" not in schema_info:
                return self._generate_fallback_questions()
            
            for table_name, table_info in schema_info["tables"].items():
                # Analyze table structure
                columns = table_info.get("columns", [])
                sample_data = table_info.get("sample_rows", [])
                
                # Generate structure-based questions
                structure_questions = self._analyze_table_structure(table_name, columns, sample_data)
                suggestions.extend(structure_questions)
            
            # Remove duplicates and sort by priority
            unique_suggestions = self._deduplicate_suggestions(suggestions)
            unique_suggestions.sort(key=lambda x: x.priority, reverse=True)
            
            logger.info(f"Generated {len(unique_suggestions)} structure-based questions")
            return unique_suggestions[:8]  # Limit to 8 questions
            
        except Exception as e:
            logger.error(f"Error generating structure-based questions: {str(e)}")
            return self._generate_fallback_questions()
    
    def detect_proactive_insights(self, query_results: ExecuteResponse, original_question: str) -> List[ProactiveInsight]:
        """
        Create proactive insights when interesting patterns are detected in responses.
        
        Args:
            query_results: Results from query execution
            original_question: The user's original question
            
        Returns:
            List[ProactiveInsight]: Proactive insights discovered in the data
        """
        logger.info(f"Detecting proactive insights for question: {original_question[:50]}...")
        
        try:
            insights = []
            
            # Convert results to analyzable format
            data = self._convert_results_to_data(query_results)
            
            if not data:
                return insights
            
            # Detect various types of patterns
            insights.extend(self._detect_anomaly_patterns(data, original_question))
            insights.extend(self._detect_trend_patterns(data, original_question))
            insights.extend(self._detect_opportunity_patterns(data, original_question))
            insights.extend(self._detect_correlation_patterns(data, original_question))
            
            # Sort by confidence and limit results
            insights.sort(key=lambda x: x.confidence, reverse=True)
            top_insights = insights[:4]  # Limit to 4 proactive insights
            
            logger.info(f"Detected {len(top_insights)} proactive insights")
            return top_insights
            
        except Exception as e:
            logger.error(f"Error detecting proactive insights: {str(e)}")
            return []
    
    def generate_contextual_suggestions(self, conversation_history: List[Dict[str, Any]]) -> List[QuestionSuggestion]:
        """
        Generate contextual question suggestions based on conversation history.
        
        Args:
            conversation_history: Previous questions and responses in the conversation
            
        Returns:
            List[QuestionSuggestion]: Contextual question suggestions
        """
        logger.info("Generating contextual suggestions from conversation history")
        
        try:
            if not conversation_history:
                return self.generate_initial_questions()
            
            suggestions = []
            
            # Analyze conversation patterns
            recent_topics = self._extract_conversation_topics(conversation_history)
            question_types = self._analyze_question_types(conversation_history)
            
            # Generate suggestions based on conversation flow
            if "overview" in question_types and "details" not in question_types:
                suggestions.extend(self._generate_drill_down_questions(recent_topics))
            
            if "trends" not in question_types and any("time" in topic.lower() for topic in recent_topics):
                suggestions.extend(self._generate_trend_questions(recent_topics))
            
            if "comparisons" not in question_types:
                suggestions.extend(self._generate_comparison_questions(recent_topics))
            
            # Always add breakdown questions for financial topics
            if "financial" in recent_topics:
                suggestions.append(QuestionSuggestion(
                    question="How does this break down by different categories?",
                    category="comparisons",
                    priority=4,
                    reasoning="Financial data often benefits from categorical breakdown"
                ))
            
            # Sort and limit suggestions
            suggestions.sort(key=lambda x: x.priority, reverse=True)
            
            logger.info(f"Generated {len(suggestions)} contextual suggestions")
            return suggestions[:5]  # Limit to 5 contextual suggestions
            
        except Exception as e:
            logger.error(f"Error generating contextual suggestions: {str(e)}")
            return []
    
    # Private helper methods
    
    def _analyze_data_characteristics(self, table_name: str = None) -> DataCharacteristics:
        """Analyze characteristics of the available data."""
        try:
            if self.schema_service:
                schema_info = self.schema_service.get_all_tables_schema()
            else:
                # Fallback to basic analysis
                schema_info = {"tables": {}}
            
            # Initialize characteristics
            has_time_data = False
            has_financial_data = False
            has_categorical_data = False
            has_user_data = False
            has_geographic_data = False
            total_rows = 0
            total_columns = 0
            all_numeric_columns = []
            all_date_columns = []
            all_categorical_columns = []
            primary_entities = []
            
            # Analyze each table
            for t_name, table_info in schema_info.get("tables", {}).items():
                if table_name and t_name != table_name:
                    continue
                
                columns = table_info.get("columns", [])
                total_columns += len(columns)
                total_rows += table_info.get("row_count", 0)
                
                for col in columns:
                    col_name = col.get("name", "").lower()
                    col_type = col.get("type", "").lower()
                    
                    # Detect data types
                    if any(word in col_name for word in ["date", "time", "created", "updated"]):
                        has_time_data = True
                        all_date_columns.append(col["name"])
                    
                    if any(word in col_name for word in ["revenue", "sales", "cost", "price", "profit", "amount"]):
                        has_financial_data = True
                        all_numeric_columns.append(col["name"])
                    
                    if any(word in col_name for word in ["user", "customer", "client", "member"]):
                        has_user_data = True
                        primary_entities.append("users")
                    
                    if any(word in col_name for word in ["country", "state", "city", "region", "location"]):
                        has_geographic_data = True
                        all_categorical_columns.append(col["name"])
                    
                    if "int" in col_type or "float" in col_type or "decimal" in col_type:
                        all_numeric_columns.append(col["name"])
                    elif "varchar" in col_type or "text" in col_type:
                        all_categorical_columns.append(col["name"])
                        has_categorical_data = True
            
            return DataCharacteristics(
                has_time_data=has_time_data,
                has_financial_data=has_financial_data,
                has_categorical_data=has_categorical_data,
                has_user_data=has_user_data,
                has_geographic_data=has_geographic_data,
                row_count=total_rows,
                column_count=total_columns,
                numeric_columns=list(set(all_numeric_columns)),
                date_columns=list(set(all_date_columns)),
                categorical_columns=list(set(all_categorical_columns)),
                primary_entities=list(set(primary_entities))
            )
            
        except Exception as e:
            logger.error(f"Error analyzing data characteristics: {str(e)}")
            # Return default characteristics
            return DataCharacteristics(
                has_time_data=False,
                has_financial_data=False,
                has_categorical_data=False,
                has_user_data=False,
                has_geographic_data=False,
                row_count=0,
                column_count=0,
                numeric_columns=[],
                date_columns=[],
                categorical_columns=[],
                primary_entities=[]
            )
    
    def _generate_overview_questions(self, characteristics: DataCharacteristics) -> List[QuestionSuggestion]:
        """Generate basic overview questions."""
        questions = []
        
        if characteristics.row_count > 0:
            questions.append(QuestionSuggestion(
                question="What does my data look like overall?",
                category="overview",
                priority=5,
                reasoning="Essential starting point for data exploration"
            ))
            
            questions.append(QuestionSuggestion(
                question="How much data do I have in total?",
                category="overview", 
                priority=4,
                reasoning="Understanding data volume is important for analysis planning"
            ))
        
        if characteristics.column_count > 3:
            questions.append(QuestionSuggestion(
                question="What are the main categories in my data?",
                category="overview",
                priority=4,
                reasoning="Helps understand data structure and available dimensions"
            ))
        
        return questions
    
    def _generate_time_based_questions(self, characteristics: DataCharacteristics) -> List[QuestionSuggestion]:
        """Generate questions for time-series data."""
        questions = []
        
        questions.append(QuestionSuggestion(
            question="How has activity changed over time?",
            category="trends",
            priority=5,
            reasoning="Time-based trends are crucial for understanding business patterns"
        ))
        
        questions.append(QuestionSuggestion(
            question="What does the recent trend look like?",
            category="trends",
            priority=4,
            reasoning="Recent trends indicate current business direction"
        ))
        
        if characteristics.has_financial_data:
            questions.append(QuestionSuggestion(
                question="How have revenues changed month by month?",
                category="trends",
                priority=5,
                reasoning="Financial trends over time are key business metrics"
            ))
        
        return questions
    
    def _generate_financial_questions(self, characteristics: DataCharacteristics) -> List[QuestionSuggestion]:
        """Generate questions for financial data."""
        questions = []
        
        questions.append(QuestionSuggestion(
            question="What are my total sales or revenue?",
            category="overview",
            priority=5,
            reasoning="Total financial performance is a primary business concern"
        ))
        
        questions.append(QuestionSuggestion(
            question="Which are my top performing categories?",
            category="comparisons",
            priority=4,
            reasoning="Identifying top performers helps focus business efforts"
        ))
        
        if characteristics.has_time_data:
            questions.append(QuestionSuggestion(
                question="What was my best month for sales?",
                category="details",
                priority=4,
                reasoning="Peak performance periods provide insights for replication"
            ))
        
        return questions
    
    def _generate_categorical_questions(self, characteristics: DataCharacteristics) -> List[QuestionSuggestion]:
        """Generate questions for categorical data."""
        questions = []
        
        questions.append(QuestionSuggestion(
            question="How does performance break down by category?",
            category="comparisons",
            priority=4,
            reasoning="Category breakdowns reveal performance patterns"
        ))
        
        questions.append(QuestionSuggestion(
            question="Which categories have the most activity?",
            category="comparisons",
            priority=3,
            reasoning="Activity distribution shows business focus areas"
        ))
        
        return questions
    
    def _generate_user_analysis_questions(self, characteristics: DataCharacteristics) -> List[QuestionSuggestion]:
        """Generate questions for user/customer data."""
        questions = []
        
        questions.append(QuestionSuggestion(
            question="How many active users or customers do I have?",
            category="overview",
            priority=4,
            reasoning="User base size is a fundamental business metric"
        ))
        
        if characteristics.has_time_data:
            questions.append(QuestionSuggestion(
                question="How is user activity trending over time?",
                category="trends",
                priority=4,
                reasoning="User growth trends indicate business health"
            ))
        
        return questions
    
    def _analyze_table_structure(self, table_name: str, columns: List[Dict], sample_data: List[Dict]) -> List[QuestionSuggestion]:
        """Analyze table structure to generate relevant questions."""
        questions = []
        
        # Analyze column names for business context
        column_names = [col.get("name", "").lower() for col in columns]
        
        # Generate questions based on detected patterns
        if any("revenue" in name or "sales" in name for name in column_names):
            questions.append(QuestionSuggestion(
                question=f"What are the total sales in the {table_name} data?",
                category="overview",
                priority=4,
                reasoning=f"Sales data detected in {table_name} table"
            ))
        
        if any("date" in name or "time" in name for name in column_names):
            questions.append(QuestionSuggestion(
                question=f"How has {table_name} activity changed over time?",
                category="trends",
                priority=4,
                reasoning=f"Time data detected in {table_name} table"
            ))
        
        if any("category" in name or "type" in name for name in column_names):
            questions.append(QuestionSuggestion(
                question=f"How does {table_name} break down by category?",
                category="comparisons",
                priority=3,
                reasoning=f"Categorical data detected in {table_name} table"
            ))
        
        return questions
    
    def _convert_results_to_data(self, query_results: ExecuteResponse) -> List[Dict[str, Any]]:
        """Convert ExecuteResponse to list of dictionaries for analysis."""
        data = []
        try:
            for row in query_results.rows:
                row_dict = {}
                for i, col in enumerate(query_results.columns):
                    row_dict[col] = row[i] if i < len(row) else None
                data.append(row_dict)
        except Exception as e:
            logger.error(f"Error converting results to data: {str(e)}")
        return data
    
    def _detect_anomaly_patterns(self, data: List[Dict[str, Any]], original_question: str) -> List[ProactiveInsight]:
        """Detect anomaly patterns in the data."""
        insights = []
        
        try:
            if len(data) < 3:
                return insights
            
            # Look for numeric outliers
            for col in data[0].keys():
                values = [row.get(col) for row in data if isinstance(row.get(col), (int, float))]
                
                if len(values) < 3:
                    continue
                
                # Simple outlier detection
                mean_val = sum(values) / len(values)
                max_val = max(values)
                
                if max_val > mean_val * 2:  # Value is 2x the average
                    insights.append(ProactiveInsight(
                        message=f"There's an unusually high {col.replace('_', ' ')} value that might be worth investigating.",
                        insight_type="anomaly",
                        confidence=0.8,
                        suggested_actions=[
                            f"Investigate what caused the high {col.replace('_', ' ')} value",
                            "Check if this represents an opportunity or an error",
                            "Look at similar patterns in other time periods"
                        ]
                    ))
        
        except Exception as e:
            logger.error(f"Error detecting anomaly patterns: {str(e)}")
        
        return insights
    
    def _detect_trend_patterns(self, data: List[Dict[str, Any]], original_question: str) -> List[ProactiveInsight]:
        """Detect trend patterns in the data."""
        insights = []
        
        try:
            if len(data) < 4:
                return insights
            
            # Look for increasing/decreasing trends
            for col in data[0].keys():
                values = [row.get(col) for row in data if isinstance(row.get(col), (int, float))]
                
                if len(values) < 4:
                    continue
                
                # Simple trend detection
                increasing = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
                decreasing = sum(1 for i in range(1, len(values)) if values[i] < values[i-1])
                
                if increasing >= len(values) * 0.7:  # 70% or more increasing
                    insights.append(ProactiveInsight(
                        message=f"Your {col.replace('_', ' ')} shows a strong upward trend - this could indicate growing success.",
                        insight_type="trend",
                        confidence=0.9,
                        suggested_actions=[
                            "Analyze what's driving this positive trend",
                            "Consider how to sustain or accelerate this growth",
                            "Look for similar patterns in related metrics"
                        ]
                    ))
                elif decreasing >= len(values) * 0.7:  # 70% or more decreasing
                    insights.append(ProactiveInsight(
                        message=f"Your {col.replace('_', ' ')} shows a declining trend that might need attention.",
                        insight_type="trend",
                        confidence=0.9,
                        suggested_actions=[
                            "Investigate potential causes of the decline",
                            "Consider corrective actions or interventions",
                            "Compare with industry benchmarks or historical data"
                        ]
                    ))
        
        except Exception as e:
            logger.error(f"Error detecting trend patterns: {str(e)}")
        
        return insights
    
    def _detect_opportunity_patterns(self, data: List[Dict[str, Any]], original_question: str) -> List[ProactiveInsight]:
        """Detect opportunity patterns in the data."""
        insights = []
        
        try:
            # Look for underperforming categories or segments
            if len(data) > 5:
                # Check for distribution imbalances
                categorical_cols = [col for col in data[0].keys() 
                                 if not isinstance(data[0].get(col), (int, float))]
                
                for col in categorical_cols[:2]:  # Check first 2 categorical columns
                    values = [str(row.get(col, "")) for row in data if row.get(col) is not None]
                    unique_values = set(values)
                    
                    if len(unique_values) > 2 and len(values) > 0:
                        # Check for imbalanced distribution
                        value_counts = {val: values.count(val) for val in unique_values}
                        max_count = max(value_counts.values())
                        min_count = min(value_counts.values())
                        
                        if max_count > min_count * 3:  # 3x imbalance (reduced threshold)
                            insights.append(ProactiveInsight(
                                message=f"There's significant variation in {col.replace('_', ' ')} distribution - some categories might have untapped potential.",
                                insight_type="opportunity",
                                confidence=0.7,
                                suggested_actions=[
                                    f"Investigate why some {col.replace('_', ' ')} categories perform differently",
                                    "Consider strategies to improve underperforming categories",
                                    "Analyze successful categories for best practices"
                                ]
                            ))
        
        except Exception as e:
            logger.error(f"Error detecting opportunity patterns: {str(e)}")
        
        return insights
    
    def _detect_correlation_patterns(self, data: List[Dict[str, Any]], original_question: str) -> List[ProactiveInsight]:
        """Detect correlation patterns between different metrics."""
        insights = []
        
        try:
            if len(data) < 5:
                return insights
            
            # Look for potential correlations between numeric columns
            numeric_cols = [col for col in data[0].keys() 
                          if isinstance(data[0].get(col), (int, float))]
            
            if len(numeric_cols) >= 2:
                insights.append(ProactiveInsight(
                    message="Your data has multiple numeric metrics that might be related - exploring correlations could reveal valuable insights.",
                    insight_type="pattern",
                    confidence=0.6,
                    suggested_actions=[
                        "Compare different metrics to find relationships",
                        "Look for patterns between performance indicators",
                        "Analyze how different factors influence each other"
                    ]
                ))
        
        except Exception as e:
            logger.error(f"Error detecting correlation patterns: {str(e)}")
        
        return insights
    
    def _extract_conversation_topics(self, conversation_history: List[Dict[str, Any]]) -> List[str]:
        """Extract main topics from conversation history."""
        topics = []
        
        try:
            for message in conversation_history[-5:]:  # Last 5 messages
                content = message.get("content", "").lower()
                
                # Extract key business terms
                if any(word in content for word in ["sales", "revenue", "profit"]):
                    topics.append("financial")
                if any(word in content for word in ["time", "trend", "month", "year"]):
                    topics.append("temporal")
                if any(word in content for word in ["user", "customer", "client"]):
                    topics.append("users")
                if any(word in content for word in ["category", "type", "segment"]):
                    topics.append("categories")
        
        except Exception as e:
            logger.error(f"Error extracting conversation topics: {str(e)}")
        
        return list(set(topics))
    
    def _analyze_question_types(self, conversation_history: List[Dict[str, Any]]) -> List[str]:
        """Analyze types of questions asked in conversation."""
        question_types = []
        
        try:
            for message in conversation_history:
                if message.get("message_type") == "user":
                    content = message.get("content", "").lower()
                    
                    if any(word in content for word in ["total", "how much", "overall"]):
                        question_types.append("overview")
                    if any(word in content for word in ["trend", "over time", "change"]):
                        question_types.append("trends")
                    if any(word in content for word in ["compare", "vs", "versus", "difference"]):
                        question_types.append("comparisons")
                    if any(word in content for word in ["detail", "specific", "breakdown"]):
                        question_types.append("details")
        
        except Exception as e:
            logger.error(f"Error analyzing question types: {str(e)}")
        
        return list(set(question_types))
    
    def _generate_drill_down_questions(self, topics: List[str]) -> List[QuestionSuggestion]:
        """Generate drill-down questions based on topics."""
        questions = []
        
        if "financial" in topics:
            questions.append(QuestionSuggestion(
                question="Which specific products or services drive the most revenue?",
                category="details",
                priority=4,
                reasoning="Drilling down into financial performance details"
            ))
        
        if "users" in topics:
            questions.append(QuestionSuggestion(
                question="What are the characteristics of my most active users?",
                category="details",
                priority=4,
                reasoning="Understanding user behavior in detail"
            ))
        
        return questions
    
    def _generate_trend_questions(self, topics: List[str]) -> List[QuestionSuggestion]:
        """Generate trend-based questions."""
        questions = []
        
        questions.append(QuestionSuggestion(
            question="What seasonal patterns can I see in my data?",
            category="trends",
            priority=3,
            reasoning="Seasonal analysis provides business planning insights"
        ))
        
        return questions
    
    def _generate_comparison_questions(self, topics: List[str]) -> List[QuestionSuggestion]:
        """Generate comparison questions."""
        questions = []
        
        questions.append(QuestionSuggestion(
            question="How do different segments compare in performance?",
            category="comparisons",
            priority=3,
            reasoning="Comparative analysis reveals relative performance"
        ))
        
        return questions
    
    def _deduplicate_suggestions(self, suggestions: List[QuestionSuggestion]) -> List[QuestionSuggestion]:
        """Remove duplicate suggestions based on question text."""
        seen_questions = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            if suggestion.question not in seen_questions:
                seen_questions.add(suggestion.question)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    def _generate_fallback_questions(self) -> List[QuestionSuggestion]:
        """Generate fallback questions when analysis fails."""
        return [
            QuestionSuggestion(
                question="What does my data look like overall?",
                category="overview",
                priority=3,
                reasoning="Basic data exploration starting point"
            ),
            QuestionSuggestion(
                question="What are the main patterns in my data?",
                category="overview",
                priority=3,
                reasoning="Pattern discovery for general insights"
            ),
            QuestionSuggestion(
                question="How much data do I have to work with?",
                category="overview",
                priority=2,
                reasoning="Understanding data volume and scope"
            )
        ]