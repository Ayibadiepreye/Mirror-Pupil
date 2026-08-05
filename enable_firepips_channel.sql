-- Enable FirePips channel and subscribe all accounts
-- Date: 2026-08-04

-- 1. Enable the FirePips channel globally
UPDATE channels 
SET enabled = TRUE 
WHERE display_name = 'FirePips' OR display_name ILIKE '%firepips%';

-- Verify the channel is enabled
SELECT channel_id, display_name, enabled, priority 
FROM channels 
WHERE display_name ILIKE '%firepips%';

-- 2. Subscribe all accounts to FirePips channel (if not already subscribed)
-- First, get the FirePips channel_id
DO $$
DECLARE
    firepips_channel_id INT;
    account_record RECORD;
BEGIN
    -- Get FirePips channel ID
    SELECT channel_id INTO firepips_channel_id 
    FROM channels 
    WHERE display_name = 'FirePips' OR display_name ILIKE '%firepips%'
    LIMIT 1;
    
    IF firepips_channel_id IS NULL THEN
        RAISE NOTICE 'FirePips channel not found!';
        RETURN;
    END IF;
    
    RAISE NOTICE 'FirePips channel_id: %', firepips_channel_id;
    
    -- Subscribe all accounts to FirePips (if not already subscribed)
    FOR account_record IN 
        SELECT account_key 
        FROM accounts 
        WHERE NOT breached AND NOT paused
    LOOP
        -- Check if subscription already exists
        IF NOT EXISTS (
            SELECT 1 FROM channel_subscriptions 
            WHERE account_key = account_record.account_key 
            AND channel_id = firepips_channel_id
        ) THEN
            -- Insert subscription
            INSERT INTO channel_subscriptions (account_key, channel_id)
            VALUES (account_record.account_key, firepips_channel_id);
            
            RAISE NOTICE 'Subscribed account: %', account_record.account_key;
        END IF;
    END LOOP;
END $$;

-- 3. Verify subscriptions
SELECT 
    cs.account_key,
    c.display_name as channel_name,
    c.enabled as channel_enabled
FROM channel_subscriptions cs
JOIN channels c ON cs.channel_id = c.channel_id
WHERE c.display_name ILIKE '%firepips%'
ORDER BY cs.account_key;

-- 4. Show summary
SELECT 
    'FirePips Subscriptions' as summary,
    COUNT(*) as total_subscriptions
FROM channel_subscriptions cs
JOIN channels c ON cs.channel_id = c.channel_id
WHERE c.display_name ILIKE '%firepips%';
