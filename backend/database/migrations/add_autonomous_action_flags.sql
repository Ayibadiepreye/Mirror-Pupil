-- Migration: Add autonomous action tracking flags to active_trades
-- Purpose: Prevent autonomous manager from spamming repeated actions on the same trade
-- Date: 2026-07-22

-- Add three boolean flags to track whether autonomous actions have been applied
ALTER TABLE active_trades 
ADD COLUMN IF NOT EXISTS auto_tp_applied BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS auto_be_applied BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS auto_partial_applied BOOLEAN DEFAULT FALSE;

-- Backfill existing trades with FALSE (default behavior)
UPDATE active_trades 
SET 
    auto_tp_applied = true,
    auto_be_applied = true,
    auto_partial_applied = true
WHERE 
    auto_tp_applied IS NULL 
    OR auto_be_applied IS NULL 
    OR auto_partial_applied IS NULL;

-- Add helpful comment
COMMENT ON COLUMN active_trades.auto_tp_applied IS 'Flag: Autonomous 15-min TP assignment already applied';
COMMENT ON COLUMN active_trades.auto_be_applied IS 'Flag: Autonomous 1.5-hour breakeven already applied';
COMMENT ON COLUMN active_trades.auto_partial_applied IS 'Flag: Autonomous 3-hour 50% partial close already applied';
