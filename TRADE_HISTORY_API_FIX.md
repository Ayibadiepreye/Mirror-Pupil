# Trade History API Response Format Fix

**Date:** 2026-06-09  
**Issue:** React Query error: "Query data cannot be undefined" on trade history page

## Problem

**API Contract Mismatch** between frontend expectations and backend reality.

**Frontend Expected:**
```json
{
  "trades": [...],
  "total": 123
}
```

**Backend Actually Returns:**
```json
[{...}, {...}, ...]  // Just an array
```

### Error Details

**Console Error:**
```
@tanstack_react-query.js:1312 Query data cannot be undefined. 
Please make sure to return a value other than undefined from your query function. 
Affected query key: ["trade-history","all"]
```

**Why:**
- Frontend: `http.get<{ trades, total }>(...).then(r => r.data.trades)`
- Backend: Returns `List[TradeHistoryResponse]` (array, not object)
- Result: `r.data.trades` is `undefined` because `r.data` IS the array

## Solution

Fixed both web and mobile frontends to handle backend's array response correctly.

### Web Frontend Fix

**File:** `Lovable Frontend/src/lib/mp/api.ts`

**Before:**
```typescript
history: (params) =>
  http.get<{ trades: TradeHistory[]; total: number }>("/api/trades/history", { params })
    .then(r => r.data),  // ❌ Expects {trades, total}

historyAll: (params) =>
  http.get<{ trades: TradeHistory[]; total: number }>("/api/trades/history", ...)
    .then(r => r.data.trades),  // ❌ Tries to access .trades
```

**After:**
```typescript
history: (params) =>
  http.get<TradeHistory[]>("/api/trades/history", { params })
    .then(r => ({ trades: r.data, total: r.data.length })),  // ✅ Wraps array

historyAll: (params) =>
  http.get<TradeHistory[]>("/api/trades/history", ...)
    .then(r => r.data),  // ✅ Returns array directly
```

### Flutter Mobile Fix

**File:** `Lovable Frontend/export/mobile/lib/api/api_client.dart`

**Before:**
```dart
Future<({List<TradeHistory> trades, int total})> tradeHistory(...) async {
  final r = await _send('GET', '/api/trades/history', ...) as Map<String, dynamic>;
  return (
    trades: (r['trades'] as List).map((j) => TradeHistory.fromJson(j)).toList(),
    total: r['total'] as int,  // ❌ Expects {trades, total}
  );
}
```

**After:**
```dart
Future<({List<TradeHistory> trades, int total})> tradeHistory(...) async {
  final r = await _send('GET', '/api/trades/history', ...) as List;  // ✅ Cast to List
  final trades = r.map((j) => TradeHistory.fromJson(j)).toList();
  return (trades: trades, total: trades.length);  // ✅ Wraps array
}
```

## Impact

**Before:**
- Trade history page crashed with React Query error
- No trades displayed
- Console error about undefined data

**After:**
- Trade history page loads correctly
- All trades displayed with proper formatting
- No console errors
- Flutter app also fixed to match

## Testing

1. Restart frontend dev server
2. Navigate to Trade History page
3. Should see trades (if any exist in database)
4. No console errors

## Files Changed

1. `Lovable Frontend/src/lib/mp/api.ts` - Fixed web API client
2. `Lovable Frontend/export/mobile/lib/api/api_client.dart` - Fixed Flutter API client
