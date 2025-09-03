"""
Response caching system for common questions and query results.

Provides intelligent caching for chat responses, query results, and LLM outputs
to improve performance and reduce API costs.
"""

import hashlib
import json
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import OrderedDict

try:
    from .logging_config import get_logger
    from .models import ConversationalResponse, ExecuteResponse
except ImportError:
    from logging_config import get_logger
    from models import ConversationalResponse, ExecuteResponse

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: int
    size_bytes: int


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0


class LRUCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()
        
        logger.info(f"LRU Cache initialized: max_size={max_size}, default_ttl={default_ttl}s")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            self._stats.total_requests += 1
            
            if key not in self._cache:
                self._stats.cache_misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if self._is_expired(entry):
                del self._cache[key]
                self._stats.cache_misses += 1
                self._stats.evictions += 1
                return None
            
            # Update access info and move to end (most recently used)
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            self._cache.move_to_end(key)
            
            self._stats.cache_hits += 1
            self._update_hit_rate()
            
            return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Put value in cache."""
        with self._lock:
            ttl = ttl or self.default_ttl
            now = datetime.now()
            
            # Calculate size (rough estimate)
            size_bytes = self._estimate_size(value)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                last_accessed=now,
                access_count=0,
                ttl_seconds=ttl,
                size_bytes=size_bytes
            )
            
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats.total_size_bytes -= old_entry.size_bytes
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = entry
            self._stats.total_size_bytes += size_bytes
            
            # Evict if necessary
            self._evict_if_needed()
    
    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._stats.total_size_bytes -= entry.size_bytes
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats.total_size_bytes = 0
            self._stats.evictions += len(self._cache)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            stats = CacheStats(
                total_requests=self._stats.total_requests,
                cache_hits=self._stats.cache_hits,
                cache_misses=self._stats.cache_misses,
                evictions=self._stats.evictions,
                total_size_bytes=self._stats.total_size_bytes,
                hit_rate=self._stats.hit_rate
            )
            return stats
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count."""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache[key]
                self._stats.total_size_bytes -= entry.size_bytes
                del self._cache[key]
                self._stats.evictions += 1
            
            return len(expired_keys)
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        age = (datetime.now() - entry.created_at).total_seconds()
        return age > entry.ttl_seconds
    
    def _evict_if_needed(self) -> None:
        """Evict least recently used entries if cache is full."""
        while len(self._cache) > self.max_size:
            # Remove least recently used (first item)
            key, entry = self._cache.popitem(last=False)
            self._stats.total_size_bytes -= entry.size_bytes
            self._stats.evictions += 1
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of cached value in bytes."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (dict, list)):
                return len(json.dumps(value, default=str).encode('utf-8'))
            elif hasattr(value, '__dict__'):
                return len(json.dumps(asdict(value) if hasattr(value, '__dataclass_fields__') else value.__dict__, default=str).encode('utf-8'))
            else:
                return len(str(value).encode('utf-8'))
        except Exception:
            return 1024  # Default estimate
    
    def _update_hit_rate(self) -> None:
        """Update cache hit rate."""
        if self._stats.total_requests > 0:
            self._stats.hit_rate = self._stats.cache_hits / self._stats.total_requests


