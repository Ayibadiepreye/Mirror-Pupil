# Mirror Pupil v5.1 - Comprehensive Gap Analysis

**Date:** Context Transfer Session  
**Status:** Complete spec review completed  
**Purpose:** Identify ALL missing features and timing corrections before Phase 6

---

## ✅ COMPLETED PHASES (1-5)

### Phase 1: Telegram Client ✅
- Pytdbot/TDLib implementation
- Anti-ban features (random delays, mark as read, typing indicators)
- Auto-reconnect with exponential backoff
- Health check loop (30s)
- Multi-channel support

### Phase 2: Signal Parser System ✅
- Channel plugin architecture
- BillirichyFX parser (25+ symbols, 10+ management actions)
- Firepips parser (15+ symbols, 10+ management actions)
- Waiting room logic (15-minute expiry)
- Re-entry detection
- Duplicate prevention (message cache)

### Phase 3: TradeLocker Integration ✅
- Rate-limited wrapper (5 req/s)
- Circuit breaker (3 failures → 120s cooldown)
- Retry logic (3 attempts with exponential backoff)
- Instrument caching (5-minute TTL)
- AccountManager (multi-credential, sub-account discovery, token refresh 23h)
- TradeExecutor (ParsedSignal → TradeLocker order)

### Phase 4: Database Layer (Neon PostgreSQL) ✅
- Complete schema (10 tables, v5)
- DatabaseManager with asyncpg connection pooling
- 40+ query helper methods
- Background cleanup tasks
- Built-in data (2 channels, 1 risk profile)

### Phase 5: Risk Management System ✅
- RiskCalculator (price delta, floor/room calculations, profit lock)
- RiskEnforcer (pre-trade validation, breach monitoring 60s)
- DailyResetHandler (5pm EST daily reset)
- EODCloseHandler (4:45pm EST force close)
- ConsistencyScoreCalculator (20% rule)

### Phase 5.5: Trade Executor Database Recording ✅
- Trades recorded in `active_trades` immediately after placement
- Status handling: 'pending', 'filled', 'partially_filled', 'failed'
- Channel_id tracking for all trades
- Risk validation before execution

---

## 🔴 CRITICAL TIMING CORRECTIONS (MUST FIX IMMEDIATELY)

### 1. Pending Order Monitor Timing ❌
**Current:** Check every 30 seconds  
**Spec:** Check every **10 minutes** (600 seconds)  
**File:** `backend/core/pending_order_monitor.py`  
**Fix:** Change `poll_interval = 600`

### 2. Pending Order Expiry ❌
**Current:** Cancel after 24 hours  
**Spec:** Cancel after **2 hours** (for BOTH channels)  
**File:** `backend/core/pending_order_monitor.py`  
**Fix:** Change `order_expiry_hours = 2`

### 3. Message Cache Cleanup ❌
**Current:** Clean every 2 minutes  
**Spec:** Clean every **30 seconds**  
**File:** `backend/database/manager.py`  
**Fix:** Change cleanup interval to 30 seconds

### 4. Balance Reconciliation - MISSING ❌
**Spec:** Poll TradeLocker balance every **5 minutes** per account  
**Purpose:** Detect withdrawals and balance changes  
**File:** Need to create `backend/core/balance_reconciliation.py`  
**Details:**
- Compare actual balance vs `last_synced_balance`
- Detect withdrawals (balance drop > $0.50 without closed trade)
- Update `current_balance` and `last_synced_balance`
- **DO NOT** update `highest_banked_balance` on withdrawal
- **DO NOT** update `daily_start_balance` on withdrawal
- Send WARNING notification with new headroom
- Broadcast WebSocket event for GUI update

### 5. Trailing Stop Updates - MISSING ❌
**Spec:** Update trailing stops every **60 seconds** for trades with `tp1_hit = True`  
**File:** Need to create `backend/core/trailing_stop_updater.py`  
**Details:**
- Only for trades where `tp1_hit = True`
- Trail distances:
  - XAUUSD: 15 pips (0.15)
  - Forex non-JPY: 8 pips (0.0008)
  - Forex JPY: 8 pips (0.08)
  - US30: 15 points
  - USOIL: 10 pips
