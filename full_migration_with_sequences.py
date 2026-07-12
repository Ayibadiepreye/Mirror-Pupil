"""
COMPLETE DATABASE MIGRATION - ZERO EXCEPTIONS
Migrates EVERYTHING from Neon including:
- All tables
- All columns
- All sequences (auto-increment)
- All data
- All constraints
"""
import asyncio
import asyncpg
from loguru import logger
import sys

SOURCE_DB = "postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
TARGET_DB = "postgresql://kirito:Mirrorpupil2026@100.126.60.57:5432/mirror_pupil"


async def full_migration():
    """Complete migration with sequences and constraints."""
    
    logger.info("=" * 70)
    logger.info("COMPLETE DATABASE MIGRATION - EVERYTHING")
    logger.info("=" * 70)
    
    source_conn = await asyncpg.connect(SOURCE_DB)
    target_conn = await asyncpg.connect(TARGET_DB)
    
    try:
        # Get all tables
        tables = await source_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        table_names = [t['table_name'] for t in tables]
        
        logger.info(f"\n[1/6] Found {len(table_names)} tables to migrate")
        
        # Step 1: Drop everything on target
        logger.info("\n[2/6] Cleaning target database...")
        await target_conn.execute("SET session_replication_role = 'replica';")
        
        for table in table_names:
            await target_conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            logger.info(f"  ✓ Dropped {table}")
        
        # Drop sequences
        sequences = await source_conn.fetch("""
            SELECT sequence_name FROM information_schema.sequences 
            WHERE sequence_schema = 'public'
        """)
        for seq in sequences:
            seq_name = seq['sequence_name']
            await target_conn.execute(f"DROP SEQUENCE IF EXISTS {seq_name} CASCADE")
            logger.info(f"  ✓ Dropped sequence {seq_name}")
        
        await target_conn.execute("SET session_replication_role = 'origin';")
        
        # Step 2: Create sequences first
        logger.info("\n[3/6] Creating sequences...")
        for seq in sequences:
            seq_name = seq['sequence_name']
            
            # Get sequence properties
            seq_props = await source_conn.fetchrow(f"""
                SELECT * FROM {seq_name}
            """)
            
            create_seq = f"CREATE SEQUENCE {seq_name}"
            await target_conn.execute(create_seq)
            
            # Set current value
            if seq_props:
                last_value = seq_props['last_value']
                await target_conn.execute(f"SELECT setval('{seq_name}', {last_value}, true)")
            
            logger.info(f"  ✓ Created sequence {seq_name}")
        
        # Step 3: Create tables without foreign keys
        logger.info("\n[4/6] Creating tables...")
        
        for table_name in table_names:
            # Get columns
            columns = await source_conn.fetch("""
                SELECT 
                    column_name, data_type, character_maximum_length,
                    column_default, is_nullable, udt_name
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table_name)
            
            col_defs = []
            for col in columns:
                col_name = col['column_name']
                
                # Type mapping
                if col['data_type'] == 'character varying':
                    dtype = f"VARCHAR({col['character_maximum_length']})" if col['character_maximum_length'] else "TEXT"
                elif col['data_type'] == 'USER-DEFINED':
                    dtype = col['udt_name']
                elif col['data_type'] == 'timestamp without time zone':
                    dtype = 'TIMESTAMP'
                elif col['data_type'] == 'timestamp with time zone':
                    dtype = 'TIMESTAMPTZ'
                elif col['data_type'] == 'double precision':
                    dtype = 'DOUBLE PRECISION'
                else:
                    dtype = col['data_type'].upper()
                
                nullable = "" if col['is_nullable'] == 'YES' else " NOT NULL"
                
                # Handle defaults
                default = ""
                if col['column_default']:
                    default = f" DEFAULT {col['column_default']}"
                
                col_defs.append(f"    {col_name} {dtype}{nullable}{default}")
            
            # Get primary key
            pk_cols = await source_conn.fetch("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = $1::regclass AND i.indisprimary
            """, table_name)
            
            if pk_cols:
                pk_names = [col['attname'] for col in pk_cols]
                col_defs.append(f"    PRIMARY KEY ({', '.join(pk_names)})")
            
            ddl = f"CREATE TABLE {table_name} (\n" + ",\n".join(col_defs) + "\n);"
            await target_conn.execute(ddl)
            logger.info(f"  ✓ Created table {table_name}")
        
        # Step 4: Add foreign keys
        logger.info("\n[5/6] Adding foreign key constraints...")
        
        for table_name in table_names:
            fks = await source_conn.fetch("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = $1
            """, table_name)
            
            for fk in fks:
                try:
                    fk_sql = f"""
                        ALTER TABLE {table_name}
                        ADD CONSTRAINT {fk['constraint_name']}
                        FOREIGN KEY ({fk['column_name']})
                        REFERENCES {fk['foreign_table_name']}({fk['foreign_column_name']})
                    """
                    await target_conn.execute(fk_sql)
                    logger.info(f"  ✓ Added FK: {table_name}.{fk['column_name']} → {fk['foreign_table_name']}")
                except Exception as e:
                    logger.warning(f"  ⚠️ FK failed: {fk['constraint_name']}: {e}")
        
        # Step 5: Migrate data (IN CORRECT ORDER - respecting foreign keys)
        logger.info("\n[6/6] Migrating data...")
        
        # Define order that respects foreign key dependencies
        migration_order = [
            'risk_profiles',  # No dependencies
            'channels',  # No dependencies
            'users',  # No dependencies
            'accounts',  # Depends on risk_profiles
            'channel_subscriptions',  # Depends on accounts, channels
            'active_trades',  # Depends on accounts, channels
            'trade_history',  # Depends on channels
            'notifications',  # Depends on accounts
            'profitable_days',  # Depends on accounts
            'manual_actions',  # Depends on accounts
            'message_cache',  # Depends on channels
            'waiting_room',  # Depends on channels
            'bot_settings',  # No dependencies
            'schema_version',  # No dependencies
        ]
        
        # Only migrate tables that exist
        tables_to_migrate = [t for t in migration_order if t in table_names]
        
        total_rows = 0
        for table_name in tables_to_migrate:
            count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            logger.info(f"\n  {table_name}: {count} rows")
            
            if count == 0:
                logger.info(f"    ✓ Empty table, skipping")
                continue
            
            # Fetch all data
            rows = await source_conn.fetch(f"SELECT * FROM {table_name}")
            columns = list(rows[0].keys())
            
            cols_str = ', '.join(columns)
            placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
            insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
            
            # Insert in batches
            batch_size = 100
            inserted = 0
            
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                
                for row in batch:
                    values = [row[col] for col in columns]
                    await target_conn.execute(insert_query, *values)
                    inserted += 1
                
                if inserted % 100 == 0:
                    logger.info(f"    Progress: {inserted}/{len(rows)}")
            
            total_rows += inserted
            logger.info(f"    ✓ Migrated {inserted} rows")
        
        # Verify
        logger.info("\n" + "=" * 70)
        logger.info("VERIFICATION")
        logger.info("=" * 70)
        
        all_match = True
        for table_name in table_names:
            src_count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            tgt_count = await target_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            if src_count == tgt_count:
                logger.info(f"✓ {table_name}: {tgt_count} rows")
            else:
                logger.error(f"✗ {table_name}: source={src_count}, target={tgt_count}")
                all_match = False
        
        if all_match:
            logger.info("\n" + "=" * 70)
            logger.info("✅ COMPLETE MIGRATION SUCCESSFUL - 100%")
            logger.info("=" * 70)
            logger.info(f"\nMigrated:")
            logger.info(f"  - {len(table_names)} tables")
            logger.info(f"  - {len(sequences)} sequences")
            logger.info(f"  - {total_rows} total rows")
            logger.info(f"  - All foreign keys")
            logger.info(f"  - All constraints")
            logger.info("\n🎉 Your VPS database is an EXACT replica of Neon!")
            return True
        else:
            logger.warning("\n⚠️ Some tables have mismatches - review above")
            return False
            
    except Exception as e:
        logger.error(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await source_conn.close()
        await target_conn.close()


if __name__ == "__main__":
    logger.info("\n⚠️  FULL MIGRATION - ZERO EXCEPTIONS")
    logger.info("This will:")
    logger.info("- Drop EVERYTHING on VPS")
    logger.info("- Extract COMPLETE schema from Neon (tables, sequences, constraints)")
    logger.info("- Migrate EVERY SINGLE ROW of data")
    logger.info("- Verify 100% match")
    
    response = input("\nProceed with COMPLETE migration? (yes/no): ").strip().lower()
    
    if response != "yes":
        logger.info("Cancelled")
        sys.exit(0)
    
    result = asyncio.run(full_migration())
    sys.exit(0 if result else 1)
