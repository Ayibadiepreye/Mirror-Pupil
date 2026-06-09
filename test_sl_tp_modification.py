"""
Test SL/TP Modification with Fixed camelCase Keys
Creates a position, lets you verify on TradeLocker, then modifies it.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.core.tradelocker_client import TradeLockerClient
from backend.database import DatabaseManager


async def test_modification():
    print("=" * 70)
    print("SL/TP MODIFICATION TEST - Fixed camelCase Keys")
    print("=" * 70)
    
    # Initialize database
    print("\n🗄️ Connecting to database...")
    db = DatabaseManager()
    await db.connect()
    
    # Get account from database (same as comprehensive test)
    accounts = await db.get_all_accounts()
    if not accounts or len(accounts) == 0:
        print("❌ No accounts found in database!")
        print("Please add TradeLocker credentials via GUI first.")
        await db.disconnect()
        return
    
    # Get first active account
    account = None
    for acc in accounts:
        if not acc.breached and not acc.paused:
            account = acc
            break
    
    if not account:
        print("❌ No active accounts found (all breached or paused)!")
        await db.disconnect()
        return
    
    print(f"✓ Found account: {account.display_name or account.account_key}")
    
    # Extract credentials from database
    email = account.tl_email
    password = account.tl_password
    account_id = account.tl_account_id
    prop_firm = account.tl_prop_firm or ""
    server = account.tl_server  # "live" or "demo"
    
    print(f"\n📧 Email: {email}")
    print(f"🏢 Prop Firm: {prop_firm or 'Default'}")
    print(f"🔢 Account ID: {account_id}")
    print(f"🌐 Server: {server}")
    
    # Disconnect database (no longer needed)
    await db.disconnect()
    
    # Create client
    client = TradeLockerClient(
        email=email,
        password=password,
        server=prop_firm,
        environment=server,
        account_id=account_id
    )
    
    # Authenticate
    print("\n🔐 Authenticating...")
    success = await client.authenticate()
    if not success:
        print("❌ Authentication failed!")
        return
    print("✓ Authenticated")
    
    # Get EURUSD instrument
    print("\n🔍 Finding EURUSD...")
    instrument_id = await client.get_instrument_id_from_symbol_name("EURUSD")
    if not instrument_id:
        print("❌ EURUSD not found!")
        return
    
    print(f"✓ EURUSD ID: {instrument_id}")
    
    # Get current price
    print("\n💱 Getting current price...")
    mid_price = await client.get_market_price("EURUSD")
    if not mid_price:
        print("❌ Could not get current price!")
        return
    
    print(f"✓ Current mid price: {mid_price:.5f}")
    
    # Create a BUY order with NO SL/TP
    print("\n📝 Creating BUY order (0.01 lots, NO SL/TP)...")
    order_id = await client.create_order(
        instrument_id=instrument_id,
        quantity=0.01,
        side="buy",
        type_="market",
        validity="IOC"  # Required for market orders
    )
    
    if not order_id:
        print("❌ Order creation failed!")
        return
    
    print(f"✓ Order created: {order_id}")
    
    # Wait for fill
    await asyncio.sleep(1)
    
    # Get position ID
    print("\n🔍 Getting position ID...")
    positions = await client.get_all_positions()
    position = None
    for pos in positions:
        if pos.get('id') == order_id or pos.get('orderId') == order_id:
            position = pos
            break
    
    if not position:
        # Try finding by latest position
        if positions:
            position = positions[-1]
            print(f"⚠️ Using latest position: {position.get('id')}")
    
    if not position:
        print("❌ Could not find position!")
        return
    
    position_id = position.get('id')
    current_sl = position.get('stopLoss')
    current_tp = position.get('takeProfit')
    
    print(f"✓ Position ID: {position_id}")
    print(f"  Symbol: {position.get('symbol')}")
    print(f"  Side: {position.get('tradeSide')}")
    print(f"  Qty: {position.get('qty')}")
    print(f"  Entry: {position.get('avgPrice')}")
    print(f"  Current SL: {current_sl}")
    print(f"  Current TP: {current_tp}")
    
    # Pause for user verification
    print("\n" + "=" * 70)
    print("🔍 STEP 1: Verify position on TradeLocker")
    print("=" * 70)
    print(f"Position ID: {position_id}")
    print("Go to TradeLocker and check that this position exists.")
    print("It should have NO SL and NO TP set.")
    input("\nPress ENTER when ready to continue...")
    
    # Ask if user wants to modify
    print("\n" + "=" * 70)
    print("🛠️ STEP 2: Modify SL/TP?")
    print("=" * 70)
    modify_choice = input("Do you want to modify SL/TP? (y/n): ").strip().lower()
    
    if modify_choice != 'y':
        print("\n⏭️ Skipping modification...")
        # Ask if want to close
        close_choice = input("\nDo you want to close this position? (y/n): ").strip().lower()
        if close_choice == 'y':
            print("\n🔴 Closing position...")
            await client.close_position(position_id)
            print("✓ Position closed")
        else:
            print("\n⚠️ Position left open. Close it manually on TradeLocker.")
        return
    
    # Get modification parameters from user
    print("\n" + "=" * 70)
    print("🛠️ Set new SL/TP values")
    print("=" * 70)
    
    entry_price = position.get('avgPrice')
    print(f"\nEntry price: {entry_price}")
    print("\nExample values:")
    print(f"  SL (20 pips below): {entry_price - 0.0020}")
    print(f"  TP (40 pips above): {entry_price + 0.0040}")
    
    new_sl_input = input("\nEnter new Stop Loss (or press ENTER to skip): ").strip()
    new_tp_input = input("Enter new Take Profit (or press ENTER to skip): ").strip()
    
    new_sl = float(new_sl_input) if new_sl_input else None
    new_tp = float(new_tp_input) if new_tp_input else None
    
    if not new_sl and not new_tp:
        print("❌ No modifications requested!")
        # Ask if want to close
        close_choice = input("\nDo you want to close this position? (y/n): ").strip().lower()
        if close_choice == 'y':
            print("\n🔴 Closing position...")
            await client.close_position(position_id)
            print("✓ Position closed")
        else:
            print("\n⚠️ Position left open. Close it manually on TradeLocker.")
        return
    
    # Confirm modification
    print("\n" + "=" * 70)
    print("⚠️ CONFIRM MODIFICATION")
    print("=" * 70)
    print(f"Position ID: {position_id}")
    print(f"New SL: {new_sl}")
    print(f"New TP: {new_tp}")
    confirm = input("\nProceed with modification? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("\n❌ Modification cancelled")
        # Ask if want to close
        close_choice = input("\nDo you want to close this position? (y/n): ").strip().lower()
        if close_choice == 'y':
            print("\n🔴 Closing position...")
            await client.close_position(position_id)
            print("✓ Position closed")
        else:
            print("\n⚠️ Position left open. Close it manually on TradeLocker.")
        return
    
    # Modify position with FIXED camelCase keys
    print("\n📝 Modifying position with FIXED camelCase keys...")
    print(f"  New SL: {new_sl}")
    print(f"  New TP: {new_tp}")
    
    result = await client.modify_position(
        position_id=position_id,
        stop_loss=new_sl,
        take_profit=new_tp
    )
    
    print(f"✓ Modification result: {result}")
    
    # Wait and refetch position
    await asyncio.sleep(1)
    
    print("\n🔍 Refetching position...")
    positions = await client.get_all_positions()
    updated_position = None
    for pos in positions:
        if pos.get('id') == position_id:
            updated_position = pos
            break
    
    if updated_position:
        updated_sl = updated_position.get('stopLoss')
        updated_tp = updated_position.get('takeProfit')
        sl_id = updated_position.get('stopLossId')
        tp_id = updated_position.get('takeProfitId')
        
        print(f"✓ Position refetched")
        print(f"  Updated SL: {updated_sl}")
        print(f"  Updated TP: {updated_tp}")
        print(f"  SL Order ID: {sl_id}")
        print(f"  TP Order ID: {tp_id}")
        
        # Verification
        print("\n" + "=" * 70)
        print("✅ VERIFICATION")
        print("=" * 70)
        
        sl_match = (new_sl is None) or (abs(updated_sl - new_sl) < 0.00001 if updated_sl else False)
        tp_match = (new_tp is None) or (abs(updated_tp - new_tp) < 0.00001 if updated_tp else False)
        
        if sl_match and tp_match:
            print("✅ SUCCESS! SL/TP updated correctly!")
        else:
            print("❌ MISMATCH!")
            if new_sl and not sl_match:
                print(f"  Expected SL: {new_sl}, Got: {updated_sl}")
            if new_tp and not tp_match:
                print(f"  Expected TP: {new_tp}, Got: {updated_tp}")
    
    # Final verification step
    print("\n" + "=" * 70)
    print("🔍 STEP 3: Final verification on TradeLocker")
    print("=" * 70)
    print(f"Position ID: {position_id}")
    print("Go to TradeLocker and verify the SL/TP values match what you entered.")
    print(f"Expected SL: {new_sl}")
    print(f"Expected TP: {new_tp}")
    input("\nPress ENTER when done verifying...")
    
    # Ask if want to modify again
    while True:
        print("\n" + "=" * 70)
        print("🔄 MODIFY AGAIN?")
        print("=" * 70)
        modify_again = input("Do you want to modify SL/TP again? (y/n): ").strip().lower()
        
        if modify_again != 'y':
            break
        
        # Get new modification parameters
        print("\n" + "=" * 70)
        print("🛠️ Set NEW SL/TP values")
        print("=" * 70)
        
        entry_price = position.get('avgPrice')
        print(f"\nEntry price: {entry_price}")
        print(f"Current SL: {updated_sl}")
        print(f"Current TP: {updated_tp}")
        
        new_sl_input = input("\nEnter new Stop Loss (or press ENTER to keep current): ").strip()
        new_tp_input = input("Enter new Take Profit (or press ENTER to keep current): ").strip()
        
        new_sl = float(new_sl_input) if new_sl_input else None
        new_tp = float(new_tp_input) if new_tp_input else None
        
        if not new_sl and not new_tp:
            print("⚠️ No changes requested, keeping current values")
            continue
        
        # Modify position again
        print("\n📝 Modifying position again...")
        print(f"  New SL: {new_sl}")
        print(f"  New TP: {new_tp}")
        
        result = await client.modify_position(
            position_id=position_id,
            stop_loss=new_sl,
            take_profit=new_tp
        )
        
        print(f"✓ Modification result: {result}")
        
        # Refetch and verify
        await asyncio.sleep(1)
        positions = await client.get_all_positions()
        for pos in positions:
            if pos.get('id') == position_id:
                updated_position = pos
                updated_sl = pos.get('stopLoss')
                updated_tp = pos.get('takeProfit')
                break
        
        print(f"✓ Updated SL: {updated_sl}")
        print(f"✓ Updated TP: {updated_tp}")
        print("\nVerify on TradeLocker...")
        input("Press ENTER when done...")
    
    # Ask if want to close
    print("\n" + "=" * 70)
    print("🔴 CLOSE POSITION?")
    print("=" * 70)
    close_choice = input("Do you want to close this position now? (y/n): ").strip().lower()
    
    if close_choice == 'y':
        print("\n🔴 Closing position...")
        await client.close_position(position_id)
        print("✓ Position closed")
    else:
        print("\n⚠️ Position left open. Close it manually on TradeLocker.")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_modification())
