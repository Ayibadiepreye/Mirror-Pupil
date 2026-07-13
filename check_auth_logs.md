# Steps to Diagnose "No TradeLocker Client" Issue

## Step 1: Verify Account in Database

Run this SQL command on your PostgreSQL server:

```sql
-- Copy and paste this into psql
SELECT 
    account_key, 
    credential_key, 
    tl_email, 
    tl_server, 
    tl_prop_firm,
    display_name,
    paused,
    breached
FROM accounts 
WHERE account_key = 'owidavid2002@gmail.com:2329061';
```

**Expected result:** 1 row showing the account details

## Step 2: Check Channel Subscriptions

```sql
SELECT 
    cs.account_key,
    c.display_name as channel_name,
    c.channel_id,
    cs.enabled
FROM channel_subscriptions cs
JOIN channels c ON cs.channel_id = c.channel_id
WHERE cs.account_key = 'owidavid2002@gmail.com:2329061';
```

**Expected result:** Should show BillirichyFX subscription with enabled=TRUE

If NO rows returned, add subscription with:

```sql
INSERT INTO channel_subscriptions (account_key, channel_id, enabled)
VALUES ('owidavid2002@gmail.com:2329061', -1001859598768, TRUE);
```

## Step 3: Restart Backend and Check Startup Logs

**CRITICAL:** After account is in database, you MUST restart the backend to load the credential.

1. Stop the backend process
2. Start it again
3. Watch the startup logs carefully for these lines:

**Look for SUCCESS:**
```
✓ Loaded credential: owidavid2002@gmail.com
  ✓ Discovered sub-account: 2329061 (ID: 2329061, Balance: $X,XXX.XX)
✓ Loaded 2 credential(s) into AccountManager
```

**Look for FAILURE:**
```
✗ Failed to load credential: owidavid2002@gmail.com
✗ Error loading credential owidavid2002@gmail.com: Authentication failed (400, "Incorrect email or password")
```

OR

```
✗ Error loading credential owidavid2002@gmail.com: Cannot connect to host demo.tradelocker.com
```

## Step 4: Diagnosis Based on Logs

### If you see "Failed to load credential" with authentication error:
- **Problem:** TradeLocker credentials are incorrect
- **Solution:** Double-check the email/password for the CLRTYFX demo server
- **Action:** Delete account from database and re-add with correct credentials

### If you see DNS/connection errors:
- **Problem:** Network issue reaching demo.tradelocker.com
- **Solution:** Check internet connection, firewall, or wait and retry

### If you see "Loaded credential" successfully:
- **Problem:** Was a timing issue, now resolved
- **Solution:** Account should work now. Check for new trades in logs.

## Step 5: Test Trade Execution

Once backend starts successfully and shows "Loaded credential: owidavid2002@gmail.com":

1. Check if balance reconciliation works:
   - Watch logs for: `Balance reconciled: owidavid2002@gmail.com:2329061`
   - Should NOT see: `No TradeLocker client for owidavid2002@gmail.com:2329061`

2. Wait for a signal from BillirichyFX channel
   - Watch for: `Processing signal from BillirichyFX`
   - Should see: Trade execution attempts for BOTH accounts

## Step 6: Frontend Race Condition (Optional Fix)

The "duplicate key" error you saw is cosmetic - the account DOES get added despite the error popup.

**Why it happens:**
- Frontend sends multiple requests when you click "Add Account"
- First request succeeds, second gets duplicate key error

**To fix (optional):**
- Would need to modify frontend to prevent double-submission
- Or modify backend to return 200 OK for duplicate keys instead of error
- Not urgent since the account is actually added successfully
