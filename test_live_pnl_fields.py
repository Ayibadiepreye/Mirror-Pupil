"""
Simple test to see what fields TradeLocker returns for positions.

This script:
1. Connects to database
2. Gets ANY account credentials
3. Authenticates with TradeLocker
4. Fetches all positions
5. Shows EVERY field returned
"""

import asyncio
import json
import os
from loguru import logger
from dotenv import load_dotenv

# Import backend modules
from backend.database.manager import DatabaseManager
from backend.core.tradelocker_client import TradeLockerClient

# Load environment
load_dotenv()


async def main():
    """Run the position fields inspection test."""
    
    logger.info("=" * 80)
    logger.info("TRADELOCKER POSITION FIELDS INSPECTOR")
    logger.info("=" * 80)
    
    db = None
    client = None
    
    try:
        # ==================== STEP 1: Connect to Database ====================
        logger.info("\n[STEP 1] Connecting to database...")
        db = DatabaseManager()
        await db.connect()
        logger.info("✓ Database connected")
        
        # ==================== STEP 2: Get Account Credentials ====================
        logger.info("\n[STEP 2] Getting account credentials...")
        
        # Get first account from database
        account_query = """
            SELECT account_key, credential_key, tl_account_id, tl_email, tl_server
            FROM accounts
            LIMIT 1
        """
        
        async with db.pool.acquire() as conn:
            account_row = await conn.fetchrow(account_query)
        
        if not account_row:
            logger.error("❌ No accounts found in database")
            return
        
        logger.info(f"✓ Found account: {account_row['account_key']}")
        logger.info(f"  Email: {account_row['tl_email']}")
        logger.info(f"  Server: {account_row['tl_server']}")
        logger.info(f"  Account ID: {account_row['tl_account_id']}")
        
        # Get credentials from secret vault
        from backend.core.secret_vault import get_vault
        
        vault = get_vault()
        creds_data = await vault.get_credential(account_row['credential_key'])
        
        if not creds_data:
            logger.error(f"❌ Credentials not found in vault for {account_row['credential_key']}")
            return
        
        logger.info(f"✓ Credentials: {creds_data['email']}")
        
        # ==================== STEP 3: Authenticate with TradeLocker ====================
        logger.info("\n[STEP 3] Authenticating with TradeLocker...")
        
        client = TradeLockerClient(
            email=creds_data['email'],
            password=creds_data['password'],
            server=creds_data['server'],
            environment=creds_data['environment'],
            account_id=int(account_row['tl_account_id'])
        )
        
        await client.authenticate()
        logger.info("✓ Authenticated")
        
        # ==================== STEP 4: Fetch All Positions ====================
        logger.info("\n[STEP 4] Fetching all open positions from TradeLocker...")
        
        positions = await client.get_all_positions()
        
        if not positions:
            logger.warning("⚠ No open positions found")
            logger.info("\nThis means either:")
            logger.info("  1. No trades are currently open on this account")
            logger.info("  2. Positions API call failed")
            return
        
        logger.info(f"✓ Found {len(positions)} open position(s)")
        
        # ==================== STEP 5: Display ALL Position Fields ====================
        logger.info("\n[STEP 5] COMPLETE FIELD ANALYSIS")
        logger.info("=" * 100)
        
        for idx, pos in enumerate(positions, 1):
            logger.info(f"\n{'='*100}")
            logger.info(f"POSITION #{idx}")
            logger.info(f"{'='*100}")
            
            # Show ALL fields in alphabetical order
            logger.info("\n📋 ALL FIELDS:")
            for key, value in sorted(pos.items()):
                value_str = str(value)
                if len(value_str) > 70:
                    value_str = value_str[:67] + "..."
                logger.info(f"  {key:<30} = {value_str}")
            
            # Specifically check PnL fields
            logger.info(f"\n{'='*100}")
            logger.info("🔍 PNL FIELD CHECK:")
            logger.info(f"{'='*100}")
            
            pnl_fields = [
                'unrealizedPl', 'unrealizedPL', 'unrealized_pl',
                'profit', 'pnl', 'PnL', 'netPl', 'grossPl',
                'openNetPnL', 'openGrossPnL', 'pl', 'Pl'
            ]
            
            found_pnl = False
            for field in pnl_fields:
                val = pos.get(field)
                if val is not None:
                    logger.info(f"  ✅ FOUND: {field:<20} = {val}")
                    found_pnl = True
            
            if not found_pnl:
                logger.warning("  ❌ NO PNL FIELD FOUND IN THIS POSITION!")
            
            logger.info(f"\n{'='*100}")
        
        # ==================== STEP 6: Export to JSON ====================
        logger.info("\n[STEP 6] Exporting data...")
        
        output_file = "tradelocker_positions_raw.json"
        with open(output_file, 'w') as f:
            json.dump(positions, f, indent=2, default=str)
        
        logger.info(f"✓ Raw position data saved to: {output_file}")
        logger.info("\n✅ TEST COMPLETE - Check the output above for all position fields")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if db:
            await db.disconnect()
            logger.info("\n✓ Database connection closed")
        if client:
            await client.close()
            logger.info("✓ TradeLocker connection closed")


if __name__ == "__main__":
    asyncio.run(main())
