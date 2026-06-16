-- Migration: Add current_pnl column to active_trades
-- This stores the live unrealized P&L fetched from TradeLocker

ALTER TABLE active_trades 
ADD COLUMN IF NOT EXISTS current_pnl REAL;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_active_trades_pnl ON active_trades(current_pnl);
