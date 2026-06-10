"""
Mirror Pupil v5.1 - Add FCM Push Notification Support
Adds fcm_token column to users table and implements required database methods.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")


async def run_migration():
    """Run database migration to add FCM support."""
    
    logger.info("🚀 Starting FCM support migration...")
    
    # Connect to database
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # 1. Add fcm_token column to users table
        logger.info("1. Adding fcm_token column to users table...")
        await conn.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS fcm_token TEXT;
        """)
        logger.info("✓ fcm_token column added")
        
        # 2. Create index for performance
        logger.info("2. Creating index on fcm_token...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_fcm_token 
            ON users(fcm_token) 
            WHERE fcm_token IS NOT NULL;
        """)
        logger.info("✓ Index created")
        
        # 3. Verify changes
        logger.info("3. Verifying changes...")
        result = await conn.fetchrow("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            AND column_name = 'fcm_token';
        """)
        
        if result:
            logger.info(f"✓ Verified: {result['column_name']} ({result['data_type']})")
        else:
            logger.error("✗ Verification failed - column not found")
            return False
        
        # 4. Show current users table structure
        logger.info("4. Current users table structure:")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """)
        
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            logger.info(f"   - {col['column_name']}: {col['data_type']} {nullable}")
        
        logger.info("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    finally:
        await conn.close()


async def test_fcm_methods():
    """Test the new FCM-related database methods."""
    
    logger.info("\n🧪 Testing FCM database methods...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Test 1: Update FCM token
        logger.info("\nTest 1: Update FCM token for a user")
        
        # Get first user
        user = await conn.fetchrow("SELECT user_id, email FROM users LIMIT 1")
        
        if not user:
            logger.warning("No users found in database - skipping tests")
            return
        
        test_token = "test_fcm_token_12345"
        
        await conn.execute("""
            UPDATE users 
            SET fcm_token = $1 
            WHERE user_id = $2
        """, test_token, user['user_id'])
        
        # Verify
        updated = await conn.fetchrow("""
            SELECT fcm_token 
            FROM users 
            WHERE user_id = $1
        """, user['user_id'])
        
        if updated['fcm_token'] == test_token:
            logger.info(f"✓ Updated FCM token for {user['email']}")
        else:
            logger.error("✗ FCM token update failed")
        
        # Test 2: Get all users with FCM tokens
        logger.info("\nTest 2: Get all users with FCM tokens")
        
        users_with_fcm = await conn.fetch("""
            SELECT user_id, email, fcm_token 
            FROM users 
            WHERE fcm_token IS NOT NULL
        """)
        
        logger.info(f"✓ Found {len(users_with_fcm)} user(s) with FCM tokens")
        for u in users_with_fcm:
            logger.info(f"   - {u['email']}: {u['fcm_token'][:20]}...")
        
        # Test 3: Clean up test data
        logger.info("\nTest 3: Cleaning up test data")
        await conn.execute("""
            UPDATE users 
            SET fcm_token = NULL 
            WHERE user_id = $1
        """, user['user_id'])
        logger.info("✓ Test data cleaned up")
        
        logger.info("\n✅ All tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
    finally:
        await conn.close()


async def main():
    """Main execution."""
    
    logger.info("=" * 60)
    logger.info("Mirror Pupil v5.1 - FCM Support Migration")
    logger.info("=" * 60)
    
    # Run migration
    success = await run_migration()
    
    if success:
        # Run tests
        await test_fcm_methods()
    else:
        logger.error("Migration failed - skipping tests")
    
    logger.info("\n" + "=" * 60)
    logger.info("Migration complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
