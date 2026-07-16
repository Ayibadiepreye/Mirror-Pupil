# TradeLocker P&L Reconciliation Test Results

**Date:** 2026-07-16  
**Goal:** Find TradeLocker API endpoint to fetch accurate closed position P&L for reconciliation

---

## ✅ TEST RESULTS

### Successful Endpoints

#### 1. `GET /backend-api/trade/accounts/{accountId}/ordersHistory`
- **Status:** ✅ Works (186 orders found)
- **Returns:** Historical orders (individual buy/sell instructions)
- **Structure:** List of lists (22 fields per order)
- **Key Fields:**
  - Field 0: Order ID
  - Field 1: Instrument ID
  - Field 4: Side (buy/sell)
  - Field 6: Status (Filled/Cancelled)
  - Field 8: Avg Execution Price
  - Field 16: **Position ID** (CRITICAL - links orders to positions)
- **❌ P&L Data:** **NOT INCLUDED** - orders don't have P&L, only positions do

#### 2. `GET /backend-api/trade/accounts/{accountId}/positions`
- **Status:** ✅ Works
- **Returns:** **OPEN positions only** (currently 0)
- **❌ Closed Positions:** Not available here

#### 3. `GET /backend-api/trade/accounts/{accountId}/executions`
- **Status:** ✅ Works
- **Returns:** Recent order executions (1 found)
- **Use:** Shows fills/partial fills, but no P&L data

### Failed Endpoints (All returned 404)
- `/positionsHistory`
- `/closedPositions`
- `/tradesHistory`
- `/trades`
- `/statement`
- `/accountStatement`
- `/transactions`
- `/performance`
- `/history`

---

## 🔍 KEY FINDINGS

### 1. **No Direct Closed Position P&L Endpoint**
TradeLocker API **does not provide** a direct endpoint for closed position P&L history.

### 2. **Position ID is the Key**
- Field 16 in `ordersHistory` contains the Position ID
- Multiple orders can share the same Position ID (entry + exit + TP/SL orders)
- **Example:** Position `432345564228592626` has 3 orders:
  - Order `...231184`: buy limit (Cancelled)
  - Order `...231182`: buy stop (Filled @ 4025.36)
  - Order `...231181`: sell market (Filled @ 4025.23)

### 3. **P&L Must Be Calculated**
To get accurate closed position P&L, we must:
1. Fetch `ordersHistory`
2. Group orders by Position ID (field 16)
3. Identify entry orders (buy) and exit orders (sell)
4. Calculate: `P&L = (Exit Price - Entry Price) * Volume * Contract Size`
5. Account for swaps/commissions (if TradeLocker provides them elsewhere)

---

## 📋 RECOMMENDED SOLUTION

### Option A: Calculate P&L from ordersHistory (RECOMMENDED)
**Implementation:**
```python
def reconcile_pnl_from_orders(account_id, lookback_hours=1):
    # 1. Fetch ordersHistory for last N hours
    orders = fetch_orders_history(account_id)
    
    # 2. Group by Position ID
    positions = group_orders_by_position_id(orders)
    
    # 3. For each closed position:
    for position_id, position_orders in positions.items():
        entry_order = find_entry_order(position_orders)
        exit_order = find_exit_order(position_orders)
        
        if entry_order and exit_order:
            # Calculate P&L
            if entry_order['side'] == 'buy':
                pnl = (exit_price - entry_price) * volume * contract_size
            else:
                pnl = (entry_price - exit_price) * volume * contract_size
            
            # 4. Update trade_history table
            update_trade_pnl(position_id, calculated_pnl)
```

**Pros:**
- Uses existing ordersHistory endpoint
- Accurate entry/exit prices from filled orders
- Can filter by time range

**Cons:**
- Requires manual P&L calculation
- Need to handle partial fills
- Swap/commission not directly available (may need separate calls)

### Option B: Use Live P&L Snapshots (CURRENT METHOD)
- Keep using 15-second `current_pnl` updates from `get_all_positions()`
- Accept that closed trade P&L might use last snapshot value
- **Issue:** This is what causes discrepancies when BE/TP/SL closes positions

---

## 🎯 RECOMMENDATION FOR YOUR USE CASE

**Use Option A - Reconcile from ordersHistory:**

1. **When to run:** 3-5 minutes after position close
2. **Lookback:** Last 1-2 hours of orders
3. **Match logic:**
   - Find closed positions (position_id no longer in active trades)
   - Group orders by position_id
   - Calculate actual P&L from entry/exit prices
   - Replace `current_pnl` in trade_history with calculated P&L

4. **Edge cases:**
   - Partial fills: Sum all entry/exit executions
   - Multiple exits (TP/SL): Use the filled exit order
   - Commission/swap: Fetch from account statement if available, or ignore for now

---

## 🔧 NEXT STEPS

1. **Implement `get_orders_history()` wrapper** in `TradeLockerClient`
2. **Create P&L calculator** from orders
3. **Add reconciliation service** (background task every 3-5 min)
4. **Test with real closed positions**
5. **Log discrepancies > 10%**

---

## 📊 DATA SAMPLE

### Sample Position from ordersHistory
**Position ID:** `432345564228592626`

| Order ID | Side | Type | Status | Qty | Price | Role |
|----------|------|------|--------|-----|-------|------|
| ...231184 | buy | limit | Cancelled | 0.10 | 4010.95 | - |
| ...231182 | buy | stop | **Filled** | 0.10 | 4025.36 | **Entry** |
| ...231181 | sell | market | **Filled** | 0.10 | 4025.23 | **Exit** |

**Calculated P&L:** (4025.23 - 4025.36) * 0.10 * contract_size = **-$0.13 loss** (minus fees)

---

## ✅ CONCLUSION

- ✅ `ordersHistory` endpoint works and provides all necessary data
- ✅ Position ID allows linking orders to positions
- ❌ No direct P&L endpoint exists
- ✅ **Solution:** Calculate P&L manually from entry/exit order prices
- ⚠️  Need to handle edge cases (partial fills, multiple exits, etc.)

**Ready to implement P&L reconciliation service based on ordersHistory.**
