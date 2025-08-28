"""
Tests for SQL execution configuration management.

This module tests the configuration system including environment variable loading,
validation, runtime configuration management, and file-based configuration.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from backend.src.sql_execution_config import (
    SQLExecutionConfig,
    get_sql_execution_config,
    reload_config,
    update_config,
    ConfigurationManager,
    _config_instance
)


class TestSQLExecutionConfig:
    """Test cases for SQLExecutionConfig class."""
    
    def test_default_configuration(self):
        """Test that default configuration values are set correctly."""
        config = SQLExecutionConfig()
        
        # Test default timeout values (Requirement 6.1)
        assert config.query_timeout_seconds == 30
        assert config.explain_timeout_seconds == 10
        
        # Test default result limits (Requirement 6.2)
        assert config.max_result_rows == 10000
        assert config.max_result_size_mb == 50.0
        
        # Test default concurrent limits (Requirement 6.3)
        assert config.max_concurrent_queries == 5
        assert config.query_queue_timeout_seconds == 30
        
        # Test default performance settings (Requirement 3.2)
        assert config.slow_query_threshold_ms == 1000
        assert config.enable_performance_logging is True
        
        # Test default security settings
        assert config.strict_validation_mode is True
        assert config.enable_query_logging is True
    
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            'QUERY_TIMEOUT_SECONDS': '45',
            'MAX_RESULT_ROWS': '5000',
            'MAX_CONCURRENT_QUERIES': '3',
            'SLOW_QUERY_THRESHOLD_MS': '2000',
            'ENABLE_PERFORMANCE_LOGGING': 'false',
            'STRICT_VALIDATION_MODE': 'false',
            'DEBUG_MODE': 'true',
        }
        
        with patch.dict(os.environ, env_vars):
            config = SQLExecutionConfig()
            
            assert config.query_timeout_seconds == 45
            assert config.max_result_rows == 5000
            assert config.max_concurrent_queries == 3
            assert config.slow_query_threshold_ms == 2000
            assert config.enable_performance_logging is False
            assert config.strict_validation_mode is False
            assert config.debug_mode is True
    
    def test_boolean_parsing(self):
        """Test parsing of boolean values from environment variables."""
        test_cases = [
            ('true', True),
            ('True', True),
            ('TRUE', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('enabled', True),
            ('false', False),
            ('False', False),
            ('FALSE', False),
            ('0', False),
            ('no', False),
            ('off', False),
            ('disabled', False),
            ('invalid', False),
        ]
        
        for env_value, expected in test_cases:
            assert SQLExecutionConfig._parse_bool(env_value) == expected
    
    def test_configuration_validation_success(self):
        """Test successful configuration validation."""
        config = SQLExecutionConfig(
            query_timeout_seconds=60,
            max_result_rows=5000,
            max_concurrent_queries=10,
            slow_query_threshold_ms=500,
            memory_limit_mb=256.0
        )
        
        # Should not raise any exceptions
        config._validate_configuration()
    
    def test_configuration_validation_failures(self):
        """Test configuration validation with invalid values."""
        # Test negative timeout
        with pytest.raises(ValueError, match="query_timeout_seconds must be positive"):
            SQLExecutionConfig(query_timeout_seconds=-1)
        
        # Test excessive timeout
        with pytest.raises(ValueError, match="query_timeout_seconds cannot exceed 300 seconds"):
            SQLExecutionConfig(query_timeout_seconds=400)
        
        # Test negative result rows
        with pytest.raises(ValueError, match="max_result_rows must be positive"):
            SQLExecutionConfig(max_result_rows=-1)
        
        # Test excessive result rows
        with pytest.raises(ValueError, match="max_result_rows cannot exceed 100,000"):
            SQLExecutionConfig(max_result_rows=200000)
        
        # Test negative concurrent queries
        with pytest.raises(ValueError, match="max_concurrent_queries must be positive"):
            SQLExecutionConfig(max_concurrent_queries=0)
        
        # Test excessive concurrent queries
        with pytest.raises(ValueError, match="max_concurrent_queries cannot exceed 50"):
            SQLExecutionConfig(max_concurrent_queries=100)
        
        # Test negative memory limit
        with pytest.raises(ValueError, match="memory_limit_mb must be positive"):
            SQLExecutionConfig(memory_limit_mb=-1.0)
        
        # Test excessive memory limit
        with pytest.raises(ValueError, match="memory_limit_mb cannot exceed 8192 MB"):
            SQLExecutionConfig(memory_limit_mb=10000.0)
    
    def test_invalid_environment_variables(self):
        """Test handling of invalid environment variable values."""
        env_vars = {
            'QUERY_TIMEOUT_SECONDS': 'invalid',
            'MAX_RESULT_ROWS': 'not_a_number',
            'ENABLE_PERFORMANCE_LOGGING': 'maybe',
        }
        
        with patch.dict(os.environ, env_vars):
            # Should use default values when environment variables are invalid
            config = SQLExecutionConfig()
            
            assert config.query_timeout_seconds == 30  # default
            assert config.max_result_rows == 10000  # default
            assert config.enable_performance_logging is False  # 'maybe' parses to False
    
    def test_to_dict_conversion(self):
        """Test converting configuration to dictionary."""
        config = SQLExecutionConfig(
            query_timeout_seconds=45,
            max_result_rows=5000,
            debug_mode=True
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['query_timeout_seconds'] == 45
        assert config_dict['max_result_rows'] == 5000
        assert config_dict['debug_mode'] is True
        assert 'slow_query_threshold_ms' in config_dict
    
    def test_from_dict_creation(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            'query_timeout_seconds': 60,
            'max_result_rows': 8000,
            'enable_performance_logging': False,
            'debug_mode': True
        }
        
        config = SQLExecutionConfig.from_dict(config_dict)
        
        assert config.query_timeout_seconds == 60
        assert config.max_result_rows == 8000
        assert config.enable_performance_logging is False
        assert config.debug_mode is True
    
    def test_update_from_dict(self):
        """Test updating configuration from dictionary."""
        config = SQLExecutionConfig()
        original_timeout = config.query_timeout_seconds
        
        updates = {
            'query_timeout_seconds': 90,
            'max_result_rows': 15000,
            'unknown_key': 'should_be_ignored'
        }
        
        config.update_from_dict(updates)
        
        assert config.query_timeout_seconds == 90
        assert config.max_result_rows == 15000
        # Other values should remain unchanged
        assert config.explain_timeout_seconds == 10
    
    def test_get_timeout_for_operation(self):
        """Test getting timeout values for specific operations."""
        config = SQLExecutionConfig(
            query_timeout_seconds=30,
            explain_timeout_seconds=10,
            connection_timeout_seconds=5,
            query_queue_timeout_seconds=60
        )
        
        assert config.get_timeout_for_operation('execute') == 30
        assert config.get_timeout_for_operation('explain') == 10
        assert config.get_timeout_for_operation('connection') == 5
        assert config.get_timeout_for_operation('queue') == 60
        assert config.get_timeout_for_operation('unknown') == 30  # default
    
    def test_is_slow_query(self):
        """Test slow query detection."""
        config = SQLExecutionConfig(slow_query_threshold_ms=1000)
        
        assert config.is_slow_query(500.0) is False
        assert config.is_slow_query(1000.0) is False
        assert config.is_slow_query(1001.0) is True
        assert config.is_slow_query(2500.0) is True
    
    def test_should_log_query(self):
        """Test query logging decision logic."""
        # Test with logging disabled
        config = SQLExecutionConfig(enable_query_logging=False)
        assert config.should_log_query() is False
        assert config.should_log_query(is_slow=True) is False
        assert config.should_log_query(has_error=True) is False
        
        # Test with log all queries enabled
        config = SQLExecutionConfig(
            enable_query_logging=True,
            log_all_queries=True
        )
        assert config.should_log_query() is True
        assert config.should_log_query(is_slow=False, has_error=False) is True
        
        # Test with selective logging
        config = SQLExecutionConfig(
            enable_query_logging=True,
            log_all_queries=False
        )
        assert config.should_log_query() is False
        assert config.should_log_query(is_slow=True) is True
        assert config.should_log_query(has_error=True) is True
        assert config.should_log_query(is_slow=True, has_error=True) is True


class TestGlobalConfigurationFunctions:
    """Test cases for global configuration management functions."""
    
    def setup_method(self):
        """Reset global configuration before each test."""
        global _config_instance
        _config_instance = None
    
    def test_get_sql_execution_config_singleton(self):
        """Test that get_sql_execution_config returns singleton instance."""
        config1 = get_sql_execution_config()
        config2 = get_sql_execution_config()
        
        assert config1 is config2
        assert isinstance(config1, SQLExecutionConfig)
    
    def test_reload_config(self):
        """Test configuration reloading."""
        # Get initial config
        config1 = get_sql_execution_config()
        original_timeout = config1.query_timeout_seconds
        
        # Modify environment and reload
        with patch.dict(os.environ, {'QUERY_TIMEOUT_SECONDS': '120'}):
            config2 = reload_config()
            
            assert config2 is not config1  # New instance
            assert config2.query_timeout_seconds == 120
            
            # Subsequent calls should return the new instance
            config3 = get_sql_execution_config()
            assert config3 is config2
    
    def test_update_config(self):
        """Test updating global configuration."""
        config = get_sql_execution_config()
        original_timeout = config.query_timeout_seconds
        
        update_config(
            query_timeout_seconds=75,
            max_result_rows=7500
        )
        
        # Same instance should be updated
        assert config.query_timeout_seconds == 75
        assert config.max_result_rows == 7500
    
    def test_update_config_validation(self):
        """Test that update_config validates new values."""
        with pytest.raises(ValueError):
            update_config(query_timeout_seconds=-1)


class TestConfigurationManager:
    """Test cases for ConfigurationManager class."""
    
    def test_initialization(self):
        """Test ConfigurationManager initialization."""
        manager = ConfigurationManager()
        
        assert isinstance(manager.config, SQLExecutionConfig)
        assert manager.config_file is None
    
    def test_load_from_file_success(self):
        """Test successful configuration loading from file."""
        config_data = {
            'query_timeout_seconds': 90,
            'max_result_rows': 8000,
            'enable_performance_logging': False
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigurationManager()
            manager.load_from_file(config_file)
            
            assert manager.config.query_timeout_seconds == 90
            assert manager.config.max_result_rows == 8000
            assert manager.config.enable_performance_logging is False
        finally:
            os.unlink(config_file)
    
    def test_load_from_file_not_found(self):
        """Test loading from non-existent file."""
        manager = ConfigurationManager()
        
        # Should not raise exception, just log warning
        manager.load_from_file('/nonexistent/config.json')
        
        # Configuration should remain at defaults
        assert manager.config.query_timeout_seconds == 30
    
    def test_load_from_file_invalid_json(self):
        """Test loading from file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json content')
            config_file = f.name
        
        try:
            manager = ConfigurationManager()
            
            with pytest.raises(json.JSONDecodeError):
                manager.load_from_file(config_file)
        finally:
            os.unlink(config_file)
    
    def test_save_to_file_success(self):
        """Test successful configuration saving to file."""
        manager = ConfigurationManager()
        manager.config.query_timeout_seconds = 120
        manager.config.max_result_rows = 15000
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'test_config.json')
            manager.save_to_file(config_file)
            
            # Verify file was created and contains correct data
            assert os.path.exists(config_file)
            
            with open(config_file, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['query_timeout_seconds'] == 120
            assert saved_data['max_result_rows'] == 15000
    
    def test_save_to_file_creates_directory(self):
        """Test that save_to_file creates parent directories."""
        manager = ConfigurationManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'subdir', 'config.json')
            manager.save_to_file(config_file)
            
            assert os.path.exists(config_file)
            assert os.path.exists(os.path.dirname(config_file))
    
    def test_validate_runtime_config_success(self):
        """Test successful runtime configuration validation."""
        manager = ConfigurationManager()
        
        assert manager.validate_runtime_config() is True
    
    def test_validate_runtime_config_failure(self):
        """Test runtime configuration validation failure."""
        manager = ConfigurationManager()
        
        # Set invalid configuration
        manager.config.query_timeout_seconds = -1
        
        assert manager.validate_runtime_config() is False


