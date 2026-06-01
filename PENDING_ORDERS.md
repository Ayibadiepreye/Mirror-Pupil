# 📊 Pending Order Management

## Overview

This document explains how Mirror Pupil handles **LIMIT and STOP orders** that don't fill immediately. Unlike MARKET orders that execute instantly, pending orders require continuous monitoring until they fill, cancel, or expire.

---

## 🔄 Order Types & Behavior

### 1. MARKET Orders
```
Signal: "GOLD BUY @ MARKET SL 2640 TP 2670"
         ↓
TradeLocker: Order placed
         ↓
Status: FILLED immediately
         ↓
Database: status='filled', entry_price=2650.50 (actual fill)
```

**Behavior**:
- ✅ Fills immediately at current market price
- ✅ Recorded in database with status='filled'
- ✅ No monitoring needed

---

### 2. LIMIT Orders
```
Signal: "GOLD BUY @ 2650 SL 2640 TP 2670"
         ↓
TradeLocker: Order placed at limit price 2650
         ↓
Status: PENDING (waiting for price to reach 2650)
         ↓
Database: status='pending', entry_price=2650 (limit price)
         ↓
Monitor: Checks every 30 seconds
         ↓
Price reaches 2650 → Order FILLS
         ↓
Database: status='filled', entry_price=2650 (actual fill)
```

**Behavior**:
- ⏳ Waits for price to reach limit price
- ✅ Recorded in database with status='pending'
- 🔍 Monitored every 30 seconds
- ✅ Updated to 'filled' when executed
- ❌ Cancelled after 24 hours if not filled

---

### 3. STOP Orders
```
Signal: "GOLD SELL STOP @ 2640 SL 2650 TP 2620"
         ↓
TradeLocker: Order placed at stop price 2640
         ↓
Status: PENDING (waiting for price to reach 2640)
         ↓
Database: status='pending', entry_price=2640 (stop price)
         ↓
Monitor: Checks every 30 seconds
         ↓
Price reaches 2640 → Order FILLS
         ↓
Database: status='filled', entry_price=2640 (actual fill)
```

**Behavior**:
- ⏳ Waits for price to reach stop price
- ✅ Recorded in database with status='pending'
- 🔍 Monitored every 30 seconds
- ✅ Updated to 'filled' when executed
- ❌ Cancelled after 24 hours if not filled

---

## 🗄️ Database Status Flow

### Active Trades Table - Status Field

```sql
CREATE TABLE active_trades (
    ...
    status TEXT NOT NULL,  -- 'pending', 'filled', 'partially_filled', 'failed'
    ...
);
```

### Status Transitions

```
┌─────────────────────────────────────────────────────────────┐
│ ORDER PLACED                                                 │
│ ↓                                                            │
│ status = 'pending'                                           │
│ - LIMIT/STOP orders waiting for price                       │
│ - Recorded immediately in database                          │
│ - PendingOrderMonitor starts tracking                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ MONITORING (every 30 seconds)                                │
│ - Check order status on TradeLocker                         │
│ - Check if order expired (>24 hours)                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
         ┌───────┴───────┐
         │               │
         ▼               ▼
┌─────────────┐   ┌─────────────┐
│ FILLED      │   │ CANCELLED   │
│             │   │             │
│ status =    │   │ - Expired   │
│ 'filled'    │   │ - Rejected  │
│             │   │ - Manual    │
│ Update:     │   │             │
│ - fill_price│   │ Remove from │
│ - lot_size  │   │ database    │
└─────────────┘   └─────────────┘
```

---

## 🔍 Pending Order Monitor

### File: `backend/core/pending_order_monitor.py`

### Features

1. **Background Monitoring**
   - Runs every 30 seconds
   - Checks all pending orders
   - Updates database when status changes

2. **Order Expiry**
   - Default: 24 hours
   - Configurable via `order_expiry_hours`
   - Auto-cancels expired orders

3. **Status Detection**
   - Filled → Update to 'filled'
   - Partially filled → Update to 'partially_filled'
   - Cancelled/Rejected → Remove from database
   - Still pending → No action

4. **Error Handling**
   - Retries on API errors
   - Logs all status changes
   - Continues monitoring other orders if one fails

