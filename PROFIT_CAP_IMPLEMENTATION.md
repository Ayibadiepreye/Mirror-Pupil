# PROFIT CAP FEATURE - IMPLEMENTATION COMPLETE

## OVERVIEW
Profit cap feature for prop firm compliance (e.g., Blue Guardian). Automatically closes all trades and freezes account when profit exceeds a configurable threshold above initial balance.

## WHAT IT DOES (SIMPLE)

**Starting Point:**
- When you add an account, `initial_balance` is stored (e.g., $5,000)
- This baseline NEVER changes (locked forever)

**Setting the Cap:**
- Choose cap type: **Percentage** (e.g., 5%) OR **Dollar** (e.g., $250)
- Set safety buffer: Default 2% (triggers slightly before exact cap)

**How It Calculates:**
```
Total Value = Current Balance + All Open Trades P&L
Current Profit = Total Value - Initial Balance

If cap_type == 'percentage':
    Cap Threshold = Initial Balance × (1 + cap_value/100)
else:  # dollar
    Cap Threshold = Initial Balance + cap_value

Buffered Threshold = Cap Threshold × (1 - buffer_pct/100)

IF Total Value ≥ Buffered Threshold → TRIGGER CAP BREACH
```

**Example (Blue Guardian):**
- Initial Balance: $5,000
- Profit Cap: $214 (dollar)
- Buffer: 2%
- Threshold: $5,214
- Buffered Threshold: $5,209.72

**When Balance + Open P&L ≥ $5,210:**
1. All trades closed immediately (including pending orders)
2. Account frozen (rejects all new trades)
3. Notification sent
4. Requires manual unfreeze to resume trading

**Key Points:**
- ✅ Drawdowns don't affect cap - always measured from initial $5,000
- ✅ If balance drops to $4,500, cap is still $5,214 (not recalculated)
- ✅ Includes open trades P&L in calculation (not just closed balance)
- ✅ Check runs every **10 seconds** for tight control

---

## IMPLEMENTATION DETAILS

### Phase 1: Database Schema ✅
**Files Modified:**
- `backend/database/schema.py` - Added 5 profit cap columns to accounts table
- `backend/database/migrations/add_profit_cap.sql` - Migration SQL
- `backend/database/models.py` - Updated Account model
- `backend/database/manager.py` - Added helper methods + migration logic

**New Database Fields:**
- `profit_cap_enabled` (BOOLEAN, default FALSE)
- `profit_cap_type` (TEXT, 'percentage' or 'dollar')
- `profit_cap_value` (REAL, percentage or dollar amount)
- `profit_cap_buffer_pct` (REAL, default 2.0)
- `profit_cap_frozen` (BOOLEAN, default FALSE)

**New Database Methods:**
- `update_account_profit_cap()` - Configure profit cap settings
- `set_account_profit_cap_frozen()` - Freeze/unfreeze account

### Phase 2: Risk Enforcer ✅
**Files Modified:**
- `backend/risk/enforcer.py`

**New Components:**
- `_profit_cap_monitoring_loop()` - Dedicated 10-second check loop (faster than breach monitoring)
- `_check_profit_cap()` - Core cap breach detection logic

**Algorithm:**
1. Skip if account is paused, breached, or already frozen
2. Skip if profit cap not enabled
3. Validate initial_balance > 0, cap_type and cap_value present
4. Get current equity from TradeLocker
5. Sum all active trades `current_pnl` (updated every 15s by PnL updater)
6. Calculate: `total_value = current_equity + open_pnl`
7. Calculate cap threshold based on type (percentage vs dollar)
8. Apply safety buffer
9. If breached:
   - Set `profit_cap_frozen = True`
   - Send notification
   - Close ALL trades via `_close_all_account_trades()`

**Monitoring:**
- Breach monitoring: Every 60 seconds (daily/overall loss limits)
- Profit cap monitoring: Every 10 seconds (tighter control)

### Phase 3: Trade Executor ✅
**Files Modified:**
- `backend/core/trade_executor.py`

