# User Questions - Detailed Answers

**Date:** Context Transfer Session  
**Context:** Complete spec review completed

---

## Your Questions:

1. **What of the autonomous execution mentioned in the docs? Is it part of the phases?**
2. **The timing for bare signals and waiting for SL - the 15 minute stuff - what about that?**
3. **What about re-entries?**
4. **Explain the trailing stop update to me**
5. **Withdrawal tracking and management**
6. **The rest of the logic added in the spec doc**

---

## 1. AUTONOMOUS EXECUTION - IS IT PART OF THE PHASES?

### Answer: YES - It's Phase 6 (Not Yet Implemented)

**What is Autonomous Execution?**
Autonomous execution means the bot automatically manages trades based on time elapsed since entry, WITHOUT waiting for manual management messages from the channel.

### BillirichyFX Autonomous Actions (Section 4.7)

| Time Since Entry | Condition | Action |
|---|---|---|
| **15 minutes** | SL present, no TP | Auto-assign TP = entry ± 2× SL distance |
| **1 hour** | No TP hit; profit ≥ 15 pips (XAUUSD) or 8 pips (forex) | Move SL to BE |
| **2 hours** | No management update; trade in profit | Close 50% |
| **4 hours** | No management update | Close remaining 100% |
| **4:45 PM EST daily** | Any open trade | Force close all (EOD) ✅ DONE |
| **Friday 4:45 PM EST** | Any open trade | Force close all (weekend) ✅ DONE |

### Firepips Autonomous Actions (Section 6.7)

| Time Since Entry | Condition | Action |
|---|---|---|
| **1 hour** | Trade in profit (floating P&L > 0) | Move SL to BE |
| **2 hours** | Trade in profit | Close 50% |
| **4 hours** | Any state | Force close remaining |
| **4:45 PM EST daily** | Any open trade | Force close all (EOD) ✅ DONE |
| **Friday 4:45 PM EST** | Any open trade | Force close all (weekend) ✅ DONE |

### What's Already Done?
- ✅ EOD force close at 4:45 PM EST (implemented in `backend/risk/eod_close.py`)
- ✅ Weekend force close at Friday 4:45 PM EST (same file)

### What's Missing?
- ❌ 15-minute auto-TP assignment (BillirichyFX only)
- ❌ 1-hour breakeven logic (both channels)
- ❌ 2-hour partial close 50% (both channels)
- ❌ 4-hour full close (both channels)

### How to Implement?
Create background schedulers:
- `backend/channels/billirichy/autonomous.py`
- `backend/channels/firepips/autonomous.py`

Each scheduler:
1. Runs every 60 seconds
2. Checks all active trades for that channel
3. Calculates time since entry
4. Checks conditions (profit level, TP hit status, etc.)
5. Executes actions via TradeExecutor
6. Logs all autonomous actions
7. Sends INFO notifications to GUI

---

## 2. BARE SIGNALS AND 15-MINUTE WAITING ROOM

### Answer: Already Implemented ✅ (But Needs One Fix)

**What is the Waiting Room?**
When a signal arrives with NO stop loss (called a "bare signal"), the bot doesn't execute immediately. Instead, it stores the signal in a "waiting room" and waits up to 15 minutes for the SL to arrive in a follow-up message.

### Current Implementation Status:
- ✅ Waiting room table exists in database
- ✅ 15-minute expiry logic implemented
- ✅ Completion detection (reply, edit, or new message with SL)
- ✅ Expiry cleanup (discards after 15 minutes)
- ✅ Implemented in both BillirichyFX and Firepips parsers

### What's Missing?
❌ **Second Bare Signal Handling** (Section 3.7, 5.6)

**Problem:** If a second bare signal arrives for the same symbol+direction while one is already waiting, the current code might create a duplicate entry.

**Spec Says:** 
- Do NOT create a second entry
- Instead, RESET the existing entry's `expires_at` to `now + 15 minutes`
- This extends the waiting period

**Example:**
```
10:00 AM - Bare signal: "BUY XAUUSD" (no SL) → waiting room, expires 10:15 AM
10:10 AM - Another bare signal: "BUY XAUUSD" (no SL) → reset expiry to 10:25 AM
10:12 AM - SL arrives: "SL 1950" → merge and execute
```

### Completion Priority (Section 3.7, 5.6):

| Priority | Completion Condition |
|---|---|
| 1 | Direct reply to the bare signal's message ID AND contains SL |
| 2 | Same symbol + same direction + contains SL |
| 3 | Same symbol only OR same direction only, AND contains SL |
| 4 | Price pattern matches AND SL is logically valid |

### Files Involved:
- `backend/channels/billirichy/entry.py`
- `backend/channels/firepips/entry.py`
- `backend/database/manager.py` (waiting room queries)

