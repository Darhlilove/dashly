#!/usr/bin/env python3
"""
Demonstration script for SQL execution configuration system.

This script shows how to use the configuration system including:
- Loading configuration from environment variables
- Runtime configuration updates
- Configuration validation
- File-based configuration management
"""

import os
import tempfile
from pathlib import Path

from sql_execution_config import (
    SQLExecutionConfig,
    get_sql_execution_config,
    reload_config,
    update_config,
    ConfigurationManager
)


def demo_basic_configuration():
    """Demonstrate basic configuration usage."""
    print("=== Basic Configuration Demo ===")
    
    # Get default configuration
    config = get_sql_execution_config()
    print(f"Default query timeout: {config.query_timeout_seconds}s")
    print(f"Default max result rows: {config.max_result_rows:,}")
    print(f"Default slow query threshold: {config.slow_query_threshold_ms}ms")
    print(f"Default concurrent queries: {config.max_concurrent_queries}")
    print()


def demo_environment_configuration():
    """Demonstrate configuration loading from environment variables."""
    print("=== Environment Configuration Demo ===")
    
    # Set environment variables
    os.environ.update({
        'QUERY_TIMEOUT_SECONDS': '60',
        'MAX_RESULT_ROWS': '5000',
        'SLOW_QUERY_THRESHOLD_MS': '2000',
        'ENABLE_PERFORMANCE_LOGGING': 'false',
        'DEBUG_MODE': 'true'
    })
    
    # Reload configuration to pick up environment changes
    config = reload_config()
    print(f"Environment query timeout: {config.query_timeout_seconds}s")
    print(f"Environment max result rows: {config.max_result_rows:,}")
    print(f"Environment slow query threshold: {config.slow_query_threshold_ms}ms")
    print(f"Environment performance logging: {config.enable_performance_logging}")
    print(f"Environment debug mode: {config.debug_mode}")
    print()


def demo_runtime_configuration_updates():
    """Demonstrate runtime configuration updates."""
    print("=== Runtime Configuration Updates Demo ===")
    
    config = get_sql_execution_config()
    print(f"Before update - timeout: {config.query_timeout_seconds}s")
    
    # Update configuration at runtime
    update_config(
        query_timeout_seconds=90,
        max_result_rows=15000,
        slow_query_threshold_ms=1500
    )
    
    print(f"After update - timeout: {config.query_timeout_seconds}s")
    print(f"After update - max rows: {config.max_result_rows:,}")
    print(f"After update - slow threshold: {config.slow_query_threshold_ms}ms")
    print()


def demo_configuration_validation():
    """Demonstrate configuration validation."""
    print("=== Configuration Validation Demo ===")
    
    config = get_sql_execution_config()
    
    try:
        # Try to set invalid configuration
        config.update_from_dict({
            'query_timeout_seconds': -1,  # Invalid
            'max_result_rows': 8000  # Valid
        })
        print("ERROR: Validation should have failed!")
    except ValueError as e:
        print(f"✓ Validation correctly prevented invalid configuration: {e}")
        print(f"Configuration unchanged - timeout: {config.query_timeout_seconds}s")
        print(f"Configuration unchanged - max rows: {config.max_result_rows:,}")
    print()


def demo_utility_methods():
    """Demonstrate configuration utility methods."""
    print("=== Configuration Utility Methods Demo ===")
    
    config = SQLExecutionConfig(
        slow_query_threshold_ms=1500,
        enable_query_logging=True,
        log_all_queries=False
    )
    
    # Test slow query detection
    print(f"Is 1000ms slow? {config.is_slow_query(1000.0)}")
    print(f"Is 2000ms slow? {config.is_slow_query(2000.0)}")
    
    # Test timeout operations
    print(f"Execute timeout: {config.get_timeout_for_operation('execute')}s")
    print(f"Explain timeout: {config.get_timeout_for_operation('explain')}s")
    
    # Test logging decisions
    print(f"Should log normal query? {config.should_log_query()}")
    print(f"Should log slow query? {config.should_log_query(is_slow=True)}")
    print(f"Should log error query? {config.should_log_query(has_error=True)}")
    print()


def demo_file_configuration():
    """Demonstrate file-based configuration management."""
    print("=== File-Based Configuration Demo ===")
    
    # Create a temporary configuration file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_file = f.name
    
    try:
        # Create configuration manager
        manager = ConfigurationManager()
        
        # Update configuration
        manager.config.query_timeout_seconds = 120
        manager.config.max_result_rows = 20000
        manager.config.debug_mode = True
        
        # Save to file
        manager.save_to_file(config_file)
        print(f"Configuration saved to: {config_file}")
        
        # Create new manager and load from file
        new_manager = ConfigurationManager()
        print(f"Before loading - timeout: {new_manager.config.query_timeout_seconds}s")
        
        new_manager.load_from_file(config_file)
        print(f"After loading - timeout: {new_manager.config.query_timeout_seconds}s")
        print(f"After loading - max rows: {new_manager.config.max_result_rows:,}")
        print(f"After loading - debug mode: {new_manager.config.debug_mode}")
        
    finally:
        # Clean up
        if os.path.exists(config_file):
            os.unlink(config_file)
    print()


def demo_configuration_serialization():
    """Demonstrate configuration serialization."""
    print("=== Configuration Serialization Demo ===")
    
    config = SQLExecutionConfig(
        query_timeout_seconds=75,
        max_result_rows=12000,
        enable_performance_logging=False,
        debug_mode=True
    )
    
    # Convert to dictionary
    config_dict = config.to_dict()
    print("Configuration as dictionary:")
    for key, value in sorted(config_dict.items()):
        if key in ['query_timeout_seconds', 'max_result_rows', 'enable_performance_logging', 'debug_mode']:
            print(f"  {key}: {value}")
    
    # Create new configuration from dictionary
    new_config = SQLExecutionConfig.from_dict(config_dict)
    print(f"\nRecreated config - timeout: {new_config.query_timeout_seconds}s")
    print(f"Recreated config - max rows: {new_config.max_result_rows:,}")
    print()


def main():
    """Run all configuration demos."""
    print("SQL Execution Configuration System Demo")
    print("=" * 50)
    print()
    
    demo_basic_configuration()
    demo_environment_configuration()
    demo_runtime_configuration_updates()
    demo_configuration_validation()
    demo_utility_methods()
    demo_file_configuration()
    demo_configuration_serialization()
    
    print("Demo completed successfully!")


if __name__ == '__main__':
    main()