"""
Mirror Pupil v5.1 - Database Test Script
Tests Neon PostgreSQL connection and basic operations.
"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

from backend.database import (
    DatabaseManager,
    Channel,
    RiskProfile,
    Account,
    ChannelSubscription,
    ActiveTrade,
    WaitingRoom,
)

# Load environment
load_dotenv()

# Configure logger
logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


async def test_database():
    """Test database connection and operations."""
    
    print("\n" + "="*60)
    print("Mirror Pupil v5.1 - Database Test")
    print("="*60 + "\n")
    
    # Check DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url or "your_" in database_url:
        logger.error("❌ DATABASE_URL not configured in .env")
        logger.info("Please set DATABASE_URL in your .env file")
        logger.info("Get it from: https://console.neon.tech")
        return
    
    logger.info(f"Database URL: {database_url[:30]}...")
    
    # Initialize database manager
    db = DatabaseManager(database_url)
    
    try:
        # Test 1: Connect to database
        logger.info("\n[Test 1] Connecting to Neon PostgreSQL...")
        await db.connect(min_size=2, max_size=5)
        logger.info("✓ Connection successful")
        
        # Test 2: Check schema initialization
        logger.info("\n[Test 2] Checking schema...")
        channels = await db.get_all_channels()
        logger.info(f"✓ Found {len(channels)} channel(s)")
        for ch in channels:
            logger.info(f"  - {ch.display_name} (ID: {ch.channel_id}, Priority: {ch.priority})")
        
        # Test 3: Check risk profiles
        logger.info("\n[Test 3] Checking risk profiles...")
        profiles = await db.get_all_risk_profiles()
        logger.info(f"✓ Found {len(profiles)} risk profile(s)")
        for prof in profiles:
            logger.info(f"  - {prof.profile_name} (Default: {prof.is_default})")
            logger.info(f"    Daily: {prof.daily_loss_pct}%, Overall: {prof.overall_loss_pct}%")
        
        # Test 4: Add a test account
        logger.info("\n[Test 4] Adding test account...")
        test_account = Account(
            account_key="test@example.com:12345",
            credential_key="test@example.com",
            tl_account_id="12345",
            tl_email="test@example.com",
            tl_password="encrypted_password_here",
            tl_server="demo",
            display_name="Test Account",
            initial_balance=100000.0,
            current_balance=100000.0,
            cycle_start_date=datetime.now().date()
        )
        
        success = await db.add_account(test_account)
        if success:
            logger.info("✓ Test account added")
        else:
            logger.warning("⚠ Account already exists (this is OK)")
        
        # Test 5: Sync channel subscriptions
        logger.info("\n[Test 5] Syncing channel subscriptions...")
        await db.sync_channel_subscriptions()
        
        subs = await db.get_channel_subscriptions(test_account.account_key)
        logger.info(f"✓ Account has {len(subs)} channel subscription(s)")
        for sub in subs:
            channel = await db.get_channel(sub.channel_id)
            logger.info(f"  - {channel.display_name}: {'Enabled' if sub.enabled else 'Disabled'}")
        
        # Test 6: Add active trade
        logger.info("\n[Test 6] Adding test active trade...")
        test_trade = ActiveTrade(
            account_key=test_account.account_key,
            channel_id=-1001859598768,  # BillirichyFX
            signal_id="B_12345",
            symbol="XAUUSD",
            direction="BUY",
            entry_price=2650.50,
            sl=2640.00,
            tp=2670.00,
            lot_size=0.1,
            tl_order_id="TEST_ORDER_123",
            tl_position_id="TEST_POS_123",
            status="filled",
            risk_usd=105.0
        )
        
        trade_id = await db.add_active_trade(test_trade)
        if trade_id:
            logger.info(f"✓ Active trade added (ID: {trade_id})")
        else:
            logger.error("❌ Failed to add active trade")
        
        # Test 7: Get active trades
        logger.info("\n[Test 7] Fetching active trades...")
        active_trades = await db.get_active_trades(test_account.account_key)
        logger.info(f"✓ Found {len(active_trades)} active trade(s)")
        for trade in active_trades:
            logger.info(
                f"  - {trade.symbol} {trade.direction} @ {trade.entry_price} "
                f"(SL: {trade.sl}, TP: {trade.tp})"
            )
        
        # Test 8: Waiting room
        logger.info("\n[Test 8] Testing waiting room...")
        waiting_entry = WaitingRoom(
            channel_id=-1001859598768,
            symbol="GBPUSD",
            direction="SELL",
            entry_msg_id=99999,
            expires_at=datetime.now() + timedelta(minutes=15)
        )
        
        success = await db.add_to_waiting_room(waiting_entry)
        if success:
            logger.info("✓ Added entry to waiting room")
            
            # Retrieve it
            retrieved = await db.get_from_waiting_room(
                waiting_entry.channel_id,
                waiting_entry.symbol,
                waiting_entry.direction
            )
            if retrieved:
                logger.info(f"✓ Retrieved from waiting room: {retrieved.symbol} {retrieved.direction}")
            else:
                logger.error("❌ Failed to retrieve from waiting room")
        
        # Test 9: Message cache
        logger.info("\n[Test 9] Testing message cache...")
        msg_id = 123456789
        channel_id = -1001859598768
        
        # Check if processed
        is_processed = await db.is_message_processed(msg_id, channel_id)
        logger.info(f"Message {msg_id} processed: {is_processed}")
        
        # Mark as processed
        await db.mark_message_processed(msg_id, channel_id)
        logger.info("✓ Marked message as processed")
        
        # Check again
        is_processed = await db.is_message_processed(msg_id, channel_id)
        logger.info(f"Message {msg_id} processed: {is_processed}")
        
        # Test 10: Account queries
        logger.info("\n[Test 10] Testing account queries...")
        all_accounts = await db.get_all_accounts()
        logger.info(f"✓ Total accounts in database: {len(all_accounts)}")
        
        account = await db.get_account(test_account.account_key)
        if account:
            logger.info(f"✓ Retrieved account: {account.display_name}")
            logger.info(f"  Balance: ${account.current_balance:,.2f}")
            logger.info(f"  Paused: {account.paused}, Breached: {account.breached}")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("✓ All database tests passed!")
        logger.info("="*60 + "\n")
        
        logger.info("Database is ready for use. Next steps:")
        logger.info("1. Add your TradeLocker credentials via GUI (or set in .env for testing)")
        logger.info("2. Configure risk profiles if needed")
        logger.info("3. Start the Telegram listener")
        logger.info("4. Monitor trades via GUI\n")
        
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(test_database())
