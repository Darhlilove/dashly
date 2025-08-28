"""
Integration tests for SQL execution configuration with existing components.

This module tests that the configuration system properly integrates with
the SQL execution components and that configuration changes are properly
applied at runtime.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from backend.src.sql_execution_config import (
    SQLExecutionConfig,
    get_sql_execution_config,
    reload_config
)


class TestConfigurationIntegrationWithComponents:
    """Test configuration integration with SQL execution components."""
    
    def test_configuration_provides_correct_values_for_components(self):
        """Test that configuration provides correct values for component initialization."""
        # Set custom configuration via environment
        env_vars = {
            'QUERY_TIMEOUT_SECONDS': '60',
            'MAX_RESULT_ROWS': '5000',
            'MAX_CONCURRENT_QUERIES': '3',
            'MEMORY_LIMIT_MB': '256.0',
            'SLOW_QUERY_THRESHOLD_MS': '2500'
        }
        
        with patch.dict(os.environ, env_vars):
            config = reload_config()
            
            # Verify configuration values that would be used for component initialization
            assert config.query_timeout_seconds == 60
            assert config.max_result_rows == 5000
            assert config.max_concurrent_queries == 3
            assert config.memory_limit_mb == 256.0
            assert config.slow_query_threshold_ms == 2500
            
            # Test that these values would be passed correctly to components
            # (This simulates what happens in main.py without importing it)
            query_executor_params = {
                'timeout_seconds': config.query_timeout_seconds,
                'max_rows': config.max_result_rows,
                'max_concurrent': config.max_concurrent_queries,
                'memory_limit_mb': config.memory_limit_mb
            }
            
            performance_monitor_params = {
                'slow_query_threshold_ms': config.slow_query_threshold_ms
            }
            
            # Verify the parameters match expected values
            assert query_executor_params['timeout_seconds'] == 60
            assert query_executor_params['max_rows'] == 5000
            assert query_executor_params['max_concurrent'] == 3
            assert query_executor_params['memory_limit_mb'] == 256.0
            assert performance_monitor_params['slow_query_threshold_ms'] == 2500
    
    def test_runtime_configuration_update(self):
        """Test that configuration can be updated at runtime."""
        config = get_sql_execution_config()
        
        # Store original values
        original_timeout = config.query_timeout_seconds
        original_max_rows = config.max_result_rows
        
        # Update configuration
        config.update_from_dict({
            'query_timeout_seconds': 90,
            'max_result_rows': 15000
        })
        
        # Verify updates were applied
        assert config.query_timeout_seconds == 90
        assert config.max_result_rows == 15000
        
        # Verify utility methods work with new values
        assert config.get_timeout_for_operation('execute') == 90
    
    def test_configuration_validation_prevents_invalid_runtime_changes(self):
        """Test that configuration validation prevents invalid runtime changes."""
        config = get_sql_execution_config()
        
        # Attempt to set invalid values
        with pytest.raises(ValueError):
            config.update_from_dict({
                'query_timeout_seconds': -1,  # Invalid
                'max_result_rows': 5000  # Valid
            })
        
        # Verify that no changes were applied due to validation failure
        assert config.query_timeout_seconds != -1
    
    def test_configuration_environment_precedence(self):
        """Test that environment variables take precedence over defaults."""
        # Test with multiple environment variables
        env_vars = {
            'QUERY_TIMEOUT_SECONDS': '45',
            'MAX_RESULT_ROWS': '8000',
            'SLOW_QUERY_THRESHOLD_MS': '1500',
            'ENABLE_PERFORMANCE_LOGGING': 'false',
            'STRICT_VALIDATION_MODE': 'false',
            'DEBUG_MODE': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            config = SQLExecutionConfig()
            
            # Verify all environment values were loaded
            assert config.query_timeout_seconds == 45
            assert config.max_result_rows == 8000
            assert config.slow_query_threshold_ms == 1500
            assert config.enable_performance_logging is False
            assert config.strict_validation_mode is False
            assert config.debug_mode is True
            
            # Verify defaults are used for unset variables
            assert config.explain_timeout_seconds == 10  # default
            assert config.max_concurrent_queries == 5  # default


class TestConfigurationErrorHandling:
    """Test error handling in configuration system."""
    
    def test_configuration_handles_missing_environment_gracefully(self):
        """Test that missing environment variables don't cause errors."""
        # Clear any existing environment variables
        env_to_clear = [
            'QUERY_TIMEOUT_SECONDS', 'MAX_RESULT_ROWS', 'SLOW_QUERY_THRESHOLD_MS'
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise any exceptions
            config = SQLExecutionConfig()
            
            # Should use default values
            assert config.query_timeout_seconds == 30
            assert config.max_result_rows == 10000
            assert config.slow_query_threshold_ms == 1000
    
    def test_configuration_handles_partial_environment_variables(self):
        """Test configuration with only some environment variables set."""
        env_vars = {
            'QUERY_TIMEOUT_SECONDS': '75',
            # MAX_RESULT_ROWS not set - should use default
            'SLOW_QUERY_THRESHOLD_MS': '2000',
            # Other variables not set - should use defaults
        }
        
        with patch.dict(os.environ, env_vars):
            config = SQLExecutionConfig()
            
            # Verify set values are used
            assert config.query_timeout_seconds == 75
            assert config.slow_query_threshold_ms == 2000
            
            # Verify defaults are used for unset values
            assert config.max_result_rows == 10000
            assert config.max_concurrent_queries == 5
            assert config.enable_performance_logging is True
    
    def test_configuration_logs_invalid_values_appropriately(self):
        """Test that invalid environment values are logged but don't crash."""
        env_vars = {
            'QUERY_TIMEOUT_SECONDS': 'not_a_number',
            'MAX_RESULT_ROWS': 'invalid',
            'ENABLE_PERFORMANCE_LOGGING': 'maybe'
        }
        
        with patch.dict(os.environ, env_vars):
            # Should not raise exceptions
            config = SQLExecutionConfig()
            
            # Should use defaults for invalid values
            assert config.query_timeout_seconds == 30
            assert config.max_result_rows == 10000
            assert config.enable_performance_logging is False  # 'maybe' -> False


class TestConfigurationUtilityMethods:
    """Test utility methods in configuration system."""
    
    def test_timeout_operations_mapping(self):
        """Test that timeout operations return correct values."""
        config = SQLExecutionConfig(
            query_timeout_seconds=30,
            explain_timeout_seconds=15,
            connection_timeout_seconds=10,
            query_queue_timeout_seconds=60
        )
        
        assert config.get_timeout_for_operation('execute') == 30
        assert config.get_timeout_for_operation('explain') == 15
        assert config.get_timeout_for_operation('connection') == 10
        assert config.get_timeout_for_operation('queue') == 60
        assert config.get_timeout_for_operation('unknown') == 30  # defaults to execute
    
    def test_slow_query_detection_with_custom_threshold(self):
        """Test slow query detection with custom threshold."""
        config = SQLExecutionConfig(slow_query_threshold_ms=2500)
        
        assert config.is_slow_query(1000.0) is False
        assert config.is_slow_query(2500.0) is False  # Equal to threshold
        assert config.is_slow_query(2501.0) is True
        assert config.is_slow_query(5000.0) is True
    
    def test_query_logging_decision_logic(self):
        """Test query logging decision with various configurations."""
        # Test with all logging disabled
        config = SQLExecutionConfig(enable_query_logging=False)
        assert config.should_log_query() is False
        assert config.should_log_query(is_slow=True, has_error=True) is False
        
        # Test with log all queries enabled
        config = SQLExecutionConfig(
            enable_query_logging=True,
            log_all_queries=True
        )
        assert config.should_log_query() is True
        assert config.should_log_query(is_slow=False, has_error=False) is True
        
        # Test with selective logging (default behavior)
        config = SQLExecutionConfig(
            enable_query_logging=True,
            log_all_queries=False
        )
        assert config.should_log_query() is False
        assert config.should_log_query(is_slow=True) is True
        assert config.should_log_query(has_error=True) is True
        assert config.should_log_query(is_slow=True, has_error=True) is True


if __name__ == '__main__':
    pytest.main([__file__])