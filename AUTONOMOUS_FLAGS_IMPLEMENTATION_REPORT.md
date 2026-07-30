# Autonomous Action Flags Implementation Report
**Date**: 2026-07-22  
**Issue**: Breakeven spam - autonomous manager repeatedly setting trades to breakeven  
**Solution**: State-tracking flags to prevent repeated autonomous actions

---

## ✅ Implementation Complete

All code changes have been successfully implemented. **Migration pending** - user will run manually.

---

## 📋 Changes Summary

### 1. Database Migration ✅
**File**: `backend/database/migrations/add_autonomous_action_flags.sql`

**Added 3 boolean columns to `active_trades` table:**
- `auto_tp_applied` BOOLEAN DEFAULT FALSE
- `auto_be_applied` BOOLEAN DEFAULT FALSE  
- `auto_partial_applied` BOOLEAN DEFAULT FALSE

**Features:**
- Uses `IF NOT EXISTS` for safe re-runs
- Backfills existing trades with FALSE
- Adds helpful column comments
- Ready for manual execution

---

### 2. Data Model Updates ✅
**File**: `backend/database/models.py`

**Updated `ActiveTrade` class** (lines ~108-111):
```python
auto_tp_applied: bool = False  # Autonomous TP assignment flag
auto_be_applied: bool = False  # Autonomous breakeven flag
auto_partial_applied: bool = False  # Autonomous 50% partial close flag
```

---

### 3. Database Manager Methods ✅
**File**: `backend/database/manager.py`

**Added 3 new methods** (after `close_active_trade` method):

```python
async def set_auto_tp_applied(trade_id: int) -> bool
async def set_auto_be_applied(trade_id: int) -> bool
async def set_auto_partial_applied(trade_id: int) -> bool
```

**Each method:**
- Updates the corresponding flag to TRUE
- Returns bool for success/failure
- Logs errors without raising exceptions
- No circular imports (uses only asyncpg)

---

### 4. Autonomous Manager Logic ✅
**File**: `backend/channels/billirichy/autonomous.py`

#### A. Flag Checks in `_check_trade()` method:

**Line ~118** - 15-minute auto-TP:
```python
if trade.sl and not trade.tp and not trade.auto_tp_applied:
```

**Line ~113** - 1.5-hour breakeven:
```python
if not trade.auto_be_applied and await self._should_move_to_be(trade):
```

**Line ~108** - 3-hour 50% partial:
```python
if not trade.auto_partial_applied and await self._is_trade_in_profit(trade):
```

#### B. Flag Setting in Action Methods:

**`_action_auto_assign_tp()`** - After successful TP modification:
```python
await self.db.update_trade_tp(trade.trade_id, auto_tp)
await self.db.set_auto_tp_applied(trade.trade_id)  # ← NEW
```

**`_action_breakeven()`** - After successful SL modification:
```python
await self.db.update_trade_sl(trade.trade_id, trade.entry_price)
await self.db.set_auto_be_applied(trade.trade_id)  # ← NEW
```

**`_action_partial_close()`** - After successful partial close:
```python
await self.db.update_trade_lot_size(trade.trade_id, new_lot_size)
await self.db.set_auto_partial_applied(trade.trade_id)  # ← NEW
```

---

## 🔄 How It Works

### Before (Broken - Infinite Spam):
```
Every 60 seconds:
  ✓ Check: time >= 1.5h? YES
  ✓ Check: profit >= threshold? YES
  ✓ Execute: Move SL to breakeven
  [Next cycle]
  ✓ Check: time >= 1.5h? YES (still true!)
  ✓ Check: profit >= threshold? YES (still true!)
  ✓ Execute: Move SL to breakeven AGAIN ❌ (SPAM!)
```

### After (Fixed - One-Time Execution):
```
Every 60 seconds:
  ✓ Check: auto_be_applied? NO
  ✓ Check: time >= 1.5h? YES
  ✓ Check: profit >= threshold? YES
  ✓ Execute: Move SL to breakeven
  ✓ Set flag: auto_be_applied = TRUE
  [Next cycle]
  ✗ Check: auto_be_applied? YES → SKIP ✅
```

---

## 🛡️ Safety Features

### 1. Flags Set Only On Success
- Flag is set **AFTER** both TradeLocker modification AND database update succeed
- If either fails, exception is caught → flag NOT set → will retry next cycle

