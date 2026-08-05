-- Check which channels are enabled for all accounts
-- Date: 2026-08-05
-- Fixed: accounts table uses tl_email and tl_account_id (not email/account_id)

-- 1. Show all accounts with their subscribed channels
SELECT 
    a.account_key,
    a.tl_email,
    a.tl_account_id,
    a.breached,
    a.paused,
    STRING_AGG(c.display_name, ', ' ORDER BY c.display_name) as subscribed_channels
FROM accounts a
LEFT JOIN channel_subscriptions cs ON a.account_key = cs.account_key
LEFT JOIN channels c ON cs.channel_id = c.channel_id AND c.enabled = TRUE
GROUP BY a.account_key, a.tl_email, a.tl_account_id, a.breached, a.paused
ORDER BY a.tl_email, a.tl_account_id;

-- 2. Show detailed view with channel status
SELECT 
    a.account_key,
    a.tl_email,
    a.tl_account_id,
    c.display_name as channel_name,
    c.enabled as channel_enabled,
    CASE 
        WHEN cs.account_key IS NOT NULL THEN 'Subscribed'
        ELSE 'Not Subscribed'
    END as subscription_status,
    a.breached,
    a.paused
FROM accounts a
CROSS JOIN channels c
LEFT JOIN channel_subscriptions cs 
    ON a.account_key = cs.account_key 
    AND c.channel_id = cs.channel_id
ORDER BY a.tl_email, a.tl_account_id, c.display_name;

-- 3. Summary: Count of subscriptions per channel
SELECT 
    c.display_name as channel_name,
    c.enabled as channel_enabled,
    COUNT(cs.account_key) as total_subscriptions,
    COUNT(CASE WHEN NOT a.breached AND NOT a.paused THEN 1 END) as active_account_subscriptions
FROM channels c
LEFT JOIN channel_subscriptions cs ON c.channel_id = cs.channel_id
LEFT JOIN accounts a ON cs.account_key = a.account_key
GROUP BY c.channel_id, c.display_name, c.enabled
ORDER BY c.display_name;

-- 4. Summary: Accounts with no channel subscriptions
SELECT 
    a.account_key,
    a.tl_email,
    a.tl_account_id,
    a.breached,
    a.paused,
    'NO CHANNELS' as status
FROM accounts a
LEFT JOIN channel_subscriptions cs ON a.account_key = cs.account_key
WHERE cs.channel_id IS NULL
ORDER BY a.tl_email, a.tl_account_id;

-- 5. Quick overview: Channel status
SELECT 
    channel_id,
    display_name,
    enabled,
    priority,
    CASE 
        WHEN enabled THEN '✓ ENABLED'
        ELSE '✗ DISABLED'
    END as status
FROM channels
ORDER BY display_name;
