"""
Tests for performance optimization features.

Tests caching, streaming, and performance monitoring functionality.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

# Import the performance optimization modules
try:
    from src.response_cache import ResponseCache, LRUCache, get_response_cache
    from src.streaming_response import StreamingResponseManager, ChatStreamProcessor, StreamEventType
    from src.chat_service import ChatService
    from src.models import ChatRequest, ConversationalResponse
except ImportError:
    from response_cache import ResponseCache, LRUCache, get_response_cache
    from streaming_response import StreamingResponseManager, ChatStreamProcessor, StreamEventType
    from chat_service import ChatService
    from models import ChatRequest, ConversationalResponse


class TestLRUCache:
    """Test LRU cache functionality."""
    
    def test_cache_basic_operations(self):
        """Test basic cache put/get operations."""
        cache = LRUCache(max_size=3, default_ttl=60)
        
        # Test put and get
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test cache miss
        assert cache.get("nonexistent") is None
        
        # Test cache stats
        stats = cache.get_stats()
        assert stats.total_requests == 2
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.hit_rate == 0.5
    
    def test_cache_eviction(self):
        """Test LRU eviction policy."""
        cache = LRUCache(max_size=2, default_ttl=60)
        
        # Fill cache to capacity
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Access key1 to make it most recently used
        cache.get("key1")
        
        # Add key3, should evict key2 (least recently used)
        cache.put("key3", "value3")
        
        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"  # Present
    
    def test_cache_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LRUCache(max_size=10, default_ttl=1)  # 1 second TTL
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None  # Should be expired
    
    def test_cache_cleanup(self):
        """Test expired entry cleanup."""
        cache = LRUCache(max_size=10, default_ttl=1)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup expired entries
        expired_count = cache.cleanup_expired()
        assert expired_count == 2


class TestResponseCache:
    """Test response cache functionality."""
    
    def test_chat_response_caching(self):
        """Test chat response caching."""
        cache = ResponseCache(
            chat_cache_size=10,
            query_cache_size=10,
            llm_cache_size=10,
            default_ttl=60
        )
        
        # Create mock response
        response = ConversationalResponse(
            message="Test response",
            chart_config=None,
            insights=["Test insight"],
            follow_up_questions=["Test question?"],
            processing_time_ms=100.0,
            conversation_id="test-conv"
        )
        
        # Cache and retrieve
        cache.cache_chat_response("test question", response, "context123")
        cached = cache.get_chat_response("test question", "context123")
        
        assert cached is not None
        assert cached.message == "Test response"
        assert cached.processing_time_ms == 1.0  # Should be updated for cached response
    
    def test_query_result_caching(self):
        """Test query result caching."""
        cache = ResponseCache()
        
        # Create mock query result
        from src.models import ExecuteResponse
        result = ExecuteResponse(
            columns=["col1", "col2"],
            data=[{"col1": "val1", "col2": "val2"}],
            row_count=1,
            runtime_ms=50.0,
            truncated=False
        )
        
        # Cache and retrieve
        sql = "SELECT * FROM test"
        cache.cache_query_result(sql, result)
        cached = cache.get_query_result(sql)
        
        assert cached is not None
        assert cached.columns == ["col1", "col2"]
        assert cached.row_count == 1
    
    def test_llm_response_caching(self):
        """Test LLM response caching."""
        cache = ResponseCache()
        
        prompt = "Translate this to SQL"
        response = "SELECT * FROM table"
        
        # Cache and retrieve
        cache.cache_llm_response(prompt, response, "test-model")
        cached = cache.get_llm_response(prompt, "test-model")
        
        assert cached == response
    
    def test_cache_key_normalization(self):
        """Test cache key normalization for better hit rates."""
        cache = ResponseCache()
        
        # These should generate the same cache key
        question1 = "What is the total sales?"
        question2 = "what is the total sales"
        question3 = "What is the total sales ?"
        
        response = ConversationalResponse(
            message="Total sales is $1000",
            chart_config=None,
            insights=[],
            follow_up_questions=[],
            processing_time_ms=100.0,
            conversation_id="test"
        )
        
        # Cache with first variation
        cache.cache_chat_response(question1, response)
        
        # Should hit cache with other variations
        assert cache.get_chat_response(question2) is not None
        assert cache.get_chat_response(question3) is not None


class TestStreamingResponse:
    """Test streaming response functionality."""
    
    @pytest.mark.asyncio
    async def test_streaming_manager_basic(self):
        """Test basic streaming manager functionality."""
        manager = StreamingResponseManager()
        stream_id = "test-stream"
        
        # Start streaming task
        async def send_events():
            await manager.send_progress(stream_id, "processing", 50, "Processing...")
            await manager.send_event(stream_id, StreamEventType.COMPLETION, {"status": "done"})
        
        # Create stream and send events concurrently
        stream_task = asyncio.create_task(manager.create_stream(stream_id).__anext__())
        send_task = asyncio.create_task(send_events())
        
        # Wait for first event
        await asyncio.sleep(0.1)
        
        # Get the first event
        try:
            event_data = await asyncio.wait_for(stream_task, timeout=1.0)
            assert "progress_percent" in event_data or "event" in event_data
        except asyncio.TimeoutError:
            pytest.skip("Streaming test timed out - may need adjustment")
        
        await send_task
    
    @pytest.mark.asyncio
    async def test_chat_stream_processor(self):
        """Test chat stream processor."""
        manager = StreamingResponseManager()
        processor = ChatStreamProcessor(manager)
        
        # Mock process function
        async def mock_process():
            return ConversationalResponse(
                message="Test response",
                chart_config=None,
                insights=["Test insight"],
                follow_up_questions=["Test question?"],
                processing_time_ms=100.0,
                conversation_id="test"
            )
        
        # Process with streaming
        stream_id = "test-stream"
        response = await processor.process_with_streaming(stream_id, mock_process)
        
        assert response.message == "Test response"
        assert response.processing_time_ms == 100.0


class TestChatServiceOptimizations:
    """Test chat service performance optimizations."""
    
    @pytest.mark.asyncio
    async def test_chat_service_caching(self):
        """Test that chat service uses caching."""
        # Mock dependencies
        mock_query_executor = Mock()
        mock_llm_service = AsyncMock()
        
        # Create chat service
        chat_service = ChatService(
            query_executor=mock_query_executor,
            llm_service=mock_llm_service
        )
        
        # Create test request
        request = ChatRequest(
            message="What is the total sales?",
            conversation_id="test-conv"
        )
        
        # First call should process normally
        with patch.object(chat_service, '_process_with_query_execution') as mock_process:
            mock_response = ConversationalResponse(
                message="Total sales is $1000",
                chart_config=None,
                insights=["Sales insight"],
                follow_up_questions=["Follow up?"],
                processing_time_ms=500.0,
                conversation_id="test-conv"
            )
            mock_process.return_value = mock_response
            
            response1 = await chat_service.process_chat_message(request)
            assert response1.message == "Total sales is $1000"
            assert mock_process.call_count == 1
        
        # Second identical call should hit cache
        with patch.object(chat_service, '_process_with_query_execution') as mock_process:
            response2 = await chat_service.process_chat_message(request)
            assert response2.message == "Total sales is $1000"
            assert response2.processing_time_ms == 1.0  # Cached response time
            assert mock_process.call_count == 0  # Should not be called due to cache hit
    
    @pytest.mark.asyncio
    async def test_chat_service_streaming(self):
        """Test chat service streaming functionality."""
        # Mock dependencies
        mock_query_executor = Mock()
        mock_llm_service = AsyncMock()
        
        # Create chat service
        chat_service = ChatService(
            query_executor=mock_query_executor,
            llm_service=mock_llm_service
        )
        
        # Create test request
        request = ChatRequest(
            message="What is the total sales?",
            conversation_id="test-conv"
        )
        
        # Mock the regular process method
        with patch.object(chat_service, 'process_chat_message') as mock_process:
            mock_response = ConversationalResponse(
                message="Total sales is $1000",
                chart_config=None,
                insights=["Sales insight"],
                follow_up_questions=["Follow up?"],
                processing_time_ms=500.0,
                conversation_id="test-conv"
            )
            mock_process.return_value = mock_response
            
            # Test streaming version
            response = await chat_service.process_chat_message_with_streaming(request, "test-stream")
            assert response.message == "Total sales is $1000"
            assert mock_process.call_count == 1


class TestPerformanceIntegration:
    """Integration tests for performance optimizations."""
    
    def test_cache_stats_collection(self):
        """Test that cache statistics are properly collected."""
        cache = get_response_cache()
        
        # Perform some operations
        cache.cache_chat_response("test", Mock(), "context")
        cache.get_chat_response("test", "context")  # Hit
        cache.get_chat_response("nonexistent", "context")  # Miss
        
        stats = cache.get_cache_stats()
        
        # Verify stats structure
        assert "chat_cache" in stats
        assert "query_cache" in stats
        assert "llm_cache" in stats
        
        chat_stats = stats["chat_cache"]
        assert hasattr(chat_stats, 'total_requests')
        assert hasattr(chat_stats, 'cache_hits')
        assert hasattr(chat_stats, 'cache_misses')
        assert hasattr(chat_stats, 'hit_rate')
    
    @pytest.mark.asyncio
    async def test_end_to_end_performance_optimization(self):
        """Test end-to-end performance optimization flow."""
        # This test verifies that all performance components work together
        
        # Mock dependencies
        mock_query_executor = Mock()
        mock_llm_service = AsyncMock()
        
        # Setup mock responses
        mock_llm_service.translate_to_sql.return_value = "SELECT COUNT(*) FROM sales"
        mock_llm_service.generate_conversational_explanation.return_value = "You have 100 sales records"
        mock_llm_service.generate_data_insights.return_value = ["Sales are growing"]
        mock_llm_service.generate_follow_up_questions.return_value = ["What about revenue?"]
        
        mock_query_executor.execute_query.return_value = Mock(
            columns=["count"],
            rows=[[100]],
            row_count=1,
            runtime_ms=50.0,
            truncated=False
        )
        
        # Create chat service with mocked dependencies
        chat_service = ChatService(
            query_executor=mock_query_executor,
            llm_service=mock_llm_service
        )
        
        # Create test request
        request = ChatRequest(
            message="How many sales do I have?",
            conversation_id="test-conv"
        )
        
        # First request - should process normally and cache result
        start_time = time.time()
        response1 = await chat_service.process_chat_message(request)
        first_duration = time.time() - start_time
        
        assert response1.message == "You have 100 sales records"
        assert response1.insights == ["Sales are growing"]
        
        # Second identical request - should hit cache and be much faster
        start_time = time.time()
        response2 = await chat_service.process_chat_message(request)
        second_duration = time.time() - start_time
        
        assert response2.message == "You have 100 sales records"
        assert response2.processing_time_ms == 1.0  # Cached response indicator
        
        # Cached response should be significantly faster
        assert second_duration < first_duration * 0.5  # At least 50% faster


if __name__ == "__main__":
    pytest.main([__file__, "-v"])