**Change:**
- Added check in `_execute_on_account()` method
- Rejects trade if `account_db.profit_cap_frozen == True`
- Returns clear rejection message

### Phase 4: API Endpoints ✅
**Files Modified:**
- `backend/api/routes/accounts.py`

**New Request Models:**
- `ProfitCapUpdate` - Configure profit cap settings

**New Endpoints:**

**1. POST /accounts/{account_key}/profit-cap**
- Configure profit cap settings
- **Validations:**
  - initial_balance must be > 0
  - cap_type must be 'percentage' or 'dollar'
  - cap_value must be > 0
  - buffer_pct must be 0-100
  - **OPTION 2:** Current profit must be BELOW cap (blocks if already exceeded)
- Returns: Updated AccountResponse

**2. POST /accounts/{account_key}/unfreeze-profit-cap**
- Manually unfreeze account after profit cap breach
- Validates account is actually frozen
- Returns: Updated AccountResponse

**Updated Response Model:**
- `AccountResponse` - Added 5 profit cap fields

### Phase 5: Frontend UI (NOT YET IMPLEMENTED)
**File to Modify:**
- `Lovable Frontend/export/mobile/lib/screens/accounts_screen.dart`

**Required UI Components:**
1. Profit Cap section in account settings
2. Toggle: Enable/Disable
3. Dropdown: Type (Percentage / Dollar)
4. Input: Cap value
5. Input: Safety buffer %
6. Status indicator: Show enabled/frozen state
7. **Unfreeze button** (only visible when frozen)
8. Visual warning when account is frozen

---

## EDGE CASES HANDLED

### 1. Race Conditions ✅
- **Issue:** Profit cap check every 10s, but trades execute instantly
- **Solution:** 10-second interval + safety buffer + frozen check in trade executor

### 2. Data Accuracy ✅
- **Issue:** `current_pnl` updated every 15 seconds (slightly stale)
- **Solution:** Acceptable lag with safety buffer

### 3. Account State Conflicts ✅
- **Issue:** Account breached AND profit cap triggered
- **Solution:** Skip profit cap check if `breached = True`

### 4. Configuration Validation ✅
- **Issue:** User sets cap below current profit
- **Solution:** OPTION 2 - Block with error message (must close trades first)

### 5. Invalid Inputs ✅
- **Issue:** $0 cap, negative values, invalid types
- **Solution:** API validation rejects invalid inputs

### 6. Initial Balance Changes ✅
- **Issue:** User wants to change initial_balance
- **Solution:** LOCKED - cannot change after account creation

### 7. Closing Trades Failures ✅
- **Issue:** TradeLocker API fails during close
- **Solution:** Best-effort close, log critical errors, account stays frozen

### 8. UI/UX Confusion ✅
- **Issue:** User forgets why account is frozen
- **Solution:** Clear "FROZEN: Profit Cap Exceeded" message + unfreeze button (in UI phase)

---

## API USAGE EXAMPLES

### Configure Profit Cap (Dollar)
```bash
POST /api/accounts/user@example.com:12345/profit-cap
{
  "enabled": true,
  "cap_type": "dollar",
  "cap_value": 214,
  "buffer_pct": 2.0
}
```

### Configure Profit Cap (Percentage)
```bash
POST /api/accounts/user@example.com:12345/profit-cap
{
  "enabled": true,
  "cap_type": "percentage",
  "cap_value": 5.0,
  "buffer_pct": 2.0
}
```

### Disable Profit Cap
```bash
POST /api/accounts/user@example.com:12345/profit-cap
{
  "enabled": false
}
```

### Unfreeze Account
```bash
POST /api/accounts/user@example.com:12345/unfreeze-profit-cap
```

### Error Response (Current Profit Exceeds Cap)
```json
{
  "detail": "Cannot set profit cap: Current profit $300.00 exceeds cap $250.00. Close trades or set a higher cap."
}
```

---

