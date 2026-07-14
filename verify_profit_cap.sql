-- ============================================
-- Verify Profit Cap Columns in Database
-- ============================================

-- Check if profit cap columns exist in accounts table
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'accounts'
AND column_name IN (
    'profit_cap_enabled',
    'profit_cap_type',
    'profit_cap_value',
    'profit_cap_buffer_pct',
    'profit_cap_frozen'
)
ORDER BY ordinal_position;

-- Expected output:
-- column_name            | data_type | is_nullable | column_default
-- -----------------------|-----------|-------------|----------------
-- profit_cap_enabled     | boolean   | YES         | false
-- profit_cap_type        | text      | YES         | NULL
-- profit_cap_value       | real      | YES         | NULL
-- profit_cap_buffer_pct  | real      | YES         | 2.0
-- profit_cap_frozen      | boolean   | YES         | false

-- If you see 5 rows returned, profit cap is installed! ✅
-- If you see 0 rows, profit cap is NOT installed ❌