### Configuration

```python
class PendingOrderMonitor:
    def __init__(self, db: DatabaseManager):
        self.poll_interval = 30  # Check every 30 seconds
        self.order_expiry_hours = 24  # Cancel after 24 hours
```

### Usage

```python
from backend.core import get_pending_order_monitor
from backend.database import get_db

# Initialize
db = await get_db()
monitor = await get_pending_order_monitor(db)

# Monitor starts automatically
# Runs in background, no manual intervention needed

# Get summary
summary = await monitor.get_pending_orders_summary()
print(f"Pending: {summary['pending']}")
print(f"Partially filled: {summary['partially_filled']}")
```

---

## 📊 Complete Flow Example

### Example: LIMIT Order Lifecycle

```
1. SIGNAL RECEIVED
   "GOLD BUY @ 2650 SL 2640 TP 2670"
   
2. TRADE EXECUTOR
   - Validates risk
   - Places LIMIT order at 2650
   - Gets order_id from TradeLocker
   
3. DATABASE RECORDING
   INSERT INTO active_trades (
       account_key, channel_id, signal_id,
       symbol, direction, entry_price,
       sl, tp, lot_size,
       tl_order_id, status
   ) VALUES (
       'user@example.com:12345', -1001859598768, 'B_12345',
       'XAUUSD', 'BUY', 2650.00,
       2640.00, 2670.00, 0.1,
       'TL-ORDER-123', 'pending'  ← PENDING STATUS
   );
   
4. PENDING ORDER MONITOR (every 30 seconds)
   
   Check 1 (30s later):
   - Query TradeLocker: GET /orders/TL-ORDER-123
   - Status: 'pending'
   - Action: None (still waiting)
   
   Check 2 (60s later):
   - Query TradeLocker: GET /orders/TL-ORDER-123
   - Status: 'pending'
   - Action: None (still waiting)
   
   Check 3 (90s later):
   - Query TradeLocker: GET /orders/TL-ORDER-123
   - Status: 'filled'
   - Fill price: 2650.00
   - Action: Update database
   
5. DATABASE UPDATE
   UPDATE active_trades
   SET status = 'filled',
       entry_price = 2650.00
   WHERE trade_id = 123;
   
6. TRADE NOW ACTIVE
   - Management actions can find it
   - Risk monitoring applies
   - Can be closed normally
```

---

## 🎯 Management Actions on Pending Orders

### Scenario: Management Message Before Fill

```
1. LIMIT order placed: "GOLD BUY @ 2650"
   Database: status='pending'
   
2. Management message: "GOLD BREAKEVEN"
   
3. Management Handler:
   - Queries active_trades for GOLD BUY
   - Finds trade with status='pending'
   - Decision: SKIP (can't set breakeven on unfilled order)
   - OR: Cancel the pending order
   
4. Alternative: "GOLD CLOSE"
   - Finds pending order
   - Cancels order on TradeLocker
   - Removes from database
```

### Handling Logic

```python
async def execute_management(mgmt: ParsedManagement):
    # Find trades
    trades = await db.get_active_trades_by_symbol(mgmt.symbol, mgmt.direction)
    
    for trade in trades:
        if trade.status == 'pending':
            if mgmt.action in ['CLOSE', 'CLOSE_ALL', 'CANCEL']:
                # Cancel pending order
                await client.cancel_order(trade.tl_order_id)
                await db.delete_active_trade(trade.trade_id)
                logger.info(f"Cancelled pending order {trade.tl_order_id}")
            else:
                # Skip other actions on pending orders
                logger.warning(
                    f"Cannot execute {mgmt.action} on pending order {trade.tl_order_id}"
                )
                continue
        
        elif trade.status == 'filled':
            # Execute management action normally
            await execute_action(trade, mgmt)
```

---

## ⚠️ Edge Cases & Handling

### 1. Partial Fills

```
Order: BUY 1.0 lot @ 2650
Fill: 0.5 lot filled, 0.5 lot pending

Database:
- status = 'partially_filled'
- lot_size = 0.5 (filled amount)
- Monitor continues tracking remaining 0.5 lot
```