## TESTING CHECKLIST

### Backend Testing
- [ ] Profit cap triggers at correct threshold with buffer
- [ ] All positions close when cap triggered
- [ ] Account freezes and stays frozen
- [ ] New trades rejected when frozen
- [ ] Manual unfreeze works
- [ ] Skip checks if paused/breached
- [ ] Validation blocks invalid cap configurations
- [ ] Validation blocks setting cap below current profit
- [ ] Cap calculation correct for percentage type
- [ ] Cap calculation correct for dollar type
- [ ] Drawdowns don't affect cap calculation
- [ ] Multiple open trades P&L summed correctly

### API Testing
- [ ] POST /profit-cap creates cap successfully
- [ ] POST /profit-cap validates all inputs
- [ ] POST /profit-cap blocks if current profit > cap
- [ ] POST /unfreeze-profit-cap unfreezes account
- [ ] GET /accounts returns profit cap fields
- [ ] Unauthorized access blocked

### Frontend Testing (AFTER UI IMPLEMENTATION)
- [ ] Profit cap section visible in account settings
- [ ] Toggle enable/disable works
- [ ] Type dropdown works (percentage/dollar)
- [ ] Value input validates correctly
- [ ] Buffer input validates (0-100%)
- [ ] Status shows enabled/frozen state
- [ ] Unfreeze button only visible when frozen
- [ ] Visual warning when account frozen
- [ ] Error message shown if setting cap below current profit

---

## DEPLOYMENT NOTES

### Database Migration
The schema will automatically apply on next bot startup via `initialize_schema()` in database manager. No manual migration needed.

### Monitoring After Deployment
1. Check logs for "✓ Started profit cap monitoring (10s interval)"
2. Monitor accounts approaching cap with debug logs
3. Verify breach notifications sent correctly
4. Confirm trades close properly on breach

### Configuration Recommendations
- **Default buffer:** 2% (triggers at 98% of cap)
- **Buffer range:** 0-10% (allow user control)
- **Blue Guardian:** $214 cap on instant accounts
- **Check interval:** 10 seconds (hardcoded for safety)

---

## FILES MODIFIED

### Backend Core
1. `backend/database/schema.py` - Schema definition
2. `backend/database/models.py` - Account model
3. `backend/database/manager.py` - Helper methods + migration
4. `backend/risk/enforcer.py` - Profit cap monitoring loop
5. `backend/core/trade_executor.py` - Frozen account check
6. `backend/api/routes/accounts.py` - API endpoints

### New Files
7. `backend/database/migrations/add_profit_cap.sql` - Migration SQL
8. `PROFIT_CAP_IMPLEMENTATION.md` - This document

### Frontend (NOT YET MODIFIED)
9. `Lovable Frontend/export/mobile/lib/screens/accounts_screen.dart` - UI (TO DO)

---

## NEXT STEPS

1. **Frontend Implementation:** Add profit cap UI to accounts screen (Flutter)
2. **Testing:** Comprehensive backend and API testing
3. **VPS Deployment:** Deploy to production VPS
4. **Monitoring:** Watch profit cap checks in production logs

---

## TECHNICAL SUMMARY

**What was built:**
- Complete profit cap system for prop firm compliance
- Database schema, models, and helper methods
- 10-second monitoring loop in risk enforcer
- Trade executor integration (frozen check)
- Two API endpoints (configure + unfreeze)
- Full validation and edge case handling

**What's left:**
- Flutter UI implementation
- End-to-end testing
- Production deployment

**Key features:**
- Cap measured from locked initial_balance
- Percentage OR dollar cap types
- Configurable safety buffer
- 10-second check interval (faster than breach monitoring)
- Automatic trade closing + account freeze
- Manual unfreeze required
- Blocks setting cap below current profit (OPTION 2)
- Comprehensive validation

---

**Implementation Status:** BACKEND COMPLETE ✅  
**Next Phase:** FRONTEND UI + TESTING
**Ready for:** VPS deployment after frontend complete
