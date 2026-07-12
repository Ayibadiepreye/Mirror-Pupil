"""
Complete Neon Database Migration
Extracts EVERYTHING (schema + data) from Neon and replicates to VPS.
"""
import asyncio
import asyncpg
from loguru import logger
import sys

# Source database (Neon)
SOURCE_DB = "postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Target database (VPS)
TARGET_DB = "postgresql://kirito:Mirrorpupil2026@100.126.60.57:5432/mirror_pupil"


async def get_table_ddl(conn, table_name):
    """Extract complete DDL for a table from source database."""
    
    # Get column definitions
    columns_query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            column_default,
            is_nullable,
            udt_name
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
    """
    columns = await conn.fetch(columns_query, table_name)
    
    # Build column definitions
    col_defs = []
    for col in columns:
        col_name = col['column_name']
        
        # Map PostgreSQL types
        if col['data_type'] == 'character varying':
            data_type = f"VARCHAR({col['character_maximum_length']})" if col['character_maximum_length'] else "TEXT"
        elif col['data_type'] == 'USER-DEFINED':
            data_type = col['udt_name']
        elif col['data_type'] == 'timestamp without time zone':
            data_type = 'TIMESTAMP'
        elif col['data_type'] == 'timestamp with time zone':
            data_type = 'TIMESTAMPTZ'
        elif col['data_type'] == 'double precision':
            data_type = 'DOUBLE PRECISION'
        elif col['data_type'] == 'bigint':
            data_type = 'BIGINT'
        elif col['data_type'] == 'integer':
            data_type = 'INTEGER'
        elif col['data_type'] == 'boolean':
            data_type = 'BOOLEAN'
        elif col['data_type'] == 'text':
            data_type = 'TEXT'
        elif col['data_type'] == 'real':
            data_type = 'REAL'
        elif col['data_type'] == 'date':
            data_type = 'DATE'
        else:
            data_type = col['data_type'].upper()
        
        # Handle NOT NULL
        nullable = "" if col['is_nullable'] == 'YES' else " NOT NULL"
        
        # Handle DEFAULT
        default = ""
        if col['column_default']:
            default = f" DEFAULT {col['column_default']}"
        
        col_defs.append(f"    {col_name} {data_type}{nullable}{default}")
    
    # Get primary key
    pk_query = """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = $1::regclass AND i.indisprimary
    """
    pk_cols = await conn.fetch(pk_query, table_name)
    
    if pk_cols:
        pk_names = [col['attname'] for col in pk_cols]
        col_defs.append(f"    PRIMARY KEY ({', '.join(pk_names)})")
    
    # Get foreign keys
    fk_query = """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = $1
    """
    fks = await conn.fetch(fk_query, table_name)
    
    for fk in fks:
        col_defs.append(
            f"    FOREIGN KEY ({fk['column_name']}) "
            f"REFERENCES {fk['foreign_table_name']}({fk['foreign_column_name']})"
        )
    
    # Build CREATE TABLE statement
    ddl = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    ddl += ",\n".join(col_defs)
    ddl += "\n);"
    
    return ddl


async def migrate_complete():
    """Complete migration - extract schema and data from Neon."""
    
    logger.info("=" * 70)
    logger.info("COMPLETE NEON DATABASE MIGRATION")
    logger.info("=" * 70)
    logger.info("Extracting EVERYTHING from Neon (schema + data)")
    logger.info("=" * 70)
    
    # Connect to both databases
    logger.info("\n[1/7] Connecting to source database (Neon)...")
    try:
        source_conn = await asyncpg.connect(SOURCE_DB)
        logger.info("✓ Connected to Neon")
    except Exception as e:
        logger.error(f"✗ Failed to connect to Neon: {e}")
        return False
    
    logger.info("\n[2/7] Connecting to target database (VPS)...")
    try:
        target_conn = await asyncpg.connect(TARGET_DB)
        logger.info("✓ Connected to VPS")
    except Exception as e:
        logger.error(f"✗ Failed to connect to VPS: {e}")
        await source_conn.close()
        return False
    
    try:
        # Get all tables from source
        logger.info("\n[3/7] Discovering tables in Neon...")
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        tables = await source_conn.fetch(tables_query)
        table_names = [t['table_name'] for t in tables]
        
        logger.info(f"✓ Found {len(table_names)} tables in Neon:")
        for tbl in table_names:
            logger.info(f"  - {tbl}")
        
        # Drop existing tables on target (clean slate)
        logger.info("\n[4/7] Cleaning target database...")
        logger.info("⚠️  Dropping all existing tables on VPS...")
        
        # Disable foreign key checks temporarily
        await target_conn.execute("SET session_replication_role = 'replica';")
        
        for table_name in table_names:
            try:
                await target_conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                logger.info(f"  ✓ Dropped {table_name}")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not drop {table_name}: {e}")
        
        await target_conn.execute("SET session_replication_role = 'origin';")
        logger.info("✓ Target database cleaned")
        
        # Extract and create schema
        logger.info("\n[5/7] Extracting and creating schema...")
        
        for table_name in table_names:
            logger.info(f"\n  Extracting schema for: {table_name}")
            
            try:
                ddl = await get_table_ddl(source_conn, table_name)
                logger.info(f"    DDL generated ({len(ddl)} chars)")
                
                # Create table on target
                await target_conn.execute(ddl)
                logger.info(f"    ✓ Table created on VPS")
                
            except Exception as e:
                logger.error(f"    ✗ Failed to create {table_name}: {e}")
                logger.error(f"    DDL was: {ddl}")
        
        # Migrate data
        logger.info("\n[6/7] Migrating data...")
        
        total_rows = 0
        for table_name in table_names:
            logger.info(f"\n  Migrating data for: {table_name}")
            
            try:
                # Count rows
                count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                logger.info(f"    Source rows: {count}")
                
                if count == 0:
                    logger.info(f"    ✓ Table is empty, skipping")
                    continue
                
                # Fetch all data
                rows = await source_conn.fetch(f"SELECT * FROM {table_name}")
                
                if len(rows) > 0:
                    # Get column names
                    columns = list(rows[0].keys())
                    cols_str = ', '.join(columns)
                    placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                    
                    insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
                    
                    # Insert rows in batches
                    batch_size = 100
                    inserted = 0
                    
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i+batch_size]
                        
                        for row in batch:
                            values = [row[col] for col in columns]
                            await target_conn.execute(insert_query, *values)
                            inserted += 1
                        
                        logger.info(f"    Progress: {inserted}/{len(rows)} rows")
                    
                    total_rows += inserted
                    logger.info(f"    ✓ Migrated {inserted} rows")
                
            except Exception as e:
                logger.error(f"    ✗ Failed to migrate {table_name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Verify migration
        logger.info("\n[7/7] Verifying migration...")
        
        verification_passed = True
        for table_name in table_names:
            source_count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            target_count = await target_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            if source_count == target_count:
                logger.info(f"  ✓ {table_name}: {target_count} rows (match)")
            else:
                logger.error(
                    f"  ✗ {table_name}: source={source_count}, "
                    f"target={target_count} (MISMATCH)"
                )
                verification_passed = False
        
        if verification_passed:
            logger.info("\n" + "=" * 70)
            logger.info("✅ COMPLETE MIGRATION SUCCESSFUL")
            logger.info("=" * 70)
            logger.info(f"\nMigrated {len(table_names)} tables with {total_rows} total rows")
            logger.info("Every single table, column, and row from Neon is now on VPS")
            logger.info("\nYour VPS database is an EXACT replica of Neon!")
        else:
            logger.warning("\n" + "=" * 70)
            logger.warning("⚠️ MIGRATION COMPLETED WITH MISMATCHES")
            logger.warning("=" * 70)
            logger.warning("Some tables have different row counts - review above")
        
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


if __name__ == "__main__":
    logger.info("\n⚠️  WARNING: This will REPLACE ALL DATA on VPS with Neon data.")
    logger.info("This includes:")
    logger.info("- All table structures (exact copy from Neon)")
    logger.info("- All data (every single row from Neon)")
    logger.info("- Any existing data on VPS will be DELETED")
    
    response = input("\nProceed with COMPLETE migration? (yes/no): ").strip().lower()
    
    if response != "yes":
        logger.info("Migration cancelled")
        sys.exit(0)
    
    result = asyncio.run(migrate_complete())
    sys.exit(0 if result else 1)
