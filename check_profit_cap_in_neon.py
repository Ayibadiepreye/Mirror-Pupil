"""
Check if profit cap columns exist in Neon database
"""
import asyncio
import asyncpg
from loguru import logger

NEON_DB = "postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"


async def check_profit_cap():
    """Check if profit cap columns exist in Neon accounts table."""
    
    logger.info("=" * 70)
    logger.info("CHECKING PROFIT CAP IN NEON DATABASE")
    logger.info("=" * 70)
    
    try:
        conn = await asyncpg.connect(NEON_DB)
        logger.info("✓ Connected to Neon database")
        
        # Get all columns in accounts table
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'accounts'
            ORDER BY ordinal_position
        """)
        
        logger.info(f"\n✓ Found {len(columns)} columns in accounts table")
        
        # Check for profit cap columns
        profit_cap_columns = [
            'profit_cap_enabled',
            'profit_cap_type',
            'profit_cap_value',
            'profit_cap_buffer_pct',
            'profit_cap_frozen'
        ]
        
        logger.info("\n" + "=" * 70)
        logger.info("PROFIT CAP COLUMN STATUS:")
        logger.info("=" * 70)
        
        found_columns = []
        missing_columns = []
        
        for pc_col in profit_cap_columns:
            found = False
            for col in columns:
                if col['column_name'] == pc_col:
                    found = True
                    found_columns.append(col)
                    logger.info(f"✓ {pc_col:25} | Type: {col['data_type']:15} | Nullable: {col['is_nullable']} | Default: {col['column_default']}")
                    break
            
            if not found:
                missing_columns.append(pc_col)
                logger.error(f"✗ {pc_col:25} | MISSING")
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("SUMMARY:")
        logger.info("=" * 70)
        logger.info(f"Found: {len(found_columns)}/{len(profit_cap_columns)} profit cap columns")
        
        if missing_columns:
            logger.error(f"\n❌ MISSING COLUMNS IN NEON:")
            for col in missing_columns:
                logger.error(f"  - {col}")
            logger.error("\nThe profit cap migration has NOT been applied to Neon!")
        else:
            logger.info(f"\n✅ ALL PROFIT CAP COLUMNS EXIST IN NEON")
            logger.info("The profit cap feature is fully deployed to Neon!")
        
        # Check if any accounts have profit cap enabled
        if not missing_columns:
            enabled_count = await conn.fetchval("""
                SELECT COUNT(*) FROM accounts WHERE profit_cap_enabled = TRUE
            """)
            
            total_count = await conn.fetchval("SELECT COUNT(*) FROM accounts")
            
            logger.info(f"\nAccounts with profit cap enabled: {enabled_count}/{total_count}")
        
        await conn.close()
        return len(missing_columns) == 0
        
    except Exception as e:
        logger.error(f"\n✗ Failed to check Neon database: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(check_profit_cap())
    exit(0 if result else 1)
