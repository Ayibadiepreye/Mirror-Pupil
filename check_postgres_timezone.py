"""
Quick script to check PostgreSQL timezone configuration.
Run this to see what timezone your Neon database is using.
"""

import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def check_timezone():
    """Check PostgreSQL timezone setting."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in .env")
        return
    
    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Check PostgreSQL timezone
        pg_timezone = await conn.fetchval("SHOW timezone")
        print(f"\n📍 PostgreSQL timezone: {pg_timezone}")
        
        # Check what PostgreSQL thinks "now" is
        pg_now = await conn.fetchval("SELECT NOW()")
        print(f"🕐 PostgreSQL NOW(): {pg_now}")
        
        # Check what PostgreSQL thinks CURRENT_TIMESTAMP is
        pg_current = await conn.fetchval("SELECT CURRENT_TIMESTAMP")
        print(f"🕐 PostgreSQL CURRENT_TIMESTAMP: {pg_current}")
        
        # Check what Python thinks UTC is
        from datetime import datetime
        py_utcnow = datetime.utcnow()
        print(f"\n🐍 Python datetime.utcnow(): {py_utcnow}")
        
        # Check difference
        # Note: pg_now is timezone-aware, so we need to make it naive for comparison
        pg_now_naive = pg_now.replace(tzinfo=None)
        diff = pg_now_naive - py_utcnow
        print(f"\n⚠️  Time difference (PostgreSQL - Python): {diff}")
        print(f"    That's {diff.total_seconds() / 3600:.2f} hours")
        
        if abs(diff.total_seconds()) > 300:  # More than 5 minutes difference
            print(f"\n🔴 PROBLEM DETECTED!")
            print(f"    PostgreSQL and Python have different times.")
            print(f"    This is causing the 4-hour autonomous close bug!")
        else:
            print(f"\n✅ PostgreSQL and Python times match.")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_timezone())