### 2. Order Rejection

```
Order placed → TradeLocker rejects (insufficient margin, etc.)

Database:
- Remove from active_trades
- Log rejection reason
- Notify user
```

### 3. Order Expiry

```
Order pending for >24 hours

Action:
1. Cancel order on TradeLocker
2. Remove from active_trades
3. Log expiry
4. Notify user
```

### 4. Network Errors

```
Monitor can't reach TradeLocker API

Action:
- Log error
- Continue monitoring other orders
- Retry on next cycle (30s later)
```

### 5. Order Not Found

```
Order ID not found on TradeLocker (already cancelled/filled)

Action:
- Check if it was filled recently
- If not found and old: remove from database
- Log discrepancy
```

---

## 📈 Monitoring Dashboard (GUI)

### Pending Orders Panel

```
┌─────────────────────────────────────────────────────────┐
│ PENDING ORDERS                                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ XAUUSD BUY @ 2650.00                                   │
│ ⏳ Pending for 5 minutes                               │
│ SL: 2640.00 | TP: 2670.00 | Lot: 0.1                  │
│ [Cancel Order]                                          │
│                                                         │
│ EURUSD SELL STOP @ 1.0800                              │
│ ⏳ Pending for 2 hours                                 │
│ SL: 1.0850 | TP: 1.0750 | Lot: 0.5                    │
│ [Cancel Order]                                          │
│                                                         │
│ Total Pending: 2 orders                                │
│ Total Risk: $150.00                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing Pending Orders

### Test Script

```python
import asyncio
from backend.database import get_db
from backend.core import get_trade_executor, get_pending_order_monitor
from backend.channels.base import ParsedSignal

async def test_pending_orders():
    # Initialize
    db = await get_db()
    executor = await get_trade_executor(db)
    monitor = await get_pending_order_monitor(db)
    
    # Create LIMIT order signal
    signal = ParsedSignal(
        channel_id=-1001859598768,
        msg_id=12345,
        symbol="XAUUSD",
        direction="BUY",
        entry_price=2650.00,  # LIMIT price
        sl=2640.00,
        tp=[2670.00],
        order_type="LIMIT",
        is_reentry=False,
        raw_text="GOLD BUY @ 2650 SL 2640 TP 2670",
        timestamp=datetime.now()
    )
    
    # Execute (will create pending order)
    results = await executor.execute_signal(signal, channel_id=-1001859598768)
    
    # Check database
    pending = await db.get_active_trades("test@example.com:12345")
    print(f"Pending orders: {len(pending)}")
    for trade in pending:
        print(f"  - {trade.symbol} {trade.direction} @ {trade.entry_price} (status: {trade.status})")
    
    # Wait for monitor to check (30 seconds)
    await asyncio.sleep(35)
    
    # Check again
    updated = await db.get_active_trades("test@example.com:12345")
    for trade in updated:
        print(f"  - {trade.symbol} {trade.direction} @ {trade.entry_price} (status: {trade.status})")

asyncio.run(test_pending_orders())
```

---

## 📝 Summary

### ✅ What Works

1. **MARKET orders**: Fill immediately, recorded as 'filled'
2. **LIMIT orders**: Recorded as 'pending', monitored until filled
3. **STOP orders**: Recorded as 'pending', monitored until filled
4. **Partial fills**: Tracked with 'partially_filled' status
5. **Order expiry**: Auto-cancelled after 24 hours
6. **Management actions**: Can cancel pending orders
7. **Database tracking**: All orders tracked from placement to fill/cancel

### 🔍 Monitoring

- **Frequency**: Every 30 seconds
- **Expiry**: 24 hours (configurable)
- **Status updates**: Automatic
- **Error handling**: Robust with retries

### 📊 Database States

| Status | Meaning | Can Manage? |
|---|---|---|
| `pending` | Order placed, waiting for fill | Cancel only |
| `partially_filled` | Partial fill, rest pending | Limited |
| `filled` | Order fully filled | Yes, all actions |
| `failed` | Order failed/rejected | No (removed) |

---

**Status**: ✅ **COMPLETE**  
**Ready for**: Phase 6 (Management Actions)
