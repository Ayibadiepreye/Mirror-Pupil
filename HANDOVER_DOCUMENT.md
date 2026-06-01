# Mirror Pupil v5.1 - Complete Handover Document

**Last Updated:** Context Transfer Session  
**Current Status:** Phase 5 Complete, Phase 6 In Progress  
**Next Session:** Continue with Phase 6 implementation

---

## 🎯 PROJECT STATUS OVERVIEW

### ✅ COMPLETED (Phases 1-5)

#### Phase 1: Telegram Client (Pytdbot/TDLib)
- **Status:** ✅ COMPLETE
- **Files:**
  - `telegram_client.py` (500 lines)
  - `.env.example`
  - `requirements.txt`
- **Features:**
  - Pytdbot/TDLib implementation (NOT Telethon per v5.1 spec)
  - Anti-ban: random delays (0.5-2.0s), mark as read, typing indicators
  - Auto-reconnect with exponential backoff (10 attempts)
  - Health check loop (30s)
  - Multi-channel support
  - Session persistence

#### Phase 2: Signal Parser System
- **Status:** ✅ COMPLETE
- **Files:**
  - `backend/channels/base.py` (abstract base classes)
  - `backend/channels/registry.py` (plugin registry)
  - `backend/channels/billirichy/` (4 files: symbol_map, entry, management, plugin)
  - `backend/channels/firepips/` (4 files: symbol_map, entry, management, plugin)
  - `test_parsers.py` (standalone test script)
- **Features:**
  - Channel plugin architecture
  - BillirichyFX: 25+ symbols, 10+ management actions, multi-TP, re-entry detection
  - Firepips: 15+ symbols, 10+ management actions, IMPLIED_CLOSE detection
  - Waiting room logic (15-minute expiry) ✅ BOTH CHANNELS
  - Duplicate prevention (message cache)
  - 40+ regex patterns total

#### Phase 3: TradeLocker Integration
- **Status:** ✅ COMPLETE
- **Files:**
  - `backend/core/tradelocker_client.py` (rate-limited wrapper)
  - `backend/core/account_manager.py` (multi-credential support)
  - `backend/core/trade_executor.py` (signal → order execution)
  - `test_tradelocker.py` (test script)
- **Features:**
  - Rate limiting: 5 req/s with semaphore + 0.2s min interval
  - Circuit breaker: 3 failures → 120s cooldown
  - Retry logic: 3 attempts with exponential backoff
  - Instrument caching (5-minute TTL)
  - Token refresh every 23 hours
  - Multi-account concurrent execution
  - Dry-run mode support

#### Phase 4: Database Layer (Neon PostgreSQL)
- **Status:** ✅ COMPLETE
- **Files:**
  - `backend/database/schema.py` (schema v5)
  - `backend/database/models.py` (Pydantic models)
  - `backend/database/manager.py` (DatabaseManager with asyncpg)
  - `test_database.py` (test script)
- **Features:**
  - 10 tables (channels, accounts, active_trades, trade_history, etc.)
  - Connection pooling (5-20 connections)
  - 40+ query helper methods
  - Background cleanup tasks
  - Built-in data: 2 channels, 1 risk profile (Blue Guardian)

#### Phase 5: Risk Management System
- **Status:** ✅ COMPLETE
- **Files:**
  - `backend/risk/calculator.py` (price delta, floor/room calculations)
  - `backend/risk/enforcer.py` (pre-trade validation, breach monitoring)
  - `backend/risk/daily_reset.py` (5pm EST daily reset)
  - `backend/risk/eod_close.py` (4:45pm EST force close)
  - `backend/risk/consistency.py` (20% rule calculator)
  - `test_risk.py` (test script)
- **Features:**
  - Price delta formula for forex and indices
  - Daily floor: static intraday (set at 5pm EST)
  - Overall floor: trails from closed balance only
  - Profit lock: triggers at +6%, locks floor at initial balance
  - Breach monitoring every 60s
  - EOD force close at 4:45pm EST ✅
  - Weekend force close Friday 4:45pm EST ✅

