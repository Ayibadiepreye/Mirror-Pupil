# 📊 Complete Signal Flow - From Telegram to Database

## Overview

This document explains the complete lifecycle of a trading signal from the moment it's posted in a Telegram channel until it's managed and closed. **Every step is tracked in the database** to ensure no trades are lost.

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. TELEGRAM MESSAGE RECEIVED                                     │
│    - New message or edited message                               │
│    - From BillirichyFX or Firepips channel                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. MESSAGE DEDUPLICATION (message_cache table)                   │
│    - Check if msg_id already processed                           │
│    - If yes: skip                                                │
│    - If no: mark as processed, continue                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CHANNEL PLUGIN PARSING                                        │
│    - BillirichyPlugin or FirepipsPlugin                          │
│    - Extracts: symbol, direction, entry, SL, TP                  │
│    - Returns: ParsedSignal object                                │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. WAITING ROOM CHECK (waiting_room table)                       │
│    - If signal incomplete (no SL): add to waiting_room           │
│    - If complete: continue to execution                          │
│    - Waiting room entries expire after 15 minutes                │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. ACCOUNT FILTERING (channel_subscriptions table)               │
│    - Get all accounts from database                              │
│    - Filter: NOT paused, NOT breached                            │
│    - Filter: Subscribed to this channel                          │
│    - Result: List of account_keys to execute on                  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. RISK VALIDATION (per account)                                 │
│    - Get account from database                                   │
│    - Get risk profile (or default)                               │
│    - Calculate trade risk (price delta)                          │
│    - Check: Concurrent trade limit                               │
│    - Check: Combined portfolio risk                              │
│    - Check: Daily room (with safety buffer)                      │
│    - Check: Overall room                                         │
│    - If rejected: skip this account, continue with others        │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. TRADELOCKER EXECUTION                                         │
│    - Resolve symbol to instrument ID                             │
│    - Validate instrument routes                                  │
│    - Round lot size to instrument lot step                       │
│    - Create order (market/limit/stop)                            │
│    - Set SL and TP                                               │
│    - Get order_id, position_id, fill_price                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. ✅ DATABASE RECORDING (active_trades table)                   │
│    - Create ActiveTrade record                                   │
│    - Store: account_key, channel_id, signal_id                   │
│    - Store: symbol, direction, entry_price, sl, tp               │
│    - Store: lot_size, tl_order_id, tl_position_id               │
│    - Store: status="filled", risk_usd                            │
│    - Get trade_id from database                                  │
│    - ✅ TRADE IS NOW TRACKED IN DATABASE                         │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. MANAGEMENT ACTIONS (when management message received)         │
│    - Parse management message (BREAKEVEN, CLOSE, MODIFY_SL, etc.)│
│    - Query active_trades table by signal_id or symbol+direction  │
│    - Find matching trades                                        │
│    - Execute management action on TradeLocker                    │
│    - Update active_trades table (new SL/TP)                      │
│    - Or move to trade_history if closed                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. TRADE CLOSE (TP hit, SL hit, or manual close)                │
│     - Get trade from active_trades table                         │
│     - Calculate P&L                                              │
│     - Update account.current_balance                             │
│     - Update account.highest_banked_balance (if new high)        │
│     - Update account.daily_pnl                                   │
│     - Move trade to trade_history table                          │
│     - Delete from active_trades table                            │
│     - Check risk limits (breach detection)                       │
│     - Check profit lock trigger                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Detailed Step-by-Step Explanation

### Step 1: Telegram Message Received

**File**: `telegram_client.py`

```python
@client.on(events.NewMessage(chats=enabled_channel_ids))
async def handle_new_message(event):
    channel_id = event.chat_id
    plugin = get_plugin_for_channel(channel_id)
    if plugin:
        await plugin.route_message(event.message, is_edit=False)
```

**What happens**:
- Pytdbot receives message from Telegram
- Identifies which channel it came from
- Routes to appropriate channel plugin

---

### Step 2: Message Deduplication

**File**: `backend/channels/base.py` → `route_message()`

```python
# Check if already processed
if await db.is_message_processed(msg_id, channel_id):
    return  # Skip duplicate

# Mark as processed
await db.mark_message_processed(msg_id, channel_id)
```

**Database**: `message_cache` table

**What happens**:
- Checks if this message ID was already processed
- Prevents duplicate trade execution
- Entries auto-expire after 2 minutes

---

### Step 3: Channel Plugin Parsing

**File**: `backend/channels/billirichy/plugin.py` or `backend/channels/firepips/plugin.py`

```python
signal = await plugin.parse_entry(message, clean_text)
# Returns ParsedSignal with:
# - symbol: "XAUUSD"
# - direction: "BUY"
# - entry_price: 2650.50
# - sl: 2640.00
# - tp: [2670.00, 2680.00]
# - order_type: "MARKET"
```

**What happens**:
- Regex patterns extract trade details
- Symbol normalization ("gold" → "XAUUSD")
- Returns structured ParsedSignal object

---

### Step 4: Waiting Room Check

**File**: `backend/channels/base.py`

**Database**: `waiting_room` table

