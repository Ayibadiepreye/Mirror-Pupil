#!/usr/bin/env python3
"""
Migration Script - Add Multi-User Authentication Support
Run this script to apply the database migration for Firebase auth.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import asyncpg
from loguru import logger

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "your-email@example.com")

if not DATABASE_URL:
    logger.error("DATABASE_URL not found in environment")
    sys.exit(1)


async def run_migration():
    """Run the multi-user auth migration."""
    logger.info("Starting database migration for multi-user auth...")
    
    # Read migration SQL
    migration_file = "backend/database/migrations/add_multi_user_auth.sql"
    
    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("✓ Connected to database")
        
        # Execute migration SQL
        logger.info("Executing migration SQL...")
        await conn.execute(migration_sql)
        logger.info("✓ Migration SQL executed successfully")
        
        # Create super admin user (dev mode)
        # In dev mode with AUTH_DISABLED=true, this is the user ID
        logger.info("Creating super admin user record...")
        
        await conn.execute(
            """
            INSERT INTO users (user_id, email, display_name, is_super_admin, is_approved)
            VALUES ($1, $2, $3, TRUE, TRUE)
            ON CONFLICT (user_id) DO UPDATE 
            SET is_super_admin = TRUE, is_approved = TRUE, email = $2
            """,
            "dev-super-admin",  # Dev mode user ID
            SUPER_ADMIN_EMAIL,
            "Super Admin (Dev)"
        )
        logger.info(f"✓ Created super admin user: {SUPER_ADMIN_EMAIL}")
        
        # Assign all existing accounts to super admin
        logger.info("Assigning existing accounts to super admin...")
        result = await conn.execute(
            """
            UPDATE accounts 
            SET user_id = $1 
            WHERE user_id IS NULL
            """,
            "dev-super-admin"
        )
        logger.info(f"✓ Assigned accounts to super admin: {result}")
        
        # Keep default risk profiles system-wide (user_id = NULL)
        logger.info("Default risk profiles remain system-wide (no user_id)")
        
        # Close connection
        await conn.close()
        logger.info("✓ Migration completed successfully!")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("IMPORTANT: Next Steps")
        logger.info("=" * 60)
        logger.info("1. Update .env file:")
        logger.info(f"   SUPER_ADMIN_EMAIL={SUPER_ADMIN_EMAIL}")
        logger.info("   AUTH_DISABLED=true  (for local dev)")
        logger.info("   DEV_USER_ID=dev-super-admin")
        logger.info("")
        logger.info("2. When ready for production:")
        logger.info("   - Download Firebase service account JSON")
        logger.info("   - Set FIREBASE_SERVICE_ACCOUNT_KEY=./firebase-service-account.json")
        logger.info("   - Set AUTH_DISABLED=false")
        logger.info("   - Sign in with Firebase and get your real user_id")
        logger.info("   - Update your user_id in database to be super admin")
        logger.info("")
        logger.info("3. All existing data now belongs to super admin")
        logger.info("   - Accounts: Owned by super admin")
        logger.info("   - Risk Profiles: Default profiles are system-wide")
        logger.info("   - Channels: System-wide (super admin manages)")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
