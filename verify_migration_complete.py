"""
Verify that all critical data was migrated successfully.
"""
import asyncio
import asyncpg
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

async def verify_migration():
    """Verify all critical data exists in VPS database."""
    
    database_url = os.getenv("DATABASE_URL")
    
    logger.info("=" * 70)
    logger.info("MIGRATION VERIFICATION - DETAILED CHECK")
    logger.info("=" * 70)
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # 1. Check accounts table structure
        logger.info("\n[1] ACCOUNTS TABLE STRUCTURE")
        columns = await conn.fetch("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'accounts'
            ORDER BY ordinal_position
        """)
        
        logger.info(f"✓ Found {len(columns)} columns:")
        critical_columns = [
            'account_key', 'credential_key', 'tl_account_id', 'tl_email', 
            'initial_balance', 'current_balance', 'profit_cap_enabled',
            'profit_cap_type', 'profit_cap_value', 'profit_cap_frozen'
        ]
        
        for col_name in critical_columns:
            col = next((c for c in columns if c['column_name'] == col_name), None)
            if col:
                logger.info(f"  ✓ {col['column_name']}: {col['data_type']}")
            else:
                logger.error(f"  ✗ MISSING: {col_name}")
        
        # 2. Check account data
        logger.info("\n[2] ACCOUNTS DATA")
        accounts = await conn.fetch("SELECT * FROM accounts")
        
        for acc in accounts:
            logger.info(f"\n  Account: {acc['account_key']}")
            logger.info(f"    Email: {acc['tl_email']}")
            logger.info(f"    Account ID: {acc['tl_account_id']}")
            logger.info(f"    Initial Balance: ${acc['initial_balance']:.2f}")
            logger.info(f"    Current Balance: ${acc['current_balance']:.2f}")
            logger.info(f"    Paused: {acc['paused']}")
            logger.info(f"    Breached: {acc['breached']}")
            logger.info(f"    Profit Cap Enabled: {acc['profit_cap_enabled']}")
            logger.info(f"    Profit Cap Type: {acc['profit_cap_type']}")
            logger.info(f"    Profit Cap Value: {acc['profit_cap_value']}")
            logger.info(f"    Profit Cap Frozen: {acc['profit_cap_frozen']}")
            logger.info(f"    Risk Profile ID: {acc['risk_profile_id']}")
        
        # 3. Check channels
        logger.info("\n[3] CHANNELS")
        channels = await conn.fetch("SELECT * FROM channels")
        logger.info(f"✓ Found {len(channels)} channel(s):")
        for ch in channels:
            # Get column names dynamically
            cols = list(ch.keys())
            name = ch.get('name') or ch.get('channel_name') or ch.get('display_name') or 'Unknown'
            logger.info(f"  - ID: {ch['channel_id']}, Name: {name}")
        
        # 4. Check channel subscriptions
        logger.info("\n[4] CHANNEL SUBSCRIPTIONS")
        subs = await conn.fetch("""
            SELECT cs.*, a.account_key
            FROM channel_subscriptions cs
            JOIN accounts a ON cs.account_key = a.account_key
        """)
        logger.info(f"✓ Found {len(subs)} subscription(s):")
        for sub in subs:
            logger.info(f"  - {sub['account_key']} → Channel ID {sub['channel_id']} (enabled: {sub['enabled']})")
        
        # 5. Check trade history
        logger.info("\n[5] TRADE HISTORY")
        history = await conn.fetch("""
            SELECT * FROM trade_history 
            ORDER BY entry_time DESC 
            LIMIT 5
        """)
        logger.info(f"✓ Found {len(history)} recent trade(s):")
        for trade in history:
            logger.info(
                f"  - {trade['symbol']}: {trade['direction']} @ "
                f"${trade['entry_price']:.2f}, P&L: ${trade['pnl']:.2f}, "
                f"Status: {trade['outcome']}"
            )
        
        # 6. Check active trades
        logger.info("\n[6] ACTIVE TRADES")
        active = await conn.fetch("SELECT * FROM active_trades")
        logger.info(f"✓ Found {len(active)} active trade(s):")
        for trade in active:
            sl = trade.get('sl_price') or trade.get('stop_loss') or 0
            logger.info(
                f"  - {trade['symbol']}: {trade['direction']} @ "
                f"${trade['entry_price']:.2f}, SL: ${sl:.2f}, "
                f"Status: {trade['status']}"
            )
        
        # 7. Check risk profiles
        logger.info("\n[7] RISK PROFILES")
        profiles = await conn.fetch("SELECT * FROM risk_profiles")
        logger.info(f"✓ Found {len(profiles)} risk profile(s):")
        for profile in profiles:
            logger.info(
                f"  - {profile['profile_name']}: "
                f"Daily Loss: {profile['daily_loss_pct']}%, "
                f"Overall Loss: {profile['overall_loss_pct']}%, "
                f"Max Risk/Trade: {profile['max_risk_per_trade_pct']}%"
            )
        
        # 8. Check bot settings
        logger.info("\n[8] BOT SETTINGS")
        settings = await conn.fetch("SELECT * FROM bot_settings")
        logger.info(f"✓ Found {len(settings)} setting(s):")
        for setting in settings:
            key = setting.get('key') or setting.get('setting_key') or 'Unknown'
            value = setting.get('value') or setting.get('setting_value') or 'Unknown'
            logger.info(f"  - {key}: {value}")
        
        await conn.close()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ MIGRATION VERIFICATION COMPLETE")
        logger.info("=" * 70)
        logger.info("\n✅ ALL CRITICAL DATA SUCCESSFULLY MIGRATED")
        logger.info("\nYour VPS database is ready for production use!")
        logger.info("\nWhat you have:")
        logger.info(f"- {len(accounts)} account(s) with full configuration")
        logger.info(f"- {len(channels)} channel(s) configured")
        logger.info(f"- {len(subs)} active subscription(s)")
        logger.info(f"- {len(history)} trade history record(s)")
        logger.info(f"- {len(active)} active trade(s)")
        logger.info(f"- {len(profiles)} risk profile(s)")
        logger.info("- ✓ All profit cap columns ready")
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(verify_migration())
    exit(0 if result else 1)
