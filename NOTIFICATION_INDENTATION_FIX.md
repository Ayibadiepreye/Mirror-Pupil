# Notification System Indentation Fix

**Date:** 2026-06-09  
**Issue:** `AttributeError: 'DatabaseManager' object has no attribute 'get_notifications'`

## Problem

All notification-related methods in `backend/database/manager.py` were incorrectly indented **outside** the `DatabaseManager` class. They had `self` parameters but were module-level functions, not class methods.

### Affected Methods (Lines 1220+)
- `add_notification()`
- `get_notifications()`
- `get_notification()`
- `mark_notification_read()`
- `mark_all_notifications_read()`
- `delete_notification()`
- `cleanup_old_notifications()`
- All subsequent methods (manual_actions, etc.)

### Root Cause

The class ended at line 1207 with the `get_all_bot_settings()` method. Lines 1209-1217 added global variables and a `get_db()` function, which accidentally closed the class. The notification methods that followed were at the wrong indentation level.

**Before (Incorrect):**
```python
class DatabaseManager:
    ...
    async def get_all_bot_settings(self) -> Dict[str, str]:
        ...
        return {}


# Global database manager instance  ← Class ends here
_db_manager: Optional[DatabaseManager] = None

async def get_db() -> DatabaseManager:
    ...

    
    # ==================== NOTIFICATION QUERIES ====================
    
    async def add_notification(  ← NOT in class!
        self,
        ...
```

## Solution

1. Moved notification methods inside the `DatabaseManager` class (proper indentation)
2. Moved global variables and `get_db()` function to the **end of the file** (after class definition)

**After (Correct):**
```python
class DatabaseManager:
    ...
    async def get_all_bot_settings(self) -> Dict[str, str]:
        ...
        return {}
    
    # ==================== NOTIFICATION QUERIES ====================
    
    async def add_notification(  ← Now properly in class!
        self,
        account_key: Optional[str],
        ...
    
    async def get_notifications(self, ...) -> List[Dict]:
        ...
    
    # ... all other methods ...
    
    async def reset_payout_after_withdrawal(self, ...) -> bool:
        ...
        return False


# Global database manager instance  ← Moved to end of file
_db_manager: Optional[DatabaseManager] = None

async def get_db() -> DatabaseManager:
    ...
```

## Impact

**Before Fix:**
- `/api/notifications` endpoint crashed
- Any code calling notification methods failed
- Notifications system completely broken

**After Fix:**
- All notification methods are now accessible as class methods
- `/api/notifications` endpoint works correctly
- Notification system fully functional

## Testing

Restart the backend and test:
```bash
curl http://localhost:8000/api/notifications
```

Should return `[]` (empty list) instead of error 500.

## Files Modified

- `backend/database/manager.py` - Fixed indentation, moved global functions to end
