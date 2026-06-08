#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - Database Migration Runner
Safely applies GUI enhancement schema changes with rollback on failure.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


MIGRATION_STEPS = [
    # Step 1: Add columns to accounts table
    {
        "name": "Add display_name to accounts",
        "sql": "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS display_name TEXT;",
        "rollback": "ALTER TABLE accounts DROP COLUMN IF EXISTS display_name;"
    },
    {
        "name": "Add lot_size_override to accounts",
        "sql": "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS lot_size_override REAL;",
        "rollback": "ALTER TABLE accounts DROP COLUMN IF EXISTS lot_size_override;"
    },
    
    # Step 2: Add columns to channels table
    {
        "name": "Add display_name to channels",
        "sql": "ALTER TABLE channels ADD COLUMN IF NOT EXISTS display_name TEXT;",
        "rollback": "ALTER TABLE channels DROP COLUMN IF EXISTS display_name;"
    },
    
    # Step 3: Add columns to active_trades
    {
        "name": "Add channel_name to active_trades",
        "sql": "ALTER TABLE active_trades ADD COLUMN IF NOT EXISTS channel_name TEXT;",
        "rollback": "ALTER TABLE active_trades DROP COLUMN IF EXISTS channel_name;"
    },
    {
        "name": "Add index on active_trades",
        "sql": "CREATE INDEX IF NOT EXISTS idx_active_trades_account_status ON active_trades(account_key, status);",
        "rollback": "DROP INDEX IF EXISTS idx_active_trades_account_status;"
    },
    
    # Step 4: Add columns to trade_history
    {
        "name": "Add channel_name to trade_history",
        "sql": "ALTER TABLE trade_history ADD COLUMN IF NOT EXISTS channel_name TEXT;",
        "rollback": "ALTER TABLE trade_history DROP COLUMN IF EXISTS channel_name;"
    },
    {
        "name": "Add manual_action_type to trade_history",
        "sql": "ALTER TABLE trade_history ADD COLUMN IF NOT EXISTS manual_action_type TEXT;",
        "rollback": "ALTER TABLE trade_history DROP COLUMN IF EXISTS manual_action_type;"
    },
    {
        "name": "Add index on trade_history",
        "sql": "CREATE INDEX IF NOT EXISTS idx_trade_history_account_exit ON trade_history(account_key, exit_time DESC);",
        "rollback": "DROP INDEX IF EXISTS idx_trade_history_account_exit;"
    },
    
    # Step 5: Create notifications table
    {
        "name": "Create notifications table",
        "sql": """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id SERIAL PRIMARY KEY,
                account_key TEXT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                metadata JSONB,
                read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT fk_notification_account 
                    FOREIGN KEY (account_key) 
                    REFERENCES accounts(account_key) 
                    ON DELETE CASCADE
            );
        """,
        "rollback": "DROP TABLE IF EXISTS notifications;"
    },
    {
        "name": "Add indexes on notifications",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_notifications_account ON notifications(account_key, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);
        """,
        "rollback": """
            DROP INDEX IF EXISTS idx_notifications_account;
            DROP INDEX IF EXISTS idx_notifications_read;
            DROP INDEX IF EXISTS idx_notifications_created;
        """
    },
    
    # Step 6: Create manual_actions table
    {
        "name": "Create manual_actions table",
        "sql": """
            CREATE TABLE IF NOT EXISTS manual_actions (
                action_id SERIAL PRIMARY KEY,
                account_key TEXT NOT NULL,
                trade_id INTEGER,
                action_type TEXT NOT NULL,
                action_data JSONB,
                performed_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT fk_manual_action_account 
                    FOREIGN KEY (account_key) 
                    REFERENCES accounts(account_key) 
                    ON DELETE CASCADE
            );
        """,
        "rollback": "DROP TABLE IF EXISTS manual_actions;"
    },
    {
        "name": "Add index on manual_actions",
        "sql": "CREATE INDEX IF NOT EXISTS idx_manual_actions_account ON manual_actions(account_key, performed_at DESC);",
        "rollback": "DROP INDEX IF EXISTS idx_manual_actions_account;"
    },
    
    # Step 7: Populate channel_name in existing data
    {
        "name": "Populate channel_name in active_trades",
        "sql": """
            UPDATE active_trades at
            SET channel_name = COALESCE(c.display_name, CAST(c.channel_id AS TEXT))
            FROM channels c
            WHERE at.channel_id = c.channel_id
            AND at.channel_name IS NULL;
        """,
        "rollback": None  # Data update, no rollback
    },
    {
        "name": "Populate channel_name in trade_history",
        "sql": """
            UPDATE trade_history th
            SET channel_name = COALESCE(c.display_name, CAST(c.channel_id AS TEXT))
            FROM channels c
            WHERE th.channel_id = c.channel_id
            AND th.channel_name IS NULL;
        """,
        "rollback": None  # Data update, no rollback
    },
    
    # Step 8: Create cleanup function
    {
        "name": "Create notification cleanup function",
        "sql": """
            CREATE OR REPLACE FUNCTION cleanup_old_notifications()
            RETURNS void AS $$
            BEGIN
                DELETE FROM notifications
                WHERE created_at < NOW() - INTERVAL '48 hours';
            END;
            $$ LANGUAGE plpgsql;
        """,
        "rollback": "DROP FUNCTION IF EXISTS cleanup_old_notifications();"
    }
]


async def run_migration():
    """Run the migration with error handling and rollback."""
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        return False
    
    print("🔄 Starting database migration...")
    print(f"📊 Total steps: {len(MIGRATION_STEPS)}")
    print()
    
    completed_steps = []
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = await asyncpg.connect(db_url)
        print("✓ Connected to database")
        print()
        
        # Execute each migration step
        for i, step in enumerate(MIGRATION_STEPS, 1):
            step_name = step["name"]
            sql = step["sql"]
            
            try:
                print(f"[{i}/{len(MIGRATION_STEPS)}] {step_name}...")
                
                # Execute SQL
                await conn.execute(sql)
                
                completed_steps.append(step)
                print(f"  ✓ SUCCESS")
                
            except Exception as e:
                print(f"  ❌ FAILED: {e}")
                
                # Rollback completed steps
                if completed_steps:
                    print(f"\n⚠️ Rolling back {len(completed_steps)} completed step(s)...")
                    await rollback_steps(conn, completed_steps)
                
                await conn.close()
                return False
        
        # Close connection
        await conn.close()
        
        print()
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print(f"📊 Steps completed: {len(completed_steps)}/{len(MIGRATION_STEPS)}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def rollback_steps(conn, completed_steps):
    """Rollback completed migration steps in reverse order."""
    
    for step in reversed(completed_steps):
        rollback_sql = step.get("rollback")
        
        if not rollback_sql:
            print(f"  ⏭️ No rollback for: {step['name']}")
            continue
        
        try:
            print(f"  ⏪ Rolling back: {step['name']}...")
            await conn.execute(rollback_sql)
            print(f"    ✓ Rollback successful")
            
        except Exception as e:
            print(f"    ❌ Rollback failed: {e}")


async def verify_migration():
    """Verify migration by checking for new columns and tables."""
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return False
    
    print()
    print("🔍 Verifying migration...")
    print()
    
    try:
        conn = await asyncpg.connect(db_url)
        
        # Check accounts columns
        result = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'accounts' 
            AND column_name IN ('display_name', 'lot_size_override')
        """)
        
        if len(result) == 2:
            print("  ✓ Accounts table: display_name, lot_size_override")
        else:
            print(f"  ⚠️ Accounts columns: found {len(result)}/2")
        
        # Check channels columns
        result = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'channels' 
            AND column_name = 'display_name'
        """)
        
        if result:
            print("  ✓ Channels table: display_name")
        else:
            print("  ⚠️ Channels display_name not found")
        
        # Check active_trades columns
        result = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'active_trades' 
            AND column_name = 'channel_name'
        """)
        
        if result:
            print("  ✓ Active trades: channel_name")
        else:
            print("  ⚠️ Active trades channel_name not found")
        
        # Check trade_history columns
        result = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'trade_history' 
            AND column_name IN ('channel_name', 'manual_action_type')
        """)
        
        if len(result) == 2:
            print("  ✓ Trade history: channel_name, manual_action_type")
        else:
            print(f"  ⚠️ Trade history columns: found {len(result)}/2")
        
        # Check notifications table
        result = await conn.fetch("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'notifications'
        """)
        
        if result[0]['count'] == 1:
            print("  ✓ Notifications table created")
        else:
            print("  ⚠️ Notifications table not found")
        
        # Check manual_actions table
        result = await conn.fetch("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_name = 'manual_actions'
        """)
        
        if result[0]['count'] == 1:
            print("  ✓ Manual actions table created")
        else:
            print("  ⚠️ Manual actions table not found")
        
        await conn.close()
        
        print()
        print("✅ Verification complete")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    
    print()
    print("=" * 60)
    print("  Mirror Pupil v5.1 - Database Migration")
    print("  GUI Enhancements Schema Update")
    print("=" * 60)
    print()
    
    # Run migration
    success = await run_migration()
    
    if not success:
        print()
        print("❌ Migration failed. Database may be partially updated.")
        print("   Check the error messages above for details.")
        return
    
    # Verify migration
    await verify_migration()
    
    print()
    print("🎉 Migration completed! You can now restart the bot.")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
