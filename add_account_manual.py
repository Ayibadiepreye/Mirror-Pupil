#!/usr/bin/env python3
"""
Manually add account to database.
Fill in your TradeLocker credentials below.
"""

import asyncio
from backend.database import DatabaseManager
from backend.database.models import Account


async def add_account_to_db():
    """Add account manually to database."""
    
    # ===== FILL IN YOUR CREDENTIALS HERE =====
    TL_EMAIL = "bonnieprincewill6@gmail.com"
    TL_PASSWORD = "your_password_here"  # ← PUT YOUR ACTUAL PASSWORD HERE
    TL_SERVER = "demo"  # "demo" or "live"
    TL_PROP_FIRM = "HEROFX"
    TL_ACCOUNT_ID = "2135871"
    
    # Account settings
    DISPLAY_NAME = "Test"
    INITIAL_BALANCE = 99711.54
    RISK_PROFILE_ID = 1  # Default risk profile
    # =========================================
    
    if TL_PASSWORD == "your_password_here":
        print("❌ Please edit add_account_manual.py and add your password!")
        return
    
    # Initialize database
    db = DatabaseManager()
    await db.connect()
    
    try:
        account_key = f"{TL_EMAIL}:{TL_ACCOUNT_ID}"
        
        print(f"📝 Adding account: {account_key}")
        print(f"   Email: {TL_EMAIL}")
        print(f"   Server: {TL_SERVER}")
        print(f"   Prop Firm: {TL_PROP_FIRM}")
        print(f"   Account ID: {TL_ACCOUNT_ID}")
        print()
        
        # Create account object
        account = Account(
            account_key=account_key,
            credential_key=TL_EMAIL,
            tl_account_id=int(TL_ACCOUNT_ID),
            tl_email=TL_EMAIL,
            tl_password=TL_PASSWORD,  # Will be encrypted automatically
            tl_server=TL_SERVER,
            tl_prop_firm=TL_PROP_FIRM,
            display_name=DISPLAY_NAME,
            initial_balance=INITIAL_BALANCE,
            current_balance=INITIAL_BALANCE,
            risk_profile_id=RISK_PROFILE_ID,
            user_id=None  # No user association (single-user setup)
        )
        
        # Add to database
        success = await db.add_account(account, user_id=None)
        
        if success:
            print("✅ Account added successfully!")
            print()
            print("🔍 Verifying...")
            
            # Verify it can be retrieved and decrypted
            retrieved = await db.get_account(account_key)
            if retrieved:
                print(f"✓ Account retrieved successfully")
                print(f"✓ Password decryption works!")
                print(f"✓ Balance: ${retrieved.current_balance:,.2f}")
            else:
                print("⚠️  Could not retrieve account")
        else:
            print("❌ Failed to add account")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()
        print()
        print("✓ Done!")


if __name__ == "__main__":
    print("=" * 60)
    print("Add Account to Database")
    print("=" * 60)
    print()
    
    asyncio.run(add_account_to_db())
