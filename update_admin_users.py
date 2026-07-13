#!/usr/bin/env python3
"""
Update admin status for users in the database
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def update_admin_status():
    """Update admin status for bonnieprincewill6@gmail.com and dotacademy.ai@gmail.com"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"Connecting to database...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✓ Connected to database")
        
        # Update bonnieprincewill6@gmail.com to super admin
        print("\nUpdating bonnieprincewill6@gmail.com to super admin...")
        result1 = await conn.execute(
            """
            UPDATE users 
            SET is_super_admin = TRUE, is_approved = TRUE
            WHERE email = $1
            """,
            "bonnieprincewill6@gmail.com"
        )
        print(f"✓ Updated bonnieprincewill6@gmail.com: {result1}")
        
        # Update dotacademy.ai@gmail.com to non-admin
        print("\nUpdating dotacademy.ai@gmail.com to non-admin...")
        result2 = await conn.execute(
            """
            UPDATE users 
            SET is_super_admin = FALSE
            WHERE email = $1
            """,
            "dotacademy.ai@gmail.com"
        )
        print(f"✓ Updated dotacademy.ai@gmail.com: {result2}")
        
        # Fetch and display updated users
        print("\n" + "=" * 80)
        print("UPDATED USER STATUS:")
        print("=" * 80)
        
        rows = await conn.fetch(
            """
            SELECT user_id, email, display_name, is_super_admin, is_approved, created_at
            FROM users
            WHERE email IN ($1, $2)
            ORDER BY email
            """,
            "bonnieprincewill6@gmail.com",
            "dotacademy.ai@gmail.com"
        )
        
        if rows:
            print(f"\n{'Email':<35} {'Super Admin':<15} {'Approved':<10} {'User ID':<30}")
            print("-" * 100)
            for row in rows:
                email = row['email']
                is_super_admin = '✅ YES' if row['is_super_admin'] else '❌ NO'
                is_approved = '✅ YES' if row['is_approved'] else '❌ NO'
                user_id = row['user_id'][:27] + '...' if len(row['user_id']) > 30 else row['user_id']
                print(f"{email:<35} {is_super_admin:<15} {is_approved:<10} {user_id:<30}")
        else:
            print("\n⚠️  No users found with those email addresses")
        
        print("\n" + "=" * 80)
        print("✅ Admin status update complete!")
        print("=" * 80)
        
        # Close connection
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(update_admin_status())
