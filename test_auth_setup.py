"""
Test Firebase Authentication Setup
Verifies service account key, database connection, and auth flow.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_auth_setup():
    print("=" * 60)
    print("Firebase Authentication Setup Verification")
    print("=" * 60)
    
    # 1. Check environment variables
    print("\n1. Checking environment variables...")
    env_vars = {
        "FIREBASE_SERVICE_ACCOUNT_KEY": os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"),
        "AUTH_DISABLED": os.getenv("AUTH_DISABLED"),
        "DEV_USER_ID": os.getenv("DEV_USER_ID"),
        "SUPER_ADMIN_EMAIL": os.getenv("SUPER_ADMIN_EMAIL"),
    }
    
    for key, value in env_vars.items():
        status = "✓" if value else "✗"
        print(f"   {status} {key}: {value}")
    
    # 2. Check service account file
    print("\n2. Checking service account key file...")
    service_key_path = env_vars["FIREBASE_SERVICE_ACCOUNT_KEY"]
    
    if service_key_path:
        full_path = Path(service_key_path)
        if full_path.exists():
            print(f"   ✓ File exists: {full_path.absolute()}")
            
            # Verify JSON structure
            import json
            try:
                with open(full_path, 'r') as f:
                    key_data = json.load(f)
                
                required_keys = [
                    "type", "project_id", "private_key_id", "private_key",
                    "client_email", "client_id", "auth_uri", "token_uri"
                ]
                
                missing = [k for k in required_keys if k not in key_data]
                if missing:
                    print(f"   ✗ Missing keys: {', '.join(missing)}")
                else:
                    print(f"   ✓ Valid service account JSON")
                    print(f"   ✓ Project ID: {key_data.get('project_id')}")
                    print(f"   ✓ Client Email: {key_data.get('client_email')}")
            except json.JSONDecodeError as e:
                print(f"   ✗ Invalid JSON: {e}")
        else:
            print(f"   ✗ File not found: {full_path.absolute()}")
    else:
        print("   ✗ FIREBASE_SERVICE_ACCOUNT_KEY not set")
    
    # 3. Test Firebase Admin SDK initialization
    print("\n3. Testing Firebase Admin SDK...")
    try:
        from backend.core.firebase_auth import FIREBASE_INITIALIZED, AUTH_DISABLED
        
        if AUTH_DISABLED:
            print("   ⚠️  AUTH_DISABLED=true (dev mode)")
            print(f"   ℹ️  Using dev user: {env_vars['DEV_USER_ID']}")
        elif FIREBASE_INITIALIZED:
            print("   ✓ Firebase Admin SDK initialized successfully")
        else:
            print("   ✗ Firebase Admin SDK failed to initialize")
    except Exception as e:
        print(f"   ✗ Error loading firebase_auth: {e}")
    
    # 4. Test database connection
    print("\n4. Testing database connection...")
    try:
        from backend.database import DatabaseManager
        
        db = DatabaseManager()
        await db.connect()
        
        # Check if users table exists
        async with db.pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'accounts', 'risk_profiles')
                ORDER BY table_name
            """)
            
            table_names = [t['table_name'] for t in tables]
            print(f"   ✓ Connected to database")
            print(f"   ✓ Tables found: {', '.join(table_names)}")
            
            # Check if dev-super-admin user exists
            dev_user = await db.get_user_by_id(env_vars['DEV_USER_ID'])
            if dev_user:
                print(f"   ✓ Dev user exists: {dev_user['email']}")
                print(f"     - Super Admin: {dev_user['is_super_admin']}")
                print(f"     - Approved: {dev_user['is_approved']}")
            else:
                print(f"   ⚠️  Dev user not found (will be created on first login)")
        
        await db.disconnect()
        
    except Exception as e:
        print(f"   ✗ Database error: {e}")
    
    # 5. Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if env_vars["AUTH_DISABLED"] == "true":
        print("✓ Dev Mode Active")
        print("  - No Firebase authentication required")
        print(f"  - Auto-login as: {env_vars['DEV_USER_ID']}")
        print("  - To enable production auth: Set AUTH_DISABLED=false in .env")
    else:
        if service_key_path and Path(service_key_path).exists() and FIREBASE_INITIALIZED:
            print("✓ Production Mode Ready")
            print("  - Firebase authentication enabled")
            print("  - Service account key configured")
            print(f"  - Super admin email: {env_vars['SUPER_ADMIN_EMAIL']}")
        else:
            print("✗ Production Mode NOT Ready")
            print("  - Check service account key path and file")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Start backend: py -m uvicorn backend.api.main:app --reload")
    print("2. Start frontend: cd 'Lovable Frontend' && npm run dev")
    print("3. Open browser: http://localhost:5173")
    print("=" * 60)

if __name__ == "__main__":
    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment")
    
    asyncio.run(test_auth_setup())