- Only move SL in favorable direction (never worse)

---

## 🟡 PHASE 6: AUTONOMOUS MANAGEMENT LOGIC (MISSING)

### BillirichyFX Autonomous Actions
**File:** Need to create `backend/channels/billirichy/autonomous.py`

| Time Since Entry | Condition | Action | Status |
|---|---|---|---|
| 15 minutes | SL present, no TP | Auto-assign TP = entry ± 2× SL distance | ❌ Missing |
| 1 hour | No TP hit; profit ≥ 15 pips (XAUUSD) or 8 pips (forex) | Move SL to BE | ❌ Missing |
| 2 hours | No management update; trade in profit | Close 50% | ❌ Missing |
| 4 hours | No management update | Close remaining 100% | ❌ Missing |
| 4:45 PM EST daily | Any open trade | Force close all (EOD) | ✅ Implemented |
| Friday 4:45 PM EST | Any open trade | Force close all (weekend) | ✅ Implemented |

### Firepips Autonomous Actions
**File:** Need to create `backend/channels/firepips/autonomous.py`

| Time Since Entry | Condition | Action | Status |
|---|---|---|---|
| 1 hour | Trade in profit (floating P&L > 0) | Move SL to BE | ❌ Missing |
| 2 hours | Trade in profit | Close 50% | ❌ Missing |
| 4 hours | Any state | Force close remaining | ❌ Missing |
| 4:45 PM EST daily | Any open trade | Force close all (EOD) | ✅ Implemented |
| Friday 4:45 PM EST | Any open trade | Force close all (weekend) | ✅ Implemented |

**Implementation Requirements:**
- Background scheduler checking all active trades
- Track `last_management_time` per trade
- Check trade age and conditions
- Execute autonomous actions via TradeExecutor
- Log all autonomous actions with reason
- Send INFO notifications to GUI

---

## 🟡 MISSING FEATURES FROM SPEC

### 1. Withdrawal Detection & Balance Reconciliation ❌
**Section:** 2.9  
**Status:** NOT IMPLEMENTED  
**Priority:** HIGH  
**Details:**
- Poll every 5 minutes per account
- Compare `actual_balance` vs `last_synced_balance`
- Threshold: $0.50 (ignore smaller fluctuations)
- On withdrawal detected:
  - Update `current_balance` to actual
  - Update `last_synced_balance` to actual
  - **DO NOT** change `highest_banked_balance`
  - **DO NOT** change `daily_start_balance`
  - **DO NOT** change `profit_locked` status
  - Send WARNING notification
  - Broadcast WebSocket event
- Handle balance increases (deposits/corrections)

### 2. Consistency Score (20% Rule) ❌
**Section:** 2.10  
**Status:** PARTIALLY IMPLEMENTED (calculator exists, but not tracked/displayed)  
**Priority:** MEDIUM  
**Details:**
- Formula: `(cycle_best_day_pnl / cycle_total_pnl) × 100`
- Status thresholds:
  - < 15%: Safe (Green)
  - 15-20%: Warning (Amber)
  - ≥ 20%: Breach risk (Red)
- Update `cycle_best_day_pnl` at each 5pm reset
- Display in GUI account card
- **Already implemented in:** `backend/risk/consistency.py`
- **Missing:** Integration with daily reset and GUI display

### 3. Channel Priority & Concurrent Trade Limit ❌
**Section:** 2.12  
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Details:**
- Max concurrent trades from risk profile (default 5)
- Per-account override via `max_concurrent_trades_override`
- Priority logic:
  - If `open_trades < max`: execute immediately
  - If `open_trades == max`: queue by channel priority (lower int = higher priority)
  - Queued signals expire after 30 minutes
- BillirichyFX default priority: 1
- Firepips default priority: 2