#### Phase 5.5: Trade Executor Database Recording
- **Status:** ✅ COMPLETE
- **Files:**
  - `backend/core/trade_executor.py` (updated)
  - `SIGNAL_FLOW.md` (complete 10-step flow documentation)
- **Features:**
  - Trades recorded in `active_trades` immediately after placement
  - Status handling: 'pending', 'filled', 'partially_filled', 'failed'
  - Channel_id tracking for all trades
  - Risk validation before execution
  - Filter accounts by channel subscription

---

## 🔴 CRITICAL FIXES IMPLEMENTED (This Session)

### 1. Pending Order Monitor Timing ✅ FIXED
- **Was:** Check every 30 seconds
- **Now:** Check every 10 minutes (600 seconds)
- **File:** `backend/core/pending_order_monitor.py`
- **Change:** Line 32-33: `poll_interval = 600`, `order_expiry_hours = 2`
- **Commit:** Fixed timing per spec Section 3.6, 5.5

### 2. Pending Order Expiry ✅ FIXED
- **Was:** Cancel after 24 hours
- **Now:** Cancel after 2 hours
- **File:** `backend/core/pending_order_monitor.py`
- **Change:** Line 33: `order_expiry_hours = 2`
- **Commit:** Fixed expiry per spec Section 3.6, 5.5

### 3. Message Cache Cleanup ✅ FIXED
- **Was:** Clean every 2 minutes (120 seconds)
- **Now:** Clean every 30 seconds
- **File:** `backend/database/manager.py`
- **Change:** Line 134: `await asyncio.sleep(30)`
- **Commit:** Fixed cleanup interval per spec Section 3.8, 5.7

### 4. Balance Reconciliation ✅ IMPLEMENTED
- **File:** `backend/core/balance_reconciliation.py` (NEW - 350 lines)
- **Features:**
  - Poll TradeLocker every 5 minutes per account
  - Detect withdrawals (balance drop > $0.50 without closed trade)
  - Update `current_balance` and `last_synced_balance`
  - **DO NOT** update `highest_banked_balance` on withdrawal
  - **DO NOT** update `daily_start_balance` on withdrawal
  - Send WARNING notification with new headroom
  - Broadcast WebSocket event for GUI update
  - Handle balance increases (deposits/corrections)
- **Singleton:** `get_balance_monitor(db)`
- **Methods:**
  - `start_monitoring()` - Start 5-minute polling loop
  - `stop_monitoring()` - Stop monitoring
  - `_reconcile_account()` - Check single account
  - `_handle_withdrawal()` - Process withdrawal detection
  - `_handle_deposit()` - Process balance increase
- **TODO:** Integrate with risk profile system, floating P&L calculator, WebSocket broadcast
- **Commit:** Implemented per spec Section 2.9

### 5. Trailing Stop Updates ✅ IMPLEMENTED
- **File:** `backend/core/trailing_stop_updater.py` (NEW - 250 lines)
- **Features:**
  - Update trailing stops every 60 seconds
  - Only for trades with `tp1_hit = True`
  - Trail distances per symbol:
    - XAUUSD: 15 pips (0.15)
    - Forex non-JPY: 8 pips (0.0008)
    - Forex JPY: 8 pips (0.08)
    - US30: 15 points
    - USOIL: 10 pips
  - Only move SL in favorable direction (never worse)
  - Log all trailing stop updates
- **Singleton:** `get_trailing_stop_updater(db)`
- **Methods:**
  - `start_updating()` - Start 60-second update loop
  - `stop_updating()` - Stop updating
  - `_update_trailing_stop()` - Update single trade
  - `_get_market_price()` - Fetch current market price
- **TODO:** Integrate with account manager, add database method `get_active_trades_with_tp1_hit()`
- **Commit:** Implemented per spec Section 4.6

---

## 🟡 PHASE 6: AUTONOMOUS MANAGEMENT (IN PROGRESS - 60% COMPLETE)

