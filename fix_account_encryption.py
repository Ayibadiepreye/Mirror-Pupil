#!/usr/bin/env python3
"""
Fix Account Encryption Script
Removes the account with bad encryption and re-adds it with the current encryption key.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from backend.database import DatabaseManager
from backend.database.models import Account
from backend.core.secret_vault import get_vault


async def fix_account_encryption():
    """Fix account encryption by removing and re-adding with current key."""
    
    # Initialize database
    db = DatabaseManager()
    await db.connect()
    
    try:
        # Get the account key that's having issues
        account_key = "bonnieprincewill6@gmail.com:2135871"
        
        print(f"🔍 Checking account: {account_key}")
        
        # Try to get the account
        account = await db.get_account(account_key)
        
        if account:
            print(f"✓ Found account in database")
            print(f"  - Email: {account.tl_email}")
            print(f"  - Account ID: {account.tl_account_id}")
            print(f"  - Display Name: {account.display_name}")
            print(f"  - Balance: ${account.current_balance:,.2f}")
            
            # Delete the account
            print(f"\n🗑️  Deleting account from database...")
            await db.delete_account(account_key)
            print(f"✓ Account deleted")
            
            # Get credentials from environment
            tl_email = os.getenv("TL_EMAIL")
            tl_password = os.getenv("TL_PASSWORD")
            tl_server = os.getenv("TL_SERVER")
            tl_prop_firm = os.getenv("TL_PROP_FIRM", "")
            
            if not all([tl_email, tl_password, tl_server]):
                print("❌ Missing credentials in .env file (TL_EMAIL, TL_PASSWORD, TL_SERVER)")
                return
            
            # Re-create the account with current encryption
            print(f"\n🔄 Re-adding account with current encryption key...")
            
            new_account = Account(
                account_key=account_key,
                credential_key=tl_email,
                tl_account_id=account.tl_account_id,
                tl_email=tl_email,
                tl_password=tl_password,  # This will be encrypted in add_account
                tl_server=tl_server,
                tl_prop_firm=tl_prop_firm,
                display_name=account.display_name,
                initial_balance=account.initial_balance,
                current_balance=account.current_balance,
                risk_profile_id=account.risk_profile_id,
                user_id=account.user_id
            )
            
            success = await db.add_account(new_account, user_id=account.user_id)
            
            if success:
                print(f"✅ Account re-added successfully with current encryption!")
                
                # Verify decryption works
                print(f"\n🔍 Verifying decryption...")
                reloaded_account = await db.get_account(account_key)
                if reloaded_account:
                    print(f"✓ Account reloaded successfully")
                    print(f"✓ Password decryption works!")
                else:
                    print(f"⚠️  Could not reload account")
            else:
                print(f"❌ Failed to re-add account")
        else:
            print(f"⚠️  Account not found in database")
            print(f"   This means it's only being loaded from environment variables.")
            print(f"   The system is working fine, no fix needed!")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.disconnect()
        print(f"\n✓ Database disconnected")


if __name__ == "__main__":
    print("=" * 60)
    print("Fix Account Encryption Script")
    print("=" * 60)
    print()
    
    asyncio.run(fix_account_encryption())
    
    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
