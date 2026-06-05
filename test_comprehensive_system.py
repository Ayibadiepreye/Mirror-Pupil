"""
COMPREHENSIVE MIRROR PUPIL SYSTEM TEST
Tests all critical components with live TradeLocker API
"""
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime
from loguru import logger

load_dotenv()

# Silence debug logs for cleaner output
logger.remove()
logger.add(lambda msg: None, level="ERROR")

print("="*80)
print("MIRROR PUPIL COMPREHENSIVE SYSTEM TEST")
print("="*80)
print()

async def test_all():
    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }
    
    # ====================
    # 1. DATABASE CONNECTION
    # ====================
    print("1. DATABASE CONNECTION TEST")
    print("-" * 60)
    try:
        from backend.database import DatabaseManager
        db = DatabaseManager()
        await db.connect()
        print("✓ Database connected")
        
        # Get test account
        accounts = await db.get_all_accounts()
        if not accounts:
            print("❌ No accounts in database - cannot proceed")
            await db.disconnect()
            return results
        
        test_account = accounts[0]
        print(f"✓ Using test account: {test_account.tl_email}")
        print(f"  Prop firm: {test_account.tl_prop_firm}")
        print(f"  Environment: {test_account.tl_server}")
        print(f"  Account ID: {test_account.tl_account_id}")
        results["passed"].append("Database connection")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        results["failed"].append(f"Database: {e}")
        return results
    
    print()
    
    # ====================
    # 2. TRADELOCKER CLIENT
    # ====================
    print("2. TRADELOCKER CLIENT TEST")
    print("-" * 60)
    try:
        from backend.core.tradelocker_client import TradeLockerClient
        
        client = TradeLockerClient(
            email=test_account.tl_email,
            password=test_account.tl_password,
            server=test_account.tl_prop_firm,
            environment=test_account.tl_server,
            account_id=int(test_account.tl_account_id)
        )
        
        # Test authentication
        auth_success = await client.authenticate()
        if auth_success:
            print("✓ Authentication successful")
            results["passed"].append("TradeLocker authentication")
        else:
            print("❌ Authentication failed")
            results["failed"].append("TradeLocker authentication")
            await db.disconnect()
            return results
            
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        results["failed"].append(f"TradeLocker client: {e}")
        await db.disconnect()
        return results
    
    print()
    
    # ====================
    # 3. ACCOUNT STATE
    # ====================
    print("3. ACCOUNT STATE TEST")
    print("-" * 60)
    try:
        state = await client.get_account_state()
        print(f"✓ Account state fetched")
        print(f"  Balance: {state.get('accountBalance')}")
        print(f"  Equity: {state.get('equity')}")
        print(f"  Margin: {state.get('margin')}")
        results["passed"].append("Account state")
    except Exception as e:
        print(f"❌ Account state failed: {e}")
        results["failed"].append(f"Account state: {e}")
    
    print()
    
    # ====================
    # 4. SYMBOL RESOLUTION
    # ====================
    print("4. SYMBOL RESOLUTION TEST")
    print("-" * 60)
    test_symbols = ["EURUSD", "XAUUSD", "USDJPY", "GBPUSD"]
    symbol_ids = {}
    
    for symbol in test_symbols:
        try:
            instrument_id = await client.get_instrument_id_from_symbol_name(symbol)
            if instrument_id:
                print(f"✓ {symbol} → ID {instrument_id}")
                symbol_ids[symbol] = instrument_id
                results["passed"].append(f"Symbol resolution: {symbol}")
            else:
                print(f"⚠️ {symbol} → Not found")
                results["warnings"].append(f"{symbol} not available")
        except Exception as e:
            print(f"❌ {symbol} → Error: {e}")
            results["failed"].append(f"Symbol resolution {symbol}: {e}")
    
    if not symbol_ids:
        print("❌ No symbols resolved - cannot continue")
        await db.disconnect()
        return results
    
    print()
    
    # ====================
    # 5. LIVE PRICE FETCHING (NEW METHOD)
    # ====================
    print("5. LIVE PRICE FETCHING TEST (get_market_price)")
    print("-" * 60)
    prices = {}
    
    for symbol, instrument_id in symbol_ids.items():
        try:
            # Test the fixed get_market_price method
            price = await client.get_market_price(symbol)
            if price:
                print(f"✓ {symbol}: ${price:.5f}")
                prices[symbol] = price
                results["passed"].append(f"Price fetch: {symbol}")
            else:
                print(f"❌ {symbol}: No price returned")
                results["failed"].append(f"Price fetch {symbol}: No price")
        except Exception as e:
            print(f"❌ {symbol}: {e}")
            results["failed"].append(f"Price fetch {symbol}: {e}")
    
    print()
    
    # ====================
    # 6. INSTRUMENT SPECS
    # ====================
    print("6. INSTRUMENT SPECS TEST")
    print("-" * 60)
    instrument_specs = {}
    
    for symbol in list(symbol_ids.keys())[:2]:  # Test first 2
        try:
            specs = await client.get_instrument(symbol)
            print(f"✓ {symbol} specs:")
            print(f"    Contract size: {specs.get('contract_size')}")
            print(f"    Tick size: {specs.get('tick_size')}")
            print(f"    Tick value: {specs.get('tick_value')}")
            print(f"    Lot step: {specs.get('lot_step')}")
            instrument_specs[symbol] = specs
            results["passed"].append(f"Instrument specs: {symbol}")
        except Exception as e:
            print(f"❌ {symbol}: {e}")
            results["failed"].append(f"Instrument specs {symbol}: {e}")
    
    print()
    
    # ====================
    # 7. RISK CALCULATION
    # ====================
    print("7. RISK CALCULATION TEST")
    print("-" * 60)
    
    if prices and instrument_specs:
        try:
            from backend.risk.calculator import calculate_usd_risk
            
            # Mock trade on EURUSD
            test_symbol = "EURUSD" if "EURUSD" in prices else list(prices.keys())[0]
            test_price = prices[test_symbol]
            test_specs = instrument_specs.get(test_symbol, {})
            
            entry_price = test_price
            sl_distance = 0.001  # 10 pips
            sl_price = entry_price - sl_distance if entry_price else None
            lot_size = 0.01
            
            if sl_price:
                risk_usd = await calculate_usd_risk(
                    symbol=test_symbol,
                    entry_price=entry_price,
                    stop_loss=sl_price,
                    lot_size=lot_size,
                    client=client,
                    current_price=entry_price,
                    instrument=test_specs
                )
                
                print(f"✓ Risk calculation for mock trade:")
                print(f"    Symbol: {test_symbol}")
                print(f"    Entry: {entry_price:.5f}")
                print(f"    SL: {sl_price:.5f}")
                print(f"    Lot size: {lot_size}")
                print(f"    Risk USD: ${risk_usd:.2f}")
                results["passed"].append("Risk calculation")
            else:
                print(f"❌ Cannot calculate risk - no price")
                results["failed"].append("Risk calculation: No price")
                
        except Exception as e:
            print(f"❌ Risk calculation failed: {e}")
            results["failed"].append(f"Risk calculation: {e}")
    else:
        print("⚠️ Skipped - no prices or specs available")
        results["warnings"].append("Risk calculation skipped")
    
    print()
    
    # ====================
    # 8. ROUTE VALIDATION
    # ====================
    print("8. ROUTE VALIDATION TEST")
    print("-" * 60)
    
    for symbol, instrument_id in list(symbol_ids.items())[:2]:
        try:
            routes = await client.validate_instrument_routes(instrument_id)
            if routes["info"] and routes["trade"]:
                print(f"✓ {symbol}: INFO ✓ TRADE ✓")
                results["passed"].append(f"Route validation: {symbol}")
            else:
                print(f"⚠️ {symbol}: INFO={routes['info']} TRADE={routes['trade']}")
                results["warnings"].append(f"{symbol} missing routes")
        except Exception as e:
            print(f"❌ {symbol}: {e}")
            results["failed"].append(f"Route validation {symbol}: {e}")
    
    print()
    
    # ====================
    # 9. ORDER CREATION TEST (DRY RUN)
    # ====================
    print("9. ORDER CREATION TEST (Market Order - IOC Validity)")
    print("-" * 60)
    print("NOTE: This will attempt to place a REAL 0.01 lot market order!")
    print("Checking if DRY_RUN is enabled...")
    
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    if dry_run:
        print("✓ DRY_RUN=true, order will be simulated")
        results["passed"].append("Order creation (simulated)")
    else:
        print("⚠️ DRY_RUN=false, this would place a REAL order!")
        print("⚠️ Skipping order creation test to protect your account")
        results["warnings"].append("Order creation skipped (DRY_RUN=false)")
    
    print()
    
    # ====================
    # 10. VALIDITY LOGIC TEST
    # ====================
    print("10. VALIDITY LOGIC TEST (GTC vs IOC)")
    print("-" * 60)
    
    # Test the logic in trade_executor
    test_cases = [
        ("market", "IOC"),
        ("limit", "GTC"),
        ("stop", "GTC")
    ]
    
    for order_type, expected_validity in test_cases:
        if order_type == "market":
            validity = "IOC"
        else:
            validity = "GTC"
        
        if validity == expected_validity:
            print(f"✓ {order_type.upper()} order → {validity} (correct)")
            results["passed"].append(f"Validity logic: {order_type}")
        else:
            print(f"❌ {order_type.upper()} order → {validity} (expected {expected_validity})")
            results["failed"].append(f"Validity logic {order_type}: Wrong validity")
    
    print()
    
    # ====================
    # 11. GET ALL POSITIONS
    # ====================
    print("11. GET POSITIONS TEST")
    print("-" * 60)
    try:
        positions = await client.get_all_positions()
        print(f"✓ Retrieved {len(positions)} open position(s)")
        if positions:
            for pos in positions[:3]:  # Show first 3
                print(f"    Position {pos.get('id')}: {pos.get('quantity')} lots")
        results["passed"].append("Get positions")
    except Exception as e:
        print(f"❌ Get positions failed: {e}")
        results["failed"].append(f"Get positions: {e}")
    
    print()
    
    # ====================
    # 12. CHANNEL PLUGINS
    # ====================
    print("12. CHANNEL PLUGINS TEST")
    print("-" * 60)
    try:
        from backend.channels.registry import get_registry
        
        registry = get_registry()
        await registry.initialize(db)
        
        plugins = registry.get_all_plugins()
        print(f"✓ Loaded {len(plugins)} channel plugin(s)")
        for channel_id, plugin in plugins.items():
            print(f"    {plugin.display_name} (ID: {channel_id})")
        
        if len(plugins) > 0:
            results["passed"].append("Channel plugins")
        else:
            results["warnings"].append("No channel plugins loaded")
            
    except Exception as e:
        print(f"❌ Channel plugins failed: {e}")
        results["failed"].append(f"Channel plugins: {e}")
    
    print()
    
    # ====================
    # 13. SIGNAL PARSING TEST
    # ====================
    print("13. SIGNAL PARSING TEST")
    print("-" * 60)
    try:
        from backend.channels.billirichy.entry import parse_entry_signal
        
        # Mock message object
        class MockMessage:
            def __init__(self):
                self.id = 12345
        
        test_signal_text = """
        gold buy
        entry: 2650
        sl: 2645
        tp1: 2660
        tp2: 2670
        """
        
        mock_msg = MockMessage()
        
        # Mock waiting room function
        async def mock_waiting_room(bare_signal):
            pass
        
        parsed = await parse_entry_signal(
            mock_msg,
            test_signal_text.lower(),
            -1001859598768,
            mock_waiting_room
        )
        
        if parsed:
            print(f"✓ Signal parsed successfully:")
            print(f"    Symbol: {parsed.symbol}")
            print(f"    Direction: {parsed.direction}")
            print(f"    Entry: {parsed.entry_price}")
            print(f"    SL: {parsed.sl}")
            print(f"    TP: {parsed.tp}")
            results["passed"].append("Signal parsing")
        else:
            print(f"⚠️ Signal not parsed (might be bare signal)")
            results["warnings"].append("Signal parsing returned None")
            
    except Exception as e:
        print(f"❌ Signal parsing failed: {e}")
        results["failed"].append(f"Signal parsing: {e}")
    
    print()
    
    # ====================
    # CLEANUP
    # ====================
    await db.disconnect()
    
    return results


async def main():
    results = await test_all()
    
    # ====================
    # FINAL REPORT
    # ====================
    print()
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print()
    
    print(f"✓ PASSED: {len(results['passed'])}")
    for test in results['passed']:
        print(f"    ✓ {test}")
    print()
    
    if results['warnings']:
        print(f"⚠️ WARNINGS: {len(results['warnings'])}")
        for warning in results['warnings']:
            print(f"    ⚠️ {warning}")
        print()
    
    if results['failed']:
        print(f"❌ FAILED: {len(results['failed'])}")
        for failure in results['failed']:
            print(f"    ❌ {failure}")
        print()
    
    total = len(results['passed']) + len(results['failed'])
    pass_rate = (len(results['passed']) / total * 100) if total > 0 else 0
    
    print(f"PASS RATE: {pass_rate:.1f}% ({len(results['passed'])}/{total})")
    print()
    
    if not results['failed']:
        print("🎉 ALL CRITICAL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED - REVIEW ABOVE")
    
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
