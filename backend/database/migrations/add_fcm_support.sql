-- Migration: Add FCM Push Notification Support
-- Created: 2026-07-15
-- Description: Adds fcm_token column to users table for Firebase Cloud Messaging

BEGIN;

-- Add fcm_token column to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS fcm_token TEXT;

-- Add index for faster lookups when sending push notifications
CREATE INDEX IF NOT EXISTS idx_users_fcm_token 
ON users(fcm_token) 
WHERE fcm_token IS NOT NULL;

-- Add comment for clarity
COMMENT ON COLUMN users.fcm_token IS 'Firebase Cloud Messaging token for push notifications';

COMMIT;

-- ============================================
-- VERIFICATION
-- ============================================

-- Verify column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
AND column_name = 'fcm_token';

-- Success message
SELECT 'FCM support migration completed successfully! ✅' as status;
