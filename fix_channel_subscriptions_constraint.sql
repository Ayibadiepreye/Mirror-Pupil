-- Fix channel_subscriptions table constraint
-- This adds the missing UNIQUE constraint that allows ON CONFLICT to work

-- First, check if constraint already exists
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'channel_subscriptions';

-- If the unique constraint is missing, add it
-- (You may need to remove duplicate rows first)

-- Step 1: Check for duplicates
SELECT account_key, channel_id, COUNT(*)
FROM channel_subscriptions
GROUP BY account_key, channel_id
HAVING COUNT(*) > 1;

-- Step 2: If duplicates exist, remove them (keep only the first one)
-- DELETE FROM channel_subscriptions
-- WHERE id NOT IN (
--     SELECT MIN(id)
--     FROM channel_subscriptions
--     GROUP BY account_key, channel_id
-- );

-- Step 3: Add the unique constraint if it doesn't exist
-- The constraint name should be: channel_subscriptions_account_key_channel_id_key
ALTER TABLE channel_subscriptions
ADD CONSTRAINT channel_subscriptions_account_key_channel_id_key
UNIQUE (account_key, channel_id);

-- Verify the constraint was added
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'channel_subscriptions';
