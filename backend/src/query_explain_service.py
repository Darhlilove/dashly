"""
Query Explain Service for SQL query analysis and cost estimation.

Provides query execution plan analysis using DuckDB's EXPLAIN functionality,
cost estimation, and optimization suggestions for SQL queries.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from .exceptions import (
        QueryExplainError,
        DatabaseConnectionError,
        ValidationError
    )
    from .logging_config import get_logger
    from .sql_validator import SQLValidator, ValidationResult
except ImportError:
    from exceptions import (
        QueryExplainError,
        DatabaseConnectionError,
        ValidationError
    )
    from logging_config import get_logger
    from sql_validator import SQLValidator, ValidationResult

logger = get_logger(__name__)


@dataclass
class CostEstimate:
    """Cost estimation for query execution."""
    estimated_cost: float
    estimated_rows: int
    estimated_runtime_ms: float
    complexity_score: int


@dataclass
class ExecutionPlan:
    """Query execution plan information."""
    plan_text: str
    plan_tree: Dict[str, Any]
    operations: List[str]
    table_scans: List[str]
    joins: List[str]
    aggregations: List[str]


@dataclass
class ExplanationResult:
    """Complete query explanation result."""
    execution_plan: str
    estimated_cost: float
    estimated_rows: int
    estimated_runtime_ms: float
    optimization_suggestions: List[str]
    plan_details: ExecutionPlan
    cost_details: CostEstimate


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class QueryExplainService:
    """
    Service for analyzing SQL queries using DuckDB's EXPLAIN functionality.
    
    Provides cost estimation, execution plan generation, and optimization
    suggestions for validated SQL queries.
    """
    
    def __init__(self, db_connection, sql_validator: Optional[SQLValidator] = None):
        """
        Initialize QueryExplainService with DuckDB connection.
        
        Args:
            db_connection: DuckDB connection instance
            sql_validator: Optional SQL validator instance
        """
        self.db_connection = db_connection
        self.sql_validator = sql_validator or SQLValidator()
        
        # Cost estimation parameters
        self.base_cost_per_row = 0.001  # Base cost per row processed
        self.join_cost_multiplier = 2.0  # Additional cost for joins
        self.aggregation_cost_multiplier = 1.5  # Additional cost for aggregations
        self.sort_cost_multiplier = 1.2  # Additional cost for sorting
        
        # Performance estimation parameters (rough estimates)
        self.base_time_per_row_ms = 0.0001  # Base time per row in milliseconds
        self.join_time_multiplier = 3.0  # Time multiplier for joins
        self.aggregation_time_multiplier = 2.0  # Time multiplier for aggregations
        
        logger.info("QueryExplainService initialized")
    
    def explain_query(self, sql: str) -> ExplanationResult:
        """
        Generate comprehensive query explanation with cost estimation.
        
        Args:
            sql: SQL query to explain
            
        Returns:
            ExplanationResult: Complete explanation with cost and optimization info
            
        Raises:
            QueryExplainError: If explanation fails
            ValidationError: If query validation fails
        """
        logger.info(f"Explaining query: {sql[:100]}...")
        
        try:
            # Validate the query first (Requirements 4.1)
            validation_result = self.sql_validator.validate_query(sql)
            if not validation_result.is_valid:
                raise ValidationError(f"Query validation failed: {', '.join(validation_result.errors)}")
            
            # Get execution plan using DuckDB's EXPLAIN (Requirements 4.2)
            execution_plan = self.get_execution_plan(sql)
            
            # Estimate cost and performance (Requirements 4.3)
            cost_estimate = self.estimate_cost(sql)
            
            # Generate optimization suggestions (Requirements 4.4)
            optimization_suggestions = self._generate_optimization_suggestions(
                sql, execution_plan, cost_estimate
            )
            
            result = ExplanationResult(
                execution_plan=execution_plan.plan_text,
                estimated_cost=cost_estimate.estimated_cost,
                estimated_rows=cost_estimate.estimated_rows,
                estimated_runtime_ms=cost_estimate.estimated_runtime_ms,
                optimization_suggestions=optimization_suggestions,
                plan_details=execution_plan,
                cost_details=cost_estimate
            )
            
            logger.info(f"Query explanation completed: cost={cost_estimate.estimated_cost:.2f}, "
                       f"rows={cost_estimate.estimated_rows}, "
                       f"time={cost_estimate.estimated_runtime_ms:.2f}ms")
            
            return result
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Query explanation failed: {str(e)}")
            raise QueryExplainError(f"Failed to explain query: {str(e)}")
    
    def estimate_cost(self, sql: str) -> CostEstimate:
        """
        Estimate query execution cost and performance metrics.
        
        Args:
            sql: SQL query to analyze
            
        Returns:
            CostEstimate: Cost and performance estimates
        """
        try:
            # Get execution plan for cost analysis
            execution_plan = self.get_execution_plan(sql)
            
            # Parse plan to extract cost information
            estimated_rows = self._extract_row_estimate(execution_plan.plan_text)
            complexity_score = self._calculate_complexity_score(sql, execution_plan)
            
            # Calculate cost based on operations and estimated rows
            base_cost = estimated_rows * self.base_cost_per_row
            
            # Apply multipliers based on operations
            cost_multiplier = 1.0
            if execution_plan.joins:
                cost_multiplier *= self.join_cost_multiplier
            if execution_plan.aggregations:
                cost_multiplier *= self.aggregation_cost_multiplier
            if 'ORDER BY' in sql.upper():
                cost_multiplier *= self.sort_cost_multiplier
            
            estimated_cost = base_cost * cost_multiplier
            
            # Estimate runtime based on cost and complexity
            base_time = estimated_rows * self.base_time_per_row_ms
            time_multiplier = cost_multiplier
            
            # Additional time factors
            if len(execution_plan.joins) > 1:
                time_multiplier *= self.join_time_multiplier
            if execution_plan.aggregations:
                time_multiplier *= self.aggregation_time_multiplier
            
            estimated_runtime_ms = base_time * time_multiplier
            
            return CostEstimate(
                estimated_cost=estimated_cost,
                estimated_rows=estimated_rows,
                estimated_runtime_ms=estimated_runtime_ms,
                complexity_score=complexity_score
            )
            
        except Exception as e:
            logger.error(f"Cost estimation failed: {str(e)}")
            # Return default estimates if analysis fails
            return CostEstimate(
                estimated_cost=1.0,
                estimated_rows=100,
                estimated_runtime_ms=10.0,
                complexity_score=1
            )
    
    def get_execution_plan(self, sql: str) -> ExecutionPlan:
        """
        Get detailed execution plan using DuckDB's EXPLAIN functionality.
        
        Args:
            sql: SQL query to analyze
            
        Returns:
            ExecutionPlan: Detailed execution plan information
            
        Raises:
            QueryExplainError: If plan generation fails
        """
        try:
            # Use DuckDB's EXPLAIN to get execution plan
            explain_sql = f"EXPLAIN {sql}"
            
            logger.debug(f"Getting execution plan: {explain_sql}")
            
            # Execute EXPLAIN query using connection pool
            with self.db_connection.get_connection() as conn:
                cursor = conn.execute(explain_sql)
                plan_rows = cursor.fetchall()
            
            # DuckDB EXPLAIN returns tuples like ('physical_plan', 'actual_plan_text')
            # We need to extract the actual plan text
            plan_text = ""
            for row in plan_rows:
                if isinstance(row, (list, tuple)) and len(row) >= 2:
                    # Use the second element which contains the actual plan
                    plan_text += str(row[1]) + '\n'
                elif isinstance(row, (list, tuple)) and len(row) == 1:
                    plan_text += str(row[0]) + '\n'
                else:
                    plan_text += str(row) + '\n'
            
            plan_text = plan_text.strip()
            
            # Parse plan to extract structured information
            operations = self._extract_operations(plan_text)
            table_scans = self._extract_table_scans(plan_text)
            joins = self._extract_joins(plan_text)
            aggregations = self._extract_aggregations(plan_text)
            
            # Create plan tree structure (simplified)
            plan_tree = self._create_plan_tree(plan_text, operations)
            
            return ExecutionPlan(
                plan_text=plan_text,
                plan_tree=plan_tree,
                operations=operations,
                table_scans=table_scans,
                joins=joins,
                aggregations=aggregations
            )
            
        except Exception as e:
            logger.error(f"Failed to get execution plan: {str(e)}")
            raise QueryExplainError(f"Failed to generate execution plan: {str(e)}")
    
    def _extract_row_estimate(self, plan_text: str) -> int:
        """
        Extract estimated row count from execution plan.
        
        Args:
            plan_text: Execution plan text
            
        Returns:
            int: Estimated number of rows
        """
        # Look for row count estimates in plan text
        # DuckDB plan format may vary, so we use multiple patterns
        patterns = [
            r'(\d+)\s+rows',
            r'estimated\s+(\d+)',
            r'cardinality[:\s]+(\d+)',
            r'rows[:\s]+(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, plan_text, re.IGNORECASE)
            if matches:
                # Return the largest estimate found
                return max(int(match) for match in matches)
        
        # Default estimate if no information found
        return 1000
    
    def _calculate_complexity_score(self, sql: str, execution_plan: ExecutionPlan) -> int:
        """
        Calculate query complexity score based on SQL and execution plan.
        
        Args:
            sql: SQL query
            execution_plan: Execution plan information
            
        Returns:
            int: Complexity score (1-10)
        """
        score = 1
        
        # Base complexity from SQL features
        sql_upper = sql.upper()
        
        # Joins increase complexity
        join_count = len(execution_plan.joins)
        score += min(join_count * 2, 4)  # Max 4 points for joins
        
        # Subqueries increase complexity
        subquery_count = sql_upper.count('SELECT') - 1  # Subtract main SELECT
        score += min(subquery_count, 2)  # Max 2 points for subqueries
        
        # Aggregations increase complexity
        if execution_plan.aggregations:
            score += 1
        
        # Window functions increase complexity
        if 'OVER(' in sql_upper:
            score += 2
        
        # CTEs increase complexity
        if 'WITH' in sql_upper:
            score += 1
        
        # UNION operations increase complexity
        if 'UNION' in sql_upper:
            score += 1
        
        return min(score, 10)  # Cap at 10
    
    def _extract_operations(self, plan_text: str) -> List[str]:
        """Extract operation types from execution plan."""
        operations = []
        
        # Common DuckDB operation patterns
        operation_patterns = [
            r'SEQ_SCAN',
            r'HASH_JOIN',
            r'NESTED_LOOP_JOIN',
            r'MERGE_JOIN',
            r'HASH_GROUP_BY',
            r'SORT',
            r'FILTER',
            r'PROJECTION',
            r'AGGREGATE',
            r'LIMIT',
            r'UNION',
            r'WINDOW'
        ]
        
        for pattern in operation_patterns:
            if re.search(pattern, plan_text, re.IGNORECASE):
                operations.append(pattern.lower().replace('_', ' '))
        
        return operations
    
    def _extract_table_scans(self, plan_text: str) -> List[str]:
        """Extract table scan information from execution plan."""
        scans = []
        
        # Look for table scan patterns
        scan_patterns = [
            r'SEQ_SCAN\s+(\w+)',
            r'TABLE_SCAN\s+(\w+)',
            r'SCAN\s+(\w+)'
        ]
        
        for pattern in scan_patterns:
            matches = re.findall(pattern, plan_text, re.IGNORECASE)
            scans.extend(matches)
        
        return list(set(scans))  # Remove duplicates
    
    def _extract_joins(self, plan_text: str) -> List[str]:
        """Extract join information from execution plan."""
        joins = []
        
        # Look for join patterns
        join_patterns = [
            r'HASH_JOIN',
            r'NESTED_LOOP_JOIN',
            r'MERGE_JOIN',
            r'LEFT_JOIN',
            r'RIGHT_JOIN',
            r'INNER_JOIN',
            r'OUTER_JOIN'
        ]
        
        for pattern in join_patterns:
            if re.search(pattern, plan_text, re.IGNORECASE):
                joins.append(pattern.lower().replace('_', ' '))
        
        return joins
    
    def _extract_aggregations(self, plan_text: str) -> List[str]:
        """Extract aggregation information from execution plan."""
        aggregations = []
        
        # Look for aggregation patterns
        agg_patterns = [
            r'HASH_GROUP_BY',
            r'AGGREGATE',
            r'GROUP_BY',
            r'WINDOW'
        ]
        
        for pattern in agg_patterns:
            if re.search(pattern, plan_text, re.IGNORECASE):
                aggregations.append(pattern.lower().replace('_', ' '))
        
        return aggregations
    
    def _create_plan_tree(self, plan_text: str, operations: List[str]) -> Dict[str, Any]:
        """Create a simplified plan tree structure."""
        return {
            "root": "query_execution",
            "operations": operations,
            "estimated_complexity": len(operations),
            "plan_summary": plan_text[:200] + "..." if len(plan_text) > 200 else plan_text
        }
    
    def _generate_optimization_suggestions(
        self, 
        sql: str, 
        execution_plan: ExecutionPlan, 
        cost_estimate: CostEstimate
    ) -> List[str]:
        """
        Generate optimization suggestions based on query analysis.
        
        Args:
            sql: SQL query
            execution_plan: Execution plan information
            cost_estimate: Cost estimation
            
        Returns:
            List[str]: Optimization suggestions
        """
        suggestions = []
        sql_upper = sql.upper()
        
        # High cost query suggestions
        if cost_estimate.estimated_cost > 100:
            suggestions.append("Consider adding WHERE clauses to reduce the number of rows processed")
        
        # Large result set suggestions
        if cost_estimate.estimated_rows > 10000:
            suggestions.append("Consider using LIMIT to reduce the result set size")
            suggestions.append("Large result sets may impact performance - consider pagination")
        
        # Join optimization suggestions
        if len(execution_plan.joins) > 2:
            suggestions.append("Multiple joins detected - ensure proper indexing on join columns")
            suggestions.append("Consider breaking complex joins into smaller, simpler queries")
        
        # Aggregation suggestions
        if execution_plan.aggregations and 'GROUP BY' in sql_upper:
            if 'ORDER BY' not in sql_upper:
                suggestions.append("Consider adding ORDER BY to GROUP BY queries for consistent results")
        
        # Subquery suggestions
        subquery_count = sql_upper.count('SELECT') - 1
        if subquery_count > 1:
            suggestions.append("Multiple subqueries detected - consider using CTEs (WITH clauses) for better readability")
        
        # SELECT * suggestions
        if 'SELECT *' in sql_upper:
            suggestions.append("Avoid SELECT * - specify only the columns you need to improve performance")
        
        # Complex query suggestions
        if cost_estimate.complexity_score > 7:
            suggestions.append("High complexity query - consider breaking into smaller parts")
            suggestions.append("Complex queries may benefit from materialized views or temporary tables")
        
        # Performance suggestions based on estimated runtime
        if cost_estimate.estimated_runtime_ms > 1000:
            suggestions.append("Query may take significant time to execute - consider optimization")
        
        # Default suggestion if no specific issues found
        if not suggestions:
            suggestions.append("Query appears well-optimized for the given data structure")
        
        return suggestions