### 4. Profitable Days Tracking ❌
**Section:** 2.13  
**Status:** PARTIALLY IMPLEMENTED (table exists, but not fully tracked)  
**Priority:** MEDIUM  
**Details:**
- Rolling 30 calendar days
- Day boundary: 5pm ET
- Profitable day: P&L ≥ 0.25% of `initial_balance`
- Paused day: P&L = $0 (not profitable)
- GUI warning: < 3 profitable days remaining in 30-day window
- **Already implemented:** `profitable_days` table exists
- **Missing:** Daily insertion at 5pm reset, GUI display

### 5. Error Notification System ❌
**Section:** 2.14  
**Status:** PARTIALLY IMPLEMENTED (notify_gui function exists, but severity levels not fully used)  
**Priority:** LOW  
**Details:**
- Severity levels: INFO, WARNING, HIGH, CRITICAL
- GUI actions per severity:
  - INFO: Log only
  - WARNING: Yellow banner/toast
  - HIGH: Orange persistent alert
  - CRITICAL: Red persistent banner + sound alert
- WebSocket broadcast for real-time notifications
- **Already implemented:** Basic notify_gui function
- **Missing:** Full severity handling in GUI

### 6. Dry-Run / Paper Mode ❌
**Section:** 2.16  
**Status:** NOT IMPLEMENTED  
**Priority:** LOW (for testing)  
**Details:**
- Environment variable: `DRY_RUN=true`
- Replace order placement with log entries
- Populate `active_trades` normally (for management matching)
- Simulate P&L using mid-price
- Display "DRY-RUN MODE" banner in GUI
- Risk breach checks still run

### 7. Formal Payout Reset ❌
**Section:** 2.11.5  
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Details:**
- GUI button to reset account metrics after formal payout
- Resets:
  - `initial_balance` = new balance
  - `current_balance` = new balance
  - `highest_banked_balance` = new balance
  - `profit_locked` = False
  - `daily_start_balance` = new balance
  - `last_synced_balance` = new balance
  - `daily_pnl` = 0
  - `cycle_start_date` = today
  - `cycle_best_day_pnl` = 0
- Display `calculate_withdrawable()` value
- Warn if entered value < `floor + payout_buffer`

### 8. Multi-Profile Risk Management System ❌
**Section:** 2.18  
**Status:** DATABASE SCHEMA EXISTS, but no GUI CRUD  
**Priority:** LOW (Phase 7 - GUI)  
**Details:**
- Create/Read/Update/Delete risk profiles via GUI
- Set default profile
- Assign profile to account
- Display profile details on account card
- Block deletion if profile is assigned to accounts
- **Already implemented:** Database schema, RiskProfile dataclass
- **Missing:** GUI pages and API endpoints

### 9. Channel Plugin Architecture - Runtime Management ❌
**Section:** 2.17  
**Status:** PLUGIN SYSTEM EXISTS, but no GUI for adding channels  
**Priority:** LOW (Phase 7 - GUI)  
**Details:**
- Add/remove channels via GUI (no code changes)
- Enable/disable channels via toggle
- Edit channel priority, display name, notes
- Select entry/management logic from dial
- Clone logic from existing channel
- Rebuild Telegram listeners on channel add/toggle
- **Already implemented:** Plugin architecture, channel registry
- **Missing:** GUI pages and API endpoints

### 10. Channel Subscriptions Per Account ❌
**Section:** 2.4, 2.5 (channel_subscriptions table)  
**Status:** DATABASE SCHEMA EXISTS, but not enforced in execution  
**Priority:** HIGH  
**Details:**
- Filter accounts by channel subscription before execution
- `channel_subscriptions` table: `(account_key, channel_id, enabled)`
- Default: all accounts subscribe to all channels
- GUI toggle per account to enable/disable specific channels
- **Already implemented:** Database table
- **Missing:** Enforcement in `execute_on_all_accounts()`, GUI toggles

### 11. Waiting Room - Second Bare Signal Handling ❌
**Section:** 3.7, 5.6  
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Details:**
- If new bare signal arrives for same symbol+direction while one is waiting
- **DO NOT** create second entry
- Reset existing entry's `expires_at` to `now + 15 minutes`
- Prevents duplicate waiting room entries

