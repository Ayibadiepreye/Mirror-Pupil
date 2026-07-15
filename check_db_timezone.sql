-- Check PostgreSQL timezone configuration and current time
-- Run this in your Neon PostgreSQL console to diagnose the timezone issue

-- 1. Show PostgreSQL timezone setting
SELECT 
    'PostgreSQL Timezone' AS check_type,
    current_setting('timezone') AS value;

-- 2. Show current timestamp in different formats
SELECT 
    'Current Timestamps' AS info,
    NOW() AS "NOW() with timezone",
    CURRENT_TIMESTAMP AS "CURRENT_TIMESTAMP",
    LOCALTIMESTAMP AS "LOCALTIMESTAMP (no tz)",
    NOW() AT TIME ZONE 'UTC' AS "NOW() in UTC";

-- 3. Show what time PostgreSQL thinks it is vs what it should be
SELECT 
    'Time Check' AS info,
    NOW() AS "PostgreSQL thinks now is",
    NOW() AT TIME ZONE 'UTC' AS "UTC time according to PG",
    EXTRACT(TIMEZONE_HOUR FROM NOW()) AS "Timezone offset (hours)";

-- 4. Check a sample entry_time from active_trades (if any exist)
SELECT 
    'Sample Trade Entry Time' AS info,
    trade_id,
    entry_time,
    NOW() - entry_time AS "Age of trade",
    EXTRACT(EPOCH FROM (NOW() - entry_time))/3600 AS "Age in hours"
FROM active_trades
ORDER BY entry_time DESC
LIMIT 1;

-- 5. Summary diagnosis
SELECT 
    'DIAGNOSIS' AS "===================",
    CASE 
        WHEN current_setting('timezone') = 'UTC' THEN '✅ Timezone is UTC (correct)'
        ELSE '⚠️  Timezone is ' || current_setting('timezone') || ' (should be UTC)'
    END AS timezone_status,
    'PostgreSQL time: ' || NOW()::text AS current_time;
