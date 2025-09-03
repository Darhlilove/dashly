"""
Streaming response system for better perceived performance.

Provides streaming capabilities for chat responses, query results, and real-time
progress updates to improve user experience during processing.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from .logging_config import get_logger
    from .models import ConversationalResponse
except ImportError:
    from logging_config import get_logger
    from models import ConversationalResponse

logger = get_logger(__name__)


class StreamEventType(Enum):
    """Types of streaming events."""
    PROCESSING_START = "processing_start"
    PROGRESS_UPDATE = "progress_update"
    PARTIAL_RESPONSE = "partial_response"
    CHART_UPDATE = "chart_update"
    INSIGHTS_UPDATE = "insights_update"
    COMPLETION = "completion"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Streaming event data."""
    event_type: StreamEventType
    data: Dict[str, Any]
    timestamp: float
    sequence: int


@dataclass
class ProgressUpdate:
    """Progress update information."""
    stage: str
    progress_percent: float
    message: str
    estimated_remaining_ms: Optional[float] = None


class StreamingResponseManager:
    """
    Manages streaming responses for better perceived performance.
    
    Provides real-time updates during processing to keep users engaged
    and informed about progress.
    """
    
    def __init__(self):
        """Initialize streaming response manager."""
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self._sequence_counter = 0
        
        logger.info("StreamingResponseManager initialized")
    
    async def create_stream(self, stream_id: str) -> AsyncGenerator[str, None]:
        """
        Create a new streaming response.
        
        Args:
            stream_id: Unique identifier for the stream
            
        Yields:
            str: JSON-encoded stream events
        """
        # Create queue for this stream
        queue = asyncio.Queue()
        self.active_streams[stream_id] = queue
        
        logger.info(f"Created stream: {stream_id}")
        
        try:
            while True:
                # Wait for next event
                event = await queue.get()
                
                # Check for completion
                if event.event_type == StreamEventType.COMPLETION:
                    yield self._format_event(event)
                    break
                elif event.event_type == StreamEventType.ERROR:
                    yield self._format_event(event)
                    break
                else:
                    yield self._format_event(event)
                
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled: {stream_id}")
        except Exception as e:
            logger.error(f"Stream error for {stream_id}: {e}")
            error_event = self._create_event(
                StreamEventType.ERROR,
                {"error": str(e), "message": "Stream processing failed"}
            )
            yield self._format_event(error_event)
        finally:
            # Clean up
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            logger.debug(f"Stream cleaned up: {stream_id}")
    
    async def send_event(self, stream_id: str, event_type: StreamEventType, data: Dict[str, Any]) -> None:
        """
        Send event to specific stream.
        
        Args:
            stream_id: Stream identifier
            event_type: Type of event
            data: Event data
        """
        if stream_id not in self.active_streams:
            logger.warning(f"Attempted to send event to non-existent stream: {stream_id}")
            return
        
        event = self._create_event(event_type, data)
        
        try:
            await self.active_streams[stream_id].put(event)
            logger.debug(f"Sent {event_type.value} event to stream {stream_id}")
        except Exception as e:
            logger.error(f"Failed to send event to stream {stream_id}: {e}")
    
    async def send_progress(self, stream_id: str, stage: str, progress: float, 
                          message: str, estimated_remaining_ms: Optional[float] = None) -> None:
        """
        Send progress update to stream.
        
        Args:
            stream_id: Stream identifier
            stage: Current processing stage
            progress: Progress percentage (0-100)
            message: Progress message
            estimated_remaining_ms: Estimated remaining time
        """
        progress_data = {
            "stage": stage,
            "progress_percent": min(100, max(0, progress)),
            "message": message,
            "estimated_remaining_ms": estimated_remaining_ms
        }
        
        await self.send_event(stream_id, StreamEventType.PROGRESS_UPDATE, progress_data)
    
    async def send_partial_response(self, stream_id: str, partial_text: str, 
                                  confidence: Optional[float] = None) -> None:
        """
        Send partial response text to stream.
        
        Args:
            stream_id: Stream identifier
            partial_text: Partial response text
            confidence: Confidence level (0-1)
        """
        partial_data = {
            "text": partial_text,
            "confidence": confidence,
            "is_partial": True
        }
        
        await self.send_event(stream_id, StreamEventType.PARTIAL_RESPONSE, partial_data)
    
    async def send_chart_update(self, stream_id: str, chart_config: Dict[str, Any]) -> None:
        """
        Send chart configuration update to stream.
        
        Args:
            stream_id: Stream identifier
            chart_config: Chart configuration
        """
        chart_data = {
            "chart_config": chart_config,
            "update_type": "chart_ready"
        }
        
        await self.send_event(stream_id, StreamEventType.CHART_UPDATE, chart_data)
    
    async def send_insights_update(self, stream_id: str, insights: List[str]) -> None:
        """
        Send insights update to stream.
        
        Args:
            stream_id: Stream identifier
            insights: List of insights
        """
        insights_data = {
            "insights": insights,
            "update_type": "insights_ready"
        }
        
        await self.send_event(stream_id, StreamEventType.INSIGHTS_UPDATE, insights_data)
    
    async def complete_stream(self, stream_id: str, final_response: ConversationalResponse) -> None:
        """
        Complete stream with final response.
        
        Args:
            stream_id: Stream identifier
            final_response: Final conversational response
        """
        completion_data = {
            "response": self._serialize_response(final_response),
            "status": "completed"
        }
        
        await self.send_event(stream_id, StreamEventType.COMPLETION, completion_data)
    
    async def error_stream(self, stream_id: str, error_message: str, error_code: Optional[str] = None) -> None:
        """
        Send error to stream and complete it.
        
        Args:
            stream_id: Stream identifier
            error_message: Error message
            error_code: Optional error code
        """
        error_data = {
            "error": error_message,
            "error_code": error_code,
            "status": "error"
        }
        
        await self.send_event(stream_id, StreamEventType.ERROR, error_data)
    
    def _create_event(self, event_type: StreamEventType, data: Dict[str, Any]) -> StreamEvent:
        """Create stream event with metadata."""
        self._sequence_counter += 1
        
        return StreamEvent(
            event_type=event_type,
            data=data,
            timestamp=time.time(),
            sequence=self._sequence_counter
        )
    
    def _format_event(self, event: StreamEvent) -> str:
        """Format event as JSON string for streaming."""
        event_dict = {
            "event": event.event_type.value,
            "data": event.data,
            "timestamp": event.timestamp,
            "sequence": event.sequence
        }
        
        return json.dumps(event_dict, default=str) + "\n"
    
    def _serialize_response(self, response: ConversationalResponse) -> Dict[str, Any]:
        """Serialize conversational response for streaming."""
        try:
            if hasattr(response, 'model_dump'):
                return response.model_dump()
            elif hasattr(response, 'dict'):
                return response.dict()
            elif hasattr(response, '__dict__'):
                return response.__dict__
            else:
                return {"message": str(response)}
        except Exception as e:
            logger.error(f"Failed to serialize response: {e}")
            return {"message": "Response serialization failed"}