### 12. Re-entry Parent Matching (7-Level) ❌
**Section:** 3.4  
**Status:** PARTIALLY IMPLEMENTED (basic re-entry detection exists)  
**Priority:** MEDIUM  
**Details:**
- 7-level priority matching:
  1. Direct reply to trade message ID
  2. Exactly one open trade exists
  3. Symbol + direction both match
  4. Symbol matches (direction ambiguous)
  5. Direction matches (symbol ambiguous)
  6. Price decimal places match
  7. No match → skip re-entry, log warning
- Inherit SL/TP from parent if not explicit
- Auto-assign TP if parent has no active TP: `entry ± 2× SL distance`

### 13. Trade Group (Multi-TP) Management ❌
**Section:** 4.5  
**Status:** PARTIALLY IMPLEMENTED (multi-TP execution exists)  
**Priority:** MEDIUM  
**Details:**
- All sub-trades share same SL
- Management action on `signal_id` applies to ALL sub-trades
- When TP1 closes, detect via polling/webhook
- Set `tp1_hit = True` on remaining sub-trades
- Activate trailing stop on remaining sub-trades

### 14. Firepips IMPLIED_CLOSE Logic ❌
**Section:** 6.5  
**Status:** NOT IMPLEMENTED  
**Priority:** HIGH  
**Details:**
- Trigger conditions (ALL must be true):
  1. Profit announcement phrase detected
  2. Open Firepips trades exist
  3. At least one trade in profit (floating P&L > 0)
  4. No explicit CLOSE_ALL/MODIFY in ±5 minutes window
- Close **only profitable trades**
- Leave losing trades open
- Keywords: "TAG ME WITH YOUR PROFIT", "ENJOY YOUR PROFITS", "MASSIVE PROFIT", "MONEY PRINTED", "WE'RE IN PROFIT GUYS", "PROFIT TIME", "CASH OUT"

### 15. Context Matching - Direction Validation at Level 5 ❌
**Section:** 4.3, 6.3  
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Details:**
- When matching by price reference (Level 5):
  - `MODIFY_SL` on BUY: new SL must be < market price
  - `MODIFY_SL` on SELL: new SL must be > market price
  - `MODIFY_TP` on BUY: new TP must be > market price
  - `MODIFY_TP` on SELL: new TP must be < market price
- If validation fails → skip to next context level
- Prevents invalid SL/TP modifications

---

## 🟢 PHASE 7: FASTAPI BACKEND (NOT STARTED)

**Status:** NOT IMPLEMENTED  
**Priority:** LOW (after Phase 6)  
**Details:**
- FastAPI server for GUI
- WebSocket support for real-time updates
- API endpoints for:
  - Accounts CRUD
  - Channels CRUD
  - Risk Profiles CRUD
  - Channel Subscriptions
  - Active Trades
  - Trade History
  - Profitable Days
  - Notifications
  - Bot Control (pause/resume, dry-run toggle)
  - Payout Reset
- Authentication (if needed)
- CORS configuration for Telegram Web App

---

## 🟢 PHASE 8: REACT GUI (NOT STARTED)

**Status:** NOT IMPLEMENTED  
**Priority:** LOW (after Phase 7)  
**Details:**
- Telegram Web App (TWA) constraints
- Pages:
  - Dashboard (overview of all accounts)
  - Account Detail (per-account view)
  - Active Trades
  - Trade History
  - Settings (channels, risk profiles, bot control)
  - Notifications Panel
- Real-time updates via WebSocket
- Account cards with risk metrics
- Channel management table
- Risk profile editor
- Payout reset wizard
- Consistency score display
- Profitable days tracker

---

## 📋 IMPLEMENTATION PRIORITY ORDER

### IMMEDIATE (Fix Before Moving Forward)
1. ✅ **Fix Pending Order Monitor Timing** (30s → 10 minutes)
2. ✅ **Fix Pending Order Expiry** (24h → 2 hours)
3. ✅ **Fix Message Cache Cleanup** (2 min → 30 seconds)
4. ✅ **Implement Balance Reconciliation** (every 5 minutes)
5. ✅ **Implement Trailing Stop Updates** (every 60 seconds)

