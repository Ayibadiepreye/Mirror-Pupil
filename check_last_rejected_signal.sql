-- Check last rejected BillirichyFX signals from notifications table
-- Run this in psql or your PostgreSQL client

-- Get last 5 rejected trades
SELECT 
    notification_id,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as rejected_at,
    title,
    message,
    metadata->>'symbol' as symbol,
    metadata->>'direction' as direction,
    metadata->>'reason' as rejection_reason,
    metadata->>'account_key' as account,
    metadata->>'channel_name' as channel
FROM notifications
WHERE 
    category = 'RISK'
    AND severity = 'WARNING'
    AND title LIKE 'Trade Rejected:%'
    AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 5;

-- Get the most recent rejected signal details
\echo '\n=== MOST RECENT REJECTED SIGNAL ==='
SELECT 
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as rejected_at,
    metadata->>'symbol' as symbol,
    metadata->>'direction' as direction,
    metadata->>'reason' as rejection_reason,
    metadata->>'account_key' as account
FROM notifications
WHERE 
    category = 'RISK'
    AND severity = 'WARNING'
    AND title LIKE 'Trade Rejected:%'
    AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 1;
