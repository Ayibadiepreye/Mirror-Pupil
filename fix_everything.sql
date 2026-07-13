-- Complete fix for owidavid2002@gmail.com:2329061 account

-- Step 1: Verify account exists (without created_at column)
SELECT 
    account_key, 
    credential_key, 
    tl_email, 
    display_name,
    paused,
    breached,
    initial_balance,
    current_balance
FROM accounts 
WHERE account_key = 'owidavid2002@gmail.com:2329061';

-- Step 2: Add the missing channel subscription
-- This is CRITICAL - without this, the account won't receive signals
INSERT INTO channel_subscriptions (account_key, channel_id, enabled)
VALUES ('owidavid2002@gmail.com:2329061', -1001859598768, TRUE);

-- Step 3: Verify subscription was added
SELECT 
    cs.account_key,
    c.display_name as channel_name,
    c.channel_id,
    cs.enabled
FROM channel_subscriptions cs
JOIN channels c ON cs.channel_id = c.channel_id
WHERE cs.account_key = 'owidavid2002@gmail.com:2329061';

-- Step 4: Add the UNIQUE constraint to prevent future errors
ALTER TABLE channel_subscriptions
ADD CONSTRAINT channel_subscriptions_account_key_channel_id_key
UNIQUE (account_key, channel_id);

-- Step 5: Verify constraint was added
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'channel_subscriptions'
AND constraint_type = 'UNIQUE';

-- Step 6: Show summary of all accounts with their subscriptions
SELECT 
    a.account_key,
    a.display_name,
    a.paused,
    a.breached,
    c.display_name as channel_name,
    cs.enabled as subscription_enabled
FROM accounts a
LEFT JOIN channel_subscriptions cs ON a.account_key = cs.account_key
LEFT JOIN channels c ON cs.channel_id = c.channel_id
ORDER BY a.account_key, c.display_name;