---

## 3. RE-ENTRIES - WHAT ABOUT THEM?

### Answer: Partially Implemented (Needs Enhancement)

**What is a Re-entry?**
When the channel posts "Add more", "Second entry", "Re-enter", etc., the bot should open an additional position on the same symbol/direction as an existing trade.

### Current Implementation Status:
- ✅ Re-entry keyword detection exists
- ✅ Basic re-entry execution works
- ❌ **7-Level Parent Matching NOT fully implemented** (Section 3.4)

### The 7-Level Parent Matching System (Section 3.4):

When a re-entry signal arrives, the bot needs to find the "parent" trade to inherit SL/TP from. It tries these methods in order:

| Priority | Condition | Example |
|---|---|
| 1 | Direct reply to a trade message ID | Message replies to original entry |
| 2 | Exactly one open trade exists | Only 1 trade open → must be the parent |
| 3 | Symbol + direction both match | "Add more XAUUSD BUY" → find XAUUSD BUY trade |
| 4 | Symbol matches (direction ambiguous) | "Add more XAUUSD" → find any XAUUSD trade |
| 5 | Direction matches (symbol ambiguous) | "Add more buys" → find any BUY trade |
| 6 | Price decimal places match | Entry price format matches existing trade |
| 7 | No match → skip re-entry, log warning | Can't find parent → don't execute |

### Re-entry Inheritance Rules:

**Entry Price:** Always use current market price (market order)

**Stop Loss:**
- If re-entry message has explicit SL → use it
- Else → inherit parent's current SL

**Take Profit:**
- If re-entry message has explicit TP → use it
- Else → inherit parent's highest remaining active TP
- If parent has no active TP → auto-assign TP = entry ± 2× SL distance

### Signal ID Format:
- Parent: `B_104521`
- First re-entry: `B_104521_re1`
- Second re-entry: `B_104521_re2`

### What Needs to Be Done?
Enhance the re-entry logic in:
- `backend/channels/billirichy/entry.py`
- `backend/channels/firepips/entry.py`

Implement all 7 levels of parent matching with proper fallback logic.

---

## 4. TRAILING STOP UPDATES - EXPLAIN IT

### Answer: NOT Implemented Yet ❌ (Critical Missing Feature)

**What is a Trailing Stop?**
After TP1 is hit on a multi-TP trade, the stop loss on the remaining positions automatically "trails" the market price, locking in more profit as the trade moves in your favor.

### When Does It Activate?
- Only for trades with multiple TPs (TP1, TP2, TP3)
- Only AFTER TP1 is hit and closed
- Only on the REMAINING sub-trades (TP2, TP3 positions)

### How It Works (Section 4.6):

**Example: XAUUSD BUY Trade**
```
Entry: 1960.00
SL: 1950.00
TP1: 1970.00 (0.03 lots)
TP2: 1980.00 (0.03 lots)
TP3: 1990.00 (0.04 lots)

--- TP1 hits at 1970.00 ---
- Close 0.03 lots at TP1
- Set tp1_hit = True on remaining trades
- Activate trailing stop

--- Market moves to 1975.00 ---
- Trail distance for XAUUSD: 15 pips (0.15)
- New SL: 1975.00 - 0.15 = 1974.85
- Current SL: 1950.00
- 1974.85 > 1950.00 → UPDATE SL to 1974.85

--- Market moves to 1982.00 ---
- New SL: 1982.00 - 0.15 = 1981.85
- Current SL: 1974.85
- 1981.85 > 1974.85 → UPDATE SL to 1981.85

--- Market reverses to 1981.00 ---
- New SL: 1981.00 - 0.15 = 1980.85
- Current SL: 1981.85
- 1980.85 < 1981.85 → DO NOT UPDATE (never move SL worse)
```

### Trail Distances (Section 4.6):

| Symbol | Trail Distance |
|---|---|
| XAUUSD | 15 pips (0.15) |
| Forex non-JPY | 8 pips (0.0008) |
| Forex JPY pairs | 8 pips (0.08) |
| US30 | 15 points |
| USOIL | 10 pips |

### Update Frequency:
**Every 60 seconds** for all trades where `tp1_hit = True`

