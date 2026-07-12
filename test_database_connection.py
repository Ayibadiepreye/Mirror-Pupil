"""
Test database connection to verify migration was successful.
"""
import asyncio
import asyncpg
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    """Test connection to database and verify data."""
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.error("✗ DATABASE_URL not found in .env file")
        return False
    
    # Mask password in logs
    masked_url = database_url
    if "@" in masked_url:
        parts = masked_url.split("@")
        user_pass = parts[0].split("//")[1]
        if ":" in user_pass:
            user, password = user_pass.split(":")
            masked_url = masked_url.replace(password, "***")
    
    logger.info("=" * 70)
    logger.info("TESTING DATABASE CONNECTION")
    logger.info("=" * 70)
    logger.info(f"URL: {masked_url}")
    
    try:
        logger.info("\n[1/6] Connecting to database...")
        conn = await asyncpg.connect(database_url)
        logger.info("✓ Connected successfully")
        
        # Test 1: Check PostgreSQL version
        logger.info("\n[2/6] Checking PostgreSQL version...")
        version = await conn.fetchval("SELECT version()")
        logger.info(f"✓ Database version: {version.split(',')[0]}")
        
        # Test 2: Check tables exist
        logger.info("\n[3/6] Checking tables...")
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        table_names = [t['table_name'] for t in tables]
        logger.info(f"✓ Found {len(table_names)} tables:")
        for table_name in table_names:
            logger.info(f"  - {table_name}")
        
        # Test 3: Check accounts
        logger.info("\n[4/6] Checking accounts...")
        account_count = await conn.fetchval("SELECT COUNT(*) FROM accounts")
        logger.info(f"✓ Found {account_count} account(s)")
        
        if account_count > 0:
            accounts = await conn.fetch("""
                SELECT account_key, display_name, initial_balance, profit_cap_enabled
                FROM accounts
                LIMIT 5
            """)
            for acc in accounts:
                logger.info(
                    f"  - {acc['account_key']}: {acc['display_name']} "
                    f"(${acc['initial_balance']:.2f}, cap={acc['profit_cap_enabled']})"
                )
        
        # Test 4: Check trade history
        logger.info("\n[5/6] Checking trade history...")
        history_count = await conn.fetchval("SELECT COUNT(*) FROM trade_history")
        logger.info(f"✓ Found {history_count} trade history record(s)")
        
        # Test 5: Verify profit cap columns
        logger.info("\n[6/6] Verifying profit cap columns...")
        columns = await conn.fetch("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'accounts'
            AND column_name LIKE 'profit_cap%'
            ORDER BY column_name
        """)
        
        profit_cap_columns = [c['column_name'] for c in columns]
        expected_columns = [
            'profit_cap_buffer_pct',
            'profit_cap_enabled',
            'profit_cap_frozen',
            'profit_cap_type',
            'profit_cap_value'
        ]
        
        missing = set(expected_columns) - set(profit_cap_columns)
        
        if not missing:
            logger.info(f"✓ All {len(expected_columns)} profit cap columns exist")
            for col in columns:
                logger.info(
                    f"  - {col['column_name']} ({col['data_type']}, "
                    f"default: {col['column_default'] or 'NULL'})"
                )
        else:
            logger.error(f"✗ Missing columns: {missing}")
            return False
        
        await conn.close()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ CONNECTION TEST PASSED")
        logger.info("=" * 70)
        logger.info("\nDatabase is ready for use!")
        logger.info(f"- Tables: {len(table_names)}")
        logger.info(f"- Accounts: {account_count}")
        logger.info(f"- Trade history: {history_count}")
        logger.info(f"- Profit cap: ✓ Ready")
        
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        logger.error("\n✗ Authentication failed: Invalid password")
        logger.error("Check DATABASE_URL in .env file")
        return False
        
    except asyncpg.exceptions.PostgresConnectionError as e:
        logger.error(f"\n✗ Connection failed: {e}")
        logger.error("Possible causes:")
        logger.error("1. Database server not running")
        logger.error("2. Firewall blocking connection")
        logger.error("3. Wrong IP address or port")
        logger.error("4. pg_hba.conf not configured for remote connections")
        return False
        
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    
    if result:
        logger.info("\n✅ Next steps:")
        logger.info("1. Deploy code to VPS")
        logger.info("2. Copy .env file to VPS")
        logger.info("3. Start backend services")
        logger.info("4. Update frontend API URLs")
    else:
        logger.error("\n✗ Connection test failed")
        logger.error("Fix the issues above before proceeding")
    
    exit(0 if result else 1)
