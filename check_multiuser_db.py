"""Check multi-user database setup"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from backend.database import DatabaseManager

async def check():
    db = DatabaseManager()
    await db.connect()
    
    print("=" * 60)
    print("MULTI-USER DATABASE CHECK")
    print("=" * 60)
    
    # Check users
    users = await db.get_all_users()
    print(f"\n✓ Users table exists: {len(users)} user(s)")
    for u in users:
        print(f"  - {u['email']}")
        print(f"    ID: {u['user_id']}")
        print(f"    Super Admin: {u['is_super_admin']}")
        print(f"    Approved: {u['is_approved']}")
    
    # Check accounts
    accounts = await db.get_all_accounts()
    print(f"\n✓ Accounts table: {len(accounts)} account(s)")
    for a in accounts:
        user_id = getattr(a, 'user_id', 'MISSING')
        print(f"  - {a.account_key}")
        print(f"    user_id: {user_id}")
    
    # Check risk profiles
    profiles = await db.get_all_risk_profiles()
    print(f"\n✓ Risk profiles table: {len(profiles)} profile(s)")
    for p in profiles:
        user_id = getattr(p, 'user_id', 'MISSING')
        print(f"  - {p.profile_name}")
        print(f"    user_id: {user_id}")
        print(f"    is_default: {p.is_default}")
    
    await db.disconnect()
    
    print("\n" + "=" * 60)
    print("DATABASE READY FOR MULTI-USER")
    print("=" * 60)

asyncio.run(check())
