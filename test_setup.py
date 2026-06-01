"""
Mirror Pupil v5.1 - Setup Test
Quick verification that everything is configured correctly.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()


def test_env_file():
    """Check if .env file exists and has required variables."""
    print("Testing .env file...")
    
    if not Path(".env").exists():
        print("  ❌ .env file not found")
        print("  → Run: python setup.py")
        return False
    
    required = [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_PHONE",
        "TDLIB_ENCRYPTION_KEY",
        "DATABASE_URL"
    ]
    
    missing = []
    placeholder_values = [
        "your_api_id_here",
        "your_api_hash_here",
        "your_random_encryption_key_here",
        "postgresql://user:password@host.neon.tech/dbname"
    ]
    
    for var in required:
        value = os.getenv(var, "")
        if not value or any(placeholder in value for placeholder in placeholder_values):
            missing.append(var)
    
    if missing:
        print(f"  ❌ Missing or placeholder values: {', '.join(missing)}")
        print("  → Edit .env and fill in real values")
        return False
    
    print("  ✓ .env file configured")
    return True


def test_dependencies():
    """Check if required packages are installed."""
    print("\nTesting dependencies...")
    
    required = {
        "pytdbot": "Telegram client (TDLib)",
        "tradelocker": "TradeLocker SDK",
        "asyncpg": "PostgreSQL driver",
        "fastapi": "Web framework",
        "aiohttp": "HTTP client",
        "dotenv": "Environment loader",
        "loguru": "Logging"
    }
    
    missing = []
    for package, description in required.items():
        try:
            if package == "dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            print(f"  ✓ {package} ({description})")
        except ImportError:
            print(f"  ❌ {package} ({description})")
            missing.append(package)
    
    if missing:
        print(f"\n  Missing packages: {', '.join(missing)}")
        print("  → Run: pip install -r requirements.txt")
        return False
    
    return True


def test_directories():
    """Check if required directories exist."""
    print("\nTesting directories...")
    
    required = [
        "tdlib_data",
        "logs"
    ]
    
    for dir_name in required:
        path = Path(dir_name)
        if path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ⚠️  {dir_name}/ (will be created on first run)")
    
    return True


def test_telegram_config():
    """Validate Telegram configuration."""
    print("\nTesting Telegram config...")
    
    api_id = os.getenv("TELEGRAM_API_ID", "")
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    phone = os.getenv("TELEGRAM_PHONE", "")
    
    issues = []
    
    # Check API ID
    try:
        api_id_int = int(api_id)
        if api_id_int > 0:
            print(f"  ✓ API ID: {api_id}")
        else:
            issues.append("API ID must be positive")
    except ValueError:
        issues.append("API ID must be a number")
    
    # Check API Hash
    if len(api_hash) == 32:
        print(f"  ✓ API Hash: {api_hash[:8]}...{api_hash[-8:]}")
    else:
        issues.append(f"API Hash should be 32 chars (got {len(api_hash)})")
    
    # Check Phone
    if phone.startswith("+") and len(phone) >= 10:
        print(f"  ✓ Phone: {phone}")
    else:
        issues.append("Phone must start with + and include country code")
    
    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
        return False
    
    return True


def test_database_config():
    """Validate database configuration."""
    print("\nTesting database config...")
    
    db_url = os.getenv("DATABASE_URL", "")
    
    if not db_url or "your_" in db_url or "user:password" in db_url:
        print("  ❌ DATABASE_URL not configured")
        print("  → Get connection string from Neon dashboard")
        return False
    
    if not db_url.startswith("postgresql://"):
        print("  ❌ DATABASE_URL must start with postgresql://")
        return False
    
    if "neon.tech" in db_url or "localhost" in db_url:
        print(f"  ✓ Database URL configured")
        return True
    else:
        print("  ⚠️  Unusual database URL (expected Neon or localhost)")
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("🪞 Mirror Pupil v5.1 - Setup Test")
    print("=" * 60)
    print()
    
    results = {
        "Environment File": test_env_file(),
        "Dependencies": test_dependencies(),
        "Directories": test_directories(),
        "Telegram Config": test_telegram_config(),
        "Database Config": test_database_config()
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status:8} {test_name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("🎉 All tests passed!")
        print("\nYou're ready to run the Telegram client:")
        print("  python telegram_client.py")
        print()
        print("On first run, you'll be prompted for a verification code.")
        print("Check your Telegram app for the code.")
    else:
        print("⚠️  Some tests failed. Fix the issues above and try again.")
        print("\nCommon fixes:")
        print("  1. Run: python setup.py")
        print("  2. Edit .env with your real credentials")
        print("  3. Run: pip install -r requirements.txt")
    
    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
