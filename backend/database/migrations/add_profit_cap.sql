-- Migration: Add Profit Cap Feature
-- Date: 2026-07-06
-- Description: Adds profit cap columns to accounts table for prop firm compliance

-- Add profit cap enabled flag
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS profit_cap_enabled BOOLEAN DEFAULT FALSE;

-- Add profit cap type (percentage or dollar)
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS profit_cap_type TEXT;

-- Add profit cap value (percentage or dollar amount)
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS profit_cap_value REAL;

-- Add safety buffer percentage (default 2%)
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS profit_cap_buffer_pct REAL DEFAULT 2.0;

-- Add frozen state flag
ALTER TABLE accounts 
ADD COLUMN IF NOT EXISTS profit_cap_frozen BOOLEAN DEFAULT FALSE;

-- Update existing accounts to have default values
UPDATE accounts 
SET 
    profit_cap_enabled = FALSE,
    profit_cap_frozen = FALSE,
    profit_cap_buffer_pct = 2.0
WHERE profit_cap_enabled IS NULL;
