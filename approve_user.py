#!/usr/bin/env python3
"""
Approve and make user super admin
"""

import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.database import DatabaseManager

USER_ID = "Q0DfKbdfpKYERFqgnyhHkOLzuwG2"

async def approve_and_promote():
    db = DatabaseManager()
    await db.connect()
    
    try:
        # Get user
        user = await db.get_user_by_id(USER_ID)
        if not user:
            print(f"❌ User {USER_ID} not found")
            return
        
        print(f"📧 User: {user['email']}")
        print(f"   Approved: {user['is_approved']}")
        print(f"   Super Admin: {user['is_super_admin']}")
        print()
        
        # Update user
        async with db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users 
                SET is_approved = TRUE, is_super_admin = TRUE 
                WHERE user_id = $1
                """,
                USER_ID
            )
        
        print(f"✅ User approved and promoted to super admin!")
        
        # Verify
        user = await db.get_user_by_id(USER_ID)
        print(f"\n✓ Approved: {user['is_approved']}")
        print(f"✓ Super Admin: {user['is_super_admin']}")
        
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(approve_and_promote())
