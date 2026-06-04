# TLAPI Async/Await Fix - June 4, 2026

## Problem

The application was experiencing errors when calling TradeLocker API methods:

```
object DataFrame can't be used in 'await' expression
```

This error occurred in `backend/core/tradelocker_client.py` in the `_retry_call` method.

## Root Cause

The TLAPI SDK methods are **synchronous** (blocking), not asynchronous. They return DataFrames directly:

```python
# ❌ TLAPI methods are sync
df = client.get_all_accounts()  # Returns DataFrame immediately

# NOT async:
df = await client.get_all_accounts()  # ❌ This fails!
```

The `_retry_call` method was trying to `await` these synchronous functions directly:

```python
async def _retry_call(self, func, *args, **kwargs):
    result = await func(*args, **kwargs)  # ❌ func is sync, not async!
```

This causes the event loop to block and throws the "can't be used in 'await' expression" error.

## Solution

Wrap all synchronous TLAPI calls with `asyncio.to_thread()` to run them in a thread pool without blocking the event loop.

### Changes Made

1. **Added thread pool helper function** (line 28):

```python
async def _to_thread_with_timeout(func, *args, timeout: float = 10.0, **kwargs):
    """Run a sync function in asyncio's thread pool with a hard timeout."""
    return await asyncio.wait_for(
        asyncio.to_thread(func, *args, **kwargs),
        timeout=timeout
    )
```

2. **Updated `_retry_call` method** (line 209):

```python
async def _retry_call(self, func, *args, **kwargs):
    """
    Retry a function call with exponential backoff.
    3 attempts: 1s → 2s → 4s delays.
    
    Note: TLAPI methods are synchronous, so we run them in a thread pool
    to avoid blocking the event loop.
    """
    for attempt in range(self.retry_attempts):
        try:
            # ✅ Run sync TLAPI method in thread pool
            result = await _to_thread_with_timeout(
                func, *args, timeout=10.0, **kwargs
            )
            self._record_success()
            return result
        except Exception as e:
            # ... retry logic ...
```

## How It Works

The execution chain:

1. `get_all_accounts()` → calls `_call_api("get_all_accounts")`
2. `_call_api()` → calls `_retry_call(method)`
3. `_retry_call()` → calls `_to_thread_with_timeout(method)` ✅
4. `_to_thread_with_timeout()` → runs sync `method()` in thread pool
5. Returns DataFrame back up the chain

## Impact

- **Fixed file**: `backend/core/tradelocker_client.py`
- **Scope**: All TLAPI method calls are now properly wrapped
- **Other files**: No changes needed - they all use the TradeLockerClient wrapper correctly

## Testing

After this fix, operations like:
- Account discovery (`/api/accounts/discover`)
- Getting positions
- Creating/modifying orders
- Fetching market prices

Should all work without the "object DataFrame can't be used in 'await' expression" error.

## Why This Pattern

| Aspect | TLAPI SDK | Expected |
|--------|-----------|----------|
| Method type | Synchronous (blocking) | Async (non-blocking) |
| Return value | DataFrame immediately | Coroutine to await |
| Call syntax | `df = client.get_all_accounts()` | `df = await client.get_all_accounts()` |
| Threading | Blocks event loop ❌ | Non-blocking ✅ |

**Solution**: Use `asyncio.to_thread()` to run sync methods in a thread pool, preventing event loop blocking.

## References

This pattern is used in similar projects (e.g., Mirror Pupil) that integrate synchronous SDKs into async applications.
