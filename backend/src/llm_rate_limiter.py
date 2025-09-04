"""
Rate limiter specifically for LLM API calls to prevent abuse and manage costs.
"""

import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque

try:
    from .logging_config import get_logger
    from .exceptions import ValidationError
except ImportError:
    from logging_config import get_logger
    from exceptions import ValidationError

logger = get_logger(__name__)


@dataclass
class LLMRateLimit:
    """Rate limit configuration for LLM calls."""
    max_calls_per_minute: int = 10
    max_calls_per_hour: int = 100
    max_tokens_per_hour: int = 50000
    cooldown_seconds: int = 60


@dataclass
class CallRecord:
    """Record of an LLM API call."""
    timestamp: float
    tokens_used: int = 0
    model: str = ""
    success: bool = True


class LLMRateLimiter:
    """Rate limiter for LLM API calls with token tracking."""
    
    def __init__(self, rate_limit: Optional[LLMRateLimit] = None):
        """
        Initialize LLM rate limiter.
        
        Args:
            rate_limit: Rate limit configuration
        """
        self.rate_limit = rate_limit or LLMRateLimit()
        
        # Track calls per client/session (using IP or session ID)
        self.call_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.token_usage: Dict[str, int] = defaultdict(int)
        self.blocked_until: Dict[str, float] = {}
        
        logger.info(f"LLM rate limiter initialized: {self.rate_limit.max_calls_per_minute}/min, {self.rate_limit.max_calls_per_hour}/hour")
    
    async def check_rate_limit(self, client_id: str, estimated_tokens: int = 1000) -> bool:
        """
        Check if client can make an LLM call within rate limits.
        
        Args:
            client_id: Unique identifier for the client (IP, session, etc.)
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            bool: True if call is allowed, False if rate limited
            
        Raises:
            ValidationError: If rate limit is exceeded
        """
        current_time = time.time()
        
        # Check if client is in cooldown period
        if client_id in self.blocked_until:
            if current_time < self.blocked_until[client_id]:
                remaining = int(self.blocked_until[client_id] - current_time)
                logger.warning(f"Client {client_id} is rate limited for {remaining} more seconds")
                raise ValidationError(f"Rate limit exceeded. Try again in {remaining} seconds.")
            else:
                # Cooldown period expired
                del self.blocked_until[client_id]
        
        # Clean old records
        self._clean_old_records(client_id, current_time)
        
        # Check per-minute limit
        minute_calls = self._count_calls_in_window(client_id, current_time, 60)
        if minute_calls >= self.rate_limit.max_calls_per_minute:
            self._apply_cooldown(client_id, current_time)
            logger.warning(f"Client {client_id} exceeded per-minute limit: {minute_calls}/{self.rate_limit.max_calls_per_minute}")
            raise ValidationError(f"Too many requests per minute. Limit: {self.rate_limit.max_calls_per_minute}/min")
        
        # Check per-hour limit
        hour_calls = self._count_calls_in_window(client_id, current_time, 3600)
        if hour_calls >= self.rate_limit.max_calls_per_hour:
            self._apply_cooldown(client_id, current_time)
            logger.warning(f"Client {client_id} exceeded per-hour limit: {hour_calls}/{self.rate_limit.max_calls_per_hour}")
            raise ValidationError(f"Too many requests per hour. Limit: {self.rate_limit.max_calls_per_hour}/hour")
        
        # Check token usage per hour
        hour_tokens = self._count_tokens_in_window(client_id, current_time, 3600)
        if hour_tokens + estimated_tokens > self.rate_limit.max_tokens_per_hour:
            self._apply_cooldown(client_id, current_time)
            logger.warning(f"Client {client_id} would exceed token limit: {hour_tokens + estimated_tokens}/{self.rate_limit.max_tokens_per_hour}")
            raise ValidationError(f"Token limit would be exceeded. Limit: {self.rate_limit.max_tokens_per_hour}/hour")
        
        return True
    
    def record_call(self, client_id: str, tokens_used: int = 0, model: str = "", success: bool = True):
        """
        Record an LLM API call for rate limiting tracking.
        
        Args:
            client_id: Unique identifier for the client
            tokens_used: Actual tokens used in the call
            model: Model used for the call
            success: Whether the call was successful
        """
        current_time = time.time()
        
        call_record = CallRecord(
            timestamp=current_time,
            tokens_used=tokens_used,
            model=model,
            success=success
        )
        
        self.call_history[client_id].append(call_record)
        
        if success and tokens_used > 0:
            # Update token usage tracking
            self.token_usage[client_id] = self._count_tokens_in_window(client_id, current_time, 3600)
        
        logger.debug(f"Recorded LLM call for {client_id}: {tokens_used} tokens, model: {model}, success: {success}")
    
    def _clean_old_records(self, client_id: str, current_time: float):
        """Remove records older than 1 hour."""
        if client_id not in self.call_history:
            return
        
        # Remove records older than 1 hour
        cutoff_time = current_time - 3600
        while (self.call_history[client_id] and 
               self.call_history[client_id][0].timestamp < cutoff_time):
            self.call_history[client_id].popleft()
    
    def _count_calls_in_window(self, client_id: str, current_time: float, window_seconds: int) -> int:
        """Count calls within the specified time window."""
        if client_id not in self.call_history:
            return 0
        
        cutoff_time = current_time - window_seconds
        count = 0
        
        for record in reversed(self.call_history[client_id]):
            if record.timestamp >= cutoff_time:
                count += 1
            else:
                break  # Records are ordered by timestamp
        
        return count
    
    def _count_tokens_in_window(self, client_id: str, current_time: float, window_seconds: int) -> int:
        """Count tokens used within the specified time window."""
        if client_id not in self.call_history:
            return 0
        
        cutoff_time = current_time - window_seconds
        total_tokens = 0
        
        for record in reversed(self.call_history[client_id]):
            if record.timestamp >= cutoff_time and record.success:
                total_tokens += record.tokens_used
            elif record.timestamp < cutoff_time:
                break  # Records are ordered by timestamp
        
        return total_tokens
    
    def _apply_cooldown(self, client_id: str, current_time: float):
        """Apply cooldown period to a client."""
        self.blocked_until[client_id] = current_time + self.rate_limit.cooldown_seconds
        logger.info(f"Applied {self.rate_limit.cooldown_seconds}s cooldown to client {client_id}")
    
    def get_client_stats(self, client_id: str) -> Dict[str, int]:
        """Get rate limiting statistics for a client."""
        current_time = time.time()
        self._clean_old_records(client_id, current_time)
        
        minute_calls = self._count_calls_in_window(client_id, current_time, 60)
        hour_calls = self._count_calls_in_window(client_id, current_time, 3600)
        hour_tokens = self._count_tokens_in_window(client_id, current_time, 3600)
        
        cooldown_remaining = 0
        if client_id in self.blocked_until:
            cooldown_remaining = max(0, int(self.blocked_until[client_id] - current_time))
        
        return {
            "calls_per_minute": minute_calls,
            "calls_per_hour": hour_calls,
            "tokens_per_hour": hour_tokens,
            "cooldown_remaining": cooldown_remaining,
            "max_calls_per_minute": self.rate_limit.max_calls_per_minute,
            "max_calls_per_hour": self.rate_limit.max_calls_per_hour,
            "max_tokens_per_hour": self.rate_limit.max_tokens_per_hour
        }
    
    def get_global_stats(self) -> Dict[str, int]:
        """Get global rate limiting statistics."""
        current_time = time.time()
        
        total_clients = len(self.call_history)
        active_clients = 0
        total_calls_last_hour = 0
        total_tokens_last_hour = 0
        blocked_clients = len(self.blocked_until)
        
        for client_id in self.call_history:
            self._clean_old_records(client_id, current_time)
            hour_calls = self._count_calls_in_window(client_id, current_time, 3600)
            if hour_calls > 0:
                active_clients += 1
                total_calls_last_hour += hour_calls
                total_tokens_last_hour += self._count_tokens_in_window(client_id, current_time, 3600)
        
        return {
            "total_clients": total_clients,
            "active_clients_last_hour": active_clients,
            "total_calls_last_hour": total_calls_last_hour,
            "total_tokens_last_hour": total_tokens_last_hour,
            "blocked_clients": blocked_clients
        }


# Global LLM rate limiter instance
llm_rate_limiter = LLMRateLimiter()