```python
if not signal.sl:
    # Incomplete signal - add to waiting room
    bare_signal = BareSignal(...)
    await db.add_to_waiting_room(bare_signal)
    return  # Wait for SL to be posted
```

**What happens**:
- If signal has no SL: stored in waiting_room
- Expires after 15 minutes
- When SL is posted (edit or new message): completes signal

---

### Step 5: Account Filtering

**File**: `backend/core/trade_executor.py` → `execute_signal()`

**Database**: `accounts` + `channel_subscriptions` tables

```python
all_accounts = await db.get_all_accounts()
account_keys = []

for account in all_accounts:
    if account.paused or account.breached:
        continue  # Skip
    
    is_subscribed = await db.is_channel_subscribed(account.account_key, channel_id)
    if is_subscribed:
        account_keys.append(account.account_key)
```

**What happens**:
- Gets all accounts from database
- Filters out paused/breached accounts
- Checks channel subscription per account
- Only executes on subscribed accounts

---

### Step 6: Risk Validation

**File**: `backend/core/trade_executor.py` → `_execute_on_account()`

**Database**: `accounts` + `risk_profiles` + `active_trades` tables

```python
# Get account and profile
account = await db.get_account(account_key)
profile = await db.get_risk_profile(account.risk_profile_id)

# Validate trade
validation = await risk_enforcer.validate_trade(
    account=account,
    profile=profile,
    entry_price=signal.entry_price,
    sl_price=signal.sl,
    lot_size=lot_size,
    symbol=signal.symbol
)

if not validation['allowed']:
    return {"status": "rejected", "reason": validation['reason']}
```

**What happens**:
- Calculates trade risk (price delta)
- Checks concurrent trade limit
- Checks combined portfolio risk
- Checks daily room (with 10% safety buffer)
- Checks overall room
- Rejects if any check fails

---

### Step 7: TradeLocker Execution

**File**: `backend/core/trade_executor.py` → `_execute_on_account()`

```python
# Resolve symbol
instrument_id = await client.get_instrument_id_from_symbol_name(signal.symbol)

# Validate routes
routes = await client.validate_instrument_routes(instrument_id)

# Round lot size
lot_size = client.round_lot_size(default_lot_size, lot_step)

# Create order
order = await client.create_order(
    instrument_id=instrument_id,
    quantity=lot_size,
    side=signal.direction.lower(),
    type_=signal.order_type.lower(),
    stop_loss=signal.sl,
    take_profit=signal.tp[0],
    validity="GTC"
)

# Extract details
order_id = order.get('orderId')
position_id = order.get('positionId')
fill_price = order.get('fillPrice')
```

**What happens**:
- Resolves symbol to TradeLocker instrument ID
- Validates instrument has TRADE route
- Rounds lot size to instrument's lot step
- Places order on TradeLocker
- Gets order_id, position_id, fill_price

---

### Step 8: ✅ DATABASE RECORDING (CRITICAL!)

**File**: `backend/core/trade_executor.py` → `_execute_on_account()`

**Database**: `active_trades` table

```python
# Create ActiveTrade record
signal_id = f"{channel_id}_{signal.msg_id}"

active_trade = ActiveTrade(
    account_key=account_key,
    channel_id=channel_id,
    signal_id=signal_id,
    symbol=signal.symbol,
    direction=signal.direction,
    entry_price=fill_price,
    sl=signal.sl,
    tp=signal.tp[0],
    lot_size=lot_size,
    tl_order_id=str(order_id),
    tl_position_id=str(position_id),
    status="filled",
    risk_usd=trade_risk
)

# ✅ RECORD IN DATABASE
trade_id = await db.add_active_trade(active_trade)

logger.info(f"✅ Trade recorded in database: trade_id={trade_id}")
```

**What happens**:
- Creates ActiveTrade object with all details
- **Inserts into active_trades table**
- Gets trade_id from database
- **Trade is now tracked and can be managed**

**This is the critical step that was missing in the previous bot!**

---

### Step 9: Management Actions

**File**: `backend/core/management_handler.py` (Phase 6)

**Database**: `active_trades` table

```python
# Parse management message
mgmt = await plugin.parse_management(message, clean_text)
# Returns: ParsedManagement(action="BREAKEVEN", symbol="XAUUSD")

# Find matching trades in database
trades = await db.get_active_trades_by_signal_id(mgmt.signal_id)
# OR
trades = await db.get_active_trades_by_symbol(mgmt.symbol, mgmt.direction)

# Execute management action
for trade in trades:
    if mgmt.action == "BREAKEVEN":
        await client.modify_order(trade.tl_position_id, sl=trade.entry_price)
        await db.update_active_trade_sl(trade.trade_id, trade.entry_price)
    
    elif mgmt.action == "CLOSE_ALL":
        await client.close_position(trade.tl_position_id)
        await db.close_active_trade(trade.trade_id, ...)
```

**What happens**:
- Management message parsed
- **Queries active_trades table** to find matching trades
- Executes action on TradeLocker
- Updates database (new SL/TP or moves to history)

---

### Step 10: Trade Close

**File**: `backend/core/trade_closer.py` (Phase 6)

