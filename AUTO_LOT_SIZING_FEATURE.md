# Auto Lot Sizing Feature

## Overview
Automatically adjusts trade lot sizes to fit within available risk budget instead of rejecting trades.

## How It Works

### Before (Old Behavior)
```
Signal arrives → Calculate risk → Risk exceeds max → ❌ REJECT TRADE
```

### After (New Behavior)
```
Signal arrives → Calculate risk → Risk exceeds max → ✅ AUTO-ADJUST lot size to fit
```

## Algorithm

### Step 1: Calculate Available Risk Budget
```python
max_risk_per_trade = balance × max_risk_per_trade_pct / 100
active_trades_risk = sum(all active trades' risk_usd)
available_risk = max_risk_per_trade - active_trades_risk
```

### Step 2: Calculate Risk with Intended Lot Size
```python
intended_lot_size = lot_size_override or calculated_from_profile
risk_per_lot = calculate_usd_risk(..., lot_size=1.0)
intended_risk = intended_lot_size × risk_per_lot
```

### Step 3: Auto-Adjust if Needed
```python
if intended_risk > available_risk:
    # Risk exceeds available budget
    adjusted_lot_size = available_risk / risk_per_lot
    final_lot_size = round_to_lot_step(adjusted_lot_size, lot_step)
    # Execute with adjusted lot size
else:
    # Within budget
    final_lot_size = intended_lot_size
    # Execute normally
```

## Example Scenarios

### Scenario A: Risk Exceeds (Auto-Adjust)
- Balance: $10,000
- Max risk per trade: 1% = $100
- Active trades risk: $30
- **Available risk: $70**
- Signal lot size: 0.50
- Risk per lot: $240
- Intended risk: 0.50 × $240 = **$120** (exceeds!)
- **Auto-adjusted to: 0.29 lots** (risk = $69.60)
- ✅ Trade executed with 0.29 lots

### Scenario B: Risk Within Limit
- Balance: $10,000
- Max risk per trade: 1% = $100
- Active trades risk: $0
- **Available risk: $100**
- Signal lot size: 0.50
- Risk per lot: $240
- Intended risk: 0.50 × $240 = **$120** (exceeds!)
- **Auto-adjusted to: 0.41 lots** (risk = $98.40)
- ✅ Trade executed with 0.41 lots

### Scenario C: Multiple Active Trades
- Balance: $10,000
- Max risk per trade: 1% = $100
- Active trades: 2 trades using $60 total risk
- **Available risk: $40**
- Signal lot size: 0.50
- Risk per lot: $240
- Intended risk: 0.50 × $240 = **$120** (exceeds!)
- **Auto-adjusted to: 0.16 lots** (risk = $38.40)
- ✅ Trade executed with 0.16 lots

### Scenario D: No Adjustment Needed
- Balance: $10,000
- Max risk per trade: 2% = $200
- Active trades risk: $50
- **Available risk: $150**
- Signal lot size: 0.50
- Risk per lot: $240
- Intended risk: 0.50 × $240 = **$120** (within limit!)
- **Uses original: 0.50 lots** (no adjustment)
- ✅ Trade executed with 0.50 lots

## Key Features

### 1. Respects Lot Size Override
- If account has `lot_size_override` set, system tries to use it
- Only adjusts down if risk exceeds available budget
- Never increases lot size beyond override

### 2. Accurate Lot Step Rounding
- Rounds adjusted lot size to broker's `lot_step` (e.g., 0.01)
- Prevents decimal issues that could cause order rejection
- Examples:
  - Calculated: 0.416666... → Rounded: 0.41 (lot_step=0.01)
  - Calculated: 0.291666... → Rounded: 0.29 (lot_step=0.01)
  - Calculated: 0.047... → Rounded: 0.04 (lot_step=0.01)

### 3. Accounts for Active Trades
- Subtracts risk from existing open positions
- Ensures total portfolio risk stays within limits
- Dynamic adjustment based on current exposure

### 4. Never Rejects (Unless Impossible)
- Always tries to fit trade within available risk
- Only fails if available risk < minimum trade size
- Provides detailed logging for transparency

## Implementation Details

### Modified Function
```
_execute_on_account() in backend/core/trade_executor.py
```

### New Function
```
_auto_adjust_lot_size_for_risk() in backend/core/trade_executor.py
```

### Flow Integration
1. Calculate intended lot size (from override or profile)
2. **NEW**: Call `_auto_adjust_lot_size_for_risk()`
3. Use adjusted lot size for execution
4. Risk validation (should now always pass)
5. Execute trade

### Logging
System logs detailed information when adjustment occurs:
```
[ACCT:KEY] AUTO-ADJUSTED: 0.50 → 0.29 lots 
(risk $120.00 → $69.60, available $70.00)
```

## Benefits

1. ✅ **Never misses trades** - trades execute at reduced size instead of rejection
2. ✅ **Maximizes available risk** - uses as much as possible without exceeding
3. ✅ **Respects risk limits** - maintains strict risk management
4. ✅ **Dynamic adjustment** - adapts to current portfolio state
5. ✅ **Transparent** - detailed logging shows all adjustments

## Configuration

No additional configuration needed. Feature uses existing settings:
- `max_risk_per_trade_pct` from risk profile
- `lot_size_override` from account settings
- `lot_step` from broker instrument specs

## Testing Recommendations

1. Test with different active trade counts
2. Test with various lot_size_override values
3. Test with different max_risk_per_trade_pct settings
4. Verify logging output is clear and accurate
5. Check that adjusted lot sizes are properly rounded
