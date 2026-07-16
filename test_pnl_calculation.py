"""
Test P&L Calculation from TradeLocker ordersHistory
Calculate actual P&L for closed positions and output for manual verification
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from loguru import logger
import requests

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from tradelocker import TLAPI

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<level>{time:HH:mm:ss}</level> | <level>{level: <8}</level> | <level>{message}</level>")


def parse_order_fields(order_list):
    """Convert order list to dict with named fields"""
    field_names = [
        "id", "tradableInstrumentId", "accountId", "qty", "side", "type", 
        "status", "filledQty", "avgPrice", "limitPrice", "stopPrice",
        "timeInForce", "parentOrderId", "createTime", "updateTime",
        "unknown_15", "positionId", "takeProfitPrice", "takeProfitType",
        "stopLossPrice", "stopLossType", "clientOrderId"
    ]
    
    order_dict = {}
    for idx, field_name in enumerate(field_names):
        if idx < len(order_list):
            order_dict[field_name] = order_list[idx]
    
    return order_dict


def group_orders_by_position(orders):
    """Group orders by position ID"""
    positions = {}
    
    for order_list in orders:
        order = parse_order_fields(order_list)
        position_id = order.get('positionId')
        
        if not position_id or position_id == 'None':
            continue
        
        if position_id not in positions:
            positions[position_id] = []
        
        positions[position_id].append(order)
    
    return positions


def calculate_position_pnl(position_orders, instrument_specs):
    """Calculate P&L for a closed position"""
    
    # Separate filled entry and exit orders
    entry_orders = []
    exit_orders = []
    
    for order in position_orders:
        if order.get('status') != 'Filled':
            continue
        
        side = order.get('side')
        if side == 'buy':
            entry_orders.append(order)
        elif side == 'sell':
            exit_orders.append(order)
    
    if not entry_orders or not exit_orders:
        return None  # Position not closed
    
    # Calculate weighted average entry price
    total_entry_qty = 0
    total_entry_cost = 0
    
    for order in entry_orders:
        qty = float(order.get('filledQty') or order.get('qty') or 0)
        price = float(order.get('avgPrice') or 0)
        total_entry_qty += qty
        total_entry_cost += qty * price
    
    avg_entry_price = total_entry_cost / total_entry_qty if total_entry_qty > 0 else 0
    
    # Calculate weighted average exit price
    total_exit_qty = 0
    total_exit_value = 0
    
    for order in exit_orders:
        qty = float(order.get('filledQty') or order.get('qty') or 0)
        price = float(order.get('avgPrice') or 0)
        total_exit_qty += qty
        total_exit_value += qty * price
    
    avg_exit_price = total_exit_value / total_exit_qty if total_exit_qty > 0 else 0
    
    # Get instrument specs
    instrument_id = entry_orders[0].get('tradableInstrumentId')
    spec = instrument_specs.get(instrument_id, {})
    contract_size = spec.get('contractSize', 1.0)
    pip_value = spec.get('pipValue', 0.0001)
    symbol = spec.get('symbol', f'Instrument_{instrument_id}')
    
    # Calculate P&L (for long position: buy entry, sell exit)
    qty = min(total_entry_qty, total_exit_qty)  # Use minimum in case of partial close
    price_diff = avg_exit_price - avg_entry_price
    
    # P&L = price difference × quantity × contract size
    pnl = price_diff * qty * contract_size
    
    # Calculate in pips
    pips = price_diff / pip_value if pip_value > 0 else 0
    
    return {
        'position_id': entry_orders[0].get('positionId'),
        'symbol': symbol,
        'instrument_id': instrument_id,
        'entry_price': avg_entry_price,
        'exit_price': avg_exit_price,
        'quantity': qty,
        'contract_size': contract_size,
        'pnl': pnl,
        'pips': pips,
        'entry_orders': len(entry_orders),
        'exit_orders': len(exit_orders),
        'entry_time': entry_orders[0].get('createTime'),
        'exit_time': exit_orders[-1].get('updateTime'),
    }


async def test_pnl_calculation():
    """Test P&L calculation from orders history"""
    
    logger.info("=" * 80)
    logger.info("TRADELOCKER P&L CALCULATION TEST")
    logger.info("=" * 80)
    
    # Credentials
    tl_email = "bonnieprincewill6@gmail.com"
    tl_password = "#Princewill15"
    tl_server = "demo.tradelocker.com"
    server_name = "HEROFX"
    
    logger.info(f"\nAuthenticating to {tl_server}...")
    
    try:
        # Initialize TLAPI
        tl = TLAPI(
            environment=f"https://{tl_server}",
            username=tl_email,
            password=tl_password,
            server=server_name
        )
        
        logger.info("✓ Authenticated")
        
        # Get account info
        account_id = tl.account_id
        acc_num = tl.acc_num
        access_token = tl._access_token
        
        logger.info(f"Account ID: {account_id}")
        logger.info(f"Account Number: {acc_num}")
        
        # Fetch orders history
        logger.info("\n" + "=" * 80)
        logger.info("Fetching Orders History...")
        logger.info("=" * 80)
        
        url = f"https://{tl_server}/backend-api/trade/accounts/{account_id}/ordersHistory"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "accNum": str(acc_num)
        }
        params = {"ref": "py_c", "v": "0.56.1"}
        
        response = await asyncio.to_thread(
            requests.get, url, headers=headers, params=params, timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch orders: {response.status_code}")
            return
        
        data = response.json()
        orders = data.get('d', {}).get('ordersHistory', [])
        
        logger.info(f"✓ Fetched {len(orders)} orders")
        
        # Get instrument specifications
        logger.info("\nFetching instrument specifications...")
        
        all_instruments = await asyncio.to_thread(tl.get_all_instruments)
        
        instrument_specs = {}
        for _, row in all_instruments.iterrows():
            instrument_id = str(row['id'])
            instrument_specs[instrument_id] = {
                'symbol': row['name'],
                'contractSize': row.get('contractSize', 1.0),
                'pipValue': row.get('minPriceIncrement', 0.0001),
            }
        
        logger.info(f"✓ Loaded {len(instrument_specs)} instruments")
        
        # Group orders by position
        logger.info("\n" + "=" * 80)
        logger.info("Grouping Orders by Position...")
        logger.info("=" * 80)
        
        positions = group_orders_by_position(orders)
        logger.info(f"✓ Found {len(positions)} unique positions")
        
        # Calculate P&L for each closed position
        logger.info("\n" + "=" * 80)
        logger.info("CALCULATED P&L FOR CLOSED POSITIONS")
        logger.info("=" * 80)
        
        closed_positions = []
        
        for position_id, position_orders in positions.items():
            pnl_data = calculate_position_pnl(position_orders, instrument_specs)
            
            if pnl_data:  # Only closed positions
                closed_positions.append(pnl_data)
        
        # Sort by exit time (most recent first)
        closed_positions.sort(key=lambda x: x.get('exit_time', '0'), reverse=True)
        
        # Display results
        logger.info(f"\nFound {len(closed_positions)} closed positions\n")
        
        total_pnl = 0
        
        for idx, pos in enumerate(closed_positions[:20], 1):  # Show first 20
            logger.info(f"{'─' * 80}")
            logger.info(f"POSITION #{idx}")
            logger.info(f"{'─' * 80}")
            logger.info(f"Position ID:    {pos['position_id']}")
            logger.info(f"Symbol:         {pos['symbol']}")
            logger.info(f"Entry Price:    {pos['entry_price']:.5f}")
            logger.info(f"Exit Price:     {pos['exit_price']:.5f}")
            logger.info(f"Quantity:       {pos['quantity']:.2f} lots")
            logger.info(f"Contract Size:  {pos['contract_size']:.0f}")
            logger.info(f"")
            logger.info(f"Price Diff:     {pos['exit_price'] - pos['entry_price']:.5f}")
            logger.info(f"Pips:           {pos['pips']:.1f}")
            logger.info(f"")
            logger.info(f"💰 CALCULATED P&L: ${pos['pnl']:.2f}")
            logger.info(f"")
            logger.info(f"Entry Orders:   {pos['entry_orders']}")
            logger.info(f"Exit Orders:    {pos['exit_orders']}")
            
            # Convert timestamps
            if pos['entry_time']:
                entry_dt = datetime.fromtimestamp(int(pos['entry_time'])/1000, tz=timezone.utc)
                logger.info(f"Entry Time:     {entry_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            if pos['exit_time']:
                exit_dt = datetime.fromtimestamp(int(pos['exit_time'])/1000, tz=timezone.utc)
                logger.info(f"Exit Time:      {exit_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            logger.info("")
            
            total_pnl += pos['pnl']
        
        # Summary
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Closed Positions: {len(closed_positions)}")
        logger.info(f"Total Calculated P&L:   ${total_pnl:.2f}")
        logger.info(f"Average P&L per Trade:  ${total_pnl / len(closed_positions):.2f}" if closed_positions else "N/A")
        logger.info("=" * 80)
        
        # Save detailed output
        output_file = "test_pnl_calculation_output.txt"
        logger.info(f"\n✓ Complete output saved to: {output_file}")
        
    except Exception as e:
        logger.exception(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_pnl_calculation())
