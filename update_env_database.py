"""
Helper script to update .env file with new VPS database URL.
"""
from pathlib import Path
from loguru import logger

# Old and new database URLs
OLD_URL = "postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
NEW_URL = "postgresql://kirito:Mirrorpupil2026@100.126.60.57:5432/mirror_pupil"

def update_env_file():
    """Update DATABASE_URL in .env file."""
    env_file = Path(".env")
    
    if not env_file.exists():
        logger.error("✗ .env file not found")
        return False
    
    logger.info("Reading .env file...")
    content = env_file.read_text()
    
    if OLD_URL not in content:
        logger.warning("⚠️ Old database URL not found in .env")
        logger.info("Checking if already updated...")
        
        if NEW_URL in content:
            logger.info("✓ .env already has new VPS database URL")
            return True
        else:
            logger.error("✗ Neither old nor new URL found in .env")
            return False
    
    logger.info("Updating DATABASE_URL...")
    new_content = content.replace(OLD_URL, NEW_URL)
    
    # Backup old .env
    backup_file = Path(".env.backup")
    backup_file.write_text(content)
    logger.info(f"✓ Backed up old .env to {backup_file}")
    
    # Write new .env
    env_file.write_text(new_content)
    logger.info("✓ Updated .env with new VPS database URL")
    
    logger.info("\n" + "=" * 60)
    logger.info("DATABASE_URL UPDATED SUCCESSFULLY")
    logger.info("=" * 60)
    logger.info(f"\nOld: {OLD_URL[:50]}...")
    logger.info(f"New: {NEW_URL}")
    logger.info("\nBackup saved to: .env.backup")
    
    return True


if __name__ == "__main__":
    success = update_env_file()
    
    if success:
        logger.info("\n✅ Next steps:")
        logger.info("1. Test connection: py test_database_connection.py")
        logger.info("2. Deploy to VPS")
        logger.info("3. Update frontend API URLs")
    else:
        logger.error("\n✗ Update failed. Please update .env manually.")
