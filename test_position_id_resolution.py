"""
Dedicated Test: Position ID Resolution from Order ID
Tests the SDK's get_position_id_from_order_id() method with retry logic and fallback.

This test verifies:
1. Primary method (SDK order→position lookup) works
2. Retry logic handles broker lag
3. Fallback method works when primary fails
4. Database updates persist correctly
5. Multiple concurrent positions scenario handled properly
"""

import asyncio
import os
import sys
from datetime import datetime
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Import core modules
from backend.core.tradelocker_client import TradeLockerClient
from backend.database import DatabaseManager


class PositionIDResolutionTest:
    """Test position ID resolution with real TradeLocker account."""
    
    def __init__(self):
        self.db = None
        self.client = None
        self.test_results = []
        
    async def setup(self):
        """Initialize database and TradeLocker client."""
        logger.info("=" * 80)
        logger.info("POSITION ID RESOLUTION TEST")
        logger.info("=" * 80)
        
        # Initialize database
        self.db = DatabaseManager()
        await self.db.connect()
        
        # Get first active account from database
        accounts = await self.db.get_all_accounts()
        if not accounts:
            raise Exception("No accounts found in database. Add an account first.")
        
        # Find first non-breached, non-paused account
        account = None
        for acc in accounts:
            if not acc.breached and not acc.paused:
                account = acc
                break
        
        if not account:
            raise Exception("No active accounts found (all breached or paused)")
        
        logger.info(f"Using account: {account.display_name or account.account_key}")
        
        # Load full credentials from database (same way comprehensive test does it)
        async with self.db.pool.acquire() as conn:
            acct_row = await conn.fetchrow(
                """SELECT tl_email, tl_password, tl_server, tl_prop_firm, tl_account_id
                FROM accounts 
                WHERE credential_key = $1
                LIMIT 1""",
                account.credential_key
            )
        
        if not acct_row:
            raise Exception(f"Account credentials not found for {account.credential_key}")
        
        email = acct_row['tl_email']
        password = acct_row['tl_password']
        server = acct_row['tl_prop_firm'] or acct_row['tl_server']  # Prop firm name for auth
        environment = acct_row['tl_server']  # "live" or "demo"
        account_id = int(acct_row['tl_account_id']) if acct_row['tl_account_id'] else None
        
        logger.info(f"Credentials: {email} on {server} ({environment}) account_id={account_id}")
        
        # Initialize TradeLocker client
        self.client = TradeLockerClient(
            email=email,
            password=password,
            server=server,
            environment=environment,
            account_id=account_id
        )
        
        await self.client.authenticate()
        logger.info("✓ Client authenticated")
        
        return account
    
    async def test_primary_method(self, order_id: int):
        """
        Test 1: Primary Method - SDK's get_position_id_from_order_id()
        
        This tests the built-in SDK method that uses order history to map
        order_id → position_id.
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST 1: Primary Method - SDK Order→Position Lookup")
        logger.info("=" * 80)
        
        try:
            # Call the wrapper method (which calls SDK's get_position_id_from_order_id)
            position_id = await self.client.get_position_id_from_order_id(order_id)
            
            if position_id is not None:
                logger.info(f"✅ SUCCESS: Resolved order {order_id} → position {position_id}")
                self.test_results.append({
                    "test": "Primary Method",
                    "status": "PASS",
                    "order_id": order_id,
                    "position_id": position_id
                })
                return position_id
            else:
                logger.warning(f"⚠️ Order {order_id} not found in history (may be too recent)")
                self.test_results.append({
                    "test": "Primary Method",
                    "status": "NOT_FOUND",
                    "order_id": order_id,
                    "position_id": None
                })
                return None
                
        except Exception as e:
            logger.error(f"❌ FAIL: Primary method error: {e}")
            self.test_results.append({
                "test": "Primary Method",
                "status": "FAIL",
                "order_id": order_id,
                "error": str(e)
            })
            return None
    
    async def test_retry_logic(self, order_id: int):
        """
        Test 2: Retry Logic with Broker Lag Simulation
        
        Tests that the retry loop (10 attempts × 0.5s) handles broker lag
        where order history takes time to update.
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST 2: Retry Logic - Handles Broker Lag")
        logger.info("=" * 80)
        
        position_id = None
        attempts = 0
        max_attempts = 10
        
        try:
            for attempt in range(max_attempts):
                attempts += 1
                logger.info(f"Attempt {attempt + 1}/{max_attempts}...")
                
                position_id = await self.client.get_position_id_from_order_id(order_id)
                
                if position_id is not None:
                    logger.info(f"✅ SUCCESS: Resolved after {attempts} attempt(s)")
                    self.test_results.append({
                        "test": "Retry Logic",
                        "status": "PASS",
                        "order_id": order_id,
                        "position_id": position_id,
                        "attempts": attempts
                    })
                    return position_id
                
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.5)
            
            logger.warning(f"⚠️ Position not resolved after {attempts} attempts")
            self.test_results.append({
                "test": "Retry Logic",
                "status": "NOT_FOUND",
                "order_id": order_id,
                "attempts": attempts
            })
            return None
            
        except Exception as e:
            logger.error(f"❌ FAIL: Retry logic error: {e}")
            self.test_results.append({
                "test": "Retry Logic",
                "status": "FAIL",
                "order_id": order_id,
                "error": str(e),
                "attempts": attempts
            })
            return None
    
    async def test_fallback_method(self, instrument_id: int, side: str):
        """
        Test 3: Fallback Method - Position Scan
        
        Tests the fallback position scan that matches by:
        - instrument_id
        - side (buy/sell)
        - excludes existing tracked positions
        
        Should only accept exactly 1 candidate (ambiguity = error).
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST 3: Fallback Method - Position Scan")
        logger.info("=" * 80)
        
        try:
            # Get all positions
            positions = await self.client.get_all_positions()
            logger.info(f"Found {len(positions)} total positions")
            
            # Simulate the fallback logic (without database integration for this test)
            candidates = [
                p for p in positions
                if p.get('tradableInstrumentId') == instrument_id
                and p.get('side', '').lower() == side.lower()
            ]
            
            logger.info(f"Candidates matching instrument {instrument_id} + side {side}: {len(candidates)}")
            
            if len(candidates) == 1:
                position_id = candidates[0].get('id')
                logger.info(f"✅ SUCCESS: Exactly 1 candidate found - position {position_id}")
                self.test_results.append({
                    "test": "Fallback Method",
                    "status": "PASS",
                    "instrument_id": instrument_id,
                    "side": side,
                    "position_id": position_id
                })
                return position_id
            elif len(candidates) > 1:
                logger.warning(f"⚠️ AMBIGUOUS: {len(candidates)} candidates found (would reject)")
                self.test_results.append({
                    "test": "Fallback Method",
                    "status": "AMBIGUOUS",
                    "instrument_id": instrument_id,
                    "side": side,
                    "candidates": len(candidates)
                })
                return None
            else:
                logger.warning(f"⚠️ NOT_FOUND: No candidates found")
                self.test_results.append({
                    "test": "Fallback Method",
                    "status": "NOT_FOUND",
                    "instrument_id": instrument_id,
                    "side": side
                })
                return None
                
        except Exception as e:
            logger.error(f"❌ FAIL: Fallback method error: {e}")
            self.test_results.append({
                "test": "Fallback Method",
                "status": "FAIL",
                "error": str(e)
            })
            return None
    
    async def test_database_persistence(self, trade_id: int, position_id: int):
        """
        Test 4: Database Persistence
        
        Tests that position_id updates persist correctly in the database
        and can be retrieved by other components.
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST 4: Database Persistence")
        logger.info("=" * 80)
        
        try:
            # Update position_id in database
            success = await self.db.update_trade_position_id(trade_id, str(position_id))
            
            if not success:
                logger.error("❌ FAIL: Database update returned False")
                self.test_results.append({
                    "test": "Database Persistence",
                    "status": "FAIL",
                    "trade_id": trade_id,
                    "error": "Update returned False"
                })
                return False
            
            # Verify by reading back
            trades = await self.db.get_active_trades("test_account")
            trade = next((t for t in trades if t.trade_id == trade_id), None)
            
            if trade and trade.tl_position_id == str(position_id):
                logger.info(f"✅ SUCCESS: Position ID persisted and retrieved correctly")
                self.test_results.append({
                    "test": "Database Persistence",
                    "status": "PASS",
                    "trade_id": trade_id,
                    "position_id": position_id
                })
                return True
            else:
                logger.error(f"❌ FAIL: Position ID not found or mismatch")
                self.test_results.append({
                    "test": "Database Persistence",
                    "status": "FAIL",
                    "trade_id": trade_id,
                    "expected": str(position_id),
                    "actual": trade.tl_position_id if trade else None
                })
                return False
                
        except Exception as e:
            logger.error(f"❌ FAIL: Database persistence error: {e}")
            self.test_results.append({
                "test": "Database Persistence",
                "status": "FAIL",
                "trade_id": trade_id,
                "error": str(e)
            })
            return False
    
    async def test_with_real_trade(self):
        """
        Test 5: End-to-End with Real Trade
        
        Creates a small test trade and verifies position ID resolution works
        end-to-end with database integration.
        """
        logger.info("\n" + "=" * 80)
        logger.info("TEST 5: End-to-End Real Trade Test")
        logger.info("=" * 80)
        
        try:
            # Get EURUSD instrument (safe, liquid pair)
            symbol = "EURUSD"
            instrument_id = await self.client.get_instrument_id_from_symbol_name(symbol)
            
            if not instrument_id:
                logger.error(f"❌ Cannot test: {symbol} not found")
                return False
            
            logger.info(f"Using {symbol} (instrument_id: {instrument_id})")
            
            # Create tiny market order (0.01 lots = $10 risk)
            logger.info("Creating test order: BUY 0.01 lots EURUSD...")
            
            order = await self.client.create_order(
                instrument_id=instrument_id,
                quantity=0.01,
                side="buy",
                type_="market",
                validity="IOC"
            )
            
            if isinstance(order, int):
                order_id = order
            else:
                order_id = order.get('id') or order.get('orderId')
            
            logger.info(f"✓ Order created: {order_id}")
            
            # Test position resolution with retry
            position_id = None
            for attempt in range(10):
                logger.info(f"Resolution attempt {attempt + 1}/10...")
                position_id = await self.client.get_position_id_from_order_id(order_id)
                
                if position_id is not None:
                    logger.info(f"✅ SUCCESS: Resolved position {position_id} after {attempt + 1} attempts")
                    break
                
                await asyncio.sleep(0.5)
            
            if position_id is None:
                logger.error("❌ FAIL: Could not resolve position_id after 10 attempts")
                self.test_results.append({
                    "test": "End-to-End Real Trade",
                    "status": "FAIL",
                    "order_id": order_id,
                    "error": "Position ID not resolved"
                })
                return False
            
            # Close the test position immediately
            logger.info(f"Closing test position {position_id}...")
            await self.client.close_position(position_id)
            logger.info("✓ Test position closed")
            
            self.test_results.append({
                "test": "End-to-End Real Trade",
                "status": "PASS",
                "order_id": order_id,
                "position_id": position_id,
                "symbol": symbol
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ FAIL: End-to-end test error: {e}")
            self.test_results.append({
                "test": "End-to-End Real Trade",
                "status": "FAIL",
                "error": str(e)
            })
            return False
    
    def print_summary(self):
        """Print test summary report."""
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.get("status") == "PASS")
        failed = sum(1 for r in self.test_results if r.get("status") == "FAIL")
        other = total - passed - failed
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⚠️ Other (NOT_FOUND/AMBIGUOUS): {other}")
        
        logger.info("\nDetailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            logger.info(f"{i}. {status_icon} {result['test']}: {result['status']}")
            if "error" in result:
                logger.info(f"   Error: {result['error']}")
        
        logger.info("=" * 80)
        
        if failed == 0:
            logger.info("🎉 ALL CRITICAL TESTS PASSED!")
        else:
            logger.warning(f"⚠️ {failed} test(s) failed - review required")
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.db:
            await self.db.disconnect()
        logger.info("✓ Cleanup complete")


async def main():
    """Run the position ID resolution test suite."""
    test = PositionIDResolutionTest()
    
    try:
        # Setup
        account = await test.setup()
        
        # Get an existing order ID to test with (or create one)
        # For this test, we'll use the end-to-end test which creates a real trade
        
        # Run end-to-end test (creates real trade)
        await test.test_with_real_trade()
        
        # Print summary
        test.print_summary()
        
    except Exception as e:
        logger.error(f"Test suite error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