### Implementation Logic:
```python
async def update_trailing_stop(trade):
    """
    Called every 60 seconds for trades with tp1_hit = True
    """
    market_price = get_market_price(trade.symbol)
    trail = TRAIL_DISTANCE[trade.symbol]
    
    if trade.direction == 'BUY':
        new_sl = market_price - trail
        # Only move SL up (never down)
        if new_sl > trade.sl:
            await modify_order(trade.tl_order_id, sl=new_sl)
            db.update_trade(trade.trade_id, sl=new_sl)
            logger.info(f"[TRAIL] {trade.signal_id} SL: {trade.sl} → {new_sl}")
    
    elif trade.direction == 'SELL':
        new_sl = market_price + trail
        # Only move SL down (never up)
        if new_sl < trade.sl:
            await modify_order(trade.tl_order_id, sl=new_sl)
            db.update_trade(trade.trade_id, sl=new_sl)
            logger.info(f"[TRAIL] {trade.signal_id} SL: {trade.sl} → {new_sl}")
```

### What Needs to Be Done?
Create `backend/core/trailing_stop_updater.py`:
1. Background task running every 60 seconds
2. Query all active trades where `tp1_hit = True`
3. For each trade, calculate new trailing SL
4. Only update if new SL is better than current
5. Call TradeLocker API to modify order
6. Update database

---

## 5. WITHDRAWAL TRACKING AND MANAGEMENT

### Answer: NOT Implemented Yet ❌ (Critical Missing Feature)

**What is Withdrawal Detection?**
The bot polls TradeLocker every 5 minutes to check if the account balance has dropped (indicating a withdrawal). This is separate from trade P&L.

### Why Is This Important?
- Withdrawals affect available balance
- But they should NOT lower the risk floor
- The bot needs to detect withdrawals and update balance WITHOUT changing risk limits

### How It Works (Section 2.9):

**Balance Reconciliation Loop:**
```
Every 5 minutes:
1. Poll actual balance from TradeLocker API
2. Compare to last_synced_balance in database
3. If difference > $0.50 → investigate
4. If no trade closed to explain the difference → withdrawal detected
```

### Withdrawal Detection Logic:
```python
WITHDRAWAL_THRESHOLD = 0.50  # Ignore fluctuations < $0.50

async def reconcile_balance(account):
    """
    Runs every 5 minutes per account
    """
    actual_balance = await tl_client.get_account_balance(account.tl_account_id)
    expected_balance = account.last_synced_balance
    delta = expected_balance - actual_balance
    
    if delta > WITHDRAWAL_THRESHOLD:
        # Balance dropped externally → withdrawal
        await handle_withdrawal_detected(account, actual_balance, delta)
    
    elif actual_balance > account.current_balance + WITHDRAWAL_THRESHOLD:
        # Balance increased (deposit/correction)
        account.current_balance = actual_balance
        account.last_synced_balance = actual_balance
        db.update_account(account)
        await notify_gui(f"Balance increase: +${actual_balance - account.current_balance:.2f}", "INFO")
    
    else:
        # Normal — just sync
        account.last_synced_balance = actual_balance
        db.update_account(account)
```

### What Changes on Withdrawal? (Section 2.9)

| Field | Changes? | Reason |
|---|---|---|
| `current_balance` | ✅ YES → actual balance | Balance is genuinely lower |
| `last_synced_balance` | ✅ YES → actual balance | Sync reference |
| `highest_banked_balance` | ❌ NO | Floor never moves down |
| `daily_start_balance` | ❌ NO | Daily floor is fixed until 5pm |
| `profit_locked` | ❌ NO | Lock status unaffected |
| `initial_balance` | ❌ NO | Only changes on formal reset |

### Withdrawal vs. Formal Payout Reset:

**Withdrawal (Auto-detected):**
- You took money out mid-cycle
- Balance drops, floor stays same
- Headroom decreases
- Metrics continue tracking

**Formal Payout Reset (GUI button):**
- Blue Guardian formally restarted your account
- Everything resets: balance, floor, profit lock, cycle date
- Fresh start

### Notification on Withdrawal:
```
Withdrawal detected on Account_123: −$500.00
Balance: $4,500.00
Overall room: $300.00
Daily room: $150.00
New withdrawable: $200.00
```

### What Needs to Be Done?
Create `backend/core/balance_reconciliation.py`:
1. Background task running every 5 minutes
2. Poll all active accounts
3. Compare actual vs expected balance
4. Detect withdrawals (balance drop without closed trade)
5. Update `current_balance` and `last_synced_balance`
6. Send WARNING notification
7. Broadcast WebSocket event for GUI update

---

## 6. THE REST OF THE LOGIC IN THE SPEC

### Here's Everything Else Missing:

### A. Firepips IMPLIED_CLOSE Logic ❌
**Section:** 6.5  
**What:** When Firepips posts profit celebration messages like "TAG ME WITH YOUR PROFIT" or "MASSIVE PROFIT", close ALL profitable trades (but leave losing trades open).

**Trigger Conditions (ALL must be true):**
1. Profit announcement phrase detected
2. Open Firepips trades exist
3. At least one trade in profit
4. No explicit CLOSE_ALL in ±5 minutes window

