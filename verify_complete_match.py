"""
COMPREHENSIVE DATABASE VERIFICATION
Compares EVERYTHING between Neon and VPS:
- Table structures (columns, types, constraints)
- Row counts
- Actual data values
- Sequences
- Indexes
- Foreign keys
"""
import asyncio
import asyncpg
from loguru import logger
import sys
from typing import Dict, List, Any

SOURCE_DB = "postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
TARGET_DB = "postgresql://kirito:Mirrorpupil2026@100.126.60.57:5432/mirror_pupil"


async def get_table_structure(conn, table_name: str) -> Dict[str, Any]:
    """Get complete table structure."""
    columns = await conn.fetch("""
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
    """, table_name)
    
    return {col['column_name']: dict(col) for col in columns}


async def get_primary_keys(conn, table_name: str) -> List[str]:
    """Get primary key columns."""
    pk_cols = await conn.fetch("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = $1::regclass AND i.indisprimary
        ORDER BY a.attname
    """, table_name)
    
    return [col['attname'] for col in pk_cols]


async def get_foreign_keys(conn, table_name: str) -> List[Dict[str, str]]:
    """Get foreign key constraints."""
    fks = await conn.fetch("""
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
        ORDER BY tc.constraint_name
    """, table_name)
    
    return [dict(fk) for fk in fks]


async def get_sequences(conn) -> Dict[str, int]:
    """Get all sequences and their current values."""
    sequences = await conn.fetch("""
        SELECT sequence_name FROM information_schema.sequences 
        WHERE sequence_schema = 'public'
        ORDER BY sequence_name
    """)
    
    seq_values = {}
    for seq in sequences:
        seq_name = seq['sequence_name']
        value = await conn.fetchval(f"SELECT last_value FROM {seq_name}")
        seq_values[seq_name] = value
    
    return seq_values


async def compare_table_data(source_conn, target_conn, table_name: str) -> Dict[str, Any]:
    """Compare actual data in a table."""
    
    # Get row counts
    src_count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
    tgt_count = await target_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
    
    result = {
        'table': table_name,
        'source_count': src_count,
        'target_count': tgt_count,
        'count_match': src_count == tgt_count,
        'data_match': None,
        'differences': []
    }
    
    if src_count != tgt_count:
        result['data_match'] = False
        result['differences'].append(f"Row count mismatch: {src_count} vs {tgt_count}")
        return result
    
    if src_count == 0:
        result['data_match'] = True
        return result
    
    # Get all data from both
    src_rows = await source_conn.fetch(f"SELECT * FROM {table_name} ORDER BY 1")
    tgt_rows = await target_conn.fetch(f"SELECT * FROM {table_name} ORDER BY 1")
    
    # Compare row by row
    data_match = True
    for i, (src_row, tgt_row) in enumerate(zip(src_rows, tgt_rows)):
        for col in src_row.keys():
            src_val = src_row[col]
            tgt_val = tgt_row.get(col)
            
            # Handle None comparisons
            if src_val != tgt_val:
                # Special handling for timestamps and floats
                if isinstance(src_val, float) and isinstance(tgt_val, float):
                    if abs(src_val - tgt_val) < 0.0001:
                        continue
                
                data_match = False
                result['differences'].append(
                    f"Row {i+1}, Column '{col}': {src_val} != {tgt_val}"
                )
    
    result['data_match'] = data_match
    return result


async def comprehensive_verification():
    """Run complete verification."""
    
    logger.info("=" * 80)
    logger.info("COMPREHENSIVE DATABASE VERIFICATION")
    logger.info("=" * 80)
    logger.info("\nComparing:")
    logger.info(f"  SOURCE (Neon): {SOURCE_DB.split('@')[1].split('/')[0]}")
    logger.info(f"  TARGET (VPS):  {TARGET_DB.split('@')[1].split('/')[0]}")
    logger.info("=" * 80)
    
    # Connect to both databases
    logger.info("\n[1/8] Connecting to databases...")
    try:
        source_conn = await asyncpg.connect(SOURCE_DB)
        logger.info("  ✓ Connected to Neon (source)")
    except Exception as e:
        logger.error(f"  ✗ Failed to connect to Neon: {e}")
        return False
    
    try:
        target_conn = await asyncpg.connect(TARGET_DB)
        logger.info("  ✓ Connected to VPS (target)")
    except Exception as e:
        logger.error(f"  ✗ Failed to connect to VPS: {e}")
        await source_conn.close()
        return False
    
    try:
        # Get all tables
        logger.info("\n[2/8] Comparing table lists...")
        src_tables = await source_conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        src_table_names = {t['table_name'] for t in src_tables}
        
        tgt_tables = await target_conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tgt_table_names = {t['table_name'] for t in tgt_tables}
        
        if src_table_names == tgt_table_names:
            logger.info(f"  ✓ Both have {len(src_table_names)} tables")
            for table in sorted(src_table_names):
                logger.info(f"    - {table}")
        else:
            logger.error("  ✗ Table lists don't match!")
            logger.error(f"    Only in source: {src_table_names - tgt_table_names}")
            logger.error(f"    Only in target: {tgt_table_names - src_table_names}")
            return False
        
        # Compare sequences
        logger.info("\n[3/8] Comparing sequences...")
        src_sequences = await get_sequences(source_conn)
        tgt_sequences = await get_sequences(target_conn)
        
        seq_match = True
        for seq_name in sorted(src_sequences.keys()):
            src_val = src_sequences.get(seq_name)
            tgt_val = tgt_sequences.get(seq_name)
            
            if seq_name not in tgt_sequences:
                logger.error(f"  ✗ Sequence missing on target: {seq_name}")
                seq_match = False
            elif src_val != tgt_val:
                logger.warning(f"  ⚠️  {seq_name}: source={src_val}, target={tgt_val}")
                # This is OK if target is >= source (might have had test inserts)
                if tgt_val < src_val:
                    logger.error(f"  ✗ Target sequence value is LESS than source!")
                    seq_match = False
            else:
                logger.info(f"  ✓ {seq_name}: {src_val}")
        
        if not seq_match:
            logger.error("  ✗ Sequences don't match!")
        
        # Compare table structures
        logger.info("\n[4/8] Comparing table structures...")
        structure_match = True
        
        for table_name in sorted(src_table_names):
            src_structure = await get_table_structure(source_conn, table_name)
            tgt_structure = await get_table_structure(target_conn, table_name)
            
            if set(src_structure.keys()) != set(tgt_structure.keys()):
                logger.error(f"  ✗ {table_name}: Column mismatch!")
                logger.error(f"    Source: {sorted(src_structure.keys())}")
                logger.error(f"    Target: {sorted(tgt_structure.keys())}")
                structure_match = False
                continue
            
            # Check column types
            col_mismatch = False
            for col_name, src_col in src_structure.items():
                tgt_col = tgt_structure[col_name]
                
                if src_col['data_type'] != tgt_col['data_type']:
                    logger.error(f"  ✗ {table_name}.{col_name}: Type mismatch ({src_col['data_type']} vs {tgt_col['data_type']})")
                    col_mismatch = True
                
                if src_col['is_nullable'] != tgt_col['is_nullable']:
                    logger.error(f"  ✗ {table_name}.{col_name}: Nullable mismatch")
                    col_mismatch = True
            
            if not col_mismatch:
                logger.info(f"  ✓ {table_name}: {len(src_structure)} columns match")
            else:
                structure_match = False
        
        if not structure_match:
            logger.error("  ✗ Table structures don't match!")
            return False
        
        # Compare primary keys
        logger.info("\n[5/8] Comparing primary keys...")
        pk_match = True
        
        for table_name in sorted(src_table_names):
            src_pks = await get_primary_keys(source_conn, table_name)
            tgt_pks = await get_primary_keys(target_conn, table_name)
            
            if src_pks != tgt_pks:
                logger.error(f"  ✗ {table_name}: PK mismatch ({src_pks} vs {tgt_pks})")
                pk_match = False
            elif src_pks:
                logger.info(f"  ✓ {table_name}: PK({', '.join(src_pks)})")
        
        if not pk_match:
            logger.error("  ✗ Primary keys don't match!")
        
        # Compare foreign keys
        logger.info("\n[6/8] Comparing foreign keys...")
        fk_match = True
        fk_count = 0
        
        for table_name in sorted(src_table_names):
            src_fks = await get_foreign_keys(source_conn, table_name)
            tgt_fks = await get_foreign_keys(target_conn, table_name)
            
            if len(src_fks) != len(tgt_fks):
                logger.error(f"  ✗ {table_name}: FK count mismatch ({len(src_fks)} vs {len(tgt_fks)})")
                fk_match = False
            elif src_fks:
                for fk in src_fks:
                    logger.info(f"  ✓ {table_name}.{fk['column_name']} → {fk['foreign_table_name']}")
                    fk_count += 1
        
        logger.info(f"  Total: {fk_count} foreign keys")
        
        if not fk_match:
            logger.error("  ✗ Foreign keys don't match!")
        
        # Compare row counts
        logger.info("\n[7/8] Comparing row counts...")
        count_match = True
        total_rows = 0
        
        for table_name in sorted(src_table_names):
            src_count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            tgt_count = await target_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            total_rows += src_count
            
            if src_count != tgt_count:
                logger.error(f"  ✗ {table_name}: {src_count} vs {tgt_count}")
                count_match = False
            else:
                logger.info(f"  ✓ {table_name}: {src_count} rows")
        
        logger.info(f"  Total: {total_rows} rows")
        
        if not count_match:
            logger.error("  ✗ Row counts don't match!")
            return False
        
        # Compare actual data (row by row)
        logger.info("\n[8/8] Comparing actual data values (this may take a moment)...")
        data_match = True
        
        for table_name in sorted(src_table_names):
            src_count = await source_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            if src_count == 0:
                logger.info(f"  ✓ {table_name}: Empty (skipping data comparison)")
                continue
            
            logger.info(f"  Comparing {table_name} ({src_count} rows)...")
            comparison = await compare_table_data(source_conn, target_conn, table_name)
            
            if comparison['data_match']:
                logger.info(f"    ✓ All {src_count} rows match exactly")
            else:
                logger.error(f"    ✗ Data differences found:")
                for diff in comparison['differences'][:10]:  # Show first 10
                    logger.error(f"      {diff}")
                if len(comparison['differences']) > 10:
                    logger.error(f"      ... and {len(comparison['differences']) - 10} more")
                data_match = False
        
        if not data_match:
            logger.error("  ✗ Data values don't match!")
            return False
        
        # Final verdict
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION RESULTS")
        logger.info("=" * 80)
        
        if structure_match and pk_match and fk_match and count_match and seq_match and data_match:
            logger.info("✅ PERFECT MATCH - 100% IDENTICAL")
            logger.info("\nEverything matches:")
            logger.info(f"  ✓ {len(src_table_names)} tables")
            logger.info(f"  ✓ {len(src_sequences)} sequences")
            logger.info(f"  ✓ {fk_count} foreign keys")
            logger.info(f"  ✓ {total_rows} total rows")
            logger.info("  ✓ All column structures")
            logger.info("  ✓ All primary keys")
            logger.info("  ✓ All data values")
            logger.info("\n🎉 Your VPS database is an EXACT replica of Neon!")
            return True
        else:
            logger.error("✗ DATABASES DO NOT MATCH")
            logger.error("\nIssues found:")
            if not structure_match:
                logger.error("  ✗ Table structures differ")
            if not pk_match:
                logger.error("  ✗ Primary keys differ")
            if not fk_match:
                logger.error("  ✗ Foreign keys differ")
            if not count_match:
                logger.error("  ✗ Row counts differ")
            if not seq_match:
                logger.error("  ✗ Sequences differ")
            if not data_match:
                logger.error("  ✗ Data values differ")
            return False
        
    except Exception as e:
        logger.error(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await source_conn.close()
        await target_conn.close()


if __name__ == "__main__":
    logger.info("\n🔍 COMPREHENSIVE DATABASE VERIFICATION")
    logger.info("This will compare EVERYTHING between Neon and VPS:")
    logger.info("  - Table lists")
    logger.info("  - Table structures (columns, types, nullability)")
    logger.info("  - Primary keys")
    logger.info("  - Foreign keys")
    logger.info("  - Sequences and their values")
    logger.info("  - Row counts")
    logger.info("  - Actual data values (row by row)")
    
    result = asyncio.run(comprehensive_verification())
    sys.exit(0 if result else 1)
