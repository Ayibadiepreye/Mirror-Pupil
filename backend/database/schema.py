"""
Mirror Pupil v5.1 - PostgreSQL Schema
Complete DDL for Neon PostgreSQL database.
"""

# Schema version
SCHEMA_VERSION = 5

# Complete PostgreSQL schema
SCHEMA_DDL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Channels: Dynamic signal source registry
CREATE TABLE IF NOT EXISTS channels (
    channel_id BIGINT PRIMARY KEY,  -- Telegram numeric channel ID
    display_name TEXT NOT NULL,
    signal_prefix TEXT NOT NULL UNIQUE,  -- Short code for signal IDs (e.g., 'B', 'F')
    entry_logic_module TEXT NOT NULL,
    management_logic_module TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 10,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Risk Profiles: Named risk management rule sets
CREATE TABLE IF NOT EXISTS risk_profiles (
    profile_id SERIAL PRIMARY KEY,
    profile_name TEXT UNIQUE NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    max_risk_per_trade_pct REAL NOT NULL DEFAULT 1.0,
    daily_loss_pct REAL NOT NULL DEFAULT 3.0,
    daily_trailing BOOLEAN NOT NULL DEFAULT TRUE,
    overall_loss_pct REAL NOT NULL DEFAULT 6.0,
    overall_trailing BOOLEAN NOT NULL DEFAULT TRUE,
    overall_trail_from_closed_balance BOOLEAN NOT NULL DEFAULT TRUE,
    profit_lock_pct REAL,
    profit_lock_floor_pct REAL,
    payout_buffer_pct REAL NOT NULL DEFAULT 1.0,
    max_concurrent_trades INTEGER NOT NULL DEFAULT 5,
    commission_per_lot REAL NOT NULL DEFAULT 6.0,
    safety_buffer_pct REAL NOT NULL DEFAULT 10.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Accounts: TradeLocker sub-accounts
CREATE TABLE IF NOT EXISTS accounts (
    account_key TEXT PRIMARY KEY,  -- Format: email:account_id
    credential_key TEXT NOT NULL,  -- TradeLocker login email
    tl_account_id TEXT NOT NULL,
    tl_email TEXT NOT NULL,
    tl_password TEXT NOT NULL,  -- Encrypted
    tl_server TEXT NOT NULL DEFAULT 'live',
    display_name TEXT,
    initial_balance REAL,
    current_balance REAL,
    highest_banked_balance REAL,
    all_time_high_equity REAL,
    profit_locked BOOLEAN DEFAULT FALSE,
    daily_pnl REAL DEFAULT 0,
    daily_start_balance REAL,
    last_synced_balance REAL,
    cycle_start_date DATE,
    cycle_best_day_pnl REAL DEFAULT 0,
    paused BOOLEAN DEFAULT FALSE,
    breached BOOLEAN DEFAULT FALSE,
    risk_profile_id INTEGER REFERENCES risk_profiles(profile_id),
    max_concurrent_trades_override INTEGER
);

-- Channel Subscriptions: Per-account channel copy settings
CREATE TABLE IF NOT EXISTS channel_subscriptions (
    id SERIAL PRIMARY KEY,
    account_key TEXT NOT NULL REFERENCES accounts(account_key) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL REFERENCES channels(channel_id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(account_key, channel_id)
);

-- Active Trades: Currently open positions
CREATE TABLE IF NOT EXISTS active_trades (
    trade_id SERIAL PRIMARY KEY,
    account_key TEXT NOT NULL REFERENCES accounts(account_key),
    channel_id BIGINT NOT NULL REFERENCES channels(channel_id),
    signal_id TEXT NOT NULL,
    sub_signal_id TEXT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,  -- BUY or SELL
    entry_price REAL NOT NULL,
    sl REAL,
    tp REAL,
    lot_size REAL NOT NULL,
    entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tl_order_id TEXT,
    tl_position_id TEXT,
    status TEXT NOT NULL,  -- pending, filled, failed, partially_filled
    tp1_hit BOOLEAN DEFAULT FALSE,
    risk_usd REAL
);

-- Waiting Room: Incomplete signals awaiting completion
CREATE TABLE IF NOT EXISTS waiting_room (
    id SERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL REFERENCES channels(channel_id),
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_msg_id BIGINT NOT NULL,
    entry_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Trade History: Closed trades
CREATE TABLE IF NOT EXISTS trade_history (
    history_id SERIAL PRIMARY KEY,
    account_key TEXT NOT NULL,
    channel_id BIGINT NOT NULL REFERENCES channels(channel_id),
    signal_id TEXT NOT NULL,
    sub_signal_id TEXT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    sl REAL,
    tp REAL,
    lot_size REAL NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pnl REAL NOT NULL,
    outcome TEXT NOT NULL,  -- WIN, LOSS, BE
    close_reason TEXT NOT NULL  -- TP_HIT, SL_HIT, MANUAL, AUTONOMOUS, EOD, WEEKEND
);

-- Profitable Days: Daily P&L tracking for consistency score
CREATE TABLE IF NOT EXISTS profitable_days (
    id SERIAL PRIMARY KEY,
    account_key TEXT NOT NULL REFERENCES accounts(account_key),
    date DATE NOT NULL,
    pnl REAL NOT NULL,
    is_profitable_day BOOLEAN NOT NULL,
    UNIQUE(account_key, date)
);

-- Message Cache: Ephemeral deduplication (auto-cleanup after 2 minutes)
CREATE TABLE IF NOT EXISTS message_cache (
    msg_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL REFERENCES channels(channel_id),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (msg_id, channel_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_active_trades_account ON active_trades(account_key);
CREATE INDEX IF NOT EXISTS idx_active_trades_signal ON active_trades(signal_id);
CREATE INDEX IF NOT EXISTS idx_active_trades_channel ON active_trades(channel_id);
CREATE INDEX IF NOT EXISTS idx_trade_history_account ON trade_history(account_key);
CREATE INDEX IF NOT EXISTS idx_trade_history_channel ON trade_history(channel_id);
CREATE INDEX IF NOT EXISTS idx_trade_history_time ON trade_history(exit_time);
CREATE INDEX IF NOT EXISTS idx_profitable_days_account ON profitable_days(account_key);
CREATE INDEX IF NOT EXISTS idx_profitable_days_date ON profitable_days(date);
CREATE INDEX IF NOT EXISTS idx_waiting_room_expires ON waiting_room(expires_at);
CREATE INDEX IF NOT EXISTS idx_message_cache_processed ON message_cache(processed_at);
CREATE INDEX IF NOT EXISTS idx_channel_subscriptions_account ON channel_subscriptions(account_key);
CREATE INDEX IF NOT EXISTS idx_channel_subscriptions_channel ON channel_subscriptions(channel_id);
"""

# Built-in data: Default channels and risk profile
INITIAL_DATA = """
-- Built-in channels (BillirichyFX and Firepips)
-- FIXED: Added signal_prefix column to INSERT statement (was missing in original)
INSERT INTO channels (channel_id, display_name, signal_prefix, entry_logic_module, management_logic_module, priority, enabled)
VALUES
    (-1001859598768, 'BillirichyFX', 'B', 'channels.billirichy.plugin', 'channels.billirichy.plugin', 1, TRUE),
    (-1001182913499, 'Firepips', 'F', 'channels.firepips.plugin', 'channels.firepips.plugin', 2, TRUE)
ON CONFLICT (channel_id) DO NOTHING;

-- Built-in default risk profile (Blue Guardian Instant Standard)
INSERT INTO risk_profiles (
    profile_name, is_default,
    max_risk_per_trade_pct, daily_loss_pct, daily_trailing,
    overall_loss_pct, overall_trailing, overall_trail_from_closed_balance,
    profit_lock_pct, profit_lock_floor_pct, payout_buffer_pct,
    max_concurrent_trades, commission_per_lot, safety_buffer_pct,
    notes
) VALUES (
    'Blue Guardian Instant Standard', TRUE,
    1.0, 3.0, TRUE,
    6.0, TRUE, TRUE,
    6.0, 0.0, 1.0,
    5, 6.0, 10.0,
    'Default profile matching Blue Guardian Instant Standard drawdown rules. Daily 3% static floor, overall 6% trailing from closed balance, profit lock at +6%.'
)
ON CONFLICT (profile_name) DO NOTHING;
"""

# Cleanup queries
CLEANUP_QUERIES = """
-- Delete expired waiting room entries (older than 15 minutes)
DELETE FROM waiting_room WHERE expires_at < NOW();

-- Delete old message cache entries (older than 2 minutes)
DELETE FROM message_cache WHERE processed_at < NOW() - INTERVAL '2 minutes';
"""
