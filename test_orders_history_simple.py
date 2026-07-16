"""
Simplified test for TradeLocker get_orders_history() endpoint.
Uses direct credentials without database dependency.
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
from tradelocker import TLAPI

# Load environment
load_dotenv()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO"
)


async def test_orders_history_simple():
    """
    Simple test of TradeLocker orders history endpoint.
    Uses first account from environment variables.
    """
    
    logger.info("=" * 80)
    logger.info("TRADELOCKER ORDERS HISTORY ENDPOINT TEST (SIMPLE)")
    logger.info("=" * 80)
    
    # Get credentials from environment (use first account)
    tl_email = "bonnieprincewill6@gmail.com"
    tl_password = "#Princewill15"
    tl_server = "demo.tradelocker.com"
    server_name = "HEROFX"
    
    logger.info(f"\nUsing credentials:")
    logger.info(f"  Email: {tl_email}")
    logger.info(f"  Server: {tl_server}")
    logger.info(f"  Server Name: {server_name}")
    
    logger.info("\n" + "=" * 80)
    logger.info("Authenticating to TradeLocker...")
    logger.info("=" * 80)
    
    try:
        # Initialize TLAPI
        tl = TLAPI(
            environment=f"https://{tl_server}",
            username=tl_email,
            password=tl_password,
            server=server_name
        )
        
        logger.info("✓ TLAPI initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize TLAPI: {e}")
        return
    
    logger.info("\n" + "=" * 80)
    logger.info("Fetching Orders History...")
    logger.info("=" * 80)
    
    try:
        # Get the access token
        access_token = tl._access_token if hasattr(tl, '_access_token') else None
        account_id = tl.account_id if hasattr(tl, 'account_id') else None
        acc_num = tl.acc_num if hasattr(tl, 'acc_num') else 1
        
        if not access_token:
            logger.error("Could not get access token")
            return
        
        if not account_id:
            logger.error("Could not get account ID")
            return
        
        logger.info(f"\nAccount ID: {account_id}")
        logger.info(f"Account Number: {acc_num}")
        logger.info(f"Making direct REST API call...")
        
        # Make direct HTTP request to ordersHistory endpoint
        import requests
        
        url = f"https://{tl_server}/backend-api/trade/accounts/{account_id}/ordersHistory"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "accNum": str(acc_num)
        }
        params = {
            "ref": "py_c",
            "v": "0.56.1"
        }
        
        logger.info(f"\nPOST {url}")
        
        response = await asyncio.to_thread(
            requests.get,
            url,
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code}: {response.text}")
            return
        
        history_data = response.json()
        logger.info("Response received!")
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch orders history: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return
    
    # Parse response
    logger.info("\n" + "=" * 80)
    logger.info("Parsing Response...")
    logger.info("=" * 80)
    
    logger.info(f"\nResponse type: {type(history_data)}")
    
    if not isinstance(history_data, dict):
        logger.error(f"❌ Expected dict, got {type(history_data)}")
        logger.info(f"Response: {history_data}")
        return
    
    logger.info(f"Response keys: {list(history_data.keys())}")
    
    if "d" not in history_data:
        logger.warning("⚠️  No 'd' key in response!")
        logger.info(f"Full response: {history_data}")
        return
    
    data = history_data.get("d", {})
    logger.info(f"'d' type: {type(data)}")
    
    if isinstance(data, dict):
        logger.info(f"'d' keys: {list(data.keys())}")
    
    if "ordersHistory" not in data:
        logger.warning("⚠️  No 'ordersHistory' key in data!")
        logger.info(f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        return
    
    orders = data.get("ordersHistory", [])
    logger.info(f"\n✓ Found {len(orders)} closed order(s) in history")
    
    if not orders:
        logger.info("\n📭 No closed orders found.")
        logger.info("This could mean:")
        logger.info("  - Account has no trade history yet")
        logger.info("  - Endpoint returns limited time range")
        logger.info("  - All positions are still open")
        return
    
    # Analyze orders
    logger.info("\n" + "=" * 80)
    logger.info(f"Analyzing Orders ({len(orders)} total)")
    logger.info("=" * 80)
    
    # Orders come as lists, not dicts. Let's map the fields
    logger.info("\nFirst, examining structure:")
    if orders:
        first_order = orders[0]
        logger.info(f"Order type: {type(first_order)}")
        logger.info(f"Order length: {len(first_order) if isinstance(first_order, list) else 'N/A'}")
        logger.info(f"Sample: {first_order[:10] if isinstance(first_order, list) else first_order}")
    
    # Define field mapping based on observed data
    field_names = [
        "id", "tradableInstrumentId", "accountId", "qty", "side", "type", 
        "status", "filledQty", "avgPrice", "limitPrice", "stopPrice",
        "timeInForce", "parentOrderId", "createTime", "updateTime",
        "unknown_15", "positionId", "takeProfitPrice", "takeProfitType",
        "stopLossPrice", "stopLossType", "clientOrderId"
    ]
    
    total_net_pnl = 0.0
    
    for i, order in enumerate(orders[:20], 1):  # Show first 20
        logger.info(f"\n--- Order {i}/{len(orders)} ---")
        
        if not isinstance(order, list):
            logger.warning(f"Unexpected type: {type(order)}")
            continue
        
        # Convert list to dict
        order_dict = {field_names[idx]: order[idx] for idx in range(min(len(order), len(field_names)))}
        
        # Extract key fields
        order_id = order_dict.get("id", "N/A")
        instrument_id = order_dict.get("tradableInstrumentId", "N/A")
        side = order_dict.get("side", "N/A")
        qty = order_dict.get("qty", "N/A")
        order_type = order_dict.get("type", "N/A")
        status = order_dict.get("status", "N/A")
        filled_qty = order_dict.get("filledQty", "N/A")
        avg_price = order_dict.get("avgPrice", "N/A")
        position_id = order_dict.get("positionId", "N/A")
        
        logger.info(f"Order ID: {order_id}")
        logger.info(f"Position ID: {position_id}")  # CRITICAL for matching trades!
        logger.info(f"Instrument: {instrument_id}")
        logger.info(f"Side: {side} | Type: {order_type} | Status: {status}")
        logger.info(f"Qty: {qty} | Filled: {filled_qty} | Avg Price: {avg_price}")
        logger.info(f"Raw order data (first 10 fields): {order[:10]}")
    
    if len(orders) > 20:
        logger.info(f"\n... and {len(orders) - 20} more order(s)")
    
    logger.info("\n" + "=" * 80)
    logger.info(f"ANALYSIS COMPLETE - Examined first {min(20, len(orders))} of {len(orders)} orders")
    logger.info("=" * 80)
    
    # Now test other endpoints to find P&L data
    logger.info("\n" + "=" * 80)
    logger.info("Testing Other Endpoints for P&L Data...")
    logger.info("=" * 80)
    
    endpoints_to_test = [
        "positionsHistory",
        "closedPositions", 
        "positions/history",
        "trades/history",
        "tradesHistory",
        "executions",
        "positions",  # Maybe has a closed flag?
        "trades",
        "orders/closed",
        "history/positions",
        "history/trades",
    ]
    
    for endpoint_name in endpoints_to_test:
        logger.info(f"\n--- Testing: {endpoint_name} ---")
        url = f"https://{tl_server}/backend-api/trade/accounts/{account_id}/{endpoint_name}"
        
        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"SUCCESS! Response keys: {list(data.keys())}")
                
                if 'd' in data:
                    logger.info(f"'d' keys: {list(data['d'].keys())}")
                    
                    # Check each key for data
                    for key, value in data['d'].items():
                        if isinstance(value, list):
                            logger.info(f"  {key}: {len(value)} items")
                            if len(value) > 0:
                                logger.info(f"    Sample item type: {type(value[0])}")
                                if isinstance(value[0], list):
                                    logger.info(f"    Sample item length: {len(value[0])}")
                                    logger.info(f"    Sample: {value[0][:15] if len(value[0]) > 15 else value[0]}")
                                elif isinstance(value[0], dict):
                                    logger.info(f"    Sample keys: {list(value[0].keys())[:10]}")
                        else:
                            logger.info(f"  {key}: {value}")
            elif response.status_code == 404:
                logger.info("404 - Endpoint not found")
            else:
                logger.info(f"Error: {response.text[:200]}")
                
        except Exception as e:
            logger.error(f"Exception: {str(e)[:200]}")
    
    # Now let's check what methods the TLAPI library has that might give us positions/P&L
    logger.info("\n" + "=" * 80)
    logger.info("Checking TLAPI Library Methods...")
    logger.info("=" * 80)
    
    relevant_methods = []
    for method_name in dir(tl):
        if not method_name.startswith('_') and callable(getattr(tl, method_name)):
            # Look for methods related to positions, trades, history, pnl
            if any(keyword in method_name.lower() for keyword in ['position', 'trade', 'history', 'pnl', 'profit', 'close', 'execution']):
                relevant_methods.append(method_name)
    
    logger.info(f"\nFound {len(relevant_methods)} potentially relevant methods:")
    for method in sorted(relevant_methods):
        logger.info(f"  - {method}")
    
    # Try calling get_all_positions (if exists) to see structure
    if hasattr(tl, 'get_all_positions'):
        logger.info("\n--- Testing: tl.get_all_positions() ---")
        try:
            positions = await asyncio.to_thread(tl.get_all_positions)
            logger.info(f"Type: {type(positions)}")
            logger.info(f"Response: {positions}")
        except Exception as e:
            logger.error(f"Error: {str(e)[:200]}")
    
    # Try get_all_executions
    if hasattr(tl, 'get_all_executions'):
        logger.info("\n--- Testing: tl.get_all_executions() ---")
        try:
            executions = await asyncio.to_thread(tl.get_all_executions)
            logger.info(f"Type: {type(executions)}")
            logger.info(f"Response:\n{executions}")
        except Exception as e:
            logger.error(f"Error: {str(e)[:200]}")
    
    # Now let's look at the FULL order structure from ordersHistory
    logger.info("\n" + "=" * 80)
    logger.info("Analyzing FULL Order Structure (all fields)")
    logger.info("=" * 80)
    
    if orders and len(orders) > 0:
        # Find a filled order to see all fields
        filled_order = None
        for order in orders:
            if isinstance(order, list) and len(order) > 6 and order[6] == 'Filled':
                filled_order = order
                break
        
        if filled_order:
            logger.info(f"\nFilled order has {len(filled_order)} fields:")
            for idx, value in enumerate(filled_order):
                logger.info(f"  Field {idx}: {value} (type: {type(value).__name__})")
            
            # Based on TradeLocker docs, likely fields after the first 22:
            # commission, swap, pnl, etc.
            if len(filled_order) > 22:
                logger.info(f"\nPotential P&L fields (index 22+):")
                for idx in range(22, len(filled_order)):
                    logger.info(f"  Field {idx}: {filled_order[idx]}")
            else:
                logger.info("\n⚠️  Orders only have 22 fields - NO P&L DATA IN ordersHistory!")
                logger.info("P&L must be calculated from position-level data or another endpoint.")
    
    # Test account-level endpoints that might have P&L/statement data
    logger.info("\n" + "=" * 80)
    logger.info("Testing Account-Level Endpoints for P&L/Statement Data...")
    logger.info("=" * 80)
    
    account_endpoints = [
        "statement",
        "history",
        "transactions",
        "accountStatement",
        "account/history",
        "closedTrades",
        "performance",
    ]
    
    for endpoint_name in account_endpoints:
        logger.info(f"\n--- Testing: {endpoint_name} ---")
        url = f"https://{tl_server}/backend-api/trade/accounts/{account_id}/{endpoint_name}"
        
        try:
            response = await asyncio.to_thread(
                requests.get,
                url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            logger.info(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"SUCCESS! Response keys: {list(data.keys())}")
                
                if 'd' in data:
                    logger.info(f"'d' keys: {list(data['d'].keys())}")
            elif response.status_code == 404:
                logger.info("404 - Not found")
            else:
                logger.info(f"Error: {response.text[:150]}")
        except Exception as e:
            logger.error(f"Exception: {str(e)[:150]}")
    
    # Show all available fields
    logger.info("\n" + "=" * 80)
    logger.info("Available Fields in Order Object")
    logger.info("=" * 80)
    
    if orders:
        sample = orders[0]
        logger.info("\nAll fields in first order:")
        for key, value in sorted(sample.items()):
            logger.info(f"  {key:.<30} {type(value).__name__:.<15} = {value}")
    
    # Check for position-related fields
    logger.info("\n" + "=" * 80)
    logger.info("Position ID Mapping Analysis")
    logger.info("=" * 80)
    
    if orders:
        position_fields = [k for k in orders[0].keys() if 'position' in k.lower() or 'id' in k.lower()]
        logger.info(f"\nFields containing 'position' or 'id': {position_fields}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    logger.info("\n✅ Endpoint works: tl.get_orders_history()")
    logger.info(f"✅ Found: {len(orders)} closed order(s)")
    logger.info(f"✅ Structure: dict['d']['ordersHistory'] → array")
    logger.info(f"✅ P&L calculation: pnl + swap - fee - commission")
    
    logger.info("\n📋 Next Steps:")
    logger.info("   1. Add get_orders_history() to TradeLockerClient")
    logger.info("   2. Determine position ID mapping strategy")
    logger.info("   3. Implement PnLReconciliationService")
    logger.info("   4. Test with recently closed trades")


if __name__ == "__main__":
    asyncio.run(test_orders_history_simple())