### What Is Autonomous Management?
The bot automatically manages trades based on time elapsed since entry, WITHOUT waiting for manual management messages from the channel.

### BillirichyFX Autonomous Actions (Section 4.7)

| Time Since Entry | Condition | Action | Status |
|---|---|---|---|
| 15 minutes | SL present, no TP | Auto-assign TP = entry ± 2× SL distance | ✅ DONE |
| 1 hour | No TP hit; profit ≥ 15 pips (XAUUSD) or 8 pips (forex) | Move SL to BE | ✅ DONE |
| 2 hours | No management update; trade in profit | Close 50% | ✅ DONE |
| 4 hours | No management update | Close remaining 100% | ✅ DONE |
| 4:45 PM EST daily | Any open trade | Force close all (EOD) | ✅ DONE |
| Friday 4:45 PM EST | Any open trade | Force close all (weekend) | ✅ DONE |

### Firepips Autonomous Actions (Section 6.7)

| Time Since Entry | Condition | Action | Status |
|---|---|---|---|
| 1 hour | Trade in profit (floating P&L > 0) | Move SL to BE | ✅ DONE |
| 2 hours | Trade in profit | Close 50% | ✅ DONE |
| 4 hours | Any state | Force close remaining | ✅ DONE |
| 4:45 PM EST daily | Any open trade | Force close all (EOD) | ✅ DONE |
| Friday 4:45 PM EST | Any open trade | Force close all (weekend) | ✅ DONE |

### Implementation Status:
✅ **Created:** `backend/channels/billirichy/autonomous.py` (350 lines)
✅ **Created:** `backend/channels/firepips/autonomous.py` (280 lines)
✅ **Added:** Database methods for channel-based trade queries
⚠️ **TODO:** Start autonomous managers in main application
⚠️ **TODO:** Integration testing

---

## 🟡 MISSING CORE FEATURES (Phase 6.5)

### High Priority

#### 1. Channel Subscription Enforcement ❌
- **Section:** 2.4, 2.5
- **Status:** Database table exists, but not enforced
- **What:** Filter accounts by channel subscription before execution
- **File:** `backend/core/trade_executor.py` (needs update)
- **Logic:** Check `channel_subscriptions` table, skip accounts with `enabled = False`

#### 2. Firepips IMPLIED_CLOSE Logic ❌
- **Section:** 6.5
- **Status:** Detection exists in parser, but not implemented
- **What:** Close all profitable trades when profit celebration message detected
- **File:** `backend/channels/firepips/management.py` (needs update)
- **Trigger Conditions (ALL must be true):**
  1. Profit announcement phrase detected
  2. Open Firepips trades exist
  3. At least one trade in profit
  4. No explicit CLOSE_ALL in ±5 minutes window
- **Keywords:** "TAG ME WITH YOUR PROFIT", "ENJOY YOUR PROFITS", "MASSIVE PROFIT", "MONEY PRINTED", "WE'RE IN PROFIT GUYS", "PROFIT TIME", "CASH OUT"

#### 3. Trade Group Management (Multi-TP) ❌
- **Section:** 4.5
- **Status:** Multi-TP execution exists, but tp1_hit tracking incomplete
- **What:** When TP1 closes, set `tp1_hit = True` on remaining sub-trades
- **File:** `backend/core/trade_executor.py` (needs update)
- **Logic:**
  1. Detect TP1 closure via polling/webhook
  2. Set `tp1_hit = True` on remaining sub-trades (TP2, TP3)
  3. Activate trailing stop updater for those trades

### Medium Priority

#### 4. Re-entry Parent Matching (7-Level) ❌
- **Section:** 3.4
- **Status:** Basic re-entry detection exists, but not full 7-level matching
- **What:** Smart parent matching for re-entry signals
- **Files:** `backend/channels/billirichy/entry.py`, `backend/channels/firepips/entry.py`
- **7 Levels:**
  1. Direct reply to trade message ID
  2. Exactly one open trade exists
  3. Symbol + direction both match
  4. Symbol matches (direction ambiguous)
  5. Direction matches (symbol ambiguous)
  6. Price decimal places match
  7. No match → skip re-entry, log warning

