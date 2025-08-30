#!/usr/bin/env python3
"""
Configuration validation script for Dashly backend.
"""

import os
import sys
from pathlib import Path

def validate_environment():
    """Validate environment configuration."""
    print("🔍 Validating Dashly Backend Configuration...")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    print("✅ .env file found")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required environment variables
    required_vars = {
        "OPENROUTER_API_KEY": "OpenRouter API key for LLM integration",
        "OPENROUTER_MODEL": "OpenRouter model selection",
        "OPENROUTER_BASE_URL": "OpenRouter API base URL"
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value == "your_openrouter_api_key_here":
            missing_vars.append(f"{var} ({description})")
            print(f"❌ {var}: Missing or placeholder value")
        else:
            # Mask API key for security
            if "API_KEY" in var:
                masked_value = value[:8] + "..." + value[-8:] if len(value) > 16 else "***"
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
    
    if missing_vars:
        print("\n❌ Configuration Issues Found:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease update your .env file with valid values.")
        return False
    
    # Test OpenRouter API key format
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key.startswith("sk-or-v1-"):
        print("⚠️  Warning: API key doesn't match expected OpenRouter format (sk-or-v1-...)")
    
    # Check data directory
    data_dir = Path("data")
    if not data_dir.exists():
        print("📁 Creating data directory...")
        data_dir.mkdir(exist_ok=True)
    print("✅ Data directory ready")
    
    # Check if demo data exists
    demo_file = data_dir / "demo_sales.csv"
    if demo_file.exists():
        print("✅ Demo data file found")
    else:
        print("ℹ️  Demo data file not found (will be created on first use)")
    
    print("\n🎉 Configuration validation completed successfully!")
    return True

def test_imports():
    """Test that all required modules can be imported."""
    print("\n🔍 Testing Python imports...")
    
    required_modules = [
        "fastapi",
        "uvicorn", 
        "duckdb",
        "pandas",
        "httpx",
        "pydantic",
        "python_multipart"
    ]
    
    failed_imports = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            failed_imports.append(f"{module}: {str(e)}")
            print(f"❌ {module}: Import failed")
    
    if failed_imports:
        print("\n❌ Import Issues Found:")
        for failure in failed_imports:
            print(f"  - {failure}")
        print("\nPlease run: pip install -r requirements.txt")
        return False
    
    print("✅ All required modules imported successfully")
    return True

def main():
    """Main validation function."""
    print("=" * 50)
    print("Dashly Backend Configuration Validator")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success = True
    
    # Test imports first
    if not test_imports():
        success = False
    
    # Validate environment
    if not validate_environment():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All validations passed! Backend is ready to run.")
        print("\nTo start the backend:")
        print("  source venv/bin/activate")
        print("  python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("❌ Validation failed. Please fix the issues above.")
        sys.exit(1)
    print("=" * 50)

if __name__ == "__main__":
    main()