# ✅ Pending Order Management - Complete

## Overview

I've implemented a comprehensive **Pending Order Monitor** that tracks LIMIT and STOP orders from placement until they fill, cancel, or expire.

---

## 🔄 How It Works

### 1. Order Placement

```python
# TradeExecutor places order
order = await client.create_order(
    instrument_id=instrument_id,
    quantity=lot_size,
    side="buy",
    type_="limit",  # or "stop"
    price=2650.00,
    stop_loss=2640.00,
    take_profit=2670.00
)

# Determine status
if order_type == "market":
    status = "filled"  # Immediate
elif order_status in ['pending', 'working']:
    status = "pending"  # Needs monitoring
```

### 2. Database Recording

```python
# Record in active_trades with status
active_trade = ActiveTrade(
    account_key=account_key,
    channel_id=channel_id,
    signal_id=signal_id,
    symbol="XAUUSD",
    direction="BUY",
    entry_price=2650.00,  # Limit price
    sl=2640.00,
    tp=2670.00,
    lot_size=0.1,
    tl_order_id="TL-ORDER-123",
    status="pending",  # ← PENDING STATUS
    risk_usd=105.00
)

trade_id = await db.add_active_trade(active_trade)
```

### 3. Background Monitoring

```python
# PendingOrderMonitor runs every 30 seconds
async def _monitoring_loop(self):
    while True:
        await asyncio.sleep(30)  # Check every 30 seconds
        
        # Get all pending trades
        pending_trades = await db.get_pending_trades()
        
        for trade in pending_trades:
            # Check status on TradeLocker
            order_status = await client.get_order_status(trade.tl_order_id)
            
            if order_status == 'filled':
                # Update database
                await db.update_trade_status(trade.trade_id, 'filled', fill_price)
            
            elif order_status == 'cancelled':
                # Remove from database
                await db.delete_active_trade(trade.trade_id)
            
            elif age > 24_hours:
                # Cancel expired order
                await client.cancel_order(trade.tl_order_id)
                await db.delete_active_trade(trade.trade_id)
```

### 4. Status Updates

```
PENDING → Monitor checks every 30s
    ↓
    ├─→ FILLED: Update status='filled', entry_price=actual_fill
    ├─→ CANCELLED: Remove from database
    ├─→ EXPIRED (>24h): Cancel order, remove from database
    └─→ STILL PENDING: Continue monitoring
```

---

## 📊 Order Type Behavior

### MARKET Orders
- ✅ Fill immediately
- ✅ Recorded as status='filled'
- ✅ No monitoring needed

### LIMIT Orders
- ⏳ Wait for price to reach limit
- ✅ Recorded as status='pending'
- 🔍 Monitored every 30 seconds
- ✅ Updated to 'filled' when executed
- ❌ Cancelled after 24 hours if not filled

### STOP Orders
- ⏳ Wait for price to reach stop
- ✅ Recorded as status='pending'
- 🔍 Monitored every 30 seconds
- ✅ Updated to 'filled' when executed
- ❌ Cancelled after 24 hours if not filled

---

## 🗄️ Database Status Field

```sql
CREATE TABLE active_trades (
    ...
    status TEXT NOT NULL,  -- Values:
                           -- 'pending' = waiting for fill
                           -- 'filled' = order executed
                           -- 'partially_filled' = partial execution
                           -- 'failed' = order rejected
    ...
);
```

### Status Queries

```python
# Get all pending orders
SELECT * FROM active_trades WHERE status = 'pending';

# Get filled trades only
SELECT * FROM active_trades WHERE status = 'filled';

# Get all active (pending + filled)
SELECT * FROM active_trades WHERE status IN ('pending', 'filled', 'partially_filled');
```

---

## 🎯 Management Actions on Pending Orders

### Can Cancel Pending Orders

```python
# Management message: "GOLD CLOSE"
trades = await db.get_active_trades_by_symbol("XAUUSD", "BUY")

for trade in trades:
    if trade.status == 'pending':
        # Cancel pending order
        await client.cancel_order(trade.tl_order_id)
        await db.delete_active_trade(trade.trade_id)
        logger.info(f"Cancelled pending order {trade.tl_order_id}")
    
    elif trade.status == 'filled':
        # Close filled position
        await client.close_position(trade.tl_position_id)
        await db.close_active_trade(trade.trade_id, ...)
```

### Cannot Modify Pending Orders

```python
# Management message: "GOLD BREAKEVEN"
trades = await db.get_active_trades_by_symbol("XAUUSD", "BUY")

for trade in trades:
    if trade.status == 'pending':
        # Skip - can't set breakeven on unfilled order
        logger.warning(f"Cannot set breakeven on pending order {trade.tl_order_id}")
        continue
    
    elif trade.status == 'filled':
        # Modify SL to breakeven
        await client.modify_order(trade.tl_position_id, sl=trade.entry_price)
```

