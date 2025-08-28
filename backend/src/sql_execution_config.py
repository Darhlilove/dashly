"""
Configuration management for SQL execution API.

This module provides centralized configuration for query execution settings,
timeouts, limits, and security settings with environment variable support
and validation.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SQLExecutionConfig:
    """
    Configuration class for SQL execution settings.
    
    Provides centralized management of query execution parameters including
    timeouts, limits, security settings, and performance monitoring thresholds.
    All settings can be overridden via environment variables.
    """
    
    # Query execution timeouts (Requirement 6.1)
    query_timeout_seconds: int = field(default=30)
    explain_timeout_seconds: int = field(default=10)
    
    # Result set limits (Requirement 6.2)
    max_result_rows: int = field(default=10000)
    max_result_size_mb: float = field(default=50.0)
    
    # Concurrent query limits (Requirement 6.3)
    max_concurrent_queries: int = field(default=5)
    query_queue_timeout_seconds: int = field(default=30)
    
    # Performance monitoring (Requirement 3.2)
    slow_query_threshold_ms: int = field(default=1000)
    enable_performance_logging: bool = field(default=True)
    log_all_queries: bool = field(default=False)
    
    # Memory limits (Requirement 6.4)
    memory_limit_mb: float = field(default=512.0)
    enable_memory_monitoring: bool = field(default=True)
    
    # Security settings
    strict_validation_mode: bool = field(default=True)
    enable_query_logging: bool = field(default=True)
    log_security_violations: bool = field(default=True)
    
    # Database connection settings
    connection_pool_size: int = field(default=5)
    connection_timeout_seconds: int = field(default=5)
    enable_connection_pooling: bool = field(default=True)
    
    # Query caching settings
    enable_explain_caching: bool = field(default=True)
    explain_cache_ttl_seconds: int = field(default=300)
    explain_cache_max_size: int = field(default=100)
    
    # Development and debugging
    debug_mode: bool = field(default=False)
    enable_query_profiling: bool = field(default=False)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._load_from_environment()
        self._validate_configuration()
        self._log_configuration()
    
    def _load_from_environment(self) -> None:
        """Load configuration values from environment variables."""
        env_mappings = {
            # Query execution timeouts
            'QUERY_TIMEOUT_SECONDS': ('query_timeout_seconds', int),
            'EXPLAIN_TIMEOUT_SECONDS': ('explain_timeout_seconds', int),
            
            # Result set limits
            'MAX_RESULT_ROWS': ('max_result_rows', int),
            'MAX_RESULT_SIZE_MB': ('max_result_size_mb', float),
            
            # Concurrent query limits
            'MAX_CONCURRENT_QUERIES': ('max_concurrent_queries', int),
            'QUERY_QUEUE_TIMEOUT_SECONDS': ('query_queue_timeout_seconds', int),
            
            # Performance monitoring
            'SLOW_QUERY_THRESHOLD_MS': ('slow_query_threshold_ms', int),
            'ENABLE_PERFORMANCE_LOGGING': ('enable_performance_logging', self._parse_bool),
            'LOG_ALL_QUERIES': ('log_all_queries', self._parse_bool),
            
            # Memory limits
            'MEMORY_LIMIT_MB': ('memory_limit_mb', float),
            'ENABLE_MEMORY_MONITORING': ('enable_memory_monitoring', self._parse_bool),
            
            # Security settings
            'STRICT_VALIDATION_MODE': ('strict_validation_mode', self._parse_bool),
            'ENABLE_QUERY_LOGGING': ('enable_query_logging', self._parse_bool),
            'LOG_SECURITY_VIOLATIONS': ('log_security_violations', self._parse_bool),
            
            # Database connection settings
            'CONNECTION_POOL_SIZE': ('connection_pool_size', int),
            'CONNECTION_TIMEOUT_SECONDS': ('connection_timeout_seconds', int),
            'ENABLE_CONNECTION_POOLING': ('enable_connection_pooling', self._parse_bool),
            
            # Query caching settings
            'ENABLE_EXPLAIN_CACHING': ('enable_explain_caching', self._parse_bool),
            'EXPLAIN_CACHE_TTL_SECONDS': ('explain_cache_ttl_seconds', int),
            'EXPLAIN_CACHE_MAX_SIZE': ('explain_cache_max_size', int),
            
            # Development and debugging
            'DEBUG_MODE': ('debug_mode', self._parse_bool),
            'ENABLE_QUERY_PROFILING': ('enable_query_profiling', self._parse_bool),
        }
        
        for env_var, (attr_name, converter) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    converted_value = converter(env_value)
                    setattr(self, attr_name, converted_value)
                    logger.debug(f"Loaded {attr_name} = {converted_value} from {env_var}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for {env_var}: {env_value}. Using default. Error: {e}")
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse boolean value from string."""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def _validate_configuration(self) -> None:
        """Validate configuration values and raise errors for invalid settings."""
        errors = []
        
        # Validate timeout settings
        if self.query_timeout_seconds <= 0:
            errors.append("query_timeout_seconds must be positive")
        if self.query_timeout_seconds > 300:  # 5 minutes max
            errors.append("query_timeout_seconds cannot exceed 300 seconds")
        
        if self.explain_timeout_seconds <= 0:
            errors.append("explain_timeout_seconds must be positive")
        if self.explain_timeout_seconds > 60:  # 1 minute max
            errors.append("explain_timeout_seconds cannot exceed 60 seconds")
        
        # Validate result limits
        if self.max_result_rows <= 0:
            errors.append("max_result_rows must be positive")
        if self.max_result_rows > 100000:  # 100k rows max
            errors.append("max_result_rows cannot exceed 100,000")
        
        if self.max_result_size_mb <= 0:
            errors.append("max_result_size_mb must be positive")
        if self.max_result_size_mb > 1000:  # 1GB max
            errors.append("max_result_size_mb cannot exceed 1000 MB")
        
        # Validate concurrent query limits
        if self.max_concurrent_queries <= 0:
            errors.append("max_concurrent_queries must be positive")
        if self.max_concurrent_queries > 50:  # Reasonable upper limit
            errors.append("max_concurrent_queries cannot exceed 50")
        
        if self.query_queue_timeout_seconds <= 0:
            errors.append("query_queue_timeout_seconds must be positive")
        
        # Validate performance settings
        if self.slow_query_threshold_ms <= 0:
            errors.append("slow_query_threshold_ms must be positive")
        
        # Validate memory limits
        if self.memory_limit_mb <= 0:
            errors.append("memory_limit_mb must be positive")
        if self.memory_limit_mb > 8192:  # 8GB max
            errors.append("memory_limit_mb cannot exceed 8192 MB")
        
        # Validate connection settings
        if self.connection_pool_size <= 0:
            errors.append("connection_pool_size must be positive")
        if self.connection_pool_size > 20:  # Reasonable upper limit
            errors.append("connection_pool_size cannot exceed 20")
        
        if self.connection_timeout_seconds <= 0:
            errors.append("connection_timeout_seconds must be positive")
        
        # Validate cache settings
        if self.explain_cache_ttl_seconds <= 0:
            errors.append("explain_cache_ttl_seconds must be positive")
        if self.explain_cache_max_size <= 0:
            errors.append("explain_cache_max_size must be positive")
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            logger.error(error_message)
            raise ValueError(error_message)
    
    def _log_configuration(self) -> None:
        """Log current configuration for debugging and monitoring."""
        if self.debug_mode:
            logger.info("SQL Execution Configuration:")
            logger.info(f"  Query timeout: {self.query_timeout_seconds}s")
            logger.info(f"  Max result rows: {self.max_result_rows:,}")
            logger.info(f"  Max concurrent queries: {self.max_concurrent_queries}")
            logger.info(f"  Slow query threshold: {self.slow_query_threshold_ms}ms")
            logger.info(f"  Memory limit: {self.memory_limit_mb}MB")
            logger.info(f"  Connection pool size: {self.connection_pool_size}")
            logger.info(f"  Strict validation: {self.strict_validation_mode}")
        else:
            logger.info(f"SQL execution configured: timeout={self.query_timeout_seconds}s, "
                       f"max_rows={self.max_result_rows:,}, concurrent={self.max_concurrent_queries}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'query_timeout_seconds': self.query_timeout_seconds,
            'explain_timeout_seconds': self.explain_timeout_seconds,
            'max_result_rows': self.max_result_rows,
            'max_result_size_mb': self.max_result_size_mb,
            'max_concurrent_queries': self.max_concurrent_queries,
            'query_queue_timeout_seconds': self.query_queue_timeout_seconds,
            'slow_query_threshold_ms': self.slow_query_threshold_ms,
            'enable_performance_logging': self.enable_performance_logging,
            'log_all_queries': self.log_all_queries,
            'memory_limit_mb': self.memory_limit_mb,
            'enable_memory_monitoring': self.enable_memory_monitoring,
            'strict_validation_mode': self.strict_validation_mode,
            'enable_query_logging': self.enable_query_logging,
            'log_security_violations': self.log_security_violations,
            'connection_pool_size': self.connection_pool_size,
            'connection_timeout_seconds': self.connection_timeout_seconds,
            'enable_connection_pooling': self.enable_connection_pooling,
            'enable_explain_caching': self.enable_explain_caching,
            'explain_cache_ttl_seconds': self.explain_cache_ttl_seconds,
            'explain_cache_max_size': self.explain_cache_max_size,
            'debug_mode': self.debug_mode,
            'enable_query_profiling': self.enable_query_profiling,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SQLExecutionConfig':
        """Create configuration from dictionary."""
        return cls(**config_dict)
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """Update configuration with values from dictionary."""
        # Store original values for rollback
        original_values = {}
        
        try:
            # Apply updates and store original values
            for key, value in updates.items():
                if hasattr(self, key):
                    original_values[key] = getattr(self, key)
                    setattr(self, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")
            
            # Validate after all updates
            self._validate_configuration()
            
        except ValueError as e:
            # Rollback all changes if validation fails
            for key, original_value in original_values.items():
                setattr(self, key, original_value)
            raise e
    
    def get_timeout_for_operation(self, operation: str) -> int:
        """Get timeout value for specific operation type."""
        timeouts = {
            'execute': self.query_timeout_seconds,
            'explain': self.explain_timeout_seconds,
            'connection': self.connection_timeout_seconds,
            'queue': self.query_queue_timeout_seconds,
        }
        return timeouts.get(operation, self.query_timeout_seconds)
    
    def is_slow_query(self, runtime_ms: float) -> bool:
        """Check if query execution time exceeds slow query threshold."""
        return runtime_ms > self.slow_query_threshold_ms
    
    def should_log_query(self, is_slow: bool = False, has_error: bool = False) -> bool:
        """Determine if query should be logged based on configuration."""
        if not self.enable_query_logging:
            return False
        
        if self.log_all_queries:
            return True
        
        # Log slow queries or queries with errors
        return is_slow or has_error


# Global configuration instance
_config_instance: Optional[SQLExecutionConfig] = None


def get_sql_execution_config() -> SQLExecutionConfig:
    """
    Get the global SQL execution configuration instance.
    
    Returns:
        SQLExecutionConfig: The global configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = SQLExecutionConfig()
    return _config_instance


def reload_config() -> SQLExecutionConfig:
    """
    Reload configuration from environment variables.
    
    Returns:
        SQLExecutionConfig: The reloaded configuration instance
    """
    global _config_instance
    _config_instance = SQLExecutionConfig()
    logger.info("SQL execution configuration reloaded")
    return _config_instance


def update_config(**kwargs) -> None:
    """
    Update global configuration with new values.
    
    Args:
        **kwargs: Configuration values to update
    """
    config = get_sql_execution_config()
    config.update_from_dict(kwargs)
    logger.info(f"SQL execution configuration updated: {list(kwargs.keys())}")


class ConfigurationManager:
    """
    Advanced configuration management with file-based configuration support.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to JSON configuration file
        """
        self.config_file = config_file
        self._config = SQLExecutionConfig()
    
    def load_from_file(self, config_file: str) -> None:
        """
        Load configuration from JSON file.
        
        Args:
            config_file: Path to JSON configuration file
        """
        import json
        
        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            return
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            self._config.update_from_dict(config_data)
            logger.info(f"Configuration loaded from: {config_file}")
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to load configuration from {config_file}: {e}")
            raise
    
    def save_to_file(self, config_file: str) -> None:
        """
        Save current configuration to JSON file.
        
        Args:
            config_file: Path to save configuration file
        """
        import json
        
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config.to_dict(), f, indent=2)
            
            logger.info(f"Configuration saved to: {config_file}")
            
        except (OSError, ValueError) as e:
            logger.error(f"Failed to save configuration to {config_file}: {e}")
            raise
    
    @property
    def config(self) -> SQLExecutionConfig:
        """Get the managed configuration instance."""
        return self._config
    
    def validate_runtime_config(self) -> bool:
        """
        Validate current runtime configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            self._config._validate_configuration()
            return True
        except ValueError as e:
            logger.error(f"Runtime configuration validation failed: {e}")
            return False