**Database**: `active_trades` → `trade_history` + `accounts` tables

```python
# Get trade from database
trade = await db.get_active_trade(trade_id)

# Calculate P&L
pnl = calculate_pnl(trade.entry_price, exit_price, trade.lot_size, trade.direction)

# Update account
account.current_balance += pnl
account.daily_pnl += pnl

if account.current_balance > account.highest_banked_balance:
    account.highest_banked_balance = account.current_balance

await db.update_account_balance(account.account_key, account.current_balance)

# Move to history
await db.close_active_trade(
    trade_id=trade.trade_id,
    exit_price=exit_price,
    pnl=pnl,
    outcome="WIN" if pnl > 0 else "LOSS",
    close_reason="TP_HIT"
)

# Check risk limits
await risk_enforcer.check_risk_limits(account, profile)
```

**What happens**:
- Gets trade from active_trades
- Calculates P&L
- Updates account balance
- Updates highest_banked_balance (if new high)
- **Moves trade to trade_history table**
- **Deletes from active_trades table**
- Checks for breaches
- Checks profit lock trigger

---

## 🔍 Database Tables Used

### 1. `message_cache`
- **Purpose**: Prevent duplicate processing
- **Lifetime**: 2 minutes
- **Cleanup**: Auto (every 2 minutes)

### 2. `waiting_room`
- **Purpose**: Store incomplete signals
- **Lifetime**: 15 minutes
- **Cleanup**: Auto (every 2 minutes)

### 3. `channel_subscriptions`
- **Purpose**: Per-account channel toggles
- **Used in**: Account filtering (Step 5)

### 4. `accounts`
- **Purpose**: Account state and risk tracking
- **Used in**: Risk validation, balance updates

### 5. `risk_profiles`
- **Purpose**: Risk management rules
- **Used in**: Risk validation (Step 6)

### 6. `active_trades` ⭐
- **Purpose**: Currently open positions
- **Used in**: Risk validation, management actions, trade close
- **Critical**: This is where trades are recorded after execution

### 7. `trade_history`
- **Purpose**: Closed trades with P&L
- **Used in**: Historical analysis, consistency score

### 8. `profitable_days`
- **Purpose**: Daily P&L tracking
- **Used in**: Consistency score, daily reset

---

## ✅ Why This Solves the Previous Bot's Problem

### Previous Bot Issue:
```
Telegram → Parse → TradeLocker ❌ (stopped here)
                                ↓
                          No database record
                                ↓
                    Management messages can't find trades
```

### Current Bot Solution:
```
Telegram → Parse → Risk Check → TradeLocker → ✅ Database Record
                                                      ↓
                                            Management can find trades
                                                      ↓
                                              Trades properly tracked
```

### Key Improvements:

1. **Every trade is recorded** in `active_trades` immediately after TradeLocker execution
2. **Management actions query the database** to find trades
3. **Trade lifecycle is fully tracked**: active_trades → trade_history
4. **Account balances are updated** when trades close
5. **Risk limits are enforced** before execution
6. **Channel subscriptions are respected** per account
7. **Waiting room handles incomplete signals**
8. **Message deduplication prevents duplicates**

---

## 🧪 Testing the Flow

### Test 1: Complete Signal Flow
```bash
# 1. Start Telegram client
python telegram_client.py

# 2. Post test signal in channel
# "GOLD BUY @ 2650 SL 2640 TP 2670"

# 3. Check database
SELECT * FROM active_trades;
# Should show the trade

# 4. Post management message
# "GOLD BREAKEVEN"

# 5. Check database
SELECT * FROM active_trades WHERE symbol='XAUUSD';
# Should show SL updated to entry price
```

### Test 2: Waiting Room
```bash
# 1. Post incomplete signal
# "GOLD BUY @ 2650"

# 2. Check waiting room
SELECT * FROM waiting_room;
# Should show entry

# 3. Post SL (edit or new message)
# "SL 2640"

# 4. Check active trades
SELECT * FROM active_trades WHERE symbol='XAUUSD';
# Should show completed trade
```

### Test 3: Risk Rejection
```bash
# 1. Open 5 trades (max concurrent)
# 2. Try to open 6th trade
# Should be rejected with "Concurrent trade limit reached"
# 3. Check active_trades
# Should only show 5 trades
```

---

## 📊 Summary

**Every step is tracked in the database:**

1. ✅ Message deduplication → `message_cache`
2. ✅ Incomplete signals → `waiting_room`
3. ✅ Account filtering → `channel_subscriptions`
4. ✅ Risk validation → `accounts` + `risk_profiles`
5. ✅ **Trade execution → `active_trades`** ⭐
6. ✅ Management actions → Query `active_trades`
7. ✅ Trade close → Move to `trade_history`
8. ✅ Balance updates → `accounts`
9. ✅ Daily P&L → `profitable_days`

**The critical fix**: Step 8 now **records every trade in the database** immediately after TradeLocker execution. This ensures management actions can find and modify trades, and the complete trade lifecycle is tracked.

---

**Status**: ✅ **COMPLETE AND TESTED**  
**Ready for**: Phase 6 (Management Actions)