---

## ⚙️ Configuration

```python
class PendingOrderMonitor:
    def __init__(self, db: DatabaseManager):
        # Check every 30 seconds
        self.poll_interval = 30
        
        # Cancel orders after 24 hours
        self.order_expiry_hours = 24
```

**Configurable via environment variables** (future):
```bash
PENDING_ORDER_POLL_INTERVAL=30  # seconds
PENDING_ORDER_EXPIRY_HOURS=24   # hours
```

---

## 🧪 Testing

### Test 1: LIMIT Order Lifecycle

```bash
# 1. Place LIMIT order
Signal: "GOLD BUY @ 2650 SL 2640 TP 2670"

# 2. Check database immediately
SELECT * FROM active_trades WHERE symbol='XAUUSD';
# Result: status='pending', entry_price=2650.00

# 3. Wait 30 seconds (monitor checks)
# If price hasn't reached 2650: still pending
# If price reached 2650: status='filled'

# 4. Check database again
SELECT * FROM active_trades WHERE symbol='XAUUSD';
# Result: status='filled', entry_price=2650.00 (actual fill)
```

### Test 2: Order Expiry

```bash
# 1. Place LIMIT order at unreachable price
Signal: "GOLD BUY @ 9999 SL 9990 TP 10000"

# 2. Wait 24 hours + 30 seconds
# Monitor detects expired order

# 3. Check database
SELECT * FROM active_trades WHERE symbol='XAUUSD';
# Result: No rows (order cancelled and removed)
```

### Test 3: Management on Pending

```bash
# 1. Place LIMIT order
Signal: "GOLD BUY @ 2650 SL 2640 TP 2670"
# Database: status='pending'

# 2. Send management message
Management: "GOLD CLOSE"

# 3. Check result
# Order cancelled on TradeLocker
# Removed from database
```

---

## 📈 Monitoring Dashboard (Future GUI)

```
┌─────────────────────────────────────────────────────────┐
│ PENDING ORDERS (2)                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🟡 XAUUSD BUY @ 2650.00                                │
│    Pending for 5 minutes                               │
│    SL: 2640.00 | TP: 2670.00 | Risk: $105.00          │
│    [Cancel]                                             │
│                                                         │
│ 🟡 EURUSD SELL STOP @ 1.0800                           │
│    Pending for 2 hours                                 │
│    SL: 1.0850 | TP: 1.0750 | Risk: $250.00            │
│    [Cancel]                                             │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ FILLED TRADES (3)                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 🟢 XAUUSD BUY @ 2648.50                                │
│    Filled 10 minutes ago                               │
│    SL: 2640.00 | TP: 2670.00 | P&L: +$85.00           │
│    [Manage]                                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ What's Implemented

1. ✅ **Order status detection** (market/limit/stop)
2. ✅ **Database recording** with correct status
3. ✅ **Background monitoring** (every 30 seconds)
4. ✅ **Status updates** (pending → filled)
5. ✅ **Order expiry** (24 hours)
6. ✅ **Partial fill handling**
7. ✅ **Cancellation support**
8. ✅ **Error handling** and retries
9. ✅ **Management action filtering** (can't modify pending)
10. ✅ **Complete documentation**

---

## 📊 Complete Flow

```
1. Signal Received: "GOLD BUY @ 2650 SL 2640 TP 2670"
   ↓
2. Trade Executor: Places LIMIT order
   ↓
3. TradeLocker: Returns order_id, status='pending'
   ↓
4. Database: INSERT with status='pending'
   ↓
5. Pending Monitor: Starts tracking (every 30s)
   ↓
6. Monitor Check 1 (30s): Still pending
   ↓
7. Monitor Check 2 (60s): Still pending
   ↓
8. Monitor Check 3 (90s): FILLED!
   ↓
9. Database: UPDATE status='filled', entry_price=2650.00
   ↓
10. Trade Now Active: Can be managed normally
```

---

## 🎯 Key Benefits

1. **No lost orders**: All orders tracked from placement
2. **Automatic monitoring**: No manual intervention needed
3. **Proper lifecycle**: pending → filled → managed → closed
4. **Management compatibility**: Can cancel pending, modify filled
5. **Expiry protection**: Orders don't stay pending forever
6. **Database consistency**: Always reflects actual TradeLocker state

---

**Status**: ✅ **COMPLETE**  
**Files Created**:
- `backend/core/pending_order_monitor.py` (350 lines)
- `PENDING_ORDERS.md` (comprehensive guide)
- `PENDING_ORDERS_SUMMARY.md` (this file)

**Ready for**: Phase 6 (Management Actions) - Management handler can now properly find and act on both pending and filled trades!
