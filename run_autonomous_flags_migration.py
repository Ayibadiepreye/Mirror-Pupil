#!/usr/bin/env python3
"""
Run migration to add autonomous action flags to active_trades table.
This prevents the autonomous manager from spamming repeated actions.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

async def run_migration():
    """Execute the autonomous action flags migration."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    try:
        # Read migration SQL
        with open("backend/database/migrations/add_autonomous_action_flags.sql", "r") as f:
            migration_sql = f.read()
        
        # Connect to database
        logger.info("Connecting to database...")
        conn = await asyncpg.connect(database_url)
        
        # Execute migration
        logger.info("Running migration: add_autonomous_action_flags.sql")
        await conn.execute(migration_sql)
        
        # Verify columns were added
        result = await conn.fetch("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'active_trades' 
            AND column_name IN ('auto_tp_applied', 'auto_be_applied', 'auto_partial_applied')
            ORDER BY column_name
        """)
        
        logger.info("✓ Migration complete. Added columns:")
        for row in result:
            logger.info(f"  - {row['column_name']}: {row['data_type']} DEFAULT {row['column_default']}")
        
        # Check existing trades
        trade_count = await conn.fetchval("SELECT COUNT(*) FROM active_trades")
        logger.info(f"✓ Backfilled {trade_count} existing trade(s) with flags = FALSE")
        
        await conn.close()
        logger.info("✓ Migration successful!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
