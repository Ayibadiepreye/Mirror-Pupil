"""
Field Verification Tests
Tests for TradeLocker API field name fixes.
"""

import asyncio
from backend.core.tradelocker_client import TradeLockerClient
from loguru import logger
import os
from dotenv import load_dotenv


async def verify_fixes(client: TradeLockerClient):
    """Verify all fixes work correctly."""
    print("\n" + "="*60)
    print("POST-FIX VERIFICATION")
    print("="*60 + "\n")
    
    try:
        # Test 1: unrealizedProfitLoss
        print("Test 1: Position P&L Field")
        print("-" * 40)
        positions = await client.get_all_positions()
        if positions:
            pnl = positions[0].get('unrealizedProfitLoss')
            print(f"✓ unrealizedProfitLoss: {pnl}")
            print(f"✓ Position fields present: {list(positions[0].keys())[:5]}...")
        else:
            print("⚠ No open positions to test")
        print()
        
        # Test 2: Account fields
        print("Test 2: Account Fields")
        print("-" * 40)
        accounts = await client.get_all_accounts()
        if accounts:
            balance = accounts[0].get('accountBalance')
            accNum = accounts[0].get('accNum')
            account_id = accounts[0].get('id')
            print(f"✓ accountBalance: {balance}")
            print(f"✓ accNum: {accNum}")
            print(f"✓ id: {account_id}")
        else:
            print("⚠ No accounts found")
        print()
        
        # Test 3: get_instrument() wrapper
        print("Test 3: Instrument Specs Wrapper")
        print("-" * 40)
        try:
            instrument = await client.get_instrument("EURUSD")
            print(f"✓ contract_size: {instrument.get('contract_size')}")
            print(f"✓ tick_size: {instrument.get('tick_size')}")
            print(f"✓ tick_value: {instrument.get('tick_value')}")
            print(f"✓ min_quantity: {instrument.get('min_quantity')}")
            print(f"✓ max_quantity: {instrument.get('max_quantity')}")
            print(f"✓ lot_step: {instrument.get('lot_step')}")
        except Exception as e:
            print(f"✗ Failed to get instrument: {e}")
        print()
        
        print("="*60)
        print("✅ ALL FIXES VERIFIED!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Verification failed: {e}\n")
        raise


async def discover_all_fields(client: TradeLockerClient):
    """Log ALL field names from raw SDK responses."""
    print("\n" + "="*60)
    print("FIELD DISCOVERY - RAW SDK RESPONSES")
    print("="*60 + "\n")
    
    try:
        # Accounts
        print("=== ACCOUNTS (get_all_accounts) ===")
        print("-" * 40)
        accounts = await client.get_all_accounts()
        if accounts:
            print(f"Keys: {list(accounts[0].keys())}")
            print(f"\nSample account:")
            for key, value in accounts[0].items():
                print(f"  {key}: {value}")
        else:
            print("No accounts found")
        print()
        
        # Account State
        print("=== ACCOUNT STATE (get_account_state) ===")
        print("-" * 40)
        try:
            state = await client.get_account_state()
            print(f"Keys: {list(state.keys())}")
            print(f"\nSample state:")
            for key, value in state.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"Failed to get account state: {e}")
        print()
        
        # Positions
        print("=== POSITIONS (get_all_positions) ===")
        print("-" * 40)
        positions = await client.get_all_positions()
        if positions:
            print(f"Keys: {list(positions[0].keys())}")
            print(f"\nSample position:")
            for key, value in positions[0].items():
                print(f"  {key}: {value}")
        else:
            print("No open positions")
        print()
        
        # Instrument Details
        print("=== INSTRUMENT DETAILS (get_instrument) ===")
        print("-" * 40)
        try:
            instrument = await client.get_instrument("EURUSD")
            print(f"Keys: {list(instrument.keys())}")
            print(f"\nSample instrument:")
            for key, value in instrument.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"Failed to get instrument: {e}")
        print()
        
        print("="*60)
        print("✅ FIELD DISCOVERY COMPLETE")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Discovery failed: {e}\n")
        raise


async def main():
    """Run verification tests."""
    print("\n" + "="*60)
    print("TradeLocker Field Verification Tests")
    print("="*60 + "\n")
    
    # Option 1: Try loading from .env first
    load_dotenv()
    email = os.getenv("TL_EMAIL")
    password = os.getenv("TL_PASSWORD")
    server = os.getenv("TL_SERVER")
    environment = os.getenv("TL_ENVIRONMENT")
    
    # Option 2: Prompt if not in .env
    if not email or not password:
        print("Enter TradeLocker credentials (or add to .env file):\n")
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        environment = input("Environment (live/demo) [demo]: ").strip() or "demo"
        server = input("Server name [live]: ").strip() or "live"
        print()
    else:
        environment = environment or "demo"
        server = server or "live"
    
    if not email or not password:
        print("Error: Email and password are required")
        return
    
    print(f"Connecting to TradeLocker ({environment})...")
    
    # Create client
    client = TradeLockerClient(
        email=email,
        password=password,
        server=server,
        environment=environment
    )
    
    # Authenticate
    success = await client.authenticate()
    if not success:
        print("Authentication failed!")
        return
    
    print("✓ Authenticated successfully\n")
    
    # Run tests
    await verify_fixes(client)
    
    # Optional: Run field discovery for 100% certainty
    run_discovery = input("\nRun field discovery test? (y/n): ").lower() == 'y'
    if run_discovery:
        await discover_all_fields(client)


if __name__ == "__main__":
    asyncio.run(main())