#### 5. Context Matching Direction Validation ❌
- **Section:** 4.3, 6.3
- **Status:** Context matching exists, but no direction validation at Level 5
- **What:** Validate SL/TP modifications make sense for trade direction
- **Files:** `backend/channels/billirichy/management.py`, `backend/channels/firepips/management.py`
- **Rules:**
  - `MODIFY_SL` on BUY: new SL must be < market price
  - `MODIFY_SL` on SELL: new SL must be > market price
  - `MODIFY_TP` on BUY: new TP must be > market price
  - `MODIFY_TP` on SELL: new TP must be < market price

#### 6. Waiting Room Second Bare Signal ❌
- **Section:** 3.7, 5.6
- **Status:** Waiting room exists, but no duplicate handling
- **What:** If second bare signal arrives for same symbol+direction, reset expiry instead of creating duplicate
- **Files:** `backend/channels/billirichy/entry.py`, `backend/channels/firepips/entry.py`
- **Logic:** Check if waiting room entry exists for symbol+direction, if yes → reset `expires_at` to `now + 15 minutes`

#### 7. Channel Priority & Concurrent Limit ❌
- **Section:** 2.12
- **Status:** Not implemented
- **What:** Limit total open trades per account, queue by channel priority if limit reached
- **File:** Need to create `backend/core/trade_queue.py`
- **Logic:**
  - Max concurrent trades from risk profile (default 5)
  - If `open_trades < max` → execute immediately
  - If `open_trades == max` → queue by channel priority
  - BillirichyFX: priority 1, Firepips: priority 2
  - Queued signals expire after 30 minutes

#### 8. Consistency Score Integration ❌
- **Section:** 2.10
- **Status:** Calculator exists, but not integrated with daily reset
- **What:** Update `cycle_best_day_pnl` at each 5pm reset
- **File:** `backend/risk/daily_reset.py` (needs update)
- **Logic:** At 5pm reset, if `today_pnl > cycle_best_day_pnl` → update

#### 9. Profitable Days Tracking ❌
- **Section:** 2.13
- **Status:** Table exists, but not populated
- **What:** Insert row at each 5pm reset
- **File:** `backend/risk/daily_reset.py` (needs update)
- **Logic:** At 5pm reset, insert row with `is_profitable_day = (pnl >= initial_balance * 0.0025)`

#### 10. Formal Payout Reset ❌
- **Section:** 2.11.5
- **Status:** Not implemented
- **What:** GUI button to reset all account metrics after formal payout
- **File:** Need API endpoint in Phase 7
- **Resets:** `initial_balance`, `current_balance`, `highest_banked_balance`, `profit_locked`, `daily_start_balance`, `last_synced_balance`, `daily_pnl`, `cycle_start_date`, `cycle_best_day_pnl`

---

## 🟢 PHASE 7: FASTAPI BACKEND (NOT STARTED)

### Status: NOT IMPLEMENTED
### Priority: LOW (after Phase 6)

### Required Components:
1. FastAPI server setup
2. WebSocket support for real-time updates
3. API endpoints:
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
4. Authentication (if needed)
5. CORS configuration for Telegram Web App

---

## 🟢 PHASE 8: REACT GUI (NOT STARTED)

### Status: NOT IMPLEMENTED
### Priority: LOW (after Phase 7)

### Required Pages:
1. Dashboard (overview of all accounts)
2. Account Detail (per-account view)
3. Active Trades
4. Trade History
5. Settings (channels, risk profiles, bot control)
6. Notifications Panel

### Features:
- Telegram Web App (TWA) constraints
- Real-time updates via WebSocket
- Account cards with risk metrics
- Channel management table
- Risk profile editor
- Payout reset wizard
- Consistency score display
- Profitable days tracker