class TestConfigurationIntegration:
    """Integration tests for configuration system."""
    
    def test_configuration_with_environment_override(self):
        """Test complete configuration flow with environment overrides."""
        env_vars = {
            'QUERY_TIMEOUT_SECONDS': '45',
            'MAX_RESULT_ROWS': '5000',
            'SLOW_QUERY_THRESHOLD_MS': '2000',
            'ENABLE_PERFORMANCE_LOGGING': 'false',
            'DEBUG_MODE': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            config = SQLExecutionConfig()
            
            # Verify environment variables were loaded
            assert config.query_timeout_seconds == 45
            assert config.max_result_rows == 5000
            assert config.slow_query_threshold_ms == 2000
            assert config.enable_performance_logging is False
            assert config.debug_mode is True
            
            # Verify utility methods work correctly
            assert config.is_slow_query(1500.0) is False
            assert config.is_slow_query(2500.0) is True
            assert config.get_timeout_for_operation('execute') == 45
            assert config.should_log_query() is False
            assert config.should_log_query(is_slow=True) is True  # slow queries are logged even when log_all_queries=False
    
    def test_configuration_file_roundtrip(self):
        """Test saving and loading configuration maintains consistency."""
        original_config = SQLExecutionConfig(
            query_timeout_seconds=75,
            max_result_rows=12000,
            enable_performance_logging=False,
            debug_mode=True
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'roundtrip_config.json')
            
            # Save configuration
            manager = ConfigurationManager()
            manager._config = original_config
            manager.save_to_file(config_file)
            
            # Load into new manager
            new_manager = ConfigurationManager()
            new_manager.load_from_file(config_file)
            
            # Verify configurations match
            assert new_manager.config.query_timeout_seconds == 75
            assert new_manager.config.max_result_rows == 12000
            assert new_manager.config.enable_performance_logging is False
            assert new_manager.config.debug_mode is True
            
            # Verify other defaults are preserved
            assert new_manager.config.explain_timeout_seconds == 10
            assert new_manager.config.max_concurrent_queries == 5


if __name__ == '__main__':
    pytest.main([__file__])