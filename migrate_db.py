"""
Mirror Pupil v5.1 - Database Migration Script
Initializes Neon PostgreSQL database with complete schema.
"""

import asyncio
import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

async def migrate_database():
    """Initialize database schema and insert default data."""
    
    # Import after loading env vars
    from backend.database import DatabaseManager
    
    logger.info("=" * 60)
    logger.info("MIRROR PUPIL v5.1 - DATABASE MIGRATION")
    logger.info("=" * 60)
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not found in .env file")
        return False
    
    logger.info(f"📊 Database: {database_url.split('@')[1].split('/')[0]}")
    
    try:
        # Create database manager
        db = DatabaseManager(database_url)
        
        # Connect to database
        logger.info("🔌 Connecting to Neon PostgreSQL...")
        await db.connect(min_size=2, max_size=5)
        
        logger.info("✅ Connected successfully!")
        
        # Initialize schema (this will create all tables and insert default data)
        logger.info("📋 Initializing schema...")
        await db.initialize_schema()
        
        logger.info("✅ Schema initialized!")
        
        # Verify tables were created
        logger.info("🔍 Verifying tables...")
        async with db.pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            logger.info(f"✅ Found {len(tables)} tables:")
            for table in tables:
                logger.info(f"   • {table['table_name']}")
        
        # Verify default data
        logger.info("🔍 Verifying default data...")
        
        # Check channels
        async with db.pool.acquire() as conn:
            channels = await conn.fetch("SELECT * FROM channels ORDER BY priority")
            logger.info(f"✅ Channels: {len(channels)}")
            for ch in channels:
                logger.info(f"   • {ch['display_name']} (ID: {ch['channel_id']}, Priority: {ch['priority']})")
        
        # Check risk profiles
        async with db.pool.acquire() as conn:
            profiles = await conn.fetch("SELECT * FROM risk_profiles")
            logger.info(f"✅ Risk Profiles: {len(profiles)}")
            for prof in profiles:
                logger.info(f"   • {prof['profile_name']} (Default: {prof['is_default']})")
        
        # Disconnect
        await db.disconnect()
        
        logger.info("=" * 60)
        logger.info("✅ DATABASE MIGRATION COMPLETE!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Add your TradeLocker accounts via the GUI or API")
        logger.info("2. Configure channel subscriptions per account")
        logger.info("3. Start the bot and begin testing")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run migration
    success = asyncio.run(migrate_database())
    
    if success:
        logger.info("🎉 Your database is ready for use!")
        exit(0)
    else:
        logger.error("💥 Migration failed. Please check the errors above.")
        exit(1)