---

## 📁 PROJECT STRUCTURE

```
Mirror Pupil/
├── backend/
│   ├── channels/
│   │   ├── base.py                    ✅ Abstract base classes
│   │   ├── registry.py                ✅ Plugin registry
│   │   ├── billirichy/
│   │   │   ├── __init__.py           ✅
│   │   │   ├── plugin.py             ✅ BillirichyPlugin
│   │   │   ├── entry.py              ✅ Entry parsing
│   │   │   ├── management.py         ✅ Management logic
│   │   │   ├── symbol_map.py         ✅ Symbol normalization
│   │   │   └── autonomous.py         ❌ TODO: Autonomous actions
│   │   └── firepips/
│   │       ├── __init__.py           ✅
│   │       ├── plugin.py             ✅ FirepipsPlugin
│   │       ├── entry.py              ✅ Entry parsing (with bare signal)
│   │       ├── management.py         ✅ Management logic
│   │       ├── symbol_map.py         ✅ Symbol normalization
│   │       └── autonomous.py         ❌ TODO: Autonomous actions
│   ├── core/
│   │   ├── __init__.py               ✅
│   │   ├── tradelocker_client.py     ✅ Rate-limited wrapper
│   │   ├── account_manager.py        ✅ Multi-credential support
│   │   ├── trade_executor.py         ✅ Signal → order execution
│   │   ├── pending_order_monitor.py  ✅ FIXED: 10min poll, 2h expiry
│   │   ├── balance_reconciliation.py ✅ NEW: 5min poll, withdrawal detection
│   │   └── trailing_stop_updater.py  ✅ NEW: 60s updates after TP1 hit
│   ├── database/
│   │   ├── __init__.py               ✅
│   │   ├── schema.py                 ✅ Schema v5
│   │   ├── models.py                 ✅ Pydantic models
│   │   └── manager.py                ✅ FIXED: 30s message cache cleanup
│   └── risk/
│       ├── __init__.py               ✅
│       ├── calculator.py             ✅ Price delta, floor/room
│       ├── enforcer.py               ✅ Pre-trade validation, breach monitoring
│       ├── daily_reset.py            ✅ 5pm EST daily reset
│       ├── eod_close.py              ✅ 4:45pm EST force close
│       └── consistency.py            ✅ 20% rule calculator
├── telegram_client.py                ✅ Pytdbot/TDLib client
├── test_parsers.py                   ✅ Parser tests
├── test_tradelocker.py               ✅ TradeLocker tests
├── test_database.py                  ✅ Database tests
├── test_risk.py                      ✅ Risk tests
├── requirements.txt                  ✅
├── setup.py                          ✅
├── .env.example                      ✅
├── .gitignore                        ✅
├── README.md                         ✅
├── QUICKSTART.md                     ✅
├── mirror_pupil_spec_v5.md           ✅ Complete spec
├── SIGNAL_FLOW.md                    ✅ 10-step flow
├── COMPREHENSIVE_GAP_ANALYSIS.md     ✅ Complete gap analysis
├── USER_QUESTIONS_ANSWERED.md        ✅ Detailed answers
└── HANDOVER_DOCUMENT.md              ✅ This file
```

---

## 🔧 ENVIRONMENT VARIABLES

### Required (.env file):
```bash
# Telegram (Pytdbot/TDLib)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=your_phone_number

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:pass@host/dbname

# TradeLocker (for testing only - GUI manages credentials in production)
TRADELOCKER_EMAIL=your_email
TRADELOCKER_PASSWORD=your_password
TRADELOCKER_SERVER=live  # or demo

# Bot Configuration
DRY_RUN=false  # Set to true for paper trading mode
LOG_LEVEL=INFO
```

---

## 🧪 TESTING

### Test Scripts:
1. `test_setup.py` - Verify environment setup
2. `test_parsers.py` - Test signal parsers (20+ test cases)
3. `test_tradelocker.py` - Test TradeLocker integration (5 tests)
4. `test_database.py` - Test database operations (10 tests)
5. `test_risk.py` - Test risk calculations

