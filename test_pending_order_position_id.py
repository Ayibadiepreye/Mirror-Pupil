"""
Quick Test: Verify Pending Order Position ID Resolution
Tests that limit/stop orders get position_id resolved when they fill.
"""

import asyncio
import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

from dotenv import load_dotenv
load_dotenv()

from backend.database import DatabaseManager
from backend.core.tradelocker_client import TradeLockerClient


async def test_pending_position_resolution():
    """Test that pending orders get position_id when filled."""
    logger.info("=" * 80)
    logger.info("PENDING ORDER POSITION ID RESOLUTION TEST")
    logger.info("=" * 80)
    
    # Initialize
    db = DatabaseManager()
    await db.connect()
    
    # Get account
    accounts = await db.get_all_accounts()
    if not accounts:
        logger.error("No accounts found")
        return
    
    account = next((a for a in accounts if not a.breached and not a.paused), None)
    if not account:
        logger.error("No active accounts found")
        return
    
    # Load credentials
    async with db.pool.acquire() as conn:
        acct_row = await conn.fetchrow(
            """SELECT tl_email, tl_password, tl_server, tl_prop_firm, tl_account_id
            FROM accounts WHERE credential_key = $1 LIMIT 1""",
            account.credential_key
        )
    
    # Create client
    client = TradeLockerClient(
        email=acct_row['tl_email'],
        password=acct_row['tl_password'],
        server=acct_row['tl_prop_firm'] or acct_row['tl_server'],
        environment=acct_row['tl_server'],
        account_id=int(acct_row['tl_account_id']) if acct_row['tl_account_id'] else None
    )
    
    await client.authenticate()
    logger.info(f"✓ Authenticated as {account.display_name}")
    
    # Get EURUSD instrument
    instrument_id = await client.get_instrument_id_from_symbol_name("EURUSD")
    if not instrument_id:
        logger.error("EURUSD not found")
        return
    
    logger.info(f"✓ Found EURUSD (instrument_id: {instrument_id})")
    
    # Get current price
    price = await client.get_market_price("EURUSD")
    if not price:
        logger.error("Cannot get EURUSD price")
        return
    
    logger.info(f"✓ Current EURUSD price: {price:.5f}")
    
    # Create limit order 50 pips below market (will fill immediately in demo)
    limit_price = round(price - 0.0050, 5)  # 50 pips below
    
    logger.info(f"Creating LIMIT order: BUY 0.01 EURUSD @ {limit_price}")
    
    order = await client.create_order(
        instrument_id=instrument_id,
        quantity=0.01,
        side="buy",
        type_="limit",
        price=limit_price,
        validity="GTC"
    )
    
    order_id = order if isinstance(order, int) else order.get('id')
    logger.info(f"✓ Order created: {order_id}")
    
    # Simulate what PendingOrderMonitor does
    logger.info("\nSimulating PendingOrderMonitor behavior:")
    
    # Wait a bit for order to potentially fill
    await asyncio.sleep(2)
    
    # Check order status
    order_status = await client.get_order_status(order_id)
    if not order_status:
        logger.warning("Order status not available yet")
        # Cancel order
        await client.delete_order(order_id)
        logger.info("✓ Cancelled test order")
        await db.disconnect()
        return
    
    status = order_status.get('status', '').lower()
    logger.info(f"Order status: {status}")
    
    if status == 'filled':
        logger.info("✅ Order filled! Testing position_id resolution...")
        
        # Test position_id resolution
        position_id = None
        for attempt in range(10):
            position_id = await client.get_position_id_from_order_id(order_id)
            if position_id:
                logger.info(f"✅ SUCCESS: Resolved position_id {position_id} on attempt {attempt + 1}")
                break
            await asyncio.sleep(0.5)
        
        if position_id:
            # Close the position
            await client.close_position(position_id)
            logger.info(f"✓ Closed test position {position_id}")
            logger.info("\n🎉 TEST PASSED: Pending order position_id resolution works!")
        else:
            logger.error("❌ FAILED: Could not resolve position_id")
    
    else:
        logger.info(f"Order not filled (status: {status}), cancelling...")
        await client.delete_order(order_id)
        logger.info("✓ Cancelled test order")
        logger.info("\n✅ TEST SKIPPED: Order didn't fill (normal in some market conditions)")
    
    await db.disconnect()
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_pending_position_resolution())
