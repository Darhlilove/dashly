#!/usr/bin/env python3
"""
Secure configuration generator for Dashly.
Generates secure API keys and configuration templates.
"""

import os
import secrets
import string
from pathlib import Path


def generate_secure_api_key(length: int = 64) -> str:
    """Generate a cryptographically secure API key."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_env_file(output_path: str = ".env"):
    """Generate a secure .env file with random keys."""
    
    # Generate secure keys
    dashly_api_key = generate_secure_api_key(64)
    
    env_content = f"""# Dashly Backend Configuration - Generated {os.popen('date').read().strip()}
# IMPORTANT: Keep this file secure and never commit it to version control

# OpenRouter API Configuration
# Get your API key from: https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet:beta
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Database Configuration
DATABASE_PATH=data/dashly.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Security Configuration - SECURE RANDOM KEYS GENERATED
DASHLY_API_KEY={dashly_api_key}
REQUIRE_AUTH=true

# CORS Configuration (update with your actual frontend domains)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Environment Settings
DEBUG=false
LOG_LEVEL=info

# Rate Limiting (production values)
MAX_REQUESTS_PER_HOUR=500
MAX_UPLOADS_PER_HOUR=50

# Security Notes:
# 1. Replace OPENROUTER_API_KEY with your actual OpenRouter API key
# 2. Update ALLOWED_ORIGINS with your production frontend URLs
# 3. For production, consider using environment-specific configuration management
# 4. Monitor security logs regularly via /api/security/stats endpoint
"""

    # Write to file
    with open(output_path, 'w') as f:
        f.write(env_content)
    
    # Set secure file permissions (Unix-like systems)
    try:
        os.chmod(output_path, 0o600)  # Read/write for owner only
    except OSError:
        pass  # Windows or permission error
    
    return dashly_api_key


def validate_existing_config():
    """Validate existing configuration for security issues."""
    issues = []
    
    # Check if .env exists
    if not os.path.exists('.env'):
        issues.append("No .env file found. Run this script to generate one.")
        return issues
    
    # Read .env file
    with open('.env', 'r') as f:
        content = f.read()
    
    # Check for placeholder values
    if 'your_openrouter_api_key_here' in content:
        issues.append("OpenRouter API key is still set to placeholder value")
    
    if 'your_secure_random_key_here' in content:
        issues.append("Dashly API key is still set to placeholder value")
    
    # Check for weak API keys
    weak_patterns = ['demo', 'test', 'dev', '12345', 'password', 'admin']
    for line in content.split('\n'):
        if line.startswith('DASHLY_API_KEY='):
            api_key = line.split('=', 1)[1]
            if len(api_key) < 32:
                issues.append("Dashly API key is too short (minimum 32 characters)")
            if any(pattern in api_key.lower() for pattern in weak_patterns):
                issues.append("Dashly API key contains weak patterns")
    
    # Check authentication setting
    if 'REQUIRE_AUTH=false' in content:
        issues.append("Authentication is disabled (REQUIRE_AUTH=false)")
    
    # Check CORS settings
    if 'ALLOWED_ORIGINS=*' in content:
        issues.append("CORS allows all origins (*) - security risk")
    
    return issues


def main():
    """Main function to generate or validate configuration."""
    print("🔒 Dashly Security Configuration Generator")
    print("=" * 50)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        print("📋 Existing .env file found. Validating configuration...")
        issues = validate_existing_config()
        
        if issues:
            print("\n⚠️  Security Issues Found:")
            for issue in issues:
                print(f"   • {issue}")
            
            response = input("\n🔄 Generate new secure configuration? (y/N): ")
            if response.lower() != 'y':
                print("\n💡 To fix issues manually:")
                print("   • Generate secure API key: openssl rand -hex 32")
                print("   • Set REQUIRE_AUTH=true")
                print("   • Update ALLOWED_ORIGINS with your actual domains")
                print("   • Replace placeholder API keys with real values")
                return
        else:
            print("✅ Configuration appears secure!")
            return
    
    # Generate new configuration
    print("🔑 Generating secure configuration...")
    
    # Backup existing .env if it exists
    if os.path.exists('.env'):
        backup_path = '.env.backup'
        counter = 1
        while os.path.exists(backup_path):
            backup_path = f'.env.backup.{counter}'
            counter += 1
        
        os.rename('.env', backup_path)
        print(f"📁 Existing .env backed up to {backup_path}")
    
    # Generate new .env file
    api_key = generate_env_file()
    
    print("✅ Secure .env file generated!")
    print(f"🔑 Generated Dashly API Key: {api_key}")
    print("\n📝 Next Steps:")
    print("   1. Get your OpenRouter API key from: https://openrouter.ai/keys")
    print("   2. Replace 'your_openrouter_api_key_here' in .env with your actual key")
    print("   3. Update ALLOWED_ORIGINS with your production frontend URLs")
    print("   4. Test your configuration with: python -m backend.src.main")
    print("\n🔒 Security Reminders:")
    print("   • Never commit .env files to version control")
    print("   • Keep your API keys secure and rotate them regularly")
    print("   • Monitor security logs via /api/security/stats")
    print("   • Use HTTPS in production")


if __name__ == "__main__":
    main()