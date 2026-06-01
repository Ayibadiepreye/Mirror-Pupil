# 📘 Mirror Pupil – Complete System Specification

**Project Name:** Mirror Pupil  
**Version:** 5.0 (Production Ready – Channel Plugin Architecture + Multi-Profile Risk Management)  
**Date:** 2025  
**Scope:** Mirror Pupil is a self-hosted copy-trading bot that listens to any number of Telegram signal channels via a pluggable channel registry, mirrors trades onto multiple TradeLocker accounts (including multiple sub-accounts per credential) via the TradeLocker Python library, enforces configurable prop firm risk rules through named risk profiles, and provides a React-based Telegram Web App GUI through which every aspect of the system — channels, accounts, sub-accounts, and risk profiles — can be managed without touching code or the database directly.

> **Upgrade notes from v4.0:**
> - Channel sources are no longer hardcoded. All channels live in the database and the Telethon listener is rebuilt dynamically from those records on startup. New channels can be added from the GUI at runtime.
> - Channel identification uses the numeric **channel ID** throughout — never a username — so private channels work identically to public ones.
> - Every account and sub-account has independent toggles for which channels it copies from (defaults to all enabled channels).
> - Risk management is no longer hardcoded. Rules are stored as named **Risk Profiles** in the database. Accounts select a profile via a dial in the GUI. The built-in default profile matches **Blue Guardian Instant Standard** drawdown rules.
> - The GUI gains full CRUD for accounts, sub-accounts, channels, and risk profiles.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Common Infrastructure](#2-common-infrastructure)
   - 2.1 Telegram Client (Telethon) – Channel Plugin Registry
   - 2.2 TradeLocker Python Library Integration
   - 2.3 Authentication Flow & Token Refresh
   - 2.4 Multi-Account Management & Partial Failure Handling
   - 2.5 Database Schema (SQLite)
   - 2.6 Database Initialization, Migration & Daily Clearing
   - 2.7 Risk Management (Profile-Based)
   - 2.8 Price Delta Risk Calculation & Prop Firm Limit Validation
   - 2.7 Risk Management (Profile-Based)
   - 2.8 Price Delta – Core Risk Formula  
   - 2.9 Withdrawal Detection & Balance Reconciliation
   - 2.10 Consistency Score (20% Rule)
   - 2.11 Price Delta Risk Calculation & Prop Firm Limit Validation
   - 2.12 Channel Priority & Concurrent Trade Limit
   - 2.13 Profitable Days Tracking
   - 2.14 Error Notification System
   - 2.15 Signal ID Generation
   - 2.16 Dry-Run / Paper Mode
   - 2.17 Channel Plugin Architecture
   - 2.18 Multi-Profile Risk Management System
3. [BillirichyFX – Entry Logic](#3-billirichyfx--entry-logic)
4. [BillirichyFX – Management Logic](#4-billirichyfx--management-logic)
5. [Firepips – Entry Logic](#5-firepips--entry-logic)
6. [Firepips – Management Logic](#6-firepips--management-logic)
7. [Telegram Web App GUI (React)](#7-telegram-web-app-gui-react)
   - 7.1 Technology Stack & TWA Constraints
   - 7.2 Pages & Components
   - 7.3 Real-Time Updates (WebSockets)
   - 7.4 API Endpoints (FastAPI)
8. [Deployment & Operational Notes](#8-deployment--operational-notes)
9. [AI Development Prompt](#9-ai-development-prompt)

---

## 1. System Overview

**Mirror Pupil** connects to one or more Telegram signal channels registered in its channel database and mirrors every parsed trade signal onto one or more TradeLocker trading accounts — hence the name: it watches, and it mirrors.

At launch the system ships with two built-in signal channels:

- **BillirichyFX** (channel ID: `-1001859598768`)
- **Firepips** (channel ID: `-1001182913499`)

Additional channels can be added at any time through the GUI Settings page without restarting Mirror Pupil. Each channel is assigned an **entry logic module** and a **management logic module**, chosen from the built-in options (BillirichyFX Logic or Firepips Logic) or any custom module deployed to the server. When a signal provider migrates to a new Telegram channel but keeps the same message format, the operator simply adds the new channel via the GUI and selects the old logic from the dial.

Mirror Pupil enforces risk rules through named **Risk Profiles** stored in the database. Each account selects the profile to apply; the default is the built-in **Blue Guardian Instant Standard** profile.

The **React-based Telegram Web App (TWA)** GUI is the single control surface for Mirror Pupil. Every operational task — adding or removing channels, adding or removing accounts, toggling channel subscriptions per account, managing risk profiles, pausing trading — is performed from the GUI. No direct database access or code changes are required after initial deployment.

**Channel Priority:** Configurable per channel (integer priority — lower = higher priority). BillirichyFX defaults to priority 1, Firepips to priority 2.

**Execution Mode:** Mirror Pupil supports a **dry-run mode** for safe pre-live testing.

---

## 2. Common Infrastructure

### 2.1 Telegram Client (Telethon) – Channel Plugin Registry

Rather than hardcoding channel usernames in the event handler, the Telethon client loads all enabled channels from the database at startup (and re-registers listeners whenever a channel is added or toggled via the GUI at runtime).

**Key principle:** All channels are identified by their **numeric channel ID** (e.g., `-1001234567890`). This works identically for public and private channels. The GUI accepts channel IDs as input, not usernames.

```python
from telethon import TelegramClient, events
from channel_registry import get_enabled_channels, get_plugin_for_channel

client = TelegramClient('bot_session', API_ID, API_HASH)

async def register_channel_listeners():
    """
    Called on startup and whenever a channel is added/toggled via the GUI.
    Clears existing handlers and re-registers from the DB channel list.
    """
    client.remove_event_handler(handle_new_message)
    client.remove_event_handler(handle_edited_message)

    enabled_ids = [ch['channel_id'] for ch in get_enabled_channels()]
    if not enabled_ids:
        logger.warning("No enabled channels. Bot is listening to nothing.")
        return

    @client.on(events.NewMessage(chats=enabled_ids))
    async def handle_new_message(event):
        channel_id = event.chat_id
        plugin = get_plugin_for_channel(channel_id)
        if plugin:
            await plugin.route_message(event.message, is_edit=False)

    @client.on(events.MessageEdited(chats=enabled_ids))
    async def handle_edited_message(event):
        channel_id = event.chat_id
        plugin = get_plugin_for_channel(channel_id)
        if plugin:
            await plugin.route_message(event.message, is_edit=True)

    logger.info(f"Listening to {len(enabled_ids)} channel(s): {enabled_ids}")
```

**Runtime channel updates:** When a channel is added or its `enabled` flag is toggled via the GUI, the backend calls `await register_channel_listeners()` to rebuild the handler set without restarting the bot process.

Required environment variables: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`.

---

### 2.2 TradeLocker Python Library Integration

**Library:** `tradelocker` (Python SDK)  
**Install:** `pip install tradelocker`  
**Async:** All API calls are `await`-ed within the FastAPI/asyncio event loop.

**Core operations used:**

| Operation | Library Method |
|---|---|
| Place market order | `client.create_order(symbol, side, quantity, order_type='MARKET')` |
| Place limit order | `client.create_order(symbol, side, quantity, order_type='LIMIT', price=X)` |
| Place stop order | `client.create_order(symbol, side, quantity, order_type='STOP', stop_price=X)` |
| Modify SL/TP | `client.modify_order(order_id, sl=X, tp=X)` |
| Close full position | `client.close_position(position_id)` |
| Partial close | `client.close_position(position_id, quantity=partial_qty)` |
| Cancel pending | `client.cancel_order(order_id)` |
| Get open positions | `client.get_positions()` |
| Get account info | `client.get_account()` |
| Get symbol specs | `client.get_instrument(symbol)` |

**Partial Close:** Use `client.close_position(position_id, quantity=partial_qty)` directly. No fallback; if the call fails after retries log the error and notify via GUI (`HIGH` severity). Do **not** close full and re-enter.

**Rate Limiting:** Wrap all calls in a request queue throttled to **5 requests/second per credential**.

```python
class RateLimitedClient:
    def __init__(self, tl_client, max_rps=5):
        self.client = tl_client
        self.semaphore = asyncio.Semaphore(max_rps)

    async def call(self, method, *args, **kwargs):
        async with self.semaphore:
            return await getattr(self.client, method)(*args, **kwargs)
```

---

### 2.3 Authentication Flow & Token Refresh

**Initial Authentication:**

```python
from tradelocker import TradeLocker

tl_client = TradeLocker(
    email="account@example.com",
    password="password",
    server="live"
)
await tl_client.authenticate()
```

**Multi-Account Architecture:**

A single TradeLocker login (email + password) can hold multiple sub-accounts. The bot supports multiple credentials, each containing multiple sub-accounts.

```python
async def enumerate_accounts(credential: dict) -> list[dict]:
    tl = TradeLocker(
        email=credential['email'],
        password=credential['password'],
        server=credential['server']
    )
    await tl.authenticate()
    raw_accounts = await tl.get_accounts()
    return [
        {
            'credential_key': credential['email'],
            'tl_instance': tl,
            'account_id': acct.id,
            'account_number': acct.number,
            'initial_balance': acct.balance
        }
        for acct in raw_accounts
    ]
```

All discovered sub-accounts are stored in the `accounts` registry keyed by `(credential_key, account_id)`. They share their credential's `TradeLocker` instance but operate with independent risk tracking and independent risk profile assignments.

**Token Expiry & Refresh:** Background refresh every 23 hours per credential; immediate re-auth on HTTP 401.

```python
async def token_refresh_loop(credential_key: str):
    while True:
        await asyncio.sleep(23 * 3600)
        try:
            await credentials[credential_key].authenticate()
            logger.info(f"[Credential {credential_key}] Token refreshed.")
        except Exception as e:
            await notify_gui(f"Token refresh FAILED: {e}", severity="CRITICAL")
```

---

### 2.4 Multi-Account Management & Partial Failure Handling

When a signal is executed, the bot places the trade on **all active, non-paused, non-breached accounts that have the originating channel enabled in their subscription** concurrently via `asyncio.gather`.

- **Channel subscription filter:** Before dispatching to any account, check `channel_subscriptions` for `(account_key, channel_id, enabled=True)`. Accounts that have the channel toggled off in their subscription settings are skipped entirely.
- **Failure handling:** Retry up to 3 times with exponential backoff (1s → 2s → 4s). After 3 failures mark as `failed`, send `HIGH` severity alert.
- Management messages apply only to accounts where the trade was successfully opened (`status = 'filled'`). Accounts with `status = 'failed'` are skipped.

```python
async def execute_on_all_accounts(signal, channel_id: int):
    active = get_active_accounts()
    # Filter to accounts subscribed to this channel
    subscribed = [
        key for key in active
        if db.is_channel_subscribed(key, channel_id)
    ]
    tasks = [execute_trade(account_key, signal) for account_key in subscribed]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for account_key, result in zip(subscribed, results):
        if isinstance(result, Exception):
            logger.error(f"[Account {account_key}] Execution failed: {result}")
            await notify_gui(f"Trade execution failed on {account_key}", severity="HIGH")
```

---

### 2.5 Database Schema (SQLite)

**Schema version:** 5 (tracked in `schema_version` table)

#### `schema_version`
| Column | Type | Description |
|---|---|---|
| `version` | INTEGER | Current schema version |
| `applied_at` | TIMESTAMP | When last migration was applied |

#### `channels` *(new in v5.0)*
Stores all registered signal source channels. This is the authoritative list the Telethon listener is built from. All channel management — adding, removing, enabling, disabling, editing — is performed exclusively through the GUI. No manual DB edits or code changes are required.

| Column | Type | Description |
|---|---|---|
| `channel_id` | INTEGER PK | Numeric Telegram channel ID (e.g., `-1001234567890`). Used for all lookups — never a username. Works for both public and private channels. |
| `display_name` | TEXT NOT NULL | Human-readable name shown throughout the GUI (e.g., `BillirichyFX`, `Firepips`). This is the primary identifier visible to the operator — every table, badge, filter, log entry, and trade record that references a channel uses this name. |
| `signal_prefix` | TEXT NOT NULL | Short code (2–4 chars) used in signal IDs (e.g., `B`, `F`). Must be unique across channels. Set when the channel is added via the GUI. |
| `entry_logic_module` | TEXT NOT NULL | Python module path for entry parsing (e.g., `channels.billirichy.plugin`). Chosen from the logic dial in the GUI — see Section 2.15. |
| `management_logic_module` | TEXT NOT NULL | Python module path for management logic (e.g., `channels.billirichy.plugin`). Can differ from `entry_logic_module` if desired. |
| `priority` | INTEGER | Lower integer = higher priority. Used when concurrent limit is reached. Editable from the GUI Channel Management table. |
| `enabled` | BOOLEAN | Global on/off toggle. When `false` the bot ignores all messages from this channel entirely. Toggled from the GUI Channel Status Bar or Channel Management table. |
| `created_at` | TIMESTAMP | |
| `notes` | TEXT | Optional operator notes (e.g., "Replaced old channel after migration"). Editable from the GUI. |

**Built-in channels inserted on first-time DB init:**

```sql
INSERT OR IGNORE INTO channels
    (channel_id, display_name, signal_prefix, entry_logic_module, management_logic_module, priority, enabled)
VALUES
  (-1001859598768, 'BillirichyFX', 'B', 'channels.billirichy.plugin', 'channels.billirichy.plugin', 1, 1),
  (-1001182913499, 'Firepips',     'F', 'channels.firepips.plugin',   'channels.firepips.plugin',   2, 1);
```

*(These are the live channel IDs. After first deployment, all further channel changes are made exclusively through the GUI.)*

#### `channel_subscriptions` *(new in v5.0)*
Per-account channel copy settings. A row per `(account_key, channel_id)` pair.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `account_key` | TEXT | FK → `accounts.account_key` |
| `channel_id` | INTEGER | FK → `channels.channel_id` |
| `enabled` | BOOLEAN | If `false`, this account ignores signals from this channel. Default `true`. |

**Initialization rule:** When a new account is added or a new channel is added, insert a row for every `(account, channel)` pair that doesn't yet exist with `enabled = true`. This ensures new channels default to copying on all accounts, and new accounts default to copying from all channels.

```python
def sync_channel_subscriptions():
    """
    Called whenever a channel or account is added.
    Ensures every (account, channel) pair has a subscription row.
    """
    accounts = db.get_all_account_keys()
    channels = db.get_all_channel_ids()
    for account_key in accounts:
        for channel_id in channels:
            db.execute(
                "INSERT OR IGNORE INTO channel_subscriptions "
                "(account_key, channel_id, enabled) VALUES (?, ?, 1)",
                (account_key, channel_id)
            )
```

#### `risk_profiles` *(new in v5.0)*
Named sets of risk management parameters. Each account selects one profile.

| Column | Type | Description |
|---|---|---|
| `profile_id` | INTEGER PK | Auto-increment |
| `profile_name` | TEXT UNIQUE | Human label (e.g., `Blue Guardian Instant Standard`, `FTMO Standard`) |
| `is_default` | BOOLEAN | Exactly one row should have `is_default = true`. Fallback for accounts with no explicit assignment. |
| `max_risk_per_trade_pct` | REAL | Max combined portfolio risk as % of initial balance (e.g., `1.0` = 1%) |
| `daily_loss_pct` | REAL | Daily loss limit as % of initial balance (e.g., `3.0`). The floor is **set once at the 5pm EST reset and is completely static for the entire trading day**. Intraday equity movements do not affect it. |
| `daily_trailing` | BOOLEAN | Controls how `daily_start_balance` is set at each 5pm reset. `true` = use `max(balance, equity)` at the reset moment — so an open winning trade held through reset raises next day's floor. `false` = use only closing balance. For Blue Guardian: `true`. |
| `overall_loss_pct` | REAL | Maximum overall drawdown as % of initial balance (e.g., `6.0`). |
| `overall_trailing` | BOOLEAN | If `true`: overall floor trails upward. If `false`: static floor locked at `initial_balance × (1 − overall_loss_pct%)`. |
| `overall_trail_from_closed_balance` | BOOLEAN | Only relevant when `overall_trailing = true`. If `true`: floor trails from `highest_banked_balance` (closed trades only — Blue Guardian model). If `false`: floor trails from `all_time_high_equity` (includes floating P&L). |
| `profit_lock_pct` | REAL | Balance % gain above initial that triggers the profit lock (e.g., `6.0` = +6%). Set to `null` to disable. |
| `profit_lock_floor_pct` | REAL | Once profit lock triggers, the permanent floor = `initial_balance × (1 − profit_lock_floor_pct / 100)`. Set to `0.0` to lock the floor exactly at `initial_balance` (i.e., never lose original capital). |
| `payout_buffer_pct` | REAL | Minimum % of `initial_balance` that must remain above the floor after any withdrawal (e.g., `1.0` = 1% buffer). Withdrawable = `current_balance − floor − (initial_balance × payout_buffer_pct / 100)`. Set to `0.0` to disable buffer. |
| `max_concurrent_trades` | INTEGER | Default concurrent trade limit for accounts using this profile. Can be overridden per-account. |
| `commission_per_lot` | REAL | Round-trip commission in USD per lot (e.g., `6.0`). |
| `safety_buffer_pct` | REAL | Pre-trade buffer applied to remaining daily room before comparison (e.g., `10.0` = 10%). |
| `created_at` | TIMESTAMP | |
| `notes` | TEXT | Optional notes |

**Built-in default profile (inserted on init, `is_default = true`):**

```sql
INSERT OR IGNORE INTO risk_profiles (
    profile_name, is_default,
    max_risk_per_trade_pct, daily_loss_pct, daily_trailing,
    overall_loss_pct, overall_trailing, overall_trail_from_closed_balance,
    profit_lock_pct, profit_lock_floor_pct, payout_buffer_pct,
    max_concurrent_trades, commission_per_lot, safety_buffer_pct
) VALUES (
    'Blue Guardian Instant Standard', 1,
    1.0, 3.0, 1,
    6.0, 1, 1,
    6.0, 0.0, 1.0,
    5, 6.0, 10.0
);
```

**Blue Guardian Instant Standard – Rule Summary:**
- Daily 3% static intraday floor: floor = `daily_start_balance − 3% of initial`. The floor is **fixed for the entire trading day** from the moment of the 5pm EST reset. Intraday equity peaks do NOT move it. The only thing that sets the next day's floor higher is if equity > balance at the 5pm snapshot (an open winning position held through reset).
- Because Mirror Pupil force-closes all trades at 4:45pm EST, accounts are always flat at the 5pm snapshot. So `daily_start_balance` always equals the closing balance and the daily floor is simply: `closing_balance_at_5pm − 3% of initial`.
- Overall 6% trailing from **closed balance only**: floor = `highest_banked_balance − 6% of initial`. Only moves up when trades are banked.
- Profit lock at **+6% balance**: once `current_balance ≥ initial × 1.06`, the overall floor permanently locks at `initial_balance` (0% below — original capital is fully protected).
- Payout buffer: 1% of initial must remain above the floor after any withdrawal. Withdrawable = `current_balance − floor − (initial × 1%)`.
- All trades force-closed at **4:45 PM EST** (15 minutes before the 5pm reset) to ensure a flat account at the daily benchmark snapshot.

#### `accounts`

| Column | Type | Description |
|---|---|---|
| `account_key` | TEXT PK | `credential_email:account_id` |
| `credential_key` | TEXT | TradeLocker login email |
| `tl_account_id` | TEXT | Sub-account ID from TradeLocker |
| `tl_email` | TEXT | TradeLocker login email |
| `tl_password` | TEXT | Encrypted password |
| `tl_server` | TEXT | `live` or `demo` |
| `display_name` | TEXT | Optional human label for the GUI |
| `initial_balance` | REAL | Starting balance (updated only on formal payout reset) |
| `current_balance` | REAL | Last known balance. Updated when: (a) a trade closes, or (b) a withdrawal is detected via balance reconciliation. Never updated from floating P&L alone. |
| `highest_banked_balance` | REAL | Highest ever **closed/banked** balance. Updated in `on_trade_closed()` only when `current_balance > highest_banked_balance`. Drives the overall trailing floor. **Never updated by withdrawals** — a withdrawal brings `current_balance` closer to the floor but does not lower the floor itself. |
| `profit_locked` | BOOLEAN | Overall floor profit lock reached and permanently activated |
| `daily_pnl` | REAL | Cumulative closed P&L for today's trading session (since last 5pm reset) |
| `daily_start_balance` | REAL | **The sole daily floor reference.** Set at each 5pm EST reset to `current_balance` (account is always flat at reset due to 4:45pm force close). Daily floor = `daily_start_balance − (initial_balance × daily_loss_pct%)`. **Completely static between resets. Never touched intraday.** |
| `last_synced_balance` | REAL | Last balance value polled from TradeLocker API (every 5 minutes). Compared to `current_balance` to detect withdrawals: if actual < `last_synced_balance` and no trade closed to account for the difference → withdrawal event fires. |
| `cycle_start_date` | DATE | Date of the most recent formal payout reset. Defines the start of the current cycle for consistency score calculation. |
| `cycle_best_day_pnl` | REAL | Highest single-day P&L recorded since `cycle_start_date`. Updated at each 5pm reset if today's P&L exceeds current best. This is the numerator of the consistency score. |
| `paused` | BOOLEAN | Manual pause — no new trades opened while paused |
| `breached` | BOOLEAN | Hard breach — all trading permanently halted until manually cleared |
| `risk_profile_id` | INTEGER | FK → `risk_profiles.profile_id`. If `null`, uses the default profile. |
| `max_concurrent_trades_override` | INTEGER | Per-account override for max concurrent trades. If `null`, profile value is used. |

#### `active_trades`
*(Adds `channel_id` column for numeric channel identification)*

| Column | Type | Description |
|---|---|---|
| `trade_id` | INTEGER PK | |
| `account_key` | TEXT | FK → `accounts` |
| `channel_id` | INTEGER | FK → `channels.channel_id` *(was `channel TEXT` in v4.0)* |
| `signal_id` | TEXT | Format: `B_<msg_id>` or `F_<msg_id>` (prefix is channel's short code) |
| `sub_signal_id` | TEXT | `B_<msg_id>_tp1`, `_tp2`, etc. |
| `symbol` | TEXT | Normalized symbol |
| `direction` | TEXT | `BUY` or `SELL` |
| `entry_price` | REAL | Actual fill price |
| `sl` | REAL | Current SL |
| `tp` | REAL | Current TP (nullable) |
| `lot_size` | REAL | |
| `entry_time` | TIMESTAMP | |
| `tl_order_id` | TEXT | |
| `tl_position_id` | TEXT | |
| `status` | TEXT | `pending`, `filled`, `failed`, `partially_filled` |
| `tp1_hit` | BOOLEAN | |
| `risk_usd` | REAL | |

#### `waiting_room`
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `channel_id` | INTEGER | FK → `channels.channel_id` |
| `symbol` | TEXT | |
| `direction` | TEXT | |
| `entry_msg_id` | INTEGER | Telegram message ID |
| `entry_time` | TIMESTAMP | |
| `expires_at` | TIMESTAMP | `entry_time + 15 minutes` |

#### `trade_history`
| Column | Type | Description |
|---|---|---|
| `history_id` | INTEGER PK | |
| `account_key` | TEXT | |
| `channel_id` | INTEGER | FK → `channels.channel_id` |
| `signal_id` | TEXT | |
| `sub_signal_id` | TEXT | |
| `symbol` | TEXT | |
| `direction` | TEXT | |
| `entry_price` | REAL | |
| `exit_price` | REAL | |
| `sl` | REAL | |
| `tp` | REAL | |
| `lot_size` | REAL | |
| `entry_time` | TIMESTAMP | |
| `exit_time` | TIMESTAMP | |
| `pnl` | REAL | |
| `outcome` | TEXT | `WIN`, `LOSS`, `BE` |
| `close_reason` | TEXT | `TP_HIT`, `SL_HIT`, `MANUAL`, `AUTONOMOUS`, `EOD`, `WEEKEND` |

#### `profitable_days`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `account_key` | TEXT | FK → `accounts.account_key` |
| `date` | DATE | Trading day date (boundary: 5pm ET) |
| `pnl` | REAL | Net P&L for the day (after commission) |
| `is_profitable_day` | BOOLEAN | `true` if P&L ≥ 0.25% of account's `initial_balance` |

#### `message_cache` (ephemeral — entries older than 2 minutes auto-deleted)

| Column | Type | Description |
|---|---|---|
| `msg_id` | INTEGER | Telegram message ID |
| `channel_id` | INTEGER | FK → `channels.channel_id` |
| `processed_at` | TIMESTAMP | When the message was processed |

---

### 2.6 Database Initialization, Migration & Daily Clearing

**Schema version:** 5

```python
SCHEMA_V5 = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS schema_version (...);

CREATE TABLE IF NOT EXISTS channels (
    channel_id     INTEGER PRIMARY KEY,
    display_name   TEXT NOT NULL,
    entry_logic_module      TEXT NOT NULL,
    management_logic_module TEXT NOT NULL,
    priority       INTEGER NOT NULL DEFAULT 10,
    enabled        BOOLEAN NOT NULL DEFAULT 1,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS risk_profiles (
    profile_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name            TEXT UNIQUE NOT NULL,
    is_default              BOOLEAN NOT NULL DEFAULT 0,
    max_risk_per_trade_pct  REAL NOT NULL DEFAULT 1.0,
    daily_loss_pct          REAL NOT NULL DEFAULT 3.0,
    daily_trailing          BOOLEAN NOT NULL DEFAULT 1,
    overall_loss_pct        REAL NOT NULL DEFAULT 6.0,
    overall_trailing        BOOLEAN NOT NULL DEFAULT 1,
    profit_lock_pct         REAL,
    profit_lock_floor_pct   REAL,
    max_concurrent_trades   INTEGER NOT NULL DEFAULT 5,
    commission_per_lot      REAL NOT NULL DEFAULT 6.0,
    safety_buffer_pct       REAL NOT NULL DEFAULT 10.0,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes                   TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    account_key                   TEXT PRIMARY KEY,
    credential_key                TEXT NOT NULL,
    tl_account_id                 TEXT NOT NULL,
    tl_email                      TEXT NOT NULL,
    tl_password                   TEXT NOT NULL,
    tl_server                     TEXT NOT NULL DEFAULT 'live',
    display_name                  TEXT,
    initial_balance               REAL,
    current_balance               REAL,
    all_time_high_equity          REAL,
    profit_locked                 BOOLEAN DEFAULT 0,
    daily_pnl                     REAL DEFAULT 0,
    daily_start_balance           REAL,
    last_synced_balance           REAL,
    cycle_start_date              DATE,
    cycle_best_day_pnl            REAL DEFAULT 0,
    paused                        BOOLEAN DEFAULT 0,
    breached                      BOOLEAN DEFAULT 0,
    risk_profile_id               INTEGER REFERENCES risk_profiles(profile_id),
    max_concurrent_trades_override INTEGER
);

CREATE TABLE IF NOT EXISTS channel_subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_key TEXT NOT NULL REFERENCES accounts(account_key) ON DELETE CASCADE,
    channel_id  INTEGER NOT NULL REFERENCES channels(channel_id) ON DELETE CASCADE,
    enabled     BOOLEAN NOT NULL DEFAULT 1,
    UNIQUE(account_key, channel_id)
);

CREATE TABLE IF NOT EXISTS active_trades (...);
CREATE TABLE IF NOT EXISTS waiting_room (...);
CREATE TABLE IF NOT EXISTS trade_history (...);
CREATE TABLE IF NOT EXISTS profitable_days (...);
CREATE TABLE IF NOT EXISTS message_cache (...);
"""
```

**Migration entries added for v5.0:**

```python
MIGRATIONS = {
    # ... v1–v4 migrations unchanged ...
    5: """
        ALTER TABLE active_trades ADD COLUMN channel_id INTEGER;
        ALTER TABLE waiting_room ADD COLUMN channel_id INTEGER;
        ALTER TABLE trade_history ADD COLUMN channel_id INTEGER;
        ALTER TABLE accounts ADD COLUMN risk_profile_id INTEGER;
        ALTER TABLE accounts ADD COLUMN max_concurrent_trades_override INTEGER;
        ALTER TABLE accounts ADD COLUMN display_name TEXT;
        ALTER TABLE accounts ADD COLUMN highest_banked_balance REAL;
        ALTER TABLE accounts ADD COLUMN last_synced_balance REAL;
        ALTER TABLE accounts ADD COLUMN cycle_start_date DATE;
        ALTER TABLE accounts ADD COLUMN cycle_best_day_pnl REAL DEFAULT 0;
        ALTER TABLE risk_profiles ADD COLUMN overall_trail_from_closed_balance BOOLEAN NOT NULL DEFAULT 1;
        ALTER TABLE risk_profiles ADD COLUMN payout_buffer_pct REAL NOT NULL DEFAULT 1.0;
        UPDATE accounts SET highest_banked_balance = initial_balance WHERE highest_banked_balance IS NULL;
        UPDATE accounts SET last_synced_balance = current_balance WHERE last_synced_balance IS NULL;
        UPDATE accounts SET cycle_start_date = DATE('now') WHERE cycle_start_date IS NULL;
        UPDATE accounts SET cycle_best_day_pnl = 0 WHERE cycle_best_day_pnl IS NULL;
    """,
}
```

**EOD Force Close at 4:45 PM EST (daily):**

All open trades across all active accounts are force-closed 15 minutes before the 5pm EST daily benchmark snapshot. This ensures every account is completely flat when the daily floor resets.

**Daily Reset Sequence at 5:00 PM EST:**
1. *(Trades already closed by the 4:45pm force close.)*
2. Move any remaining `active_trades` → `trade_history` (edge-case catch-all).
3. Clear `waiting_room`.
4. For each account, set the new `daily_start_balance`:
   ```python
   # Since all trades are force-closed at 4:45pm, equity = balance at this point.
   # If somehow a trade is still open, take max(balance, equity) per Blue Guardian rules.
   equity_at_reset = account.current_balance + get_floating_pnl(account)
   account.daily_start_balance = max(account.current_balance, equity_at_reset)
   ```
5. Calculate daily P&L → insert `profitable_days`.
6. Reset: `daily_pnl = 0`.
7. Sync `last_synced_balance = current_balance`.
8. Delete stale `message_cache` entries.

> **Key point:** `daily_start_balance` is the ONLY daily floor reference. There is no intraday peak tracking. The floor is `daily_start_balance − (initial_balance × daily_loss_pct%)` and it does not change again until the next 5pm reset.

---

### 2.7 Risk Management (Profile-Based)

Risk rules are no longer hardcoded. Before executing any trade, the bot resolves the account's active risk profile:

```python
def get_risk_profile(account_key: str) -> RiskProfile:
    account = db.get_account(account_key)
    if account.risk_profile_id:
        return db.get_risk_profile(account.risk_profile_id)
    return db.get_default_risk_profile()
```

All limit calculations use fields from the resolved `RiskProfile` object. The **Blue Guardian Instant Standard** profile is the built-in default.

**How the two drawdown systems work:**

- **Daily floor** — Set once per day at the 5pm EST reset. Static for the entire trading day. Formula: `daily_floor = daily_start_balance − (initial_balance × daily_loss_pct%)`. Since Mirror Pupil force-closes all trades at 4:45pm, `daily_start_balance` is always simply the closing balance. The floor does **not** move intraday regardless of floating peaks. The only thing that raises the next day's floor is having a higher balance at 5pm.

- **Overall floor** — Trails from `highest_banked_balance` (closed trades only, per Blue Guardian). Only moves up when a trade closes and `current_balance > highest_banked_balance`. Floating P&L never affects it. Locks permanently at `initial_balance` once profit lock triggers.

**Breach monitoring** (runs every 60 seconds and on every trade open/close event):

```python
async def check_risk_limits(account):
    profile = get_risk_profile(account.account_key)
    current_equity = account.current_balance + get_floating_pnl(account)

    # --- Daily Loss ---
    # Floor is STATIC for the day — set at 5pm reset, never changed intraday.
    # daily_start_balance is the sole reference. No peak tracking here.
    daily_floor = (
        account.daily_start_balance
        - (account.initial_balance * profile.daily_loss_pct / 100)
    )
    if current_equity <= daily_floor:
        account.breached = True
        await close_all_trades(account)
        await notify_gui(
            f"Account {account.account_key} DAILY LOSS BREACHED "
            f"(equity {current_equity:.2f} ≤ floor {daily_floor:.2f})",
            severity="CRITICAL"
        )
        return

    # --- Overall Loss ---
    if profile.overall_trailing:
        if profile.overall_trail_from_closed_balance:
            trail_ref = account.highest_banked_balance
        else:
            # Non-Blue-Guardian profiles may trail from all-time equity peak.
            # For those, we track all_time_high_equity separately.
            trail_ref = account.highest_banked_balance  # fallback; use ATH equity if profile has it
        overall_floor = trail_ref - (account.initial_balance * profile.overall_loss_pct / 100)
    else:
        overall_floor = account.initial_balance * (1 - profile.overall_loss_pct / 100)

    # --- Profit Lock ---
    # Triggered when BALANCE (not equity) reaches the lock threshold.
    if profile.profit_lock_pct and not account.profit_locked:
        if account.current_balance >= account.initial_balance * (1 + profile.profit_lock_pct / 100):
            account.profit_locked = True
            logger.info(
                f"[Account {account.account_key}] Profit lock activated at "
                f"balance {account.current_balance:.2f}"
            )

    if account.profit_locked:
        # profit_lock_floor_pct = 0.0 → floor locks exactly at initial_balance
        locked_floor = account.initial_balance * (1 - (profile.profit_lock_floor_pct or 0) / 100)
        overall_floor = max(overall_floor, locked_floor)

    if current_equity <= overall_floor:
        account.breached = True
        await close_all_trades(account)
        await notify_gui(
            f"Account {account.account_key} OVERALL DRAWDOWN BREACHED "
            f"(equity {current_equity:.2f} ≤ floor {overall_floor:.2f})",
            severity="CRITICAL"
        )

def calculate_withdrawable(account) -> float:
    """
    Maximum safe withdrawal = current_balance − overall_floor − payout_buffer.
    The floor does NOT move when a withdrawal is made (balance drops toward floor).
    The buffer ensures a safety margin remains above the floor post-withdrawal.
    """
    profile = get_risk_profile(account.account_key)
    payout_buffer = account.initial_balance * (profile.payout_buffer_pct / 100)

    if account.profit_locked:
        floor = account.initial_balance * (1 - (profile.profit_lock_floor_pct or 0) / 100)
    elif profile.overall_trailing:
        trail_ref = account.highest_banked_balance
        floor = trail_ref - (account.initial_balance * profile.overall_loss_pct / 100)
    else:
        floor = account.initial_balance * (1 - profile.overall_loss_pct / 100)

    withdrawable = account.current_balance - floor - payout_buffer
    return max(withdrawable, 0.0)
```

**`highest_banked_balance` is updated in the trade close handler:**

```python
async def on_trade_closed(account, closed_pnl: float):
    account.current_balance += closed_pnl
    account.daily_pnl += closed_pnl
    if account.current_balance > account.highest_banked_balance:
        account.highest_banked_balance = account.current_balance
    db.update_account(account)
    await check_risk_limits(account)
```

**5pm EST daily reset handler:**

```python
async def daily_reset(account):
    """
    Called at exactly 5:00 PM EST after all trades are confirmed closed.
    Sets the static daily floor reference for the next 24 hours.
    Also updates the consistency score best-day tracker.
    """
    today_pnl = account.daily_pnl

    # Update best single-day P&L for this cycle (consistency score numerator)
    if today_pnl > account.cycle_best_day_pnl:
        account.cycle_best_day_pnl = today_pnl

    # Record profitable day
    is_profitable = today_pnl >= account.initial_balance * 0.0025  # 0.25%
    db.insert_profitable_day(account.account_key, today_pnl, is_profitable)

    # Set new daily floor reference — account is flat, so equity = balance
    account.daily_start_balance = account.current_balance
    account.last_synced_balance = account.current_balance
    account.daily_pnl = 0
    db.update_account(account)
```

---

### 2.9 Withdrawal Detection & Balance Reconciliation

Mirror Pupil polls each account's actual balance from TradeLocker every **5 minutes** via `tl_client.get_account()` and compares the result against `last_synced_balance`. A withdrawal is inferred when the actual balance is meaningfully lower than recorded and no trade has closed since the last poll to account for the difference.

```python
WITHDRAWAL_THRESHOLD = 0.50  # Ignore fluctuations smaller than $0.50 (rounding/fees)

async def reconcile_balance(account):
    """
    Runs every 5 minutes per account.
    Detects external balance changes (withdrawals) that didn't come from a closed trade.
    """
    actual_balance = await tl_client.get_account_balance(account.tl_account_id)
    expected_balance = account.last_synced_balance
    delta = expected_balance - actual_balance

    if delta > WITHDRAWAL_THRESHOLD:
        # Balance dropped externally — treat as withdrawal
        await handle_withdrawal_detected(account, actual_balance, delta)
    elif actual_balance > account.current_balance + WITHDRAWAL_THRESHOLD:
        # Balance increased without a closed trade (e.g., deposit, correction)
        # Update current_balance only — do not touch highest_banked_balance
        account.current_balance = actual_balance
        account.last_synced_balance = actual_balance
        db.update_account(account)
        await notify_gui(
            f"Balance increase detected on {account.account_key}: +${actual_balance - account.current_balance:.2f}",
            severity="INFO", account_key=account.account_key
        )
    else:
        # Normal — just sync
        account.last_synced_balance = actual_balance
        db.update_account(account)

async def handle_withdrawal_detected(account, actual_balance: float, withdrawn: float):
    """
    A withdrawal has occurred. Rules:
    - current_balance updates to actual_balance (balance is lower now).
    - highest_banked_balance does NOT change (floor stays where it is).
    - daily_start_balance does NOT change (daily floor stays where it is).
    - profit_locked state does NOT change.
    - GUI recalculates withdrawable amount immediately (it will be smaller).
    - WARNING notification fires showing new headroom.
    """
    account.current_balance = actual_balance
    account.last_synced_balance = actual_balance
    db.update_account(account)

    # Recalculate new headroom after withdrawal
    new_withdrawable = calculate_withdrawable(account)
    overall_floor = get_overall_floor(account)
    daily_floor = get_daily_floor(account)
    overall_room = actual_balance - overall_floor
    daily_room = account.current_balance + get_floating_pnl(account) - daily_floor

    await notify_gui(
        f"Withdrawal detected on {account.account_key}: −${withdrawn:.2f}. "
        f"Balance: ${actual_balance:.2f}. "
        f"Overall room: ${overall_room:.2f}. "
        f"Daily room: ${daily_room:.2f}. "
        f"New withdrawable: ${new_withdrawable:.2f}.",
        severity="WARNING",
        account_key=account.account_key
    )

    # Push balance_updated WebSocket event so GUI re-renders immediately
    await ws_broadcast({
        "type": "balance_updated",
        "account_key": account.account_key,
        "current_balance": actual_balance,
        "daily_pnl": account.daily_pnl,
        "equity": actual_balance + get_floating_pnl(account),
        "withdrawable": new_withdrawable,
        "overall_floor": overall_floor,
        "daily_floor": daily_floor,
    })
```

**What does and does not change on withdrawal:**

| Field | On Withdrawal | Reason |
|---|---|---|
| `current_balance` | ✅ Updates to new actual balance | Balance is genuinely lower |
| `last_synced_balance` | ✅ Updates | Sync reference |
| `highest_banked_balance` | ❌ Unchanged | Floor never moves down — you withdrew, not lost |
| `daily_start_balance` | ❌ Unchanged | Daily floor is fixed until 5pm reset |
| `profit_locked` | ❌ Unchanged | Lock status is not affected by a withdrawal |
| `initial_balance` | ❌ Unchanged | Only changes on formal payout reset |

**Formal Payout Reset vs. Withdrawal — the two distinct operations:**

| Action | When to use | What resets |
|---|---|---|
| **Withdrawal (auto-detected)** | You took a payout mid-cycle without Blue Guardian restarting your metrics | Only `current_balance` + `last_synced_balance`. Everything else unchanged. |
| **Formal Payout Reset (GUI button)** | Blue Guardian has formally restarted your account metrics (new cycle) | Everything: `initial_balance`, `highest_banked_balance`, `daily_start_balance`, `profit_locked`, `cycle_start_date`, `cycle_best_day_pnl`. |

```python
def apply_payout_reset(account, new_balance: float):
    """Formal cycle restart — use only when Blue Guardian has reset account metrics."""
    account.initial_balance = new_balance
    account.current_balance = new_balance
    account.highest_banked_balance = new_balance
    account.profit_locked = False
    account.daily_start_balance = new_balance
    account.last_synced_balance = new_balance
    account.daily_pnl = 0
    account.cycle_start_date = date.today()
    account.cycle_best_day_pnl = 0
    db.update_account(account)
```

---

### 2.10 Consistency Score (20% Rule)

The consistency score ensures no single trading day dominates the cycle's total profit. Blue Guardian (and most Instant prop firms) will flag or fail an account if one day's profit exceeds 20% of the total cycle profit — it signals lucky one-off trades rather than consistent performance.

**Formula:**

```
consistency_score = (cycle_best_day_pnl / cycle_total_pnl) × 100
```

- `cycle_best_day_pnl` — highest single-day P&L recorded since `cycle_start_date` (stored in `accounts` table, updated at each 5pm reset).
- `cycle_total_pnl` — sum of all daily P&L records in `profitable_days` since `cycle_start_date`.

```python
def calculate_consistency_score(account) -> dict:
    """
    Returns the consistency score and its components for GUI display.
    Returns None if cycle_total_pnl <= 0 (undefined — can't calculate ratio).
    """
    rows = db.query(
        "SELECT pnl FROM profitable_days "
        "WHERE account_key = ? AND date >= ? ORDER BY date",
        (account.account_key, account.cycle_start_date)
    ).fetchall()

    cycle_total_pnl = sum(r['pnl'] for r in rows)
    best_day_pnl = account.cycle_best_day_pnl

    if cycle_total_pnl <= 0:
        return {"score": None, "best_day": best_day_pnl, "total": cycle_total_pnl, "status": "undefined"}

    score = (best_day_pnl / cycle_total_pnl) * 100
    status = "safe" if score < 15 else ("warning" if score < 20 else "breach")
    return {
        "score": round(score, 1),
        "best_day": best_day_pnl,
        "total": cycle_total_pnl,
        "status": status       # "safe" | "warning" | "breach"
    }
```

**Status thresholds:**

| Score | Status | GUI Colour |
|---|---|---|
| < 15% | Safe | Green |
| 15% – <20% | Warning | Amber |
| ≥ 20% | Breach risk | Red |
| Undefined (total ≤ 0) | — | Grey / no bar |

**When `cycle_best_day_pnl` is updated:**

At each 5pm reset in `daily_reset()`:
```python
if today_pnl > account.cycle_best_day_pnl:
    account.cycle_best_day_pnl = today_pnl
```

The best day value only ever moves up within a cycle. It resets to `0` on a formal payout reset.

---

### 2.11 Price Delta Risk Calculation & Prop Firm Limit Validation

#### 2.11.1 Core Risk Formula

> **Risk (quote currency) = |Entry Price – Stop Loss Price| × Contract Size × Lot Size**

#### 2.11.2 Currency Conversion

| Case | Conversion |
|---|---|
| Quote = USD | No conversion |
| USD is base | Divide by current pair price |
| USD is quote of cross | Multiply by cross-to-USD rate |

#### 2.11.3 Indices

> **Risk (USD) = ( |Entry – SL| / Tick Size ) × Tick Value × Lot Size**

#### 2.11.4 Pre-Trade Validation

All checks use values from the account's resolved `RiskProfile`:

1. **Combined Risk Limit** — existing portfolio risk + new trade risk ≤ `initial_balance × profile.max_risk_per_trade_pct / 100`.
2. **Daily Loss Limit** — remaining daily room = `current_equity − daily_floor`; buffered by `profile.safety_buffer_pct`. If remaining room after buffer is less than the new trade's risk → reject.
3. **Overall Loss Limit** — remaining overall room = `current_equity − overall_floor` (where `overall_floor` uses `highest_banked_balance` if `overall_trail_from_closed_balance = true`, else `all_time_high_equity`). If remaining room is less than the new trade's risk → reject.

All three checks reject the trade for that specific account only; other accounts continue independently.

#### 2.11.5 Payout Reset Mechanics

On payout reset (operator confirms withdrawal has been processed and enters new starting balance):

```python
def apply_payout_reset(account, new_balance: float):
    """Formal cycle restart — use only when Blue Guardian has reset account metrics."""
    account.initial_balance = new_balance
    account.current_balance = new_balance
    account.highest_banked_balance = new_balance
    account.profit_locked = False
    account.daily_start_balance = new_balance
    account.last_synced_balance = new_balance
    account.daily_pnl = 0
    account.cycle_start_date = date.today()
    account.cycle_best_day_pnl = 0
    db.update_account(account)
```

The GUI Payout Reset button displays the `calculate_withdrawable()` value prominently and requires the operator to enter the post-withdrawal balance. It warns if the entered value would place the account below `floor + payout_buffer`.

---

### 2.12 Channel Priority & Concurrent Trade Limit

**Default concurrent trade limit:** Sourced from the account's active risk profile (`profile.max_concurrent_trades`). Can be overridden per-account via `accounts.max_concurrent_trades_override`.

```python
def get_max_concurrent_trades(account_key: str) -> int:
    account = db.get_account(account_key)
    if account.max_concurrent_trades_override:
        return account.max_concurrent_trades_override
    return get_risk_profile(account_key).max_concurrent_trades
```

**Priority logic:**

- If `open_trades < max_concurrent`: execute immediately regardless of channel.
- If `open_trades == max_concurrent` and multiple channels signal simultaneously: the channel with the **lowest `channels.priority` integer value** executes; other channels are queued in a FIFO buffer per priority level.
- Queued signals expire after **30 minutes**.

**Channel priority is configurable** from the GUI Settings → Channel Management page (integer field per channel row).

---

### 2.13 Profitable Days Tracking

- **Window:** Rolling 30 calendar days (not a fixed calendar month).
- **Day boundary:** 5pm ET (same as the daily reset).
- **Profitable day definition:** Net P&L ≥ 0.25% of the account's `initial_balance` after commissions.
- **Paused day:** If an account is paused for the entire trading day, the day is still recorded with P&L = $0 (counted as not profitable).
- **GUI warning:** A warning banner is shown on the account card when fewer than 3 profitable days remain available in the rolling 30-day window to meet the 5-day requirement.

```python
def count_profitable_days(account_key: str) -> int:
    cutoff = datetime.now() - timedelta(days=30)
    return db.query(
        "SELECT COUNT(*) FROM profitable_days "
        "WHERE account_key = ? AND date >= ? AND is_profitable_day = 1",
        (account_key, cutoff.date())
    ).fetchone()[0]
```

---

### 2.14 Error Notification System

All error and operational notifications are sent to the **GUI notification panel** — displayed as in-app alerts at appropriate severity levels. There is no dependency on a separate Telegram admin bot channel.

**Severity Levels:**

| Severity | Trigger Examples | GUI Action |
|---|---|---|
| `INFO` | Trade executed, management action applied | Log only (accessible in log viewer) |
| `WARNING` | Daily loss at 2% (1% away from limit), profitable days behind target, payout withdrawal would breach buffer | Yellow banner / toast notification |
| `HIGH` | Trade execution failed after 3 retries, token refresh failed once, partial close failed | Orange persistent alert in notification panel |
| `CRITICAL` | Account daily loss breached, overall drawdown breached, all retries exhausted, bot crash | Red persistent banner on every page until dismissed + sound alert if TWA supports it |

```python
async def notify_gui(message: str, severity: str = "INFO", account_key: str = None):
    """Push notification to the GUI notification system via WebSocket."""
    payload = {
        "type": "notification",
        "severity": severity,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "account_key": account_key
    }
    await ws_broadcast(payload)
    logger.log(getattr(logging, severity, logging.INFO), message)
```

---

### 2.15 Signal ID Generation

| ID Type | Format | Example |
|---|---|---|
| Channel signal | `<prefix>_<telegram_msg_id>` | `B_104521`, `F_88302` |
| Multi-TP sub-signal | `<signal_id>_tp<n>` | `B_104521_tp1` |
| Re-entry | `<parent_signal_id>_re<n>` | `B_104521_re1` |

The prefix is the channel's `short_code` (stored in the plugin registration — `B` for BillirichyFX, `F` for Firepips). When adding a new channel via the GUI, a short code is also specified (up to 4 alphanumeric characters).

---

### 2.16 Dry-Run / Paper Mode

**Purpose:** Validate the entire Mirror Pupil system — parser, context matching, management logic, risk checks — against live channel messages without placing any real orders.

**Activation:** Set `DRY_RUN=true` in environment variables, or toggle on the GUI Bot Control page.

**Behaviour in dry-run:**

- All signal parsing, context matching, and risk calculations run normally.
- Order placement calls are replaced with log entries:
  `[DRY-RUN] Would place: BUY XAUUSD 0.1 lot @ 1960.00 SL=1950.00 TP=1980.00`
- `active_trades` is populated normally (so management matching continues to work).
- `trade_history` is populated on simulated "close."
- P&L is simulated using mid-price at the time the trade would have closed.
- The GUI displays a prominent **"DRY-RUN MODE"** banner on every page.
- Risk breach checks still run — a breached account in dry-run will still be flagged in the GUI.

**Recommendation:** Run in dry-run mode for a minimum of **3 trading days** and verify at least 20 signals per channel before switching to live execution.

---

### 2.17 Channel Plugin Architecture

#### Overview

Every channel source is implemented as a **ChannelPlugin** — a Python class conforming to a shared abstract interface. The bot's core infrastructure is completely channel-agnostic. Plugins are stored as modules under `channels/` and registered in the `channels` database table.

#### ChannelPlugin Abstract Base Class

```python
# channels/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedSignal:
    channel_id: int
    msg_id: int
    symbol: str
    direction: str          # 'BUY' or 'SELL'
    entry_price: Optional[float]
    sl: Optional[float]
    tp: Optional[list[float]]   # list supports multi-TP
    order_type: str         # 'MARKET', 'LIMIT', 'STOP'
    is_reentry: bool
    raw_text: str

@dataclass
class ParsedManagement:
    channel_id: int
    msg_id: int
    reply_to_msg_id: Optional[int]
    action: str             # 'BREAKEVEN', 'CLOSE_ALL', 'MODIFY_SL', etc.
    new_sl: Optional[float]
    new_tp: Optional[float]
    close_pct: Optional[float]
    raw_text: str

class ChannelPlugin(ABC):
    """
    Every signal channel must implement this interface.
    An instance is created once per channel and held in the channel registry.
    """

    @property
    @abstractmethod
    def channel_id(self) -> int:
        """Numeric Telegram channel ID."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        ...

    @property
    @abstractmethod
    def signal_prefix(self) -> str:
        """Short code used in signal IDs, e.g. 'B', 'F'."""
        ...

    @abstractmethod
    def normalize_symbol(self, raw: str) -> Optional[str]:
        """Return normalized symbol or None if excluded."""
        ...

    @abstractmethod
    async def parse_entry(self, message) -> Optional[ParsedSignal]:
        """
        Parse a new message as a potential entry signal.
        Returns ParsedSignal if parseable, None to ignore.
        """
        ...

    @abstractmethod
    async def parse_management(self, message) -> Optional[ParsedManagement]:
        """
        Parse a message (or edit) as a management action.
        Returns ParsedManagement if parseable, None to ignore.
        """
        ...

    async def route_message(self, message, is_edit: bool = False):
        """
        Default routing logic — channels can override if needed.
        1. If reply to open trade → management.
        2. If reply to waiting room entry → waiting room completion.
        3. Else → attempt entry parsing.
        Edited messages always try management first, then waiting room.
        """
        msg_id = message.id
        reply_to = getattr(message, 'reply_to_msg_id', None)

        if is_edit:
            if db.is_waiting_room_entry(msg_id, self.channel_id):
                await self._handle_waiting_room_completion(message)
                return
            mgmt = await self.parse_management(message)
            if mgmt:
                await handle_management_action(mgmt, self.channel_id)
            return

        if reply_to and db.is_active_trade_entry(reply_to, self.channel_id):
            mgmt = await self.parse_management(message)
            if mgmt:
                await handle_management_action(mgmt, self.channel_id)
            return

        if reply_to and db.is_waiting_room_entry(reply_to, self.channel_id):
            await self._handle_waiting_room_completion(message)
            return

        # Try management keywords first (some channels post management without replying)
        mgmt = await self.parse_management(message)
        if mgmt:
            await handle_management_action(mgmt, self.channel_id)
            return

        signal = await self.parse_entry(message)
        if signal:
            await handle_entry_signal(signal, self.channel_id)

    async def _handle_waiting_room_completion(self, message):
        """Shared waiting room completion — called by route_message."""
        from core.waiting_room import attempt_waiting_room_completion
        await attempt_waiting_room_completion(message, self)
```

#### Channel Registry

```python
# channel_registry.py
from channels.billirichy.plugin import BillirichyPlugin
from channels.firepips.plugin import FirepipsPlugin

# Map: channel_id (int) → ChannelPlugin instance
_registry: dict[int, ChannelPlugin] = {}

def load_channels_from_db():
    """
    Called on startup and after any channel CRUD operation.
    Instantiates plugins for all enabled channels.
    """
    global _registry
    _registry.clear()
    for ch in db.get_all_channels():
        if not ch['enabled']:
            continue
        module = importlib.import_module(ch['entry_logic_module'])
        plugin_class = getattr(module, 'Plugin')  # convention: each module exposes 'Plugin'
        instance = plugin_class(
            channel_id=ch['channel_id'],
            display_name=ch['display_name']
        )
        _registry[ch['channel_id']] = instance
    logger.info(f"Channel registry loaded: {list(_registry.keys())}")

def get_plugin_for_channel(channel_id: int) -> Optional[ChannelPlugin]:
    return _registry.get(channel_id)

def get_enabled_channels() -> list[dict]:
    return db.get_channels(enabled_only=True)
```

#### Built-in Plugin Structure

```
channels/
├── base.py                   # ChannelPlugin ABC + ParsedSignal/Management dataclasses
├── billirichy/
│   ├── __init__.py
│   ├── plugin.py             # BillirichyPlugin(ChannelPlugin) — exposes Plugin = BillirichyPlugin
│   ├── entry.py              # Entry parsing (Section 3 logic)
│   ├── management.py         # Management logic (Section 4 logic)
│   └── symbol_map.py         # Symbol normalization map
└── firepips/
    ├── __init__.py
    ├── plugin.py             # FirepipsPlugin(ChannelPlugin)
    ├── entry.py              # Entry parsing (Section 5 logic)
    ├── management.py         # Management logic (Section 6 logic)
    └── symbol_map.py
```

#### Adding a New Channel (GUI Workflow — No Code Needed for Existing Logic)

**If the new channel uses the same format as BillirichyFX or Firepips:**

1. Open Settings → Channel Management → **+ Add Channel**.
2. Enter the channel's numeric ID, display name, signal prefix, and priority.
3. From the **Entry Logic** dial, select **BillirichyFX Logic** or **Firepips Logic**.
4. From the **Management Logic** dial, select the same (or a different one if needed).
5. Tap **Add Channel**. Mirror Pupil immediately starts listening — no restart required.

**If the new channel has a unique signal format (requires a developer):**

1. A developer creates a new module directory under `channels/` (e.g., `channels/newprovider/`).
2. They implement `Plugin(ChannelPlugin)` in `plugin.py`.
3. The module is deployed to the server.
4. The operator adds the channel via the GUI as above, selecting **Custom** in the logic dial and typing the module path.
5. The new module appears automatically in the dial for all future channel additions once deployed.

#### Cloning Logic from an Existing Channel (GUI Flow)

When adding a new channel via the GUI, a **"Base on existing channel"** dropdown is presented. Selecting an existing channel pre-fills the entry and management module paths with that channel's values. This covers the case where a signal provider migrates to a new channel (new ID) but keeps the same message format — simply clone the logic from the old channel.

The old channel can then be disabled (toggle off) in the Channel Management table, while the new channel goes live.

---

### 2.18 Multi-Profile Risk Management System

#### Overview

Risk profiles are named, database-stored sets of parameters. There is always one profile marked `is_default = true` (the **Blue Guardian Instant Standard** by default). Accounts that have `risk_profile_id = null` automatically use the default.

Profiles can be created, edited, and deleted entirely from the GUI. Deleting a profile that is currently assigned to one or more accounts is blocked by the GUI with an error message listing the affected accounts. The user must reassign those accounts first.

#### RiskProfile Dataclass

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RiskProfile:
    profile_id: int
    profile_name: str
    is_default: bool
    max_risk_per_trade_pct: float        # e.g. 1.0
    daily_loss_pct: float                # e.g. 3.0
    daily_trailing: bool
    overall_loss_pct: float              # e.g. 6.0
    overall_trailing: bool
    overall_trail_from_closed_balance: bool   # True = Blue Guardian model
    profit_lock_pct: Optional[float]          # e.g. 6.0 or None
    profit_lock_floor_pct: Optional[float]    # e.g. 0.0 = lock at initial_balance
    payout_buffer_pct: float             # e.g. 1.0 — min % above floor to keep after withdrawal
    max_concurrent_trades: int           # e.g. 5
    commission_per_lot: float            # e.g. 6.0
    safety_buffer_pct: float             # e.g. 10.0
```

#### Profile Resolution

```python
def get_risk_profile(account_key: str) -> RiskProfile:
    account = db.get_account(account_key)
    pid = account.risk_profile_id
    if pid:
        profile = db.get_risk_profile(pid)
        if profile:
            return profile
    # Fall back to default
    return db.query_one(
        "SELECT * FROM risk_profiles WHERE is_default = 1"
    )
```

#### CRUD Operations

All profile CRUD is exposed via API and reflected in the GUI (see Section 7.4):

- **Create:** `POST /api/risk-profiles` — body with all profile fields. `is_default` cannot be set here; use the "Set as Default" action.
- **Read:** `GET /api/risk-profiles`, `GET /api/risk-profiles/{id}`
- **Update:** `PUT /api/risk-profiles/{id}` — partial update supported.
- **Delete:** `DELETE /api/risk-profiles/{id}` — fails (400) if any account has this `risk_profile_id`.
- **Set Default:** `POST /api/risk-profiles/{id}/set-default` — atomically sets `is_default = 1` on this profile and `= 0` on all others.

#### Profile Display in GUI

On each **Account Card** and **Account Detail Page**, the active risk profile name and key values are shown in a collapsible "Risk Profile" section, e.g.:

```
Risk Profile: Blue Guardian Instant Standard  [Change ▼]
  Daily limit:    3.0% trailing (equity-based at 5pm EST)
  Overall limit:  6.0% trailing from closed balance
  Profit lock:    +6.0% balance → floor locks at initial_balance
  Payout buffer:  1.0% above floor
  Max trades:     5
  Commission:     $6/lot
```

The **[Change ▼]** selector is a dropdown or segmented dial listing all available profiles. Selecting one immediately updates `accounts.risk_profile_id` via `PUT /api/accounts/{key}/risk-profile`.

---

## 3. BillirichyFX – Entry Logic

The BillirichyFX logic is implemented as `BillirichyPlugin(ChannelPlugin)` in `channels/billirichy/plugin.py`. All `channel` string references from the original spec are replaced by `channel_id` integer references (value: `-1001859598768`). This logic is also available as a selectable option on the logic dial when adding new channels via the GUI.

### 3.1 Symbol Normalization & Exclusions

**Normalization Map (case-insensitive matching):**

| Input Pattern(s) | Normalized Symbol |
|---|---|
| `xauusd`, `gold`, `xau`, `gld` | **XAUUSD** |
| `xagusd`, `silver`, `xag` | **XAGUSD** |
| `us30`, `dow`, `dow jones`, `us 30`, `dj30` | **US30** |
| `eurusd`, `eur/usd`, `eur usd`, `eu` | **EURUSD** |
| `gbpusd`, `gbp/usd`, `gbp usd`, `cable`, `gu` | **GBPUSD** |
| `usdjpy`, `usd/jpy`, `usd jpy`, `uj` | **USDJPY** |
| `usdcad`, `usd/cad`, `usd cad` | **USDCAD** |
| `gbpjpy`, `gbp/jpy`, `gbp jpy`, `gj` | **GBPJPY** |
| `eurjpy`, `eur/jpy`, `eur jpy`, `ej` | **EURJPY** |
| `audusd`, `aud/usd`, `aud usd` | **AUDUSD** |
| `nzdusd`, `nzd/usd`, `nzd usd` | **NZDUSD** |
| `euraud`, `eur/aud`, `eur aud` | **EURAUD** |
| `gbpaud`, `gbp/aud`, `gbp aud` | **GBPAUD** |
| `usdchf`, `usd/chf`, `usd chf` | **USDCHF** |
| `gbpcad`, `gbp/cad`, `gbp cad` | **GBPCAD** |
| `audcad`, `aud/cad`, `aud cad` | **AUDCAD** |
| `cadjpy`, `cad/jpy`, `cad jpy` | **CADJPY** |
| `chfjpy`, `chf/jpy`, `chf jpy` | **CHFJPY** |
| `eurnzd`, `eur/nzd`, `eur nzd` | **EURNZD** |
| `eurgbp`, `eur/gbp`, `eur gbp`, `eg` | **EURGBP** |
| `gbpchf`, `gbp/chf`, `gbp chf` | **GBPCHF** |
| `eurcad`, `eur/cad`, `eur cad` | **EURCAD** |
| `audjpy`, `aud/jpy`, `aud jpy` | **AUDJPY** |

**Excluded (discard silently):**
`btc`, `bitcoin`, `eth`, `ethereum`, `bnb`, `sol`, `volatility`, `vix`, `step index`, `boom`, `crash`, any crypto token name.

---

### 3.2 Message Pre-processing

1. Extract: `text`, `message_id`, `reply_to_msg_id`, `timestamp`, `is_edited`.
2. Normalize: lowercase the full text, collapse multiple whitespace to single space, strip emojis (keep numbers and punctuation).
3. **Routing** (handled by `ChannelPlugin.route_message()` — Section 2.15):
   - If `reply_to_msg_id` matches an open trade's `entry_msg_id` in `active_trades` for this `channel_id` → route to **Management**.
   - If `reply_to_msg_id` matches a `waiting_room.entry_msg_id` for this `channel_id` → treat as **Waiting Room completion**.
   - Else → attempt **Entry parsing**.

---

### 3.3 Direction & Symbol Detection

```python
import re

DIRECTION_RE = re.compile(r'\b(buy|sell)\b', re.IGNORECASE)
REENTRY_KEYWORDS = [
    'add more', 'second entry', 're-enter', 'reenter',
    'stack', 'add', 'another entry', 'more buys', 'more sells'
]

def detect_direction(text):
    m = DIRECTION_RE.search(text)
    return m.group(1).upper() if m else None

def is_reentry(text):
    return any(kw in text.lower() for kw in REENTRY_KEYWORDS)
```

- No direction → ignore.
- Symbol maps to excluded asset → discard.
- Re-entry keyword present → route to Section 3.4.

---

### 3.4 Re-entry Handling

**Entry Price:** Current market price (market order).

**SL:** Explicit SL if present; else inherit parent's current SL.

**TP:** Explicit TP if present; else inherit highest remaining active TP from parent. If parent has no active TP → auto-assign TP = entry ± 2× SL distance.

**Parent Matching (7-Level, stop at first match):**

| Priority | Condition |
|---|---|
| 1 | Direct reply to a trade message ID |
| 2 | Exactly one open trade exists |
| 3 | Symbol + direction both match |
| 4 | Symbol matches (direction ambiguous) |
| 5 | Direction matches (symbol ambiguous) |
| 6 | Price decimal places match |
| 7 | No match → skip re-entry, log warning |

---

### 3.5 Primary Signal Classification

```python
ENTRY_RE = re.compile(r'(?:entry|enter|at|@)\s*:?\s*([\d.]+)', re.IGNORECASE)
SL_RE    = re.compile(r'\b(?:sl|stop\s*loss|stoploss)\s*[:\-.]?\s*([\d.]+)', re.IGNORECASE)
TP_RE    = re.compile(r'\b(?:tp\d*|take\s*profit)\s*[:\-.]?\s*([\d.]+)', re.IGNORECASE)
LIMIT_RE = re.compile(r'\blimit\b', re.IGNORECASE)
STOP_ORDER_RE = re.compile(r'\bstop\s*order\b|\bstop\s*entry\b', re.IGNORECASE)
```

| Has SL | Has TP | Classification |
|---|---|---|
| Yes | Any | WELL-DEFINED → Section 3.6 |
| No | No | BARE → Section 3.7 |
| No | Yes | DISCARD |

---

### 3.6 Executing a WELL-DEFINED Trade

**Order type determination:**

```python
if LIMIT_RE.search(text):
    order_type = 'LIMIT'
elif STOP_ORDER_RE.search(text):
    order_type = 'STOP'
else:
    order_type = 'MARKET'
```

**Auto-TP (when no TP extracted from signal):**

```python
sl_distance = abs(entry_price - sl_price)
auto_tp = (
    entry_price + (2 * sl_distance) if direction == 'BUY'
    else entry_price - (2 * sl_distance)
)
```

**Multi-TP execution (when multiple TPs found, e.g., TP1=1960, TP2=1980, TP3=2000):**

- Split the global lot size equally: `lot / n` rounded to 0.01.
- Each sub-trade uses the same SL.
- Store with the same `signal_id`, distinct `sub_signal_id`s: `B_<id>_tp1`, `B_<id>_tp2`, `B_<id>_tp3`.
- All sub-trades are placed simultaneously via `asyncio.gather`.

**Pending order timeout:**
- For LIMIT and STOP orders: cancel if not filled within **2 hours**.
- A background task checks all pending orders every 10 minutes and calls `client.cancel_order(tl_order_id)` on expired ones.

---

### 3.7 Waiting Room for BARE Signals

1. Store in `waiting_room`: `channel_id`, `symbol`, `direction`, `entry_msg_id`, `entry_time`, `expires_at = entry_time + 15 minutes`.
2. Monitor subsequent messages for completion. Check in priority order (stop at first match):

   | Priority | Completion Condition |
   |---|---|
   | **1** | Message is a **direct reply** to the bare signal's `entry_msg_id` AND contains an SL |
   | **2** | Same symbol + same direction + contains SL |
   | **3** | Same symbol only (direction assumed from bare signal) OR same direction only (symbol assumed), AND contains SL |
   | **4** | Price pattern matches bare signal context AND the SL is logically valid (SL < entry for BUY; SL > entry for SELL) |

3. On merge: construct the full signal (symbol, direction, entry, SL, any TP) and execute as per Section 3.6.
4. On expiry without SL: **discard** the waiting room entry. Log: `[BillirichyFX] Bare signal expired: XAUUSD BUY (msg_id=104521)`.

**Second bare signal for same symbol + direction:**
If a new bare signal arrives for the same symbol and direction while one is already waiting, do **not** create a second entry. Reset the existing entry's `expires_at` to `now + 15 minutes`.

---

### 3.8 Duplicate Prevention

Store `msg_id` + `channel_id` in `message_cache` on execution. Check before processing any message; skip if entry exists within last 2 minutes. Clean stale entries every 30 seconds.

---

## 4. BillirichyFX – Management Logic

All DB operations use `channel_id = -1001859598768` as the channel identifier. The edited-message handler is wired through `ChannelPlugin.route_message()` with `is_edit=True`.

### 4.1 Trade Identification

Each open trade is identified by:
- `signal_id` (e.g., `B_104521`)
- `sub_signal_id` (e.g., `B_104521_tp2`)
- `tl_order_id` + `tl_position_id`

Management messages are matched to trades via **context matching** (Section 4.3).

---

### 4.2 Management Action Keywords

| Keyword(s) / Phrase(s) | Action | Notes |
|---|---|---|
| `set be`, `breakeven`, `move sl to entry`, `move to be`, `lock`, `lock profit` | **BREAKEVEN** | SL → entry price |
| `close half`, `close 50%`, `take some profit` | **PARTIAL_CLOSE_50** | |
| `close most`, `close 75%` | **PARTIAL_CLOSE_75** | |
| `close 33%`, `close one third`, `close third` | **PARTIAL_CLOSE_33** | |
| `close all`, `exit`, `exit all`, `close trades`, `close everything` | **CLOSE_ALL** | |
| `tp1 hit`, `tp 1 hit`, `first tp hit` | **TP1_HIT** | Informational; triggers trailing stop |
| `tp2 hit`, `tp3 hit` | **TP_HIT** | Informational |
| `sl hit`, `stopped out`, `stop hit` | **SL_HIT** | Mark as closed, move to history |
| `move sl to X`, `new sl X`, `sl now X`, `adjust sl to X` | **MODIFY_SL** | X = numeric price |
| `move tp to X`, `new tp X`, `tp now X` | **MODIFY_TP** | Single-TP trades only |
| `close some and set be`, `partial and be` | **COMPOUND** | Close 33%, then set BE |

---

### 4.3 Context Matching (8-Level Smart Match)

Applied in order; stop at first match. Level 5 includes full direction validation for price-based matching:

| Level | Condition | Action |
|---|---|---|
| 1 | Message is a direct reply to an open trade's `entry_msg_id` | Use that trade |
| 2 | Symbol + Direction both found in message; match to open trade(s) | Use matching trade(s) |
| 3 | Symbol found, no direction; match to open trade(s) by symbol | Use matching trade(s) |
| 4 | Direction found, no symbol; match to open trade(s) by direction | Use matching trade(s) |
| 5 | Price found in message within pip tolerance of an open trade's entry, SL, or TP — **with direction validation** | Use matching trade(s) |
| 6 | Only one trade was opened in the last 15 minutes | Use that trade |
| 7 | Message contains broadcast keyword (e.g., `close all`) | Apply to all open trades |
| 8 | Exactly one open trade exists | Use that sole trade |

If no level matches → log as **UNMATCHED** and skip.

**Pip Tolerance for Level 5:**

| Symbol | Tolerance |
|---|---|
| Forex non-JPY | ±10 pips (±0.0010) |
| JPY pairs | ±10 pips (±0.10) |
| XAUUSD | ±20 pips (±2.00) |
| US30 | ±20 points |
| USOIL | ±10 pips (±0.10) |

**Direction Validation at Level 5 (Smart Match):**

- `MODIFY_SL` on BUY: new SL must be below current market price.
- `MODIFY_SL` on SELL: new SL must be above current market price.
- `MODIFY_TP` on BUY: new TP must be above current market price.
- `MODIFY_TP` on SELL: new TP must be below current market price.

If direction validation fails at Level 5 → skip to Level 6.

---

### 4.4 Detailed Action Implementations

**BREAKEVEN:**

```python
async def action_breakeven(trade):
    await modify_order(trade.tl_order_id, sl=trade.entry_price)
    db.update_trade(trade.trade_id, sl=trade.entry_price)
    logger.info(f"[BE] {trade.signal_id} SL moved to {trade.entry_price}")
```

**PARTIAL_CLOSE:**

```python
async def action_partial_close(trade, pct):
    qty = round(trade.lot_size * pct, 2)
    try:
        await tl_client.close_position(trade.tl_position_id, quantity=qty)
        db.update_trade(trade.trade_id, lot_size=round(trade.lot_size - qty, 2))
        logger.info(f"[PARTIAL CLOSE] {trade.signal_id} closed {pct*100:.0f}% ({qty} lots)")
    except Exception as e:
        logger.error(f"[PARTIAL CLOSE FAILED] {trade.signal_id}: {e}")
        await notify_gui(f"Partial close failed for {trade.signal_id}: {e}", severity="HIGH")
```

**MODIFY_SL:**

```python
async def action_modify_sl(trade, new_sl):
    market_price = get_market_price(trade.symbol)
    if trade.direction == 'BUY' and new_sl > market_price:
        logger.warning(f"Invalid SL for BUY: {new_sl} > market. Skipping.")
        return
    if trade.direction == 'SELL' and new_sl < market_price:
        logger.warning(f"Invalid SL for SELL: {new_sl} < market. Skipping.")
        return
    await modify_order(trade.tl_order_id, sl=new_sl)
    db.update_trade(trade.trade_id, sl=new_sl)
```

**CLOSE_ALL:**

```python
async def action_close_all(trades):
    for trade in trades:
        await close_full(trade.tl_position_id)
        db.move_to_history(trade, reason='MANUAL')
```

**COMPOUND (Close 33% + Breakeven):**

```python
async def action_compound(trade):
    await action_partial_close(trade, pct=0.33)
    await action_breakeven(trade)
```

---

### 4.5 Trade Group (Multi-TP) Management

- All sub-trades in a group share the same SL value.
- When a management action targets a `signal_id`, it applies to **all active sub-trades** with that `signal_id` prefix.
- When TP1 is hit (sub-trade closes via TradeLocker), the bot detects the closure via polling or webhook, updates `tp1_hit = True`, and activates the trailing stop on remaining sub-trades.

---

### 4.6 Trailing Stop (After TP1 Hit)

Activated when `tp1_hit = True` and remaining sub-trades are open.

**Trailing parameters:**

| Symbol | Trail distance |
|---|---|
| XAUUSD | 15 pips (0.15) |
| All other forex | 8 pips (0.0008 for non-JPY; 0.08 for JPY) |
| US30 | 15 points |
| USOIL | 10 pips |

**Logic:**

```python
async def update_trailing_stop(trade):
    market_price = get_market_price(trade.symbol)
    trail = TRAIL_DISTANCE[trade.symbol]
    new_sl = market_price - trail if trade.direction == 'BUY' else market_price + trail
    if (trade.direction == 'BUY' and new_sl > trade.sl) or \
       (trade.direction == 'SELL' and new_sl < trade.sl):
        await modify_order(trade.tl_order_id, sl=new_sl)
        db.update_trade(trade.trade_id, sl=new_sl)
```

Trailing stop updates run every **60 seconds** for active trades with `tp1_hit = True`.

---

### 4.7 Autonomous Management

Applied per trade if no manual management message has been received:

| Time Since Entry | Condition | Action |
|---|---|---|
| 15 minutes | SL present, no TP | Auto-assign TP = entry ± 2× SL distance |
| 1 hour | No TP hit; profit ≥ 15 pips (XAUUSD) or 8 pips (forex) | Move SL to BE |
| 2 hours | No management update; trade in profit | Close 50% |
| 4 hours | No management update | Close remaining 100% |
| **4:45 PM EST daily** | Any open trade | Force close all (EOD — ensures account is flat before 5pm benchmark snapshot) |
| **Friday 4:45 PM EST** | Any open trade | Force close all (weekend — before market close) |

---

### 4.8 Edited Message Handling

Edited messages from channel ID `-1001859598768` are routed through `ChannelPlugin.route_message()` with `is_edit=True`, which checks the waiting room and active trades using `channel_id`:

```python
async def on_edit(event, channel_id: int):
    msg_id = event.message.id
    plugin = get_plugin_for_channel(channel_id)
    if db.is_waiting_room_entry(msg_id, channel_id):
        await plugin._handle_waiting_room_completion(event.message)
    elif db.is_active_trade_entry(msg_id, channel_id):
        mgmt = await plugin.parse_management(event.message)
        if mgmt:
            await handle_management_action(mgmt, channel_id)
```

---

## 5. Firepips – Entry Logic

The Firepips logic is implemented as `FirepipsPlugin(ChannelPlugin)` in `channels/firepips/plugin.py`. All `channel` string references are replaced by `channel_id` integer references (value: `-1001182913499`). This logic is also available as a selectable option on the logic dial when adding new channels via the GUI.

### 5.1 Symbol Normalization & Exclusions

| Input Pattern(s) | Normalized Symbol |
|---|---|
| `XAUUSD`, `GOLD`, `XAU`, `gold` | **XAUUSD** |
| `XAGUSD`, `SILVER`, `silver` | **XAGUSD** |
| `US30`, `DOW`, `dow jones` | **US30** |
| `GBPUSD`, `GU`, `CABLE`, `cable` | **GBPUSD** |
| `GBPJPY`, `GJ` | **GBPJPY** |
| `USDJPY`, `UJ` | **USDJPY** |
| `USDCAD` | **USDCAD** |
| `CHFJPY` | **CHFJPY** |
| `AUDJPY` | **AUDJPY** |
| `EURJPY`, `EJ` | **EURJPY** |
| `EURUSD`, `EU` | **EURUSD** |
| `EURGBP`, `EG` | **EURGBP** |
| `GBPNZD` | **GBPNZD** |
| `USOIL`, `OIL`, `WTI`, `oil` | **USOIL** |

**Excluded:** All crypto (`BTCUSD`, `ETHUSD`, etc.), Synthetics (`VIX25`, `VIX75`, `VIX100`, `Step Index`, `Boom`, `Crash`).

---

### 5.2 Message Pre-processing

1. Extract: `text`, `message_id`, `reply_to_msg_id`, `timestamp`, `is_edited`.
2. Normalize: lowercase the full text, collapse multiple whitespace to single space, strip emojis (keep numbers and punctuation).
3. **Routing** (handled by `ChannelPlugin.route_message()` — Section 2.15):
   - If `reply_to_msg_id` matches an open trade's `entry_msg_id` for this `channel_id` → route to **Management**.
   - If `reply_to_msg_id` matches a `waiting_room.entry_msg_id` for this `channel_id` → treat as **Waiting Room completion**.
   - Else → attempt **Entry parsing**.

---

### 5.3 Direction & Symbol Detection

```python
DIRECTION_RE_FP = re.compile(r'\b(buy|sell|long|short)\b', re.IGNORECASE)

DIRECTION_MAP = {
    'buy': 'BUY', 'long': 'BUY',
    'sell': 'SELL', 'short': 'SELL'
}
```

- If no direction found → ignore.
- If symbol maps to an excluded asset → discard.

---

### 5.4 Signal Classification

**Parameter Extraction:**

```python
SL_RE_FP = re.compile(r'\bsl\s*[:\-;]?\s*([\d.]+)', re.IGNORECASE)
TP_RE_FP = re.compile(r'\btp\s*[:\-;]?\s*([\d.]+)', re.IGNORECASE)
OPEN_TP_RE = re.compile(
    r'leave\s*it\s*open|keep\s*it\s*open|no\s*tp|open\s*trade|run\s*it', re.IGNORECASE)
```

**Classification:**

| Condition | Action |
|---|---|
| Has SL + numeric TP | WELL-DEFINED with TP |
| Has SL + `OPEN_TP_RE` match or no TP | WELL-DEFINED without TP |
| Has SL, no TP field present | WELL-DEFINED without TP |
| No SL | BARE → Waiting Room (Section 5.6) |
| TP only, no SL | DISCARD |

---

### 5.5 Executing a WELL-DEFINED Trade

**Order type:**
- `limit` in message → LIMIT order.
- `stop order` / `stop entry` in message → STOP order.
- Else → MARKET.

**TP handling:**
- Numeric TP extracted → set TP.
- `OPEN_TP_RE` match or no TP present → no TP set (leave open).

**Multi-TP (rare):**
- Split lot equally; link as trade group using same `signal_id`, distinct `sub_signal_id`s (`F_<id>_tp1`, `F_<id>_tp2`, etc.) — same logic as BillirichyFX Section 3.6.

**Pending order timeout:** Cancel if not filled within **2 hours** (applies to both LIMIT and STOP orders). Background task checks every 10 minutes.

---

### 5.6 Waiting Room for BARE Signals

- 15-minute timer from `entry_time`; `expires_at = entry_time + 15 minutes`.
- Completion checks (evaluated in order, stop at first match):
  1. **Edit** of the original bare signal message that now contains an SL.
  2. **Reply** to the original message containing an SL.
  3. New message within 15 minutes with matching **symbol + direction + SL**.
  4. New message within 15 minutes with matching **symbol + SL** (direction already known from the bare signal).
- On merge: construct full signal and execute as per Section 5.5.
- On expiry without SL: **discard**. Log: `[Firepips] Bare signal expired without SL: GBPUSD BUY`.
- **Second bare signal for same symbol+direction:** Do not create a second entry. Reset the existing entry's `expires_at` to `now + 15 minutes`.

---

### 5.7 Duplicate Prevention

- On executing any signal, store `msg_id` + `channel_id` in `message_cache` with `processed_at = now`.
- Before processing any message, check if its `msg_id` exists in `message_cache` for this `channel_id` with `processed_at` within last 2 minutes. If so → skip.
- Clean up `message_cache` entries older than 2 minutes continuously (every 30 seconds).

---

## 6. Firepips – Management Logic

All DB operations use `channel_id = -1001182913499`. Edited-message handling follows the same pattern as Section 4.8 via `ChannelPlugin.route_message()` with `is_edit=True`.

### 6.1 Trade Identification

Each open trade is identified by:
- `signal_id` (e.g., `F_88302`)
- `sub_signal_id` (e.g., `F_88302_tp1`)
- `tl_order_id` + `tl_position_id`

Management messages are matched to trades via **context matching** (Section 6.3).

---

### 6.2 Management Action Keywords

| Keyword(s) / Phrase(s) | Action |
|---|---|
| `CLOSE IN MASSIVE PROFIT`, `CLOSE IN PROFIT`, `EXIT IN MASSIVE PROFIT`, `TAKE PROFIT`, `CLOSE [SYMBOL] NOW`, `EXIT YOUR TRADES`, `CLOSE RIGHT NOW`, `CLOSE NOW`, `EXIT NOW` | **CLOSE_ALL** |
| `CLOSE IN LOSS`, `EXIT THIS TRADE IN A LOSS`, `CUT YOUR LOSSES`, `EXIT IN LOSS` | **CLOSE_ALL** |
| `STOP LOSS HIT`, `SL HIT`, `STOP LOSS TAKEN`, `HIT SL`, `STOPPED OUT` | **SL_HIT** |
| `TIGHTEN STOP LOSS TO X`, `ADJUST STOP LOSS TO X`, `NEW SL: X`, `MOVE SL TO X` | **MODIFY_SL** |
| `TP: X`, `TAKE PROFIT: X`, `NEW TP: X`, `MOVE TP TO X` | **MODIFY_TP** |
| `BREAKEVEN`, `BREAK EVEN`, `BE`, `MOVE TO BE`, `SET BE` | **BREAKEVEN** |
| `CANCEL ORDER`, `DELETE ORDER`, `CANCEL PENDING`, `REMOVE ORDER` | **CANCEL_PENDING** |
| `TAG ME WITH YOUR PROFIT`, `ENJOY YOUR PROFITS`, `MASSIVE PROFIT`, `MONEY PRINTED`, `WE'RE IN PROFIT GUYS`, `PROFIT TIME`, `CASH OUT` | **IMPLIED_CLOSE** (Section 6.5) |

---

### 6.3 Context Matching (9-Level with Price Reference)

Applied in order; stop at first match:

| Level | Condition |
|---|---|
| 1 | Direct reply to open trade's `entry_msg_id` |
| 2 | Symbol + Direction both match |
| 3 | Symbol only match |
| 4 | Direction only match |
| 5 | Price reference within pip tolerance (with direction validation — see below) |
| 6 | Recency: only one trade opened within last 15 minutes |
| 7 | Broadcast keyword (`close all`, `exit all`) |
| 8 | Sole trade exists |
| 9 | All trades (final fallback for broadcast-type messages only) |

**Level 5 – Price Reference Details:**

| Symbol | Pip Tolerance |
|---|---|
| Forex non-JPY | ±0.0010 (10 pips) |
| JPY pairs | ±0.10 (10 pips) |
| XAUUSD | ±2.00 (20 pips) |
| US30 | ±20 points |
| USOIL | ±0.10 (10 pips) |

**Direction validation at Level 5:**

- `MODIFY_SL` on BUY: new SL must be below current market price.
- `MODIFY_SL` on SELL: new SL must be above current market price.
- `MODIFY_TP` on BUY: new TP must be above current market price.
- `MODIFY_TP` on SELL: new TP must be below current market price.

If direction validation fails → skip to next context level.

---

### 6.4 Detailed Action Implementations

All shared actions (BREAKEVEN, MODIFY_SL, MODIFY_TP, CLOSE_ALL) use the same implementations as BillirichyFX Section 4.4. Firepips adds CANCEL_PENDING:

**CANCEL_PENDING:**

```python
async def action_cancel_pending(trade):
    if trade.status == 'pending':
        await cancel_order(trade.tl_order_id)
        db.move_to_history(trade, reason='CANCELLED')
        logger.info(f"[Firepips] Pending order cancelled: {trade.signal_id}")
```

**PARTIAL_CLOSE** (no fallback — same as Section 4.4):

```python
async def action_partial_close(trade, pct):
    qty = round(trade.lot_size * pct, 2)
    try:
        await tl_client.close_position(trade.tl_position_id, quantity=qty)
        db.update_trade(trade.trade_id, lot_size=round(trade.lot_size - qty, 2))
        logger.info(f"[PARTIAL CLOSE] {trade.signal_id} closed {pct*100:.0f}% ({qty} lots)")
    except Exception as e:
        logger.error(f"[PARTIAL CLOSE FAILED] {trade.signal_id}: {e}")
        await notify_gui(f"Partial close failed for {trade.signal_id}: {e}", severity="HIGH")
```

---

### 6.5 IMPLIED_CLOSE Logic

**Trigger conditions (ALL must be true):**

1. A profit announcement phrase (Section 6.2 IMPLIED_CLOSE row) is detected in the message.
2. There are open Firepips trades (`channel_id = -1001182913499`).
3. At least one open Firepips trade is currently **in profit** (floating P&L > 0).
4. No explicit CLOSE_ALL or MODIFY action was received in the **±5 minutes** window around this message's timestamp.

**Scope:** Apply to **all currently profitable open Firepips trades** only. Trades in loss are left open.

```python
async def handle_implied_close(channel_id: int, timestamp):
    firepips_trades = db.get_active_trades(channel_id=channel_id)
    for trade in firepips_trades:
        floating_pnl = calculate_floating_pnl(trade)
        if floating_pnl > 0:
            await action_close_all([trade])
            logger.info(
                f"[IMPLIED_CLOSE] Closed {trade.signal_id} at profit {floating_pnl:.2f}"
            )
        else:
            logger.info(
                f"[IMPLIED_CLOSE] Skipped {trade.signal_id} – in loss ({floating_pnl:.2f})"
            )
```

---

### 6.6 Edited Message Handling

Edited messages from channel ID `-1001182913499` are routed through `ChannelPlugin.route_message()` with `is_edit=True`:

```python
async def on_edit(event, channel_id: int):
    msg_id = event.message.id
    plugin = get_plugin_for_channel(channel_id)
    if db.is_waiting_room_entry(msg_id, channel_id):
        await plugin._handle_waiting_room_completion(event.message)
    elif db.is_active_trade_entry(msg_id, channel_id):
        mgmt = await plugin.parse_management(event.message)
        if mgmt:
            await handle_management_action(mgmt, channel_id)
```

---

### 6.7 Autonomous Management

| Time Since Entry | Condition | Action |
|---|---|---|
| **1 hour** | Trade in profit (floating P&L > 0) | Move SL to BE |
| **2 hours** | Trade in profit | Close 50% |
| **4 hours** | Any state | Force close remaining |
| **4:45 PM EST daily** | Any open trade | Force close all (EOD — ensures account is flat before 5pm benchmark snapshot) |
| **Friday 4:45 PM EST** | Any open trade | Force close all (weekend — before market close) |

---

## 7. Telegram Web App GUI (React)

### 7.1 Technology Stack & TWA Constraints

**Stack:**
- Frontend: React (Vite), Tailwind CSS, shadcn/ui components, Zustand for state management.
- Backend: FastAPI (Python), WebSocket support via `websockets`.
- Build output: served via Nginx over HTTPS.

**TWA Constraints:**

- Must be served over **HTTPS** with a valid SSL certificate (use Let's Encrypt via Certbot).
- The TWA is opened via a bot button. A **separate BotFather bot** (not the Telethon listening account) is used as the TWA host. Configure via `BOT_TOKEN` and `WEBAPP_URL` environment variables.
- On app load: `window.Telegram.WebApp.ready()` must be called immediately.
- Use Telegram TWA CSS variables for theming: `var(--tg-theme-bg-color)`, `var(--tg-theme-text-color)`, `var(--tg-theme-button-color)`, etc.
- The TWA main button (`window.Telegram.WebApp.MainButton`) may be used for primary CTA actions (e.g., "Stop Bot" confirmation).
- The app is mobile-first — all layouts must be usable on a phone screen at 375px width minimum.

---

### 7.2 Pages & Components

#### Global Dashboard (Top Section — Always Visible)

The global dashboard is displayed at the very top of the app before any account cards. It shows **combined metrics across all accounts** at a glance:

- **Combined Balance** — sum of current balances across all accounts.
- **Combined Equity** — sum of current equity (balance + floating P&L) across all accounts.
- **Total Daily P&L** — aggregate daily P&L (green if positive, red if negative).
- **Total Open Trades** — count of all open positions across all accounts.
- **Worst Daily Loss %** — the account closest to breaching its daily limit (from its active risk profile).
- **Worst Overall Drawdown %** — the account closest to breaching its overall drawdown limit.
- **Active / Paused / Breached accounts summary** — e.g., `3 Active | 1 Paused | 0 Breached`.
- **DRY-RUN banner** — shown prominently when dry-run mode is active.

This section is always fixed or immediately visible on scroll entry. Users scroll past it to reach individual account cards.

**New elements added in v5.0:**

- **Channel Status Bar** — a compact row of channel pill badges directly below the combined metrics. Each pill shows `[Channel Name] ● LIVE` (green) or `[Channel Name] ● OFF` (grey). Each pill contains a toggle switch to enable/disable that channel globally in one tap. Changes call `PUT /api/channels/{id}/toggle`.

  ```
  ┌──────────────────────────────────────┐
  │  BillirichyFX  ●●● LIVE    ⟨toggle⟩  │
  │  Firepips      ●●● LIVE    ⟨toggle⟩  │
  └──────────────────────────────────────┘
  ```

- **Active Channels Count** in the summary row (e.g., `2 / 3 Channels Active`).

---

#### Account Cards (Scrollable, Below Global Dashboard)

Each card retains all original content per account:

- Account display name (editable from the GUI) + credential label + sub-account ID.
- Current balance and equity (real-time via WebSocket).
- Daily P&L (green if positive, red if negative).
- Daily loss progress bar (yellow warning at 2%, red at 3% or profile limit).
- Overall drawdown progress bar with profit-lock indicator if applicable.
- Profitable days count: `X / 5` with warning badge if behind target.
- **Consistency Score** — displayed as a segmented progress bar labelled `Consistency: XX%`. Green below 15%, amber 15–19%, red at 20%+. Shows `—` when cycle total P&L ≤ 0. Below the bar: `Best day: $X of $Y total` so the operator can see which day is driving the score. A red badge reads `⚠ Consistency Risk` when score ≥ 20%.
- Status badge: `Active` (green) / `Paused` (yellow) / `Breached` (red).
- Trade counts by channel (dynamic from DB — not hardcoded): e.g., `BillirichyFX: 2 | Firepips: 1`.
- **Withdrawable amount** — calculated as `current_balance − overall_floor − payout_buffer` (sourced from the account's active risk profile). For Blue Guardian: `balance − (highest_banked_balance − 6% of initial) − 1% of initial`. Once profit locked: `balance − initial_balance − 1% of initial`. Clearly labelled with the breakdown shown on hover/tap.
- **Payout Reset button** — with confirmation dialog that shows the withdrawable breakdown and warns if the entered withdrawal amount would breach the buffer. Clearly distinguishes between a **Withdrawal** (mid-cycle, balance drops but metrics stay) and a **Formal Reset** (new cycle, everything restarts).

Tapping an account card opens the **Account Detail Page** for that account.

**New v5.0 controls on each card:**

**1. Card Actions Row** — a row of three icon buttons at the top-right of each card:

| Button | Action |
|---|---|
| ⏸ / ▶ (Pause / Resume) | Toggle `accounts.paused`. Calls `PUT /api/accounts/{key}/pause`. |
| 🗑 (Delete Account) | Opens confirmation modal: "Remove this account from the bot? This will close all open trades on this account first." Calls `DELETE /api/accounts/{key}`. |

**2. Channel Subscriptions Panel** — collapsed by default; expand with a "Channels" chevron. Shows one row per registered channel with a toggle switch:

```
▶ Channels this account copies from:
  ┌─────────────────────┬────────┐
  │ BillirichyFX        │  ✓ ON  │
  │ Firepips            │  ✓ ON  │
  │ NewChannel (if any) │  ✗ OFF │
  └─────────────────────┴────────┘
```

Toggling calls `PUT /api/accounts/{key}/subscriptions/{channel_id}`.

Default is all channels ON (matching `sync_channel_subscriptions()` behaviour).

**3. Risk Profile Selector** — collapsed by default; expand with a "Risk Profile" chevron. Shows a segmented control / scrollable dial listing all available profile names. The currently active profile is highlighted. Selecting a different profile calls `PUT /api/accounts/{key}/risk-profile`. Below the selector a compact read-only summary of the selected profile's key values is shown (daily %, overall %, trailing toggles, profit lock status).

---

#### Add Account / Sub-Account Panel

A floating **"+ Add Account"** button appears at the bottom of the scrollable account cards list. Tapping opens a bottom-sheet modal with this form:

```
Add TradeLocker Account
─────────────────────────────────
Display Name:    [text input]
Email:           [text input]
Password:        [password input]
Server:          [Live / Demo toggle]
─────────────────────────────────
  [Discover Sub-Accounts]
```

On submitting the credentials and tapping **Discover Sub-Accounts**, the backend authenticates and calls `tl.get_accounts()`, returning all available sub-accounts. Each sub-account is listed with a checkbox:

```
Found 3 sub-accounts:
  ☑  ACC-001  ($10,000)
  ☑  ACC-002  ($5,000)
  ☐  ACC-003  ($10,000)

[Add Selected Accounts]
```

Tapping **Add Selected Accounts** calls `POST /api/accounts/bulk-add`. The backend:
1. Stores the credential and the selected sub-accounts in `accounts`.
2. Calls `sync_channel_subscriptions()` for the new accounts.
3. Assigns the default risk profile.
4. Pushes a `account_added` WebSocket event to refresh the GUI.

---

#### Account Detail Page

Opened by tapping any account card. Displays full information for a single account.

**Header:** Account display name, credential email, sub-account ID, status badge, live balance and equity.

**Trades Sub-section:**
- Filter bar: filter by **channel** (dynamic list from DB — all registered channels available as filter options), **status** (`Open` / `Closed` / `Pending`), **date range**.
- Table of trades: Symbol, Direction, Entry Price, Current Price, SL, TP, Floating P&L, Duration, Status, Channel name.
- Per-row actions: **Close** (manual close with confirmation), **Breakeven** (quick-set SL to entry).
- **"Close All"** button — scope selectable: all trades, or by channel.

**Risk Details Sub-section:**
- Active risk profile name with link to edit.
- Daily loss floor: current equity vs. floor level (visual bar).
- All-time high equity and current overall drawdown from it.
- Profit lock status: locked or not, and if locked — the locked floor value.
- Payout cushion amount displayed clearly.

**History Sub-section:**
- Filterable by: date range, channel, symbol, outcome (WIN / LOSS / BE).
- Summary row: Total Trades, Win Rate, Total P&L, Average R:R, Best Day, Worst Day.
- Exportable as CSV via `GET /api/trades/history/export`.

**Subscription management** — full-width channel subscription table (same toggles as the account card panel but shown as a complete table here).

**Risk Profile section** — same selector dial as on the account card, shown as a dedicated sub-section with all profile field values displayed.

---

#### Live Trades View (Global Page)

- Table of **all open trades across all accounts**.
- Columns: Channel (display name from DB), Account, Symbol, Direction, Entry Price, Current Price, SL, TP, Floating P&L, Duration, Status.
- Actions per row: **Close** (manual close with confirmation), **Breakeven** (quick-set SL to entry).
- **"Close All"** button — scope selectable: all accounts, per account, or per channel. All channel options are loaded dynamically from the DB.

---

#### Settings Page *(significantly expanded in v5.0)*

The Settings page is split into three tabs:

**Tab 1: General Settings**
- Global lot size slider (0.01–1.0, default 0.1).
- Display-only summary of active risk profiles in use across accounts.

**Tab 2: Channel Management** *(new in v5.0)*

A full-screen management table of all registered channels:

```
┌──────────────────┬──────────┬────────────────┬──────────┬─────────────────┐
│ Channel Name     │ ID       │ Priority       │ Enabled  │ Actions         │
├──────────────────┼──────────┼────────────────┼──────────┼─────────────────┤
│ BillirichyFX     │ -100123… │ [1    ▲▼]      │  ✓ ON    │ [Edit] [Delete] │
│ Firepips         │ -100987… │ [2    ▲▼]      │  ✓ ON    │ [Edit] [Delete] │
└──────────────────┴──────────┴────────────────┴──────────┴─────────────────┘
                                                         [+ Add Channel]
```

**Global Enable/Disable Toggle:** Each row has an inline toggle. Toggling calls `PUT /api/channels/{id}/toggle` and immediately rebuilds the Telethon listener.

**Priority:** Editable inline integer field. Lower = higher priority. Changes call `PUT /api/channels/{id}/priority`.

**Delete Channel:** Opens confirmation modal. Warns if the channel has any open trades. Deleting disables the listener immediately and removes the channel from all `channel_subscriptions` rows (cascade delete). Does not delete historical trades (they retain the channel_id for history purposes).

**"+ Add Channel" form (bottom-sheet modal):**

```
Add New Signal Channel
─────────────────────────────────────────────────────
Channel ID:         [numeric input — e.g. -1001234567890]
                    (find by forwarding any message to @userinfobot)
Display Name:       [text input — shown in all GUI tables and labels]
Signal Prefix:      [2-4 char input — used in signal IDs, e.g. "MC"]
Priority:           [integer input — lower = higher priority]
Notes:              [optional text]
─────────────────────────────────────────────────────
Entry Logic:        [Logic Dial — dropdown of all available logic modules]

  Built-in options (always available):
  ┌──────────────────────────────────────────────────┐
  │ ● BillirichyFX Logic                            │
  │   (channels.billirichy.plugin)                  │
  │   Parses buy/sell signals with optional limit/  │
  │   stop keywords, multi-TP splitting, re-entry,  │
  │   8-level Smart Match management.               │
  │                                                  │
  │ ○ Firepips Logic                                │
  │   (channels.firepips.plugin)                    │
  │   Parses buy/sell/long/short, open-TP support,  │
  │   implied-close detection, 9-level context      │
  │   matching management.                          │
  │                                                  │
  │ ○ [Custom — type module path]                   │
  │   For newly deployed logic modules.             │
  └──────────────────────────────────────────────────┘

Management Logic:   [same Logic Dial, independently selectable]
                    (can mix: e.g. Firepips entry + BillirichyFX management
                     if the new channel shares one but not the other)
─────────────────────────────────────────────────────
                    [Add Channel]
```

**Logic Clone Dial — how it works:** When a signal provider migrates to a new Telegram channel (new ID) but keeps the same message format, add the new channel via the GUI, select the old channel's logic from the dial for both entry and management, then disable the old channel from the Channel Management table. The bot immediately starts listening to the new channel ID using the identical parsing logic — no code deployment required.

The two built-in options, **BillirichyFX Logic** and **Firepips Logic**, are always present in the dial because their modules ship with the bot. Any additional logic module that a developer deploys to the `channels/` directory on the server will automatically appear in the dial after the backend returns it from `GET /api/channels/logic-modules`.

---

**Tab 3: Risk Profiles** *(new in v5.0)*

A management table of all risk profiles:

```
┌──────────────────────┬──────────┬──────────┬──────────────┬────────────────┐
│ Profile Name         │ Daily DD │ Overall  │ Default      │ Actions        │
├──────────────────────┼──────────┼──────────┼──────────────┼────────────────┤
│ Blue Guardian Instant Standard│ 3% trail │ 6% trail │ ⭐ Default   │ [Edit]         │
│ Conservative         │ 2% trail │ 5% trail │              │ [Edit][Delete] │
│ FTMO Standard        │ 5% static│ 10% trail│              │ [Edit][Delete] │
└──────────────────────┴──────────┴──────────┴──────────────┴────────────────┘
                                                       [+ Add Risk Profile]
```

The built-in default profile shows `[Edit]` only — it cannot be deleted (Delete button is hidden).

**"Edit / Add Risk Profile" form (bottom-sheet modal):**

All `risk_profiles` fields are presented as labeled form controls:

```
Profile Name:                 [text input]

── Daily Loss Limit ──────────────────────────────────
Daily Loss %:                 [number input, e.g. 3.0]
Daily Trailing Drawdown:      [toggle: Trailing / Static]
  • Trailing: floor = max(day-start balance, intraday equity peak) − daily%
  • Static:   floor fixed from day-start balance only

── Overall Drawdown Limit ────────────────────────────
Overall Loss %:               [number input, e.g. 6.0]
Overall Drawdown Mode:        [3-way selector]
  • Trailing – Closed Balance (Blue Guardian):
      floor trails from highest banked balance only.
      Floating P&L does NOT move the floor.
  • Trailing – Equity Peak:
      floor trails from highest ever equity (includes floating).
  • Static:
      floor = initial_balance × (1 − overall%)

── Profit Lock ───────────────────────────────────────
Enable Profit Lock:           [toggle ON/OFF]
  Lock triggers at:           [number input, e.g. 6.0] % balance gain
  Locked floor:               [number input, e.g. 0.0] % below initial
    (0.0 = floor locks exactly at initial_balance — never lose original capital)

── Payout Rules ──────────────────────────────────────
Payout Buffer %:              [number input, e.g. 1.0]
  Must remain above floor after withdrawal.
  Withdrawable = balance − floor − (initial × buffer%)
  Set to 0.0 to disable buffer.

── Trade Rules ───────────────────────────────────────
Max Risk Per Trade:           [number input, e.g. 1.0] %
Safety Buffer (pre-trade):    [number input, e.g. 10.0] %
Max Concurrent Trades:        [integer input, e.g. 5]
Commission Per Lot (USD):     [number input, e.g. 6.0]

Notes:                        [text area]

                    [Save Profile]
```

Saving calls `POST /api/risk-profiles` (create) or `PUT /api/risk-profiles/{id}` (update). Changes take effect immediately for all accounts using this profile (resolved at next trade event).

**Set as Default button:** Appears next to non-default profiles in the table. Calls `POST /api/risk-profiles/{id}/set-default`.

---

#### Bot Control

- **Start / Stop** signal monitoring (with confirmation dialog).
- **Dry-Run toggle** — enable/disable paper mode. Shows "DRY-RUN MODE" banner site-wide when active.
- **Force Close All** — per account or globally, with confirmation. Closes all open positions immediately on TradeLocker.
- **Skip Next Signal** — per channel (dynamic channel list from DB). Skips the very next signal received from the selected channel without affecting future signals.
- **Channel Priority Override** — temporarily adjust which channel takes priority when the concurrent trade limit is reached. Uses dynamic channel names from DB — no hardcoded channel names anywhere in the GUI.

---

#### Notification Panel

- Persistent in-app notification feed showing all `WARNING`, `HIGH`, and `CRITICAL` events.
- `CRITICAL` events also display a persistent red banner at the top of every page until manually dismissed.
- Filterable by severity level.
- Each notification entry shows: timestamp, severity badge, full message text, and affected account key (if applicable).
- `INFO` events are accessible in the separate log viewer only — not shown in the notification panel feed by default.

---

### 7.3 Real-Time Updates (WebSockets)

The backend pushes the following events over the WebSocket connection at `/ws`. The frontend Zustand store handles all event types and updates UI state reactively.

**Complete event table:**

| Event | Payload |
|---|---|
| `trade_executed` | `{signal_id, symbol, direction, entry, sl, tp, account_key, channel_id, channel_name}` |
| `trade_closed` | `{signal_id, exit_price, pnl, outcome, reason}` |
| `management_applied` | `{signal_id, action, new_sl, new_tp}` |
| `balance_updated` | `{account_key, current_balance, daily_pnl, equity, withdrawable, overall_floor, daily_floor, consistency_score, consistency_status}` |
| `risk_warning` | `{account_key, type, message}` |
| `notification` | `{severity, message, timestamp, account_key?}` |
| `channel_toggled` | `{channel_id, display_name, enabled}` *(new v5.0)* |
| `channel_added` | `{channel_id, display_name}` *(new v5.0)* |
| `channel_deleted` | `{channel_id}` *(new v5.0)* |
| `account_added` | `{account_key, display_name}` *(new v5.0)* |
| `account_deleted` | `{account_key}` *(new v5.0)* |
| `risk_profile_updated` | `{profile_id, profile_name}` *(new v5.0)* |
| `subscription_changed` | `{account_key, channel_id, enabled}` |

**Frontend WebSocket handler (Zustand):**

```javascript
// store.js
import { create } from 'zustand';

const useStore = create((set) => ({
  trades: [],
  accounts: [],
  channels: [],
  riskProfiles: [],
  notifications: [],
  ws: null,
  connectWS: () => {
    const ws = new WebSocket(`wss://${BACKEND_URL}/ws`);
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      set((state) => handleEvent(state, event));
    };
    ws.onclose = () => setTimeout(() => useStore.getState().connectWS(), 3000);
    set({ ws });
  }
}));

function handleEvent(state, event) {
  switch (event.type) {
    case 'trade_executed':    return { trades: [...state.trades, event] };
    case 'trade_closed':      return { trades: state.trades.filter(t => t.signal_id !== event.signal_id) };
    case 'balance_updated':   return { accounts: state.accounts.map(a => a.account_key === event.account_key ? { ...a, ...event } : a) };
    case 'channel_toggled':   return { channels: state.channels.map(c => c.channel_id === event.channel_id ? { ...c, enabled: event.enabled } : c) };
    case 'channel_added':     return { channels: [...state.channels, event] };
    case 'channel_deleted':   return { channels: state.channels.filter(c => c.channel_id !== event.channel_id) };
    case 'account_added':     return { accounts: [...state.accounts, event] };
    case 'account_deleted':   return { accounts: state.accounts.filter(a => a.account_key !== event.account_key) };
    case 'notification':      return { notifications: [event, ...state.notifications].slice(0, 200) };
    default: return state;
  }
}
```

---

### 7.4 API Endpoints (FastAPI)

All endpoints are documented below in full. No external API reference is needed.

#### Account Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/accounts` | List all accounts (all credentials, all sub-accounts) with status |
| GET | `/api/accounts/summary` | Global combined metrics across all accounts |
| GET | `/api/accounts/{key}` | Single account details |
| POST | `/api/accounts/discover` | Authenticate credential + return available sub-accounts. Body: `{email, password, server}` |
| POST | `/api/accounts/bulk-add` | Add selected sub-accounts. Body: `{email, password, server, account_ids: []}` |
| DELETE | `/api/accounts/{key}` | Remove account (closes open trades first, soft-delete retains history) |
| PUT | `/api/accounts/{key}/pause` | Pause / resume account |
| PUT | `/api/accounts/{key}/risk-profile` | Assign risk profile. Body: `{profile_id}` |
| PUT | `/api/accounts/{key}/max-trades` | Set per-account concurrent trade override. Body: `{value: int or null}` |
| PUT | `/api/accounts/{key}/subscriptions/{channel_id}` | Toggle channel subscription. Body: `{enabled: bool}` |
| POST | `/api/accounts/{key}/payout-reset` | Trigger payout reset — updates `initial_balance`, resets drawdown tracking |

#### Channel Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/channels` | List all channels (enabled and disabled) |
| GET | `/api/channels/{id}` | Single channel details |
| POST | `/api/channels` | Add new channel. Body: `{channel_id, display_name, signal_prefix, entry_logic_module, management_logic_module, priority}` |
| PUT | `/api/channels/{id}` | Update channel fields |
| PUT | `/api/channels/{id}/toggle` | Enable / disable channel (rebuilds Telethon listener immediately) |
| PUT | `/api/channels/{id}/priority` | Update priority integer |
| DELETE | `/api/channels/{id}` | Remove channel (warns if open trades exist, cascade-deletes subscriptions) |
| GET | `/api/channels/logic-modules` | List all available entry + management module paths from the `channels/` directory |

#### Risk Profile Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/risk-profiles` | List all profiles |
| GET | `/api/risk-profiles/{id}` | Single profile details |
| POST | `/api/risk-profiles` | Create new profile |
| PUT | `/api/risk-profiles/{id}` | Update profile fields (partial update supported) |
| DELETE | `/api/risk-profiles/{id}` | Delete profile — returns HTTP 400 with affected account list if any account uses it |
| POST | `/api/risk-profiles/{id}/set-default` | Atomically set as the default profile |
| GET | `/api/risk-profiles/{id}/accounts` | List accounts currently assigned to this profile |

#### Trade Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/trades/active` | All open trades (optional filter: `?account_key=&channel_id=`) |
| GET | `/api/trades/history` | Paginated history (filter params: account, channel_id, date, outcome) |
| GET | `/api/trades/history/export` | CSV export of filtered trade history |
| POST | `/api/trades/close` | Manual close. Body: `{trade_id}` |
| POST | `/api/trades/close-all` | Close all. Body: `{account_key?, channel_id?}` |

#### Bot Control Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/bot/start` | Start signal monitoring |
| POST | `/api/bot/stop` | Stop signal monitoring |
| POST | `/api/bot/dryrun` | Toggle dry-run mode |
| PUT | `/api/settings` | Update global settings. Body: `{lot_size?}` |
| GET | `/api/notifications` | Recent notifications (filterable by severity) |
| WS | `/ws` | Real-time event stream (see Section 7.3) |

---

## 8. Deployment & Operational Notes

### Environment Variables

```bash
# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890       # Dedicated account phone

# TradeLocker Credentials (JSON array for multiple credentials)
TL_CREDENTIALS='[
  {"email": "account1@example.com", "password": "pass1", "server": "live"},
  {"email": "account2@example.com", "password": "pass2", "server": "live"}
]'

# TWA Bot
BOT_TOKEN=your_twa_bot_token
WEBAPP_URL=https://yourdomain.com

# Database
DATABASE_URL=./bot.db

# App
DRY_RUN=false
LOG_LEVEL=INFO

# v5.0: channel IDs used on first-time DB init
# After init, all channel changes are made exclusively through the GUI
BILLIRICHY_CHANNEL_ID=-1001859598768
FIREPIPS_CHANNEL_ID=-1001182913499
```

**Note on channel IDs:** The two built-in channel IDs above (`-1001859598768` for BillirichyFX and `-1001182913499` for Firepips) are set. To find the numeric ID of any other Telegram channel, forward any message from it to `@userinfobot`, or use `client.get_entity('channel_username')` in a Telethon script and print `entity.id`.

### VPS Requirements

- OS: Ubuntu 22.04 LTS
- RAM: 2GB minimum (4GB recommended)
- Storage: 20GB SSD
- Uptime: 24/7 (systemd or pm2)
- SSL: Let's Encrypt via Certbot

### File Structure

```
trading-bot/
├── main.py                     # Entry point
├── channel_registry.py         # Plugin loader + Telethon listener builder
├── channels/
│   ├── base.py                 # ChannelPlugin ABC
│   ├── billirichy/
│   │   ├── plugin.py           # BillirichyPlugin
│   │   ├── entry.py
│   │   ├── management.py
│   │   └── symbol_map.py
│   └── firepips/
│       ├── plugin.py
│       ├── entry.py
│       ├── management.py
│       └── symbol_map.py
├── core/
│   ├── risk.py                 # Profile-based risk engine
│   ├── waiting_room.py
│   ├── execution.py
│   ├── autonomous.py
│   └── notifications.py
├── db/
│   ├── init_db.py
│   ├── migrations.py
│   └── queries.py
├── api/
│   ├── main.py                 # FastAPI app
│   ├── routes/
│   │   ├── accounts.py
│   │   ├── channels.py         # new v5.0
│   │   ├── risk_profiles.py    # new v5.0
│   │   ├── trades.py
│   │   ├── settings.py
│   │   └── bot_control.py
│   └── ws.py                   # WebSocket broadcast
└── frontend/
    └── src/
        ├── pages/
        │   ├── Dashboard.jsx
        │   ├── AccountDetail.jsx
        │   ├── LiveTrades.jsx
        │   ├── Settings.jsx    # tabs: General / Channels / Risk Profiles
        │   ├── BotControl.jsx
        │   └── Notifications.jsx
        └── components/
            ├── AccountCard.jsx         # includes subscription panel + risk dial
            ├── ChannelBadge.jsx
            ├── RiskProfileSelector.jsx # segmented dial
            ├── AddAccountModal.jsx
            ├── AddChannelModal.jsx
            └── RiskProfileEditor.jsx
```

### Process Management (systemd)

```ini
[Unit]
Description=Unified Trading Bot v5.0
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/trading-bot
ExecStart=/home/ubuntu/trading-bot/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/trading-bot/.env

[Install]
WantedBy=multi-user.target
```

### Daily Backup

```bash
55 21 * * 1-5 cp /home/ubuntu/trading-bot/bot.db \
  /home/ubuntu/backups/bot_$(date +\%Y\%m\%d).db
```

### Logging

- Rotating file logs: `logs/bot.log` (10MB max, 5 rotations).
- Per-channel log files: dynamically named `logs/{display_name}.log` (created when each channel is first activated).
- `logs/tradelocker.log` for all TL API calls.
- Format: `[TIMESTAMP] [LEVEL] [CHANNEL_ID:{channel_id}] message`

---

## 9. AI Development Prompt

```
You are building Mirror Pupil — a production-ready Telegram copy-trading bot.
The complete specification is in this document. Implement exactly as described.

Core Architectural Requirements:

1. CHANNEL PLUGIN ARCHITECTURE
   - Implement the ChannelPlugin ABC in channels/base.py as specified in Section 2.14.
   - BillirichyPlugin and FirepipsPlugin each implement the ABC.
     BillirichyFX channel_id = -1001859598768, signal_prefix = 'B'.
     Firepips channel_id = -1001182913499, signal_prefix = 'F'.
   - The Telethon client is built dynamically from the `channels` DB table at startup.
     Call register_channel_listeners() on startup and whenever a channel is added/toggled.
   - All channel identification uses numeric integer channel_id — never a string username.
   - channel_registry.py: load_channels_from_db() instantiates enabled plugin instances;
     get_plugin_for_channel(int) returns the instance or None.

2. CHANNEL DATABASE
   - `channels` table as specified in Section 2.5.
   - Built-in records for BillirichyFX (-1001859598768) and Firepips (-1001182913499)
     inserted on first-time init from env vars BILLIRICHY_CHANNEL_ID / FIREPIPS_CHANNEL_ID.
   - `channel_subscriptions` table: one row per (account_key, channel_id) pair, enabled=true.
   - sync_channel_subscriptions() called whenever a channel or account is added/deleted.
   - execute_on_all_accounts() filters accounts by channel subscription before dispatching.

3. MULTI-PROFILE RISK MANAGEMENT
   - `risk_profiles` table as specified in Section 2.5.
   - Built-in 'Blue Guardian Instant Standard' profile inserted on init with is_default=1:
       max_risk_per_trade_pct=1.0, daily_loss_pct=3.0, daily_trailing=1,
       overall_loss_pct=6.0, overall_trailing=1, overall_trail_from_closed_balance=1,
       profit_lock_pct=6.0, profit_lock_floor_pct=0.0, payout_buffer_pct=1.0,
       max_concurrent_trades=5, commission_per_lot=6.0, safety_buffer_pct=10.0
   - `accounts` table includes `highest_banked_balance` REAL column (Section 2.5).
     Updated in on_trade_closed() whenever current_balance > highest_banked_balance.
   - get_risk_profile(account_key) resolves: account.risk_profile_id if set, else default.
   - check_risk_limits() as specified in Section 2.7 — uses highest_banked_balance for
     overall floor when overall_trail_from_closed_balance=true.
   - Profit lock triggers on BALANCE (not equity) reaching initial × (1 + profit_lock_pct%).
   - Locked floor = initial_balance × (1 - profit_lock_floor_pct%) — 0.0 means exactly
     initial_balance (never lose original capital).
   - calculate_withdrawable() as specified in Section 2.7.
   - CRUD API for risk profiles as specified in Section 7.4.
   - Deleting a profile in use returns HTTP 400 with affected account list.

4. EOD FORCE CLOSE — 4:45 PM EST DAILY
   - All open trades on all active accounts are force-closed at 4:45 PM EST every day
     (including Fridays). This is 15 minutes before the 5pm EST daily benchmark snapshot.
   - The daily tracking reset (`daily_start_balance`, `daily_pnl`) happens
     at 5:00 PM EST, after trades are confirmed closed.
   - No news filter. No ForexFactory integration. Trading runs through all market sessions.

5. ACCOUNT CRUD
   - POST /api/accounts/discover: authenticate credential, return sub-account list.
   - POST /api/accounts/bulk-add: add selected sub-accounts, sync subscriptions,
     assign default profile, set highest_banked_balance = initial_balance.
   - DELETE /api/accounts/{key}: close open trades first, then soft-delete (retain history).
   - Per-account: risk profile assignment, concurrent trade override, channel subscriptions.

6. CHANNEL CRUD API
   - Full CRUD as per Section 7.4 Channel Management endpoints.
   - PUT /api/channels/{id}/toggle calls load_channels_from_db() + register_channel_listeners()
     after DB update so the Telethon listener rebuilds at runtime without restart.
   - GET /api/channels/logic-modules: scan channels/ directory and return list of
     {module_path, display_name} for GUI logic dial dropdowns.

7. CORE TRADING REQUIREMENTS
   - Telethon: dedicated phone account (not personal), numeric channel IDs only.
   - TradeLocker library: async, rate-limited (5 req/s per credential), multi-credential auth.
   - Partial close: client.close_position(position_id, quantity=partial_qty). No fallback.
   - Multi-account execution: asyncio.gather, filtered by channel subscription.
   - Price Delta risk engine (Section 2.8): all parameters from resolved RiskProfile.
   - BillirichyFX full entry + management logic (Sections 3–4).
   - Firepips full entry + management logic (Sections 5–6).
   - Signal IDs: <prefix>_<msg_id> where prefix from plugin.signal_prefix.
   - SQLite schema v5 with versioned migrations (Section 2.6).
   - Profitable days rolling 30-day tracking (Section 2.10).
   - GUI-only error notifications, 4 severity levels (Section 2.11).
   - Dry-run mode: full logic, no real orders, GUI DRY-RUN banner (Section 2.13).
   - Autonomous management schedulers for both channels (Sections 4.7, 6.7).
     EOD force close at 4:45 PM EST. Friday close also 4:45 PM EST.

8. REACT TWA FRONTEND
   - Global Dashboard: combined metrics + Channel Status Bar (pill badges + toggles).
     No news events panel.
   - Account Cards: Pause/Delete buttons; Channel Subscriptions panel (per-channel toggles);
     Risk Profile selector dial; withdrawable amount using calculate_withdrawable().
   - Add Account flow: credential form → discover sub-accounts → bulk select → add.
   - Settings page — 3 tabs:
     • General: lot size slider only.
     • Channel Management: table + add/edit/delete/toggle/priority.
       Add Channel modal: logic dial shows BillirichyFX Logic and Firepips Logic as
       built-in options + custom module path input.
     • Risk Profiles: table + full editor form with all profile fields including
       3-way overall drawdown selector (Trailing–Closed Balance / Trailing–Equity / Static)
       and payout buffer field.
   - RiskProfileSelector: scrollable segmented dial of profile names.
   - All channel names sourced from DB — zero hardcoded channel names in GUI.
   - WebSocket Zustand store handles all event types in Section 7.3.

Technology Stack:
- Python: Telethon, tradelocker, FastAPI, aiosqlite, importlib (dynamic module loading)
- Frontend: React (Vite), Tailwind CSS, shadcn/ui, Zustand
- Deployment: Ubuntu 22.04, systemd, Nginx, Let's Encrypt

Build Order:
1. Database init + schema v5 (channels, risk_profiles, channel_subscriptions, accounts
   with highest_banked_balance)
2. ChannelPlugin ABC + BillirichyPlugin + FirepipsPlugin
3. channel_registry.py
4. TradeLocker wrapper + multi-credential auth + sub-account enumeration
5. Profile-based risk engine (Sections 2.7/2.8) including calculate_withdrawable()
6. Dynamic Telethon client (register_channel_listeners)
7. Core execution engine (execute_on_all_accounts + on_trade_closed)
8. BillirichyFX + Firepips entry/management logic via plugin interface
9. Autonomous management scheduler (4:45 PM EST EOD force close)
10. FastAPI REST + WebSocket (all endpoints in Section 7.4)
11. React TWA frontend (dashboard → account cards → channel mgmt → risk profiles)
12. Integration tests in dry-run mode

Deliver: fully functional Mirror Pupil bot, React TWA, .env.example, init_db.py,
systemd service file, Nginx config, and README with setup instructions including
how to find numeric channel IDs and how to use the GUI for all post-deployment management.
```

---

*Mirror Pupil v5.0 — complete and self-contained. Built-in signal channels: BillirichyFX (`-1001859598768`) and Firepips (`-1001182913499`). Default risk profile: Blue Guardian Instant Standard (3% daily trailing equity, 6% overall trailing from closed balance, profit lock at +6% balance → floor locks at initial capital, 1% payout buffer). No news filter. EOD force close at 4:45 PM EST daily. All post-deployment configuration — channels, accounts, risk profiles — managed exclusively through the GUI.*



# 📘 v5.1 Addendum: Correct TL API Methods, TDlib, and Updated Entry/Management Patterns

---

## 1. Correct TradeLocker SDK Integration (v5.1)

### 1.1 TradeLocker SDK Used
The system uses **official TradeLocker Python SDK** (`pip install tradelocker`), not manual HTTP calls! The SDK provides the `TLAPI` class from `tradelocker` module!

### 1.2 Correct TLAPI Methods Called
Here are the **exact TLAPI methods** used in the system:

| Operation | TLAPI Method | Notes |
|---|---|---|
| **Authentication** | Direct HTTP POST to `/backend-api/auth/jwt/token` (not SDK) | Uses aiohttp to get access/refresh tokens |
| **Get accounts** | `client.get_all_accounts()` | Returns DataFrame → converted to list of dicts |
| **Get account state/balance** | `client.get_account_state()` | Returns balance, equity, margin, free margin, unrealized PnL |
| **Get instruments** | `client.get_all_instruments()` | Returns DataFrame of all tradable instruments |
| **Get instrument ID from symbol** | `client.get_instrument_id_from_symbol_name()` | Preferred method to resolve symbol → instrument ID |
| **Get info route ID** | `client.get_info_route_id(instrument_id)` | Check instrument has INFO route |
| **Get trade route IDs** | `client._get_route_ids(instrument_id, route_type)` | Internal SDK method to check TRADE route |
| **Create order** | `client.create_order(instrument_id, quantity, side, price, type_, validity, position_netting, take_profit, take_profit_type, stop_loss, stop_loss_type, stop_price)` | `side` lowercase ("buy"/"sell"), `type_` lowercase ("market"/"limit"/"stop"), validity "GTC"/"IOC" |
| **Modify position (SL/TP)** | `client.modify_position(position_id, stop_loss, take_profit)` | Supports both `stop_loss`/`take_profit` and `stopLoss`/`takeProfit` kwargs for backward compatibility |
| **Close position** | `client.close_position(position_id, qty)` | Supports both `qty` and `quantity` kwargs; partial close if qty is provided |
| **Delete/cancel order** | `client.delete_order(order_id)` | Supports both positional arg and `orderId` kwarg |
| **Get positions** | `client.get_all_positions()` | Returns DataFrame of open positions → converted to list of dicts |

### 1.3 Additional Features in RateLimitedClient
- **Rate limiting**: 5 requests/second via `asyncio.Semaphore(5)` + min interval of 0.2s
- **Circuit breaker**: 3 failures → opens circuit for 120s, then half-open
- **Retry decorator**: 3 retries with exponential backoff (1s → 2s → 4s)
- **Instrument cache**: 5-minute TTL per credential
- **Per-client instrument ID cache**: Cache valid instrument IDs per symbol to avoid re-resolving
- **Instrument route validation**: Validate instrument has INFO or TRADE route before using it
- **Lot step rounding**: `round_lot_size(lot_size, lot_step)` helper to ensure lot sizes are multiples of instrument lot step!

---

## 2. Telegram Client (v5.1): Uses Pytdbot (TDLib), NOT Telethon!

### 2.1 Why Pytdbot?
Pytdbot is a **TDLib-based Telegram client** (not Telethon). TDLib is Telegram's official client library, which is more stable for long-running user bots and has better human-like behavior support!

### 2.2 Pytdbot Setup
- **Library**: `pytdbot` (install: `pip install pytdbot`)
- **Client class**: `from pytdbot import Client`
- **Updates**: Uses `Update` from `pytdbot.types`
- **Logging**: `LogStreamFile` for TDLib logs

### 2.3 Human-like Behavior Features
- **Random delays**: `_human_delay()` adds random 0.5–2.0s delays between actions
- **Mark as read**: `_mark_as_read()` calls `client.viewMessages(chat_id, message_ids, force_read=True)` with human delay
- **Typing indicator**: `_typing_indicator()` calls `client.sendChatAction(chat_id, action="chatActionTyping")`
- **Health check loop**: Every 30s, calls `client.getMe()` to verify connection
- **Reconnect loop**: Auto-reconnect up to 10 times with exponential backoff (5s → 10s → ... → 60s)

### 2.4 Pytdbot Patches Added
The system applies **monkey patches** to Pytdbot to handle unknown update types gracefully:
- Patches `dict_to_obj` in `obj_encoder`, `pytdbot_utils`, and `pytdbot_client`
- Patches `Client.process_update` to skip None updates

---

## 3. Updated Entry and Management Logic Patterns (BillirichyFX)

### 3.1 Entry Signal Patterns (BillirichyFX)
Regex patterns from `channels/billirichy/entry.py`:

| Pattern | Purpose | Example |
|---|---|---|
| `DIRECTION_RE = r'\b(buy\|sell)\b'` | Detect direction (case-insensitive) | "gold buy" → "buy" |
| `ENTRY_RE = r'(?:entry\|enter)(?:\s+price)?\s*:?\s*([\d.]+)\|(?:at\|@)\s*:?\s*([\d.]+)\|\blimit\s*:?\s*([\d.]+)\|\bstop\s*:?\s*([\d.]+)'` | Extract entry price (multiple formats) | "entry price 4500" or "@ 4500" or "limit 4500" |
| `SL_RE = r'\b(?:sl\|stop\s*loss\|stoploss)\s*[:\-.]?\s*([\d.]+)'` | Extract stop loss | "sl 4450" or "stoploss: 4450" |
| `TP_RE = r'\b(?:tp\d*\|take\s*profit\|takeprofit)\s*[:\-.]?\s*([\d.]+)'` | Extract take profit(s) (supports multiple TPs like TP1, TP2, etc.) | "tp1 4900" or "take profit: 4900" |
| `LIMIT_RE = r'\blimit\b'` | Detect limit order | "limit" → order_type=LIMIT |
| `STOP_ORDER_RE = r'\bstop\s*order\b\|\bstop\s*entry\b'` | Detect stop order | "stop order" → order_type=STOP |
| **Re-entry keywords**: `add more, second entry, re-enter, reenter, stack, add, another entry, more buys, more sells` | Detect re-entry signal | "add more gold buys" → is_reentry=True |

### 3.2 Management Action Patterns (BillirichyFX)
Regex patterns from `channels/billirichy/management.py`:

| Action | Patterns | Example |
|---|---|---|
| **CLOSE_SYMBOL** | `\bclose\s+(?:the\s+)?(symbol)\b` or `\bexit\s+(?:the\s+)?(symbol)\b` | "close gold" or "exit xauusd" |
| **BREAKEVEN** | `\bset be\b\|\bbreakeven\b\|\bmove sl to entry\b\|\bmove to be\b\|\block\b\|\block profit\b` | "set be" or "breakeven" |
| **PARTIAL_CLOSE_50** | `\bclose half\b\|\bclose 50%\b\|\btake some profit\b\|\btake partials\b` | "close half" |
| **PARTIAL_CLOSE_75** | `\bclose most\b\|\bclose 75%\b` | "close 75%" |
| **PARTIAL_CLOSE_33** | `\bclose 33%\b\|\bclose one third\b\|\bclose third\b` | "close third" |
| **CLOSE_ALL** | `\bclose alll?\b\|\bexit\b\|\bexit all\b\|\bclose trades\b\|\bclose everything\b` | "close all" |
| **TP1_HIT** | `\btp1 hit\b\|\btp 1 hit\b\|\bfirst tp hit\b` | "tp1 hit" |
| **TP2_HIT** | `\btp2 hit\b` | "tp2 hit" |
| **TP3_HIT** | `\btp3 hit\b` | "tp3 hit" |
| **SL_HIT** | `\bsl hit\b\|\bstopped out\b\|\bstop hit\b` | "sl hit" |
| **MODIFY_SL** | `\bmove sl to\s+([\d.]+)\b\|\bnew sl\s*:?\s*([\d.]+)\b\|\bsl now\s*:?\s*([\d.]+)\b\|\badjust sl to\s+([\d.]+)` | "new sl 4450" or "move sl to 4450" |
| **MODIFY_TP** | `\bmove tp to\s+([\d.]+)\b\|\bnew tp\s*:?\s*([\d.]+)\b\|\btp now\s*:?\s*([\d.]+)` | "new tp 4900" or "move tp to 4900" |
| **COMPOUND** | `\bclose some and set be\b\|\bpartial and be\b` | "close some and set be" |

### 3.3 Entry Signal Parsing Flow
1. Clean up expired waiting room and message cache entries
2. Check skip_next flag (if set, skip signal, clear flag)
3. Check message cache for duplicates (if duplicate, skip)
4. Check if reply_to matches a management message (if yes, skip entry parsing)
5. Check if message completes a bare signal in waiting room
6. Detect direction, symbol, is_reentry
7. Extract SL, TPs, entry price
8. Determine order type: LIMIT (if limit keyword) / STOP (if stop order keyword) / MARKET (default)
9. If no SL → add to waiting room (bare signal)
10. If SL present → return full signal for execution

### 3.4 Waiting Room (Bare Signals)
- Stores signals without SL (bare signals) in memory: `{(channel_id, symbol, direction): {'entry_msg_id': int, 'entry_time': datetime, 'expires_at': datetime, 'signal_data': dict}}`
- Expires after 15 minutes
- Completed by:
  1. Direct reply with SL
  2. Same symbol + same direction + SL
  3. Price pattern match (no live price check now, done at execution)

---

## 4. Summary Table
| Component | v5.0 (Original) | v5.1 (Updated) |
|---|---|---|
| **Telegram Client** | Telethon | Pytdbot (TDLib-based) |
| **TradeLocker Integration** | Manual HTTP calls | Official `tradelocker` SDK with TLAPI class |
| **Lot Size Handling** | No rounding | Rounded to instrument's lot step using `round_lot_size()` |
| **Database** | SQLite only | Dual backend: SQLite + PostgreSQL (Supabase) |
| **Telegram Behavior** | No human-like delays | Random delays, mark as read, typing indicators |

