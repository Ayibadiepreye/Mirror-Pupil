# Flutter App Fixes - Mirror Pupil

## Issues Fixed

### Issue #1: Sign-up Button Calls Sign-in
**Problem:** The sign-up button was calling `signInWithPassword` instead of creating a new account, causing "invalid credentials" errors for new users.

**Solution:**
1. Added `signUpWithPassword` method to `auth_service.dart` that uses Firebase's `createUserWithEmailAndPassword`
2. Updated `login_screen.dart` to call the appropriate method based on the `_signup` state

**Files Changed:**
- `lib/auth/auth_service.dart` - Added `signUpWithPassword()` method
- `lib/screens/login_screen.dart` - Updated button to conditionally call signup or signin

### Issue #2: Infinite Loading After Login
**Problem:** After successful login, the dashboard shows infinite loading because API requests fail with 403 Forbidden (user not approved).

**Root Cause:**
- New users are auto-created in the database on first login via `/api/users/me`
- However, they are created with `is_approved = FALSE` by default
- The `get_current_user` dependency in `firebase_auth.py` checks for approval and blocks unapproved users
- This causes all dashboard API calls to fail with 403 errors

**Solution Applied:**
- Improved error handling in `dashboard_screen.dart` to show actual error messages instead of infinite loading
- Now shows a clear error message with a retry button when API calls fail

**Additional Solution Needed:**
Users need to be approved before they can use the app. Options:
1. Set `is_approved = TRUE` by default for new users (auto-approve)
2. Keep approval required but show a "pending approval" screen instead of dashboard
3. Have admin approve users via backend or admin panel

## Testing Steps

1. **Test Sign-up:**
   - Open app
   - Click "Sign up" tab
   - Enter new email and password
   - Should create Firebase account successfully

2. **Test Sign-in:**
   - Click "Sign in" tab
   - Enter existing credentials
   - Should log in successfully

3. **Test Dashboard:**
   - After login, if user is not approved:
     - Should see error message: "Account pending admin approval"
   - After admin approves user:
     - Dashboard should load with accounts, trades, bot status, etc.

## Approval Workflow

To approve a user, run on the backend:

```python
py update_admin_users.py
```

Or manually via SQL:

```sql
UPDATE users 
SET is_approved = TRUE 
WHERE email = 'user@example.com';
```

Or via the admin approval API:

```bash
POST /api/users/{user_id}/approve
```

## Auto-Approve Option

If you want all users to be auto-approved, modify `backend/database/manager.py`:

```python
async def create_user(self, user_id: str, email: str, display_name: str = None, 
                     is_super_admin: bool = False) -> dict:
    # Change is_approved to TRUE
    result = await self.pool.fetchrow(
        """
        INSERT INTO users (user_id, email, display_name, is_super_admin, is_approved)
        VALUES ($1, $2, $3, $4, TRUE)  -- Changed from FALSE to TRUE
        ON CONFLICT (user_id) DO UPDATE
        SET display_name = EXCLUDED.display_name
        RETURNING *
        """,
        user_id, email, display_name, is_super_admin
    )
```
