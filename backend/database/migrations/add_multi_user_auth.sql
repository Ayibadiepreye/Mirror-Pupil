-- Migration: Add Multi-User Authentication Support
-- Created: 2026-06-09
-- Description: Adds users table and user_id columns for multi-tenancy

-- 1. Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,           -- Firebase UID
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    is_super_admin BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,  -- Requires admin approval
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Add user_id to accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS user_id TEXT;
CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);

-- 3. Add user_id to risk_profiles table (NULL = system/default profile)
ALTER TABLE risk_profiles ADD COLUMN IF NOT EXISTS user_id TEXT;
CREATE INDEX IF NOT EXISTS idx_risk_profiles_user_id ON risk_profiles(user_id);

-- 4. Add foreign key constraints (after migration)
-- ALTER TABLE accounts ADD CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES users(user_id);
-- ALTER TABLE risk_profiles ADD CONSTRAINT fk_risk_profiles_user FOREIGN KEY (user_id) REFERENCES users(user_id);

-- Note: Channels remain global (super admin only, no user_id needed)
