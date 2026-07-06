"""
Run profit cap migration on Neon PostgreSQL database.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

async def run_migration():
    """Run the profit cap migration."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.error("DATABASE_URL not found in .env file")
        return False
    
    logger.info("Connecting to Neon PostgreSQL...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        logger.info("✓ Connected to database")
        
        # Read migration file
        migration_file = "backend/database/migrations/add_profit_cap.sql"
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        logger.info(f"Running migration: {migration_file}")
        
        # Execute migration
        await conn.execute(migration_sql)
        
        logger.info("✓ Migration completed successfully")
        
        # Verify columns were added
        columns = await conn.fetch("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'accounts'
            AND column_name IN ('profit_cap_enabled', 'profit_cap_type', 'profit_cap_value', 
                                'profit_cap_buffer_pct', 'profit_cap_frozen')
            ORDER BY column_name
        """)
        
        if columns:
            logger.info("✓ Verified new columns:")
            for col in columns:
                logger.info(f"  - {col['column_name']} ({col['data_type']}, default: {col['column_default']})")
        else:
            logger.warning("⚠ Could not verify columns (they may already exist)")
        
        # Close connection
        await conn.close()
        logger.info("✓ Database connection closed")
        
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== PROFIT CAP MIGRATION ===")
    success = asyncio.run(run_migration())
    
    if success:
        logger.info("=== MIGRATION SUCCESSFUL ===")
    else:
        logger.error("=== MIGRATION FAILED ===")
        exit(1)