class ResponseCache:
    """
    Intelligent response caching system for chat responses and query results.
    
    Provides caching for:
    - Chat responses based on question similarity
    - Query results based on SQL hash
    - LLM responses to reduce API costs
    """
    
    def __init__(self, 
                 chat_cache_size: int = 500,
                 query_cache_size: int = 200,
                 llm_cache_size: int = 1000,
                 default_ttl: int = 300):
        """
        Initialize response cache system.
        
        Args:
            chat_cache_size: Max chat responses to cache
            query_cache_size: Max query results to cache
            llm_cache_size: Max LLM responses to cache
            default_ttl: Default TTL in seconds
        """
        self.chat_cache = LRUCache(chat_cache_size, default_ttl)
        self.query_cache = LRUCache(query_cache_size, default_ttl * 2)  # Longer TTL for queries
        self.llm_cache = LRUCache(llm_cache_size, default_ttl * 4)  # Longest TTL for LLM
        
        # Cleanup thread
        self._cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("ResponseCache initialized with intelligent caching for chat, query, and LLM responses")
    
    def get_chat_response(self, question: str, context_hash: str = "") -> Optional[ConversationalResponse]:
        """
        Get cached chat response for similar question.
        
        Args:
            question: User's question
            context_hash: Hash of conversation context
            
        Returns:
            ConversationalResponse if cached, None otherwise
        """
        cache_key = self._generate_chat_key(question, context_hash)
        cached_response = self.chat_cache.get(cache_key)
        
        if cached_response:
            logger.debug(f"Cache hit for chat question: {question[:50]}...")
            # Update processing time to indicate cached response
            if hasattr(cached_response, 'processing_time_ms'):
                cached_response.processing_time_ms = 1.0  # Very fast for cached
            return cached_response
        
        return None
    
    def cache_chat_response(self, question: str, response: ConversationalResponse, 
                          context_hash: str = "", ttl: Optional[int] = None) -> None:
        """
        Cache chat response for future use.
        
        Args:
            question: User's question
            response: Chat response to cache
            context_hash: Hash of conversation context
            ttl: Optional TTL override
        """
        cache_key = self._generate_chat_key(question, context_hash)
        self.chat_cache.put(cache_key, response, ttl)
        logger.debug(f"Cached chat response for: {question[:50]}...")
    
    def get_query_result(self, sql: str) -> Optional[ExecuteResponse]:
        """
        Get cached query result.
        
        Args:
            sql: SQL query
            
        Returns:
            ExecuteResponse if cached, None otherwise
        """
        cache_key = self._generate_sql_key(sql)
        cached_result = self.query_cache.get(cache_key)
        
        if cached_result:
            logger.debug(f"Cache hit for SQL query: {sql[:50]}...")
            return cached_result
        
        return None
    
    def cache_query_result(self, sql: str, result: ExecuteResponse, ttl: Optional[int] = None) -> None:
        """
        Cache query result.
        
        Args:
            sql: SQL query
            result: Query result to cache
            ttl: Optional TTL override
        """
        cache_key = self._generate_sql_key(sql)
        self.query_cache.put(cache_key, result, ttl)
        logger.debug(f"Cached query result for: {sql[:50]}...")
    
    def get_llm_response(self, prompt: str, model: str = "default") -> Optional[str]:
        """
        Get cached LLM response.
        
        Args:
            prompt: LLM prompt
            model: Model identifier
            
        Returns:
            LLM response if cached, None otherwise
        """
        cache_key = self._generate_llm_key(prompt, model)
        cached_response = self.llm_cache.get(cache_key)
        
        if cached_response:
            logger.debug(f"Cache hit for LLM prompt: {prompt[:50]}...")
            return cached_response
        
        return None
    
    def cache_llm_response(self, prompt: str, response: str, model: str = "default", 
                          ttl: Optional[int] = None) -> None:
        """
        Cache LLM response.
        
        Args:
            prompt: LLM prompt
            response: LLM response to cache
            model: Model identifier
            ttl: Optional TTL override
        """
        cache_key = self._generate_llm_key(prompt, model)
        self.llm_cache.put(cache_key, response, ttl)
        logger.debug(f"Cached LLM response for: {prompt[:50]}...")
    
    def invalidate_chat_cache(self) -> None:
        """Invalidate all chat cache entries."""
        self.chat_cache.clear()
        logger.info("Chat cache invalidated")
    
    def invalidate_query_cache(self) -> None:
        """Invalidate all query cache entries."""
        self.query_cache.clear()
        logger.info("Query cache invalidated")
    
    def get_cache_stats(self) -> Dict[str, CacheStats]:
        """Get comprehensive cache statistics."""
        return {
            "chat_cache": self.chat_cache.get_stats(),
            "query_cache": self.query_cache.get_stats(),
            "llm_cache": self.llm_cache.get_stats()
        }
    
    def _generate_chat_key(self, question: str, context_hash: str) -> str:
        """Generate cache key for chat response."""
        # Normalize question for better cache hits
        normalized_question = self._normalize_question(question)
        combined = f"chat:{normalized_question}:{context_hash}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _generate_sql_key(self, sql: str) -> str:
        """Generate cache key for SQL query."""
        # Normalize SQL for better cache hits
        normalized_sql = self._normalize_sql(sql)
        return hashlib.md5(f"sql:{normalized_sql}".encode('utf-8')).hexdigest()
    
    def _generate_llm_key(self, prompt: str, model: str) -> str:
        """Generate cache key for LLM response."""
        combined = f"llm:{model}:{prompt}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _normalize_question(self, question: str) -> str:
        """Normalize question for better cache matching."""
        # Convert to lowercase and remove extra whitespace
        normalized = ' '.join(question.lower().strip().split())
        
        # Remove common variations that don't change meaning
        replacements = [
            ('?', ''),
            ('.', ''),
            (',', ''),
            ('!', ''),
            ('  ', ' ')
        ]
        
        for old, new in replacements:
            normalized = normalized.replace(old, new)
        
        return normalized.strip()
    
    def _normalize_sql(self, sql: str) -> str:
        """Normalize SQL for better cache matching."""
        # Remove extra whitespace and convert to uppercase
        normalized = ' '.join(sql.upper().strip().split())
        
        # Remove trailing semicolon
        if normalized.endswith(';'):
            normalized = normalized[:-1]
        
        return normalized
    
    def _periodic_cleanup(self) -> None:
        """Periodic cleanup of expired cache entries."""
        while True:
            try:
                time.sleep(60)  # Cleanup every minute
                
                chat_expired = self.chat_cache.cleanup_expired()
                query_expired = self.query_cache.cleanup_expired()
                llm_expired = self.llm_cache.cleanup_expired()
                
                total_expired = chat_expired + query_expired + llm_expired
                if total_expired > 0:
                    logger.debug(f"Cache cleanup: removed {total_expired} expired entries")
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")


# Global cache instance
_response_cache: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    """Get or create global response cache instance."""
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache()
    return _response_cache