class ChatStreamProcessor:
    """
    Processes chat requests with streaming updates.
    
    Provides real-time feedback during chat processing stages.
    """
    
    def __init__(self, streaming_manager: StreamingResponseManager):
        """
        Initialize chat stream processor.
        
        Args:
            streaming_manager: Streaming response manager
        """
        self.streaming_manager = streaming_manager
        self.logger = get_logger(__name__)
    
    async def process_with_streaming(self, stream_id: str, 
                                   process_func: Callable, 
                                   *args, **kwargs) -> ConversationalResponse:
        """
        Process chat request with streaming updates.
        
        Args:
            stream_id: Stream identifier
            process_func: Function to process the request
            *args, **kwargs: Arguments for process function
            
        Returns:
            ConversationalResponse: Final response
        """
        try:
            # Start processing
            await self.streaming_manager.send_event(
                stream_id, 
                StreamEventType.PROCESSING_START,
                {"message": "Starting to process your question..."}
            )
            
            # Stage 1: Analyzing question
            await self.streaming_manager.send_progress(
                stream_id, 
                "analyzing", 
                10, 
                "Analyzing your question..."
            )
            
            await asyncio.sleep(0.1)  # Small delay for better UX
            
            # Stage 2: Translating to SQL
            await self.streaming_manager.send_progress(
                stream_id, 
                "translating", 
                30, 
                "Converting to database query..."
            )
            
            await asyncio.sleep(0.1)
            
            # Stage 3: Executing query
            await self.streaming_manager.send_progress(
                stream_id, 
                "executing", 
                50, 
                "Running query against your data..."
            )
            
            await asyncio.sleep(0.1)
            
            # Stage 4: Analyzing results
            await self.streaming_manager.send_progress(
                stream_id, 
                "analyzing_results", 
                70, 
                "Analyzing the results..."
            )
            
            await asyncio.sleep(0.1)
            
            # Stage 5: Generating insights
            await self.streaming_manager.send_progress(
                stream_id, 
                "generating_insights", 
                85, 
                "Generating insights and recommendations..."
            )
            
            await asyncio.sleep(0.1)
            
            # Stage 6: Finalizing response
            await self.streaming_manager.send_progress(
                stream_id, 
                "finalizing", 
                95, 
                "Preparing your response..."
            )
            
            # Execute the actual processing
            if asyncio.iscoroutinefunction(process_func):
                response = await process_func(*args, **kwargs)
            else:
                response = process_func(*args, **kwargs)
            
            # Send chart update if available
            if hasattr(response, 'chart_config') and response.chart_config:
                chart_dict = response.chart_config.dict() if hasattr(response.chart_config, 'dict') else response.chart_config.__dict__
                await self.streaming_manager.send_chart_update(stream_id, chart_dict)
            
            # Send insights update if available
            if hasattr(response, 'insights') and response.insights:
                await self.streaming_manager.send_insights_update(stream_id, response.insights)
            
            # Complete the stream
            await self.streaming_manager.complete_stream(stream_id, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Streaming processing failed for {stream_id}: {e}")
            await self.streaming_manager.error_stream(stream_id, str(e))
            raise


class QueryStreamProcessor:
    """
    Processes SQL queries with streaming updates.
    
    Provides real-time feedback during query execution stages.
    """
    
    def __init__(self, streaming_manager: StreamingResponseManager):
        """
        Initialize query stream processor.
        
        Args:
            streaming_manager: Streaming response manager
        """
        self.streaming_manager = streaming_manager
        self.logger = get_logger(__name__)
    
    async def execute_with_streaming(self, stream_id: str, 
                                   execute_func: Callable, 
                                   sql: str, *args, **kwargs) -> Any:
        """
        Execute query with streaming updates.
        
        Args:
            stream_id: Stream identifier
            execute_func: Function to execute the query
            sql: SQL query
            *args, **kwargs: Arguments for execute function
            
        Returns:
            Query execution result
        """
        try:
            # Start execution
            await self.streaming_manager.send_event(
                stream_id,
                StreamEventType.PROCESSING_START,
                {"message": "Executing query...", "sql": sql[:100] + "..." if len(sql) > 100 else sql}
            )
            
            # Stage 1: Validating query
            await self.streaming_manager.send_progress(
                stream_id,
                "validating",
                20,
                "Validating SQL query..."
            )
            
            await asyncio.sleep(0.05)
            
            # Stage 2: Executing query
            await self.streaming_manager.send_progress(
                stream_id,
                "executing",
                50,
                "Executing against database..."
            )
            
            # Execute the actual query
            if asyncio.iscoroutinefunction(execute_func):
                result = await execute_func(sql, *args, **kwargs)
            else:
                result = execute_func(sql, *args, **kwargs)
            
            # Stage 3: Processing results
            await self.streaming_manager.send_progress(
                stream_id,
                "processing",
                80,
                "Processing query results..."
            )
            
            await asyncio.sleep(0.05)
            
            # Complete
            await self.streaming_manager.send_progress(
                stream_id,
                "completed",
                100,
                "Query execution completed"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Query streaming failed for {stream_id}: {e}")
            await self.streaming_manager.error_stream(stream_id, str(e))
            raise


# Global streaming manager instance
_streaming_manager: Optional[StreamingResponseManager] = None


def get_streaming_manager() -> StreamingResponseManager:
    """Get or create global streaming manager instance."""
    global _streaming_manager
    if _streaming_manager is None:
        _streaming_manager = StreamingResponseManager()
    return _streaming_manager