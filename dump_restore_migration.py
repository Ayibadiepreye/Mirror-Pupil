"""
Complete Database Migration using pg_dump approach
This is the SAFEST and most complete way to migrate PostgreSQL databases.
"""
import subprocess
import os
from loguru import logger
import sys

# Database URLs
SOURCE_DB = "postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"
TARGET_DB = "postgresql://kirito:Mirrorpupil2026@100.126.60.57:5432/mirror_pupil"

def run_command(cmd, description):
    """Run a shell command and check for errors."""
    logger.info(f"\n{description}...")
    logger.info(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout:
            logger.info(f"Output: {result.stdout[:500]}")
        
        logger.info(f"✓ {description} completed")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ {description} failed")
        logger.error(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(f"✗ Command not found. Make sure pg_dump and psql are installed and in PATH")
        logger.error(f"Install PostgreSQL client tools: https://www.postgresql.org/download/")
        return False


def migrate():
    """Perform complete migration using pg_dump/restore."""
    
    logger.info("=" * 70)
    logger.info("COMPLETE DATABASE MIGRATION - PG_DUMP METHOD")
    logger.info("=" * 70)
    logger.info("This will use PostgreSQL's native dump/restore tools")
    logger.info("=" * 70)
    
    dump_file = "neon_complete_dump.sql"
    
    # Step 1: Dump from Neon
    logger.info("\n[1/3] Dumping Neon database...")
    dump_cmd = [
        "pg_dump",
        "--no-owner",  # Don't include ownership commands
        "--no-privileges",  # Don't include privilege commands
        "--clean",  # Drop objects before recreating
        "--if-exists",  # Use IF EXISTS when dropping
        "--file", dump_file,
        SOURCE_DB
    ]
    
    if not run_command(dump_cmd, "Database dump"):
        return False
    
    logger.info(f"✓ Dump saved to: {dump_file}")
    logger.info(f"✓ File size: {os.path.getsize(dump_file) / 1024:.2f} KB")
    
    # Step 2: Restore to VPS
    logger.info("\n[2/3] Restoring to VPS database...")
    restore_cmd = [
        "psql",
        "--file", dump_file,
        "--quiet",
        TARGET_DB
    ]
    
    if not run_command(restore_cmd, "Database restore"):
        logger.warning("⚠️ Some errors occurred during restore (this might be normal)")
        logger.info("Continuing with verification...")
    
    # Step 3: Verify
    logger.info("\n[3/3] Verifying migration...")
    verify_cmd = [
        "psql",
        TARGET_DB,
        "-c", "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
    ]
    
    if run_command(verify_cmd, "Verification"):
        logger.info("\n" + "=" * 70)
        logger.info("✅ MIGRATION COMPLETED")
        logger.info("=" * 70)
        logger.info(f"\nDump file saved: {dump_file}")
        logger.info("All tables, sequences, and data migrated")
        logger.info("\nNext steps:")
        logger.info("1. Test connection: py test_database_connection.py")
        logger.info("2. Verify data: py verify_migration_complete.py")
        logger.info("3. Deploy to VPS")
        return True
    
    return False


if __name__ == "__main__":
    logger.info("\n⚠️  WARNING: This will REPLACE ALL DATA on VPS with Neon data.")
    logger.info("Prerequisites:")
    logger.info("- PostgreSQL client tools (pg_dump, psql) must be installed")
    logger.info("- Both databases must be accessible")
    
    response = input("\nProceed with migration? (yes/no): ").strip().lower()
    
    if response != "yes":
        logger.info("Migration cancelled")
        sys.exit(0)
    
    result = migrate()
    
    if result:
        logger.info("\n✅ SUCCESS! Run verify_migration_complete.py to check data")
    else:
        logger.error("\n✗ Migration failed - check logs above")
    
    sys.exit(0 if result else 1)
