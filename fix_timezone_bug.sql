-- ============================================================================
-- FIX: Set PostgreSQL timezone to UTC to match Python's datetime.utcnow()
-- This fixes the autonomous 4-hour close bug
-- ============================================================================

-- Show BEFORE state
SELECT 
    '=== BEFORE ===' AS "Status",
    current_setting('timezone') AS "Timezone",
    NOW() AS "NOW() with timezone",
    NOW() AT TIME ZONE 'UTC' AS "UTC time",
    LOCALTIMESTAMP AS "LOCALTIMESTAMP";

-- Make the permanent change for the entire database
ALTER DATABASE mirror_pupil SET timezone TO 'UTC';

-- Apply to current session immediately
SET timezone = 'UTC';

-- Show AFTER state (verify the fix)
SELECT 
    '=== AFTER ===' AS "Status",
    current_setting('timezone') AS "Timezone",
    NOW() AS "NOW() with timezone",
    NOW() AT TIME ZONE 'UTC' AS "UTC time",
    LOCALTIMESTAMP AS "LOCALTIMESTAMP";

-- Final verification
SELECT 
    '=== VERIFICATION ===' AS "Check",
    CASE 
        WHEN current_setting('timezone') = 'UTC' THEN '✅ SUCCESS: Timezone is now UTC'
        ELSE '❌ FAILED: Timezone is ' || current_setting('timezone')
    END AS "Result",
    'All future connections will use UTC' AS "Note";

-- IMPORTANT: After running this, you need to:
-- 1. Disconnect and reconnect to the database for the change to take effect globally
-- 2. Restart your Python bot so it reconnects with the new timezone setting


-- ============================================================================
-- IMPORTANT: One more thing to check after fixing PostgreSQL
-- ============================================================================

-- This will show if Python is still going to have issues
SELECT 
    '=== WARNING ===' AS "Issue",
    'Your VPS system clock is in Pacific Time' AS "Problem",
    'But Python datetime.utcnow() assumes system clock is UTC' AS "Bug Still Exists",
    'You need to ALSO set your VPS timezone to UTC' AS "Solution";

-- To fully fix the bug:
-- 1. ✅ PostgreSQL timezone → UTC (done by this script)
-- 2. ❌ VPS system timezone → UTC (still needs to be done)
-- 3. Then both will agree and the bug will be fixed