**Keywords:**
- "TAG ME WITH YOUR PROFIT"
- "ENJOY YOUR PROFITS"
- "MASSIVE PROFIT"
- "MONEY PRINTED"
- "WE'RE IN PROFIT GUYS"
- "PROFIT TIME"
- "CASH OUT"

### B. Context Matching - Direction Validation ❌
**Section:** 4.3, 6.3  
**What:** When matching management messages by price (Level 5), validate that the new SL/TP makes sense for the trade direction.

**Rules:**
- `MODIFY_SL` on BUY: new SL must be < market price
- `MODIFY_SL` on SELL: new SL must be > market price
- `MODIFY_TP` on BUY: new TP must be > market price
- `MODIFY_TP` on SELL: new TP must be < market price

If validation fails → skip to next context level.

### C. Trade Group Management ❌
**Section:** 4.5  
**What:** When a multi-TP trade has TP1 close, detect it and activate trailing stops on remaining sub-trades.

**Logic:**
1. TradeLocker closes TP1 position
2. Bot detects closure via polling/webhook
3. Set `tp1_hit = True` on remaining sub-trades (TP2, TP3)
4. Activate trailing stop updater for those trades

### D. Channel Priority & Concurrent Limit ❌
**Section:** 2.12  
**What:** Limit total open trades per account. If limit reached, queue signals by channel priority.

**Rules:**
- Max concurrent trades from risk profile (default 5)
- If `open_trades < max` → execute immediately
- If `open_trades == max` → queue by channel priority
- Lower priority number = higher priority
- BillirichyFX: priority 1
- Firepips: priority 2
- Queued signals expire after 30 minutes

### E. Consistency Score Integration ❌
**Section:** 2.10  
**What:** Track best single-day P&L and calculate consistency score (20% rule).

**Already Done:**
- ✅ Calculator exists in `backend/risk/consistency.py`
- ✅ Database fields exist

**Missing:**
- Update `cycle_best_day_pnl` at each 5pm reset
- Display in GUI

### F. Profitable Days Tracking ❌
**Section:** 2.13  
**What:** Track profitable days (P&L ≥ 0.25% of initial balance) in rolling 30-day window.

**Already Done:**
- ✅ `profitable_days` table exists

**Missing:**
- Insert row at each 5pm reset
- Calculate rolling 30-day count
- Display in GUI
- Warn when < 3 days remaining

### G. Channel Subscription Enforcement ❌
**Section:** 2.4, 2.5  
**What:** Filter accounts by channel subscription before executing trades.

**Already Done:**
- ✅ `channel_subscriptions` table exists

**Missing:**
- Check subscription in `execute_on_all_accounts()`
- Skip accounts with `enabled = False` for that channel
- GUI toggles per account

### H. Formal Payout Reset ❌
**Section:** 2.11.5  
**What:** GUI button to reset all account metrics after formal payout from Blue Guardian.

**Resets:**
- `initial_balance` = new balance
- `current_balance` = new balance
- `highest_banked_balance` = new balance
- `profit_locked` = False
- `daily_start_balance` = new balance
- `last_synced_balance` = new balance
- `daily_pnl` = 0
- `cycle_start_date` = today
- `cycle_best_day_pnl` = 0

### I. Dry-Run Mode ❌
**Section:** 2.16  
**What:** Test mode that simulates everything without placing real orders.

**Features:**
- Environment variable: `DRY_RUN=true`
- Log order placements instead of executing
- Populate database normally
- Simulate P&L
- Display "DRY-RUN MODE" banner in GUI

---

## SUMMARY OF YOUR QUESTIONS:

1. **Autonomous execution?** → YES, it's Phase 6. Partially done (EOD close ✅), but 15min/1h/2h/4h timers missing ❌

2. **15-minute waiting room?** → Already implemented ✅, but needs fix for duplicate bare signals ❌

3. **Re-entries?** → Partially implemented ✅, but 7-level parent matching needs enhancement ❌

4. **Trailing stops?** → NOT implemented ❌. Needs background task running every 60 seconds to update SL after TP1 hit.

5. **Withdrawal tracking?** → NOT implemented ❌. Needs balance reconciliation every 5 minutes to detect withdrawals and update balance without changing floors.

6. **Rest of the logic?** → 8 more missing features listed above (IMPLIED_CLOSE, direction validation, trade groups, channel priority, consistency score, profitable days, channel subscriptions, payout reset, dry-run mode).

---

**NEXT STEP:** Review the `COMPREHENSIVE_GAP_ANALYSIS.md` file for the complete list of all 30+ missing features organized by priority.

---

**END OF ANSWERS**
