#!/usr/bin/env python3
"""
Add bonnieprincewill6@gmail.com as super admin user
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def add_super_admin():
    """Add bonnieprincewill6@gmail.com as super admin"""
    
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
        
        # The user_id should be the Firebase UID
        # Since we don't have it yet, we'll need to create a placeholder
        # that will be updated when the user first logs in with Firebase
        
        email = "bonnieprincewill6@gmail.com"
        
        # Check if user already exists
        existing = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            email
        )
        
        if existing:
            print(f"\n⚠️  User {email} already exists!")
            print(f"User ID: {existing['user_id']}")
            print(f"Super Admin: {existing['is_super_admin']}")
            print(f"Approved: {existing['is_approved']}")
            
            # Update to super admin
            print(f"\nUpdating to super admin...")
            await conn.execute(
                """
                UPDATE users 
                SET is_super_admin = TRUE, is_approved = TRUE
                WHERE email = $1
                """,
                email
            )
            print("✅ Updated to super admin!")
        else:
            # Insert new user
            # Note: We'll use a temporary user_id that should be updated when they first log in
            print(f"\nCreating new super admin user: {email}")
            
            # Use email as temporary user_id (will be replaced by Firebase UID on first login)
            temp_user_id = f"temp_{email}"
            
            await conn.execute(
                """
                INSERT INTO users (user_id, email, display_name, is_super_admin, is_approved)
                VALUES ($1, $2, $3, TRUE, TRUE)
                """,
                temp_user_id,
                email,
                "Bonnie Prince Will"
            )
            print(f"✅ Created super admin user!")
            print(f"Temporary User ID: {temp_user_id}")
            print(f"Note: User ID will be updated to Firebase UID on first login")
        
        # Fetch and display all users
        print("\n" + "=" * 100)
        print("ALL USERS IN DATABASE:")
        print("=" * 100)
        
        rows = await conn.fetch(
            """
            SELECT user_id, email, display_name, is_super_admin, is_approved, created_at
            FROM users
            ORDER BY email
            """
        )
        
        if rows:
            print(f"\n{'Email':<35} {'Display Name':<20} {'Super Admin':<15} {'Approved':<10}")
            print("-" * 100)
            for row in rows:
                email = row['email']
                display_name = (row['display_name'] or '')[:18]
                is_super_admin = '✅ YES' if row['is_super_admin'] else '❌ NO'
                is_approved = '✅ YES' if row['is_approved'] else '❌ NO'
                print(f"{email:<35} {display_name:<20} {is_super_admin:<15} {is_approved:<10}")
        else:
            print("\n⚠️  No users found in database")
        
        print("\n" + "=" * 100)
        print("✅ Operation complete!")
        print("=" * 100)
        
        # Close connection
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_super_admin())
