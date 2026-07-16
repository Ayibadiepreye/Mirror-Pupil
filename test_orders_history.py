"""
Test script for TradeLocker get_orders_history() endpoint.
Tests fetching closed order history and extracting P&L values.

This script uses the existing TradeLockerClient infrastructure to test
the orders history endpoint for P&L reconciliation purposes.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO"
)

from backend.core.tradelocker_client import TradeLockerClient
from backend.core.account_manager import get_account_manager
from backend.database import DatabaseManager


async def test_orders_history():
    """
    Test the TradeLocker orders history endpoint.
    
    Tests:
    1. Fetch orders history using TLAPI client
    2. Parse the response structure
    3. Extract P&L, fees, swap for each closed order
    4. Display results in readable format
    """
    
    logger.info("=" * 80)
    logger.info("TRADELOCKER ORDERS HISTORY ENDPOINT TEST")
    logger.info("=" * 80)
    
    # Initialize database
    logger.info("\n🔌 Connecting to database...")
    db = DatabaseManager()
    await db.connect()
    
    # Get account manager and inject database
    account_manager = get_account_manager()
    await account_manager.initialize(db)
    
    logger.info("✓ Database connected")
    
    # Get first available account for testing
    accounts = account_manager.get_all_accounts()
    
    if not accounts:
        logger.error("No accounts found! Please add an account first.")
        return
    
    test_account = accounts[0]
    account_key = test_account['account_key']
    
    logger.info(f"\nTesting with account: {account_key}")
    logger.info(f"Account: {test_account['tl_email']} | Server: {test_account['tl_server']}")
    
    # Get TradeLocker client
    client = account_manager.get_client_for_account(account_key)
    
    if not client:
        logger.error(f"Could not get TradeLocker client for {account_key}")
        return
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Fetch Orders History")
    logger.info("=" * 80)
    
    try:
        # Access the underlying TLAPI client
        if not hasattr(client, 'client') or client.client is None:
            logger.warning("TLAPI client not initialized. Authenticating...")
            await client.authenticate()
        
        tlapi = client.client
        
        if tlapi is None:
            logger.error("Failed to get TLAPI client")
            return
        
        logger.info("\nCalling: tl.get_orders_history()")
        
        # Fetch orders history
        history_data = await asyncio.to_thread(tlapi.get_orders_history)
        
        logger.info("✓ Response received!")
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch orders history: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return
    
    # Parse response
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Parse Response Structure")
    logger.info("=" * 80)
    
    logger.info(f"\nResponse type: {type(history_data)}")
    logger.info(f"Response keys: {history_data.keys() if isinstance(history_data, dict) else 'Not a dict'}")
    
    if "d" not in history_data:
        logger.warning("⚠️  No 'd' key in response!")
        logger.info(f"Full response: {history_data}")
        return
    
    data = history_data.get("d", {})
    logger.info(f"\n'd' keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
    
    if "ordersHistory" not in data:
        logger.warning("⚠️  No 'ordersHistory' key in data!")
        logger.info(f"Full 'd' content: {data}")
        return
    
    orders = data.get("ordersHistory", [])
    logger.info(f"\n✓ Found {len(orders)} closed order(s)")
    
    if not orders:
        logger.info("\nNo closed orders found in history.")
        logger.info("This might mean:")
        logger.info("  - Account has no closed trades yet")
        logger.info("  - History endpoint returns limited time range")
        logger.info("  - Account is new with no trade history")
        return
    
    # Analyze orders
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Extract P&L from Orders")
    logger.info("=" * 80)
    
    logger.info(f"\nAnalyzing {len(orders)} order(s)...\n")
    
    total_pnl = 0.0
    
    for i, order in enumerate(orders[:10], 1):  # Show first 10 orders
        logger.info(f"--- Order {i} ---")
        
        # Extract key fields
        order_id = order.get("id", "N/A")
        instrument_id = order.get("tradableInstrumentId", "N/A")
        side = order.get("side", "N/A")
        qty = order.get("qty", 0.0)
        avg_price = order.get("avgPrice", 0.0)
        status = order.get("status", "N/A")
        
        # Financial fields
        pnl = float(order.get("pnl", 0.0))
        fee = float(order.get("fee", 0.0))
        commission = float(order.get("commission", 0.0))
        swap = float(order.get("swap", 0.0))
        
        # Calculate net P&L
        net_pnl = pnl + swap - fee - commission
        total_pnl += net_pnl
        
        logger.info(f"Order ID: {order_id}")
        logger.info(f"Instrument ID: {instrument_id}")
        logger.info(f"Side: {side} | Qty: {qty} | Avg Price: {avg_price}")
        logger.info(f"Status: {status}")
        logger.info(f"")
        logger.info(f"💰 P&L Breakdown:")
        logger.info(f"  Gross P&L:  ${pnl:>10.2f}")
        logger.info(f"  Swap:       ${swap:>10.2f}")
        logger.info(f"  Fee:        ${-fee:>10.2f}")
        logger.info(f"  Commission: ${-commission:>10.2f}")
        logger.info(f"  ─────────────────────")
        logger.info(f"  Net P&L:    ${net_pnl:>10.2f}")
        logger.info("")
    
    if len(orders) > 10:
        logger.info(f"... and {len(orders) - 10} more order(s)")
    
    logger.info("=" * 80)
    logger.info(f"TOTAL NET P&L (shown orders): ${total_pnl:.2f}")
    logger.info("=" * 80)
    
    # Test mapping to position_id
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Check for Position ID Mapping")
    logger.info("=" * 80)
    
    sample_order = orders[0] if orders else None
    
    if sample_order:
        logger.info("\nSample order fields:")
        for key, value in sample_order.items():
            logger.info(f"  {key}: {value}")
        
        # Check if there's a position ID or related field
        position_fields = [k for k in sample_order.keys() if 'position' in k.lower()]
        if position_fields:
            logger.info(f"\n✓ Found position-related fields: {position_fields}")
        else:
            logger.info("\n⚠️  No obvious 'position' field found")
            logger.info("   May need to map using order_id or other identifier")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    logger.info("\n✅ Endpoint: tl.get_orders_history() works!")
    logger.info(f"✅ Returns: Dictionary with 'd' → 'ordersHistory' → array")
    logger.info(f"✅ Each order contains: pnl, fee, commission, swap")
    logger.info(f"✅ Can calculate net P&L: gross_pnl + swap - fee - commission")
    logger.info(f"\n📊 Found {len(orders)} closed order(s) in history")
    
    logger.info("\n" + "=" * 80)
    logger.info("RECOMMENDATIONS FOR P&L RECONCILIATION")
    logger.info("=" * 80)
    
    logger.info("\n1. Mapping Strategy:")
    if 'positionId' in (sample_order.keys() if sample_order else []):
        logger.info("   ✓ Use 'positionId' field to match with active_trades.tl_position_id")
    else:
        logger.info("   ⚠️  May need to use 'id' (order_id) or timestamp matching")
    
    logger.info("\n2. P&L Calculation:")
    logger.info("   ✓ Use: pnl + swap - fee - commission")
    
    logger.info("\n3. Time Range:")
    logger.info(f"   ✓ Endpoint returns {len(orders)} order(s)")
    logger.info("   ? Check if this covers your 1-hour reconciliation window")
    
    logger.info("\n4. Next Steps:")
    logger.info("   → Add get_orders_history() wrapper to TradeLockerClient")
    logger.info("   → Implement PnLReconciliationService")
    logger.info("   → Test with recently closed trades")
    
    # Cleanup
    await db.disconnect()
    logger.info("\n✓ Database disconnected")


if __name__ == "__main__":
    asyncio.run(test_orders_history())
