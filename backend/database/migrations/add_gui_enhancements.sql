-- Mirror Pupil v5.1 - GUI Enhancements Migration
-- Adds columns and tables for improved frontend functionality
-- Run this with: psql -U your_user -d mirror_pupil -f add_gui_enhancements.sql

BEGIN;

-- ============================================
-- 1. ACCOUNTS TABLE ENHANCEMENTS
-- ============================================

-- Add display_name for custom account naming
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS display_name TEXT;

-- Add lot_size_override for per-account lot size customization
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS lot_size_override REAL;

-- Add comment for clarity
COMMENT ON COLUMN accounts.display_name IS 'Custom display name for GUI (optional)';
COMMENT ON COLUMN accounts.lot_size_override IS 'Override default lot size for this account (optional)';


-- ============================================
-- 2. CHANNELS TABLE ENHANCEMENTS
-- ============================================

-- Add display_name for custom channel naming
ALTER TABLE channels 
ADD COLUMN IF NOT EXISTS display_name TEXT;

-- Add comment
COMMENT ON COLUMN channels.display_name IS 'Custom display name for GUI (optional)';


-- ============================================
-- 3. ACTIVE TRADES ENHANCEMENTS
-- ============================================

-- Add channel_name for easy display without joins
ALTER TABLE active_trades 
ADD COLUMN IF NOT EXISTS channel_name TEXT;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_active_trades_account_status 
ON active_trades(account_key, status);


-- ============================================
-- 4. TRADE HISTORY ENHANCEMENTS
-- ============================================

-- Add channel_name for easy display
ALTER TABLE trade_history 
ADD COLUMN IF NOT EXISTS channel_name TEXT;

-- Add manual_action_type for tracking user interventions
ALTER TABLE trade_history 
ADD COLUMN IF NOT EXISTS manual_action_type TEXT;

-- Add comments
COMMENT ON COLUMN trade_history.channel_name IS 'Channel display name at time of trade';
COMMENT ON COLUMN trade_history.manual_action_type IS 'Type of manual action if closed by user (MANUAL_CLOSE, MANUAL_BE, MANUAL_PARTIAL)';

-- Add index for faster history queries
CREATE INDEX IF NOT EXISTS idx_trade_history_account_exit 
ON trade_history(account_key, exit_time DESC);


-- ============================================
-- 5. NOTIFICATIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    account_key TEXT,
    category TEXT NOT NULL,  -- SIGNAL, EXECUTION, MANAGEMENT, BREACH, SYSTEM
    severity TEXT NOT NULL,  -- INFO, WARNING, ERROR, CRITICAL
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,  -- Additional data (trade_id, symbol, etc.)
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Foreign key constraint
    CONSTRAINT fk_notification_account 
        FOREIGN KEY (account_key) 
        REFERENCES accounts(account_key) 
        ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_notifications_account 
ON notifications(account_key, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_read 
ON notifications(read, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_created 
ON notifications(created_at DESC);

-- Comments
COMMENT ON TABLE notifications IS 'Real-time notifications for GUI display';
COMMENT ON COLUMN notifications.category IS 'Event category: SIGNAL, EXECUTION, MANAGEMENT, BREACH, SYSTEM';
COMMENT ON COLUMN notifications.severity IS 'Severity level: INFO, WARNING, ERROR, CRITICAL';
COMMENT ON COLUMN notifications.metadata IS 'JSON data with additional context';


-- ============================================
-- 6. MANUAL ACTIONS AUDIT TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS manual_actions (
    action_id SERIAL PRIMARY KEY,
    account_key TEXT NOT NULL,
    trade_id INTEGER,
    action_type TEXT NOT NULL,  -- MANUAL_CLOSE, MANUAL_BE, MANUAL_PARTIAL_25, etc.
    action_data JSONB,  -- Additional data (qty_closed, reason, etc.)
    performed_at TIMESTAMP DEFAULT NOW(),
    
    -- Foreign key constraints
    CONSTRAINT fk_manual_action_account 
        FOREIGN KEY (account_key) 
        REFERENCES accounts(account_key) 
        ON DELETE CASCADE
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_manual_actions_account 
ON manual_actions(account_key, performed_at DESC);

-- Comments
COMMENT ON TABLE manual_actions IS 'Audit trail for all manual user actions';
COMMENT ON COLUMN manual_actions.action_type IS 'Type of manual action performed';
COMMENT ON COLUMN manual_actions.action_data IS 'JSON data with action details';


-- ============================================
-- 7. UPDATE EXISTING DATA
-- ============================================

-- Populate channel_name in active_trades from channels table
UPDATE active_trades at
SET channel_name = COALESCE(c.display_name, c.channel_name)
FROM channels c
WHERE at.channel_id = c.channel_id
AND at.channel_name IS NULL;

-- Populate channel_name in trade_history from channels table
UPDATE trade_history th
SET channel_name = COALESCE(c.display_name, c.channel_name)
FROM channels c
WHERE th.channel_id = c.channel_id
AND th.channel_name IS NULL;


-- ============================================
-- 8. CLEANUP FUNCTION FOR OLD NOTIFICATIONS
-- ============================================

-- Function to delete notifications older than 48 hours
CREATE OR REPLACE FUNCTION cleanup_old_notifications()
RETURNS void AS $$
BEGIN
    DELETE FROM notifications
    WHERE created_at < NOW() - INTERVAL '48 hours';
END;
$$ LANGUAGE plpgsql;

-- Comment
COMMENT ON FUNCTION cleanup_old_notifications IS 'Deletes notifications older than 48 hours';


COMMIT;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Run these to verify migration success:

-- Check new columns in accounts
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'accounts'
AND column_name IN ('display_name', 'lot_size_override');

-- Check new columns in channels
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'channels'
AND column_name = 'display_name';

-- Check notifications table exists
SELECT COUNT(*) as notification_count FROM notifications;

-- Check manual_actions table exists
SELECT COUNT(*) as action_count FROM manual_actions;

-- Success message
SELECT 'Migration completed successfully! ✅' as status;
