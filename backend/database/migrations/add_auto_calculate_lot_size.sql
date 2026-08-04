-- Migration: Add auto-calculate lot size toggle
-- Purpose: Allow accounts to automatically calculate optimal lot size from max risk per trade
-- Date: 2026-07-30

-- Add toggle column to accounts table
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS use_calculated_lot_size BOOLEAN DEFAULT FALSE;

-- Add helpful comment
COMMENT ON COLUMN accounts.use_calculated_lot_size IS 
'When TRUE, ignores lot_size_override and calculates lot size from max_risk_per_trade_pct to maximize profit on every signal';

-- Example: Enable for specific account
-- UPDATE accounts SET use_calculated_lot_size = TRUE WHERE account_key = 'email:account_id';
