"""
Mirror Pupil - Database Migration Script
Migrates from Neon PostgreSQL to VPS PostgreSQL
"""
import asyncio
import asyncpg
from loguru import logger
import sys

# Source database (Neon)
SOURCE_DB = "postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Target database (VPS)
TARGET_DB = "postgresql://kirito:Mirrorpupil2026@100.126.60.57:5432/mirror_pupil"


async def migrate():
    """Migrate all data from source to target database."""
    
    logger.info("=" * 70)
    logger.info("MIRROR PUPIL - DATABASE MIGRATION")
    logger.info("=" * 70)
    logger.info(f"Source: Neon PostgreSQL (neondb)")
    logger.info(f"Target: VPS PostgreSQL (100.126.60.57)")
    logger.info("=" * 70)
    
    # Connect to both databases
    logger.info("\n[1/6] Connecting to source database (Neon)...")
    try:
        source_conn = await asyncpg.connect(SOURCE_DB)
        logger.info("✓ Connected to source database")
    except Exception as e:
        logger.error(f"✗ Failed to connect to source database: {e}")
        return False
    
    logger.info("\n[2/6] Connecting to target database (VPS)...")
    try:
        target_conn = await asyncpg.connect(TARGET_DB)
        logger.info("✓ Connected to target database")
    except Exception as e:
        logger.error(f"✗ Failed to connect to target database: {e}")
        await source_conn.close()
        return False
    
    try:
        # Get table list from source
        logger.info("\n[3/6] Reading schema from source database...")
        tables = await source_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        table_names = [t['table_name'] for t in tables]
        logger.info(f"✓ Found {len(table_names)} tables: {', '.join(table_names)}")
        
        # Create schema on target
        logger.info("\n[4/6] Creating schema on target database...")
        
        # Read schema from schema.py
        from backend.database.schema import SCHEMA_DDL
        
        # Execute schema on target
        await target_conn.execute(SCHEMA_DDL)
        logger.info("✓ Schema created successfully")
        
        # Migrate data table by table
        logger.info("\n[5/6] Migrating data...")
        
        # Define table order (respecting foreign keys)
        migration_order = [
            'risk_profiles',
            'users',
            'channels',  # Must come before channel_subscriptions
            'accounts',
            'channel_subscriptions',
            'active_trades',
            'trade_history',
            'notifications',
            'profitable_days',
            'message_cache',
            'manual_actions',
            'bot_settings',
            'waiting_room',
            'schema_version',
        ]
        
        # Only migrate tables that exist
        tables_to_migrate = [t for t in migration_order if t in table_names]
        
        for table_name in tables_to_migrate:
            logger.info(f"\n  Migrating table: {table_name}")
            
            # Count source rows
            count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            logger.info(f"    Source rows: {count}")
            
            if count == 0:
                logger.info(f"    ✓ Table is empty, skipping")
                continue
            
            # Get column names from both source and target
            source_columns_query = await source_conn.fetch(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            source_columns = [col['column_name'] for col in source_columns_query]
            
            target_columns_query = await target_conn.fetch(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            target_columns = [col['column_name'] for col in target_columns_query]
            
            # Only select columns that exist in BOTH source and target
            common_columns = [col for col in source_columns if col in target_columns]
            
            if not common_columns:
                logger.warning(f"    ⚠️ No common columns found, skipping table")
                continue
            
            # Fetch all data from source (only common columns)
            select_cols = ', '.join(common_columns)
            rows = await source_conn.fetch(f"SELECT {select_cols} FROM {table_name}")
            
            # Get column names
            if len(rows) > 0:
                columns = common_columns
                
                # Build INSERT query with CONFLICT handling
                cols_str = ', '.join(columns)
                placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                
                # Determine primary key for ON CONFLICT
                # Query the actual primary key from the target database
                pk_query = await target_conn.fetch(f"""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = '{table_name}'::regclass AND i.indisprimary
                """)
                
                if pk_query:
                    conflict_key = pk_query[0]['attname']
                elif table_name == 'risk_profiles':
                    conflict_key = 'profile_id'
                elif table_name == 'users':
                    conflict_key = 'user_id'
                elif table_name == 'accounts':
                    conflict_key = 'account_key'
                elif table_name == 'channels':
                    conflict_key = 'channel_id'
                elif table_name == 'channel_subscriptions':
                    conflict_key = 'id'
                elif table_name == 'active_trades':
                    conflict_key = 'trade_id'
                elif table_name == 'trade_history':
                    conflict_key = 'history_id'
                elif table_name == 'notifications':
                    conflict_key = 'id'
                else:
                    conflict_key = 'id'
                
                # Skip if conflict key not in common columns
                if conflict_key not in columns:
                    logger.warning(f"    ⚠️ Primary key '{conflict_key}' not in common columns, skipping table")
                    continue
                
                insert_query = f"""
                    INSERT INTO {table_name} ({cols_str})
                    VALUES ({placeholders})
                    ON CONFLICT ({conflict_key}) DO UPDATE SET
                    {', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != conflict_key])}
                """
                
                # Insert rows in batches
                batch_size = 100
                total_inserted = 0
                
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i+batch_size]
                    
                    for row in batch:
                        values = [row[col] for col in columns]
                        await target_conn.execute(insert_query, *values)
                        total_inserted += 1
                    
                    logger.info(f"    Progress: {total_inserted}/{len(rows)} rows")
                
                logger.info(f"    ✓ Migrated {total_inserted} rows")
        
        # Verify migration
        logger.info("\n[6/6] Verifying migration...")
        
        verification_passed = True
        for table_name in tables_to_migrate:
            # Check if table exists in target before verifying
            table_exists = await target_conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                )
            """)
            
            if not table_exists:
                logger.warning(f"  ⚠️ {table_name}: table doesn't exist in target (skipped)")
                continue
            
            source_count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            target_count = await target_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            if source_count == target_count:
                logger.info(f"  ✓ {table_name}: {target_count} rows (match)")
            else:
                logger.error(f"  ✗ {table_name}: source={source_count}, target={target_count} (MISMATCH)")
                verification_passed = False
        
        if verification_passed:
            logger.info("\n" + "=" * 70)
            logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info("\nAll data has been migrated to your VPS PostgreSQL database.")
            logger.info("\nNext steps:")
            logger.info("1. Update .env file with new DATABASE_URL")
            logger.info("2. Restart backend services")
            logger.info("3. Test connection and functionality")
        else:
            logger.error("\n" + "=" * 70)
            logger.error("⚠️ MIGRATION COMPLETED WITH WARNINGS")
            logger.error("=" * 70)
            logger.error("Some tables have row count mismatches.")
            logger.error("Review the logs above and verify data integrity.")
        
        return verification_passed
        
    except Exception as e:
        logger.error(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await source_conn.close()
        await target_conn.close()
        logger.info("\n✓ Database connections closed")


async def test_connection():
    """Test connection to VPS database."""
    logger.info("\n" + "=" * 70)
    logger.info("TESTING VPS DATABASE CONNECTION")
    logger.info("=" * 70)
    
    try:
        conn = await asyncpg.connect(TARGET_DB)
        logger.info("✓ Successfully connected to VPS database")
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        logger.info(f"✓ PostgreSQL version: {version.split(',')[0]}")
        
        # List existing tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        if tables:
            logger.info(f"✓ Found {len(tables)} existing tables")
            for table in tables:
                logger.info(f"  - {table['table_name']}")
        else:
            logger.info("✓ Database is empty (ready for schema creation)")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Mirror Pupil database")
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only test VPS database connection, don't migrate"
    )
    
    args = parser.parse_args()
    
    if args.test_only:
        # Test connection only
        result = asyncio.run(test_connection())
        sys.exit(0 if result else 1)
    else:
        # Run full migration
        logger.info("\n⚠️  WARNING: This will migrate ALL data to the VPS database.")
        logger.info("Make sure the VPS database is ready and empty (or you want to overwrite).")
        
        response = input("\nProceed with migration? (yes/no): ").strip().lower()
        
        if response != "yes":
            logger.info("Migration cancelled by user")
            sys.exit(0)
        
        result = asyncio.run(migrate())
        sys.exit(0 if result else 1)
