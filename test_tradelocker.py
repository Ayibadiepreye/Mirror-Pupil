"""
Mirror Pupil v5.1 - TradeLocker Integration Test
Test TradeLocker client without needing Telegram.
"""

import asyncio
import os
from dotenv import load_dotenv
from loguru import logger

from backend.core.account_manager import AccountManager
from backend.core.trade_executor import TradeExecutor
from backend.channels.base import ParsedSignal
from datetime import datetime

# Load environment
load_dotenv()


async def test_authentication():
    """Test 1: Authentication and account discovery"""
    print("\n" + "=" * 80)
    print("Test 1: Authentication & Account Discovery")
    print("=" * 80)
    
    email = os.getenv("TL_EMAIL_1")
    password = os.getenv("TL_PASSWORD_1")
    server = os.getenv("TL_SERVER_1", "demo")
    
    if not email or not password:
        print("❌ TL_EMAIL_1 and TL_PASSWORD_1 not set in .env")
        print("   Add your TradeLocker credentials to test")
        return None
    
    manager = AccountManager()
    
    success = await manager.add_credential(email, password, server)
    
    if success:
        print(f"\n✓ Authentication successful!")
        print(f"\nDiscovered accounts:")
        for acct in manager.get_all_accounts():
            print(f"  • {acct['account_number']}: ${acct['current_balance']:,.2f}")
        return manager
    else:
        print(f"\n❌ Authentication failed")
        return None


async def test_instrument_resolution(manager: AccountManager):
    """Test 2: Symbol resolution and instrument caching"""
    print("\n" + "=" * 80)
    print("Test 2: Instrument Resolution")
    print("=" * 80)
    
    accounts = manager.get_all_accounts()
    if not accounts:
        print("❌ No accounts available")
        return
    
    client = accounts[0]['client']
    
    # Test symbols
    test_symbols = ["XAUUSD", "EURUSD", "US30", "GBPUSD"]
    
    for symbol in test_symbols:
        print(f"\nResolving {symbol}...")
        instrument_id = await client.get_instrument_id_from_symbol_name(symbol)
        
        if instrument_id:
            print(f"  ✓ {symbol} → instrument_id={instrument_id}")
            
            # Validate routes
            routes = await client.validate_instrument_routes(instrument_id)
            print(f"    Routes: INFO={routes['info']}, TRADE={routes['trade']}")
        else:
            print(f"  ❌ {symbol} not found")


async def test_dry_run_execution(manager: AccountManager):
    """Test 3: Dry-run trade execution"""
    print("\n" + "=" * 80)
    print("Test 3: Dry-Run Trade Execution")
    print("=" * 80)
    
    # Create a mock signal
    signal = ParsedSignal(
        channel_id=-1001859598768,
        msg_id=12345,
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2650.0,
        sl=2640.0,
        tp=[2680.0],
        order_type="MARKET",
        is_reentry=False,
        raw_text="GOLD BUY @ 2650 SL 2640 TP 2680",
        timestamp=datetime.now()
    )
    
    print(f"\nMock Signal: {signal}")
    
    # Execute in dry-run mode
    executor = TradeExecutor(dry_run=True)
    
    results = await executor.execute_signal(signal)
    
    print(f"\nExecution Results:")
    for account_key, result in results.items():
        status = result.get('status')
        if status == 'filled':
            print(f"  ✓ {account_key}: {status}")
            print(f"    Order ID: {result.get('order_id')}")
            print(f"    Position ID: {result.get('position_id')}")
            print(f"    Fill Price: {result.get('fill_price')}")
        else:
            print(f"  ❌ {account_key}: {status}")
            print(f"    Error: {result.get('error')}")


async def test_balance_update(manager: AccountManager):
    """Test 4: Balance fetching"""
    print("\n" + "=" * 80)
    print("Test 4: Balance Update")
    print("=" * 80)
    
    accounts = manager.get_all_accounts()
    
    for acct in accounts:
        account_key = acct['account_key']
        print(f"\nFetching balance for {account_key}...")
        
        balance = await manager.update_account_balance(account_key)
        
        if balance is not None:
            print(f"  ✓ Balance: ${balance:,.2f}")
            print(f"    Equity: ${acct.get('equity', 0):,.2f}")
        else:
            print(f"  ❌ Failed to fetch balance")


async def test_open_positions(manager: AccountManager):
    """Test 5: Fetch open positions"""
    print("\n" + "=" * 80)
    print("Test 5: Open Positions")
    print("=" * 80)
    
    accounts = manager.get_all_accounts()
    
    for acct in accounts:
        account_key = acct['account_key']
        print(f"\nFetching positions for {account_key}...")
        
        positions = await manager.get_open_positions(account_key)
        
        if positions:
            print(f"  ✓ Found {len(positions)} open position(s):")
            for pos in positions:
                symbol = pos.get('symbol', 'Unknown')
                side = pos.get('side', 'Unknown')
                qty = pos.get('quantity', 0)
                pnl = pos.get('unrealizedPnL', 0)
                print(f"    • {symbol} {side} {qty} lots (P&L: ${pnl:,.2f})")
        else:
            print(f"  ✓ No open positions")


async def main():
    """Run all tests"""
    print("\n🧪 Mirror Pupil v5.1 - TradeLocker Integration Test Suite\n")
    
    # Test 1: Authentication
    manager = await test_authentication()
    
    if not manager:
        print("\n❌ Authentication failed. Cannot proceed with other tests.")
        print("\nMake sure you have set in .env:")
        print("  TL_EMAIL_1=your_email@example.com")
        print("  TL_PASSWORD_1=your_password")
        print("  TL_SERVER_1=demo  # or 'live'")
        return
    
    # Test 2: Instrument resolution
    await test_instrument_resolution(manager)
    
    # Test 3: Dry-run execution
    await test_dry_run_execution(manager)
    
    # Test 4: Balance update
    await test_balance_update(manager)
    
    # Test 5: Open positions
    await test_open_positions(manager)
    
    # Cleanup
    await manager.shutdown()
    
    print("\n" + "=" * 80)
    print("✓ All tests complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Set DRY_RUN=false in .env to enable live trading")
    print("  2. Run: python telegram_client.py")
    print("  3. Real signals will be executed on TradeLocker!")
    print()


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    asyncio.run(main())
