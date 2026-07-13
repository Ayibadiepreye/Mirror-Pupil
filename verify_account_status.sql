-- Verify account exists in database
SELECT 
    account_key, 
    credential_key, 
    tl_email, 
    tl_server, 
    tl_prop_firm,
    display_name,
    initial_balance,
    current_balance,
    paused,
    breached,
    created_at
FROM accounts 
WHERE account_key = 'owidavid2002@gmail.com:2329061';

-- Check channel subscriptions for this account
SELECT 
    cs.account_key,
    c.display_name as channel_name,
    cs.enabled
FROM channel_subscriptions cs
JOIN channels c ON cs.channel_id = c.channel_id
WHERE cs.account_key = 'owidavid2002@gmail.com:2329061';

-- Check if there are any trades for this account
SELECT COUNT(*) as trade_count
FROM trade_history
WHERE account_key = 'owidavid2002@gmail.com:2329061';