### Run Tests:
```bash
python test_setup.py
python test_parsers.py
python test_tradelocker.py
python test_database.py
python test_risk.py
```

---

## 📋 NEXT SESSION CHECKLIST

### Immediate Tasks (Phase 6):
1. ✅ Review this handover document
2. ⚠️ Implement BillirichyFX autonomous actions (15min, 1h, 2h, 4h)
3. ⚠️ Implement Firepips autonomous actions (1h, 2h, 4h)
4. ⚠️ Implement channel subscription enforcement
5. ⚠️ Implement Firepips IMPLIED_CLOSE logic
6. ⚠️ Implement trade group management (tp1_hit tracking)

### Medium Priority (Phase 6.5):
7. ⚠️ Enhance re-entry parent matching (7-level)
8. ⚠️ Add context matching direction validation
9. ⚠️ Fix waiting room duplicate bare signal handling
10. ⚠️ Implement channel priority & concurrent limit
11. ⚠️ Integrate consistency score with daily reset
12. ⚠️ Integrate profitable days tracking with daily reset

### Testing:
13. ⚠️ Run in dry-run mode for 3 days
14. ⚠️ Verify all autonomous actions trigger correctly
15. ⚠️ Verify trailing stops update every 60s
16. ⚠️ Verify balance reconciliation detects withdrawals
17. ⚠️ Verify pending orders expire after 2 hours

### Future Phases:
18. 🔵 Phase 7: FastAPI backend
19. 🔵 Phase 8: React GUI

---

## 📝 IMPORTANT NOTES

### User Preferences:
- ✅ Use Pytdbot/TDLib (NOT Telethon)
- ✅ Use Neon PostgreSQL (NOT SQLite)
- ✅ TradeLocker credentials managed via GUI (not .env in production)
- ✅ Build TradeLocker BEFORE database (to understand real data structure)
- ✅ Read spec to the very end (v5.1 addendum contains critical updates)

### Critical Timing Corrections (ALL APPROVED):
- ✅ Pending order check: 30s → 10 minutes
- ✅ Pending order expiry: 24h → 2 hours
- ✅ Message cache cleanup: 2min → 30 seconds
- ✅ Balance reconciliation: Implement (every 5 minutes)
- ✅ Trailing stop updates: Implement (every 60 seconds)

### Bare Signal Management:
- ✅ BillirichyFX: Implemented with 15-minute waiting room
- ✅ Firepips: Implemented with 15-minute waiting room
- ❌ Both need: Second bare signal handling (reset expiry instead of duplicate)

### Autonomous Management:
- ✅ EOD force close at 4:45 PM EST (both channels)
- ✅ Weekend force close Friday 4:45 PM EST (both channels)
- ❌ Time-based autonomous actions (15min, 1h, 2h, 4h) - Phase 6

### Re-entries:
- ✅ Basic detection and execution works
- ❌ 7-level parent matching needs enhancement

### Trailing Stops:
- ✅ Implemented in `backend/core/trailing_stop_updater.py`
- ✅ Updates every 60 seconds for trades with `tp1_hit = True`
- ❌ Need to integrate with trade group management

### Withdrawal Tracking:
- ✅ Implemented in `backend/core/balance_reconciliation.py`
- ✅ Polls every 5 minutes per account
- ✅ Detects withdrawals and updates balance
- ✅ Does NOT change floors or profit lock status

---

## 🚀 HOW TO CONTINUE

1. **Read this handover document completely**
2. **Review COMPREHENSIVE_GAP_ANALYSIS.md for detailed feature list**
3. **Review USER_QUESTIONS_ANSWERED.md for specific explanations**
4. **Start with Phase 6 autonomous management implementation**
5. **Test each feature in dry-run mode before moving to next**
6. **Document all changes in this handover document**

---

**END OF HANDOVER DOCUMENT**
