-- Check Firepips channel configuration in database
-- This will show if the channel is properly configured

SELECT 
    channel_id,
    display_name,
    signal_prefix,
    entry_logic_module,
    management_logic_module,
    priority,
    enabled,
    created_at,
    notes
FROM channels
WHERE channel_id = -1001182913499;

-- Also check if any subscriptions exist
SELECT 
    cs.id,
    cs.account_key,
    cs.channel_id,
    cs.enabled as subscription_enabled,
    c.display_name as channel_name
FROM channel_subscriptions cs
JOIN channels c ON cs.channel_id = c.channel_id
WHERE cs.channel_id = -1001182913499;