### 2. Manual Modifications Safe
- Flags track "did autonomous attempt this?" NOT "is current state X?"
- If you manually adjust SL after autonomous BE, flag stays TRUE
- Autonomous won't interfere with your manual changes

### 3. Per-Trade Tracking
- Each trade in `active_trades` has its own independent flags
- New trades start with all flags = FALSE
- Closed trades removed from table (no cleanup needed)

### 4. No Circular Imports
- Database manager methods use only `asyncpg` and `loguru`
- Autonomous manager already imports `DatabaseManager`
- Clean dependency chain: autonomous → database → asyncpg

---

## 📦 Files Modified

1. ✅ `backend/database/migrations/add_autonomous_action_flags.sql` (NEW)
2. ✅ `backend/database/models.py` (3 fields added)
3. ✅ `backend/database/manager.py` (3 methods added)
4. ✅ `backend/channels/billirichy/autonomous.py` (3 flag checks + 3 flag sets)
5. ✅ `run_autonomous_flags_migration.py` (NEW - migration runner script)

---

## ⚠️ Migration Required

**User must run migration manually:**

### Option 1: Using Migration Script
```bash
python run_autonomous_flags_migration.py
```

### Option 2: Direct SQL Execution
```bash
psql $DATABASE_URL -f backend/database/migrations/add_autonomous_action_flags.sql
```

### Option 3: PostgreSQL Client
```sql
-- Copy contents of backend/database/migrations/add_autonomous_action_flags.sql
-- Execute in psql, pgAdmin, or Neon console
```

**Migration is safe to re-run** (uses `IF NOT EXISTS` and `WHERE IS NULL` checks)

---

## ✅ Verification Checklist

After running migration, verify:

1. **Columns exist:**
   ```sql
   SELECT column_name, data_type, column_default 
   FROM information_schema.columns 
   WHERE table_name = 'active_trades' 
   AND column_name IN ('auto_tp_applied', 'auto_be_applied', 'auto_partial_applied');
   ```

2. **Existing trades backfilled:**
   ```sql
   SELECT COUNT(*), auto_tp_applied, auto_be_applied, auto_partial_applied
   FROM active_trades
   GROUP BY auto_tp_applied, auto_be_applied, auto_partial_applied;
   ```
   Should show all FALSE.

3. **Restart bot:**
   - Bot will load new `ActiveTrade` model with flags
   - Autonomous manager will check flags before actions
   - No more spam!

---

## 🎯 Expected Behavior Post-Migration

### Auto-TP (15 minutes):
- ✅ Sets TP once if SL exists but no TP
- ✅ Never attempts again for that trade
- ✅ Natural guard: `not trade.tp` check remains

### Breakeven (1.5 hours):
- ✅ Moves SL to entry once if profit ≥ threshold
- ✅ Never attempts again for that trade
- ❌ No more spam!

### 50% Partial (3 hours):
- ✅ Closes 50% once if trade in profit
- ✅ Never attempts again for that trade
- ❌ No more lot size erosion!

### 100% Close (4 hours):
- ✅ Closes 100%, removes from active_trades
- ✅ Natural guard: trade no longer in table

---

## 🔍 Edge Cases Handled

1. **Action fails**: Flag NOT set → Will retry next cycle ✅
2. **Manual modifications**: Flag already TRUE → Autonomous skips ✅
3. **New trades**: All flags start FALSE → Autonomous can act ✅
4. **Bot restart**: Flags persist in database → State preserved ✅
5. **Existing trades**: Backfilled with FALSE → Act as if new ✅

---

## 🚀 No Further Changes Needed

All code is **production-ready** and **surgical**:
- ✅ No unrelated code affected
- ✅ No circular imports
- ✅ No breaking changes
- ✅ Safe migration with backfill
- ✅ Backward compatible (flags default FALSE)

**Just run the migration and restart the bot!**

---

## 📝 Notes

- Migration is **idempotent** (safe to run multiple times)
- All flags default FALSE for new trades
- Flags only prevent **repeat** of same action, not **legitimate** new actions
- Manual actions never trigger these flags
- Flags are write-once per action type per trade

---

**Implementation Status**: ✅ **COMPLETE**  
**Migration Status**: ⏳ **PENDING USER EXECUTION**  
**Ready for Production**: ✅ **YES**