### PHASE 6: AUTONOMOUS MANAGEMENT (HIGH PRIORITY)
6. ⚠️ **BillirichyFX Autonomous Actions** (15min, 1h, 2h, 4h timers)
7. ⚠️ **Firepips Autonomous Actions** (1h, 2h, 4h timers)
8. ⚠️ **Channel Subscription Enforcement** (filter accounts by subscription)
9. ⚠️ **Firepips IMPLIED_CLOSE Logic**
10. ⚠️ **Trade Group Management** (multi-TP, tp1_hit tracking)

### PHASE 6.5: MISSING CORE FEATURES (MEDIUM PRIORITY)
11. ⚠️ **Re-entry Parent Matching** (7-level smart match)
12. ⚠️ **Context Matching Direction Validation** (Level 5 validation)
13. ⚠️ **Waiting Room Second Bare Signal** (reset expiry instead of duplicate)
14. ⚠️ **Channel Priority & Concurrent Limit** (queue management)
15. ⚠️ **Consistency Score Integration** (daily reset + GUI)
16. ⚠️ **Profitable Days Tracking** (daily insertion + GUI)
17. ⚠️ **Formal Payout Reset** (GUI button + logic)

### PHASE 7: FASTAPI BACKEND (LOW PRIORITY)
18. 🔵 **FastAPI Server Setup**
19. 🔵 **WebSocket Implementation**
20. 🔵 **API Endpoints (Accounts, Channels, Risk Profiles)**
21. 🔵 **API Endpoints (Trades, History, Notifications)**
22. 🔵 **Bot Control Endpoints**

### PHASE 8: REACT GUI (LOW PRIORITY)
23. 🔵 **React App Setup (TWA)**
24. 🔵 **Dashboard Page**
25. 🔵 **Account Detail Page**
26. 🔵 **Settings Page**
27. 🔵 **Notifications Panel**
28. 🔵 **Real-time Updates (WebSocket)**

---

## 📊 SUMMARY

### Completed: 5 Phases
- Phase 1: Telegram Client ✅
- Phase 2: Signal Parsers ✅
- Phase 3: TradeLocker Integration ✅
- Phase 4: Database Layer ✅
- Phase 5: Risk Management ✅

### Critical Fixes Needed: 5 Items
1. Pending order check interval (30s → 10min)
2. Pending order expiry (24h → 2h)
3. Message cache cleanup (2min → 30s)
4. Balance reconciliation (MISSING - every 5min)
5. Trailing stop updates (MISSING - every 60s)

### Phase 6 (Autonomous Management): 10 Items
- BillirichyFX autonomous actions (4 timers)
- Firepips autonomous actions (3 timers)
- Channel subscription enforcement
- Firepips IMPLIED_CLOSE
- Trade group management

### Missing Core Features: 12 Items
- Re-entry parent matching
- Context matching validation
- Waiting room duplicate handling
- Channel priority & concurrent limit
- Consistency score integration
- Profitable days tracking
- Formal payout reset
- Withdrawal detection
- And 5 more...

### Phase 7 (FastAPI): Not Started
### Phase 8 (React GUI): Not Started

---

## 🎯 RECOMMENDED NEXT STEPS

1. **User Approval:** Get user confirmation on priority order
2. **Fix Critical Timings:** Implement 5 immediate fixes (items 1-5)
3. **Test Critical Fixes:** Verify timing corrections work properly
4. **Implement Phase 6:** Autonomous management logic (items 6-10)
5. **Test Phase 6:** Run in dry-run mode for 3 days
6. **Implement Phase 6.5:** Missing core features (items 11-17)
7. **Test Phase 6.5:** Comprehensive testing
8. **Move to Phase 7:** FastAPI backend (when user is ready)
9. **Move to Phase 8:** React GUI (final phase)

---

**END OF GAP ANALYSIS**
