"""
Mirror Pupil v5.1 - Setup Helper
Helps configure the environment and test connections.
"""

import os
import secrets
from pathlib import Path


def generate_encryption_key():
    """Generate a secure random encryption key."""
    return secrets.token_hex(32)


def create_env_file():
    """Create .env file from .env.example if it doesn't exist."""
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if env_path.exists():
        print("✓ .env file already exists")
        return
    
    if not example_path.exists():
        print("❌ .env.example not found!")
        return
    
    # Read example
    with open(example_path, 'r') as f:
        content = f.read()
    
    # Generate encryption key
    encryption_key = generate_encryption_key()
    api_secret = generate_encryption_key()
    
    # Replace placeholders
    content = content.replace(
        "TDLIB_ENCRYPTION_KEY=your_random_encryption_key_here",
        f"TDLIB_ENCRYPTION_KEY={encryption_key}"
    )
    content = content.replace(
        "API_SECRET_KEY=your_random_secret_key_here",
        f"API_SECRET_KEY={api_secret}"
    )
    
    # Write .env
    with open(env_path, 'w') as f:
        f.write(content)
    
    print("✓ Created .env file with auto-generated encryption keys")
    print("\n⚠️  IMPORTANT: Edit .env and fill in:")
    print("   - TELEGRAM_API_ID")
    print("   - TELEGRAM_API_HASH")
    print("   - TELEGRAM_PHONE")
    print("   - DATABASE_URL")
    print("   - TL_EMAIL_1, TL_PASSWORD_1")


def create_directories():
    """Create necessary directories."""
    dirs = [
        "tdlib_data",
        "logs",
        "backend",
        "backend/database",
        "backend/core",
        "backend/channels",
        "backend/channels/billirichy",
        "backend/channels/firepips",
        "backend/api"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    print(f"✓ Created {len(dirs)} directories")


def check_dependencies():
    """Check if required packages are installed."""
    required = [
        "pytdbot",
        "tradelocker",
        "asyncpg",
        "fastapi",
        "aiohttp",
        "python-dotenv",
        "loguru"
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("✓ All required packages installed")
        return True


def main():
    """Run setup."""
    print("=" * 60)
    print("🪞 Mirror Pupil v5.1 - Setup")
    print("=" * 60)
    print()
    
    # Step 1: Create directories
    print("Step 1: Creating directories...")
    create_directories()
    print()
    
    # Step 2: Create .env file
    print("Step 2: Creating .env file...")
    create_env_file()
    print()
    
    # Step 3: Check dependencies
    print("Step 3: Checking dependencies...")
    deps_ok = check_dependencies()
    print()
    
    # Summary
    print("=" * 60)
    print("Setup Summary")
    print("=" * 60)
    
    if deps_ok:
        print("✓ Dependencies: OK")
    else:
        print("❌ Dependencies: Missing packages")
    
    print("\nNext steps:")
    print("1. Edit .env and fill in your credentials")
    print("2. Run: python telegram_client.py")
    print("3. Enter verification code when prompted")
    print("4. Watch messages from BillirichyFX and Firepips!")
    print()
    print("For detailed instructions, see README.md")
    print()


if __name__ == "__main__":
    main()
