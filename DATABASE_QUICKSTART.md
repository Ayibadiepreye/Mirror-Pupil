# 🚀 Database Layer - Quick Start Guide

## Prerequisites

1. **Neon PostgreSQL Account**
   - Go to https://console.neon.tech
   - Sign up (free tier available)
   - Create a new project

2. **Get Connection String**
   - In your Neon dashboard, click "Connection Details"
   - Copy the connection string (looks like):
     ```
     postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```

## Setup Steps

### 1. Add Database URL to .env

Edit your `.env` file and add:

```bash
DATABASE_URL=postgresql://user:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

Replace with your actual Neon connection string.

### 2. Install Dependencies (if not already done)

```bash
pip install -r requirements.txt
```

This includes:
- `asyncpg==0.29.0` - Async PostgreSQL driver
- `psycopg2-binary==2.9.9` - Sync PostgreSQL driver (fallback)
- `pydantic==2.5.2` - Type safety

### 3. Test Database Connection

```bash
python test_database.py
```

**Expected output:**
```
============================================================
Mirror Pupil v5.1 - Database Test
============================================================

[Test 1] Connecting to Neon PostgreSQL...
✓ Connected to PostgreSQL: PostgreSQL 15.3...
✓ Schema initialized to v5
✓ Connection successful

[Test 2] Checking schema...
✓ Found 2 channel(s)
  - BillirichyFX (ID: -1001859598768, Priority: 1)
  - Firepips (ID: -1001182913499, Priority: 2)

[Test 3] Checking risk profiles...
✓ Found 1 risk profile(s)
  - Blue Guardian Instant Standard (Default: True)
    Daily: 3.0%, Overall: 6.0%

... (8 more tests)

============================================================
✓ All database tests passed!
============================================================
```

## What Gets Created

### Tables (10 total)

1. **schema_version** - Migration tracking
2. **channels** - Signal source registry (2 built-in)
3. **risk_profiles** - Risk management rules (1 built-in)
4. **accounts** - TradeLocker sub-accounts
5. **channel_subscriptions** - Per-account channel toggles
6. **active_trades** - Open positions
7. **waiting_room** - Incomplete signals (15-min expiry)
8. **trade_history** - Closed trades with P&L
9. **profitable_days** - Daily P&L tracking
10. **message_cache** - Deduplication (2-min expiry)

### Built-in Data

**Channels:**
- BillirichyFX (ID: `-1001859598768`, Priority: 1)
- Firepips (ID: `-1001182913499`, Priority: 2)

**Risk Profile:**
- Blue Guardian Instant Standard (default)
  - Daily loss: 3%
  - Overall loss: 6%
  - Profit lock: +6%
  - Max concurrent: 5 trades
  - Commission: $6/lot

## Usage Examples

### Connect to Database

```python
from backend.database import get_db

# Get database manager (singleton)
db = await get_db()
```

### Get All Channels

```python
channels = await db.get_all_channels()
for ch in channels:
    print(f"{ch.display_name}: Priority {ch.priority}")
```

### Add an Account

```python
from backend.database import Account

account = Account(
    account_key="email@example.com:12345",
    credential_key="email@example.com",
    tl_account_id="12345",
    tl_email="email@example.com",
    tl_password="encrypted_password",
    tl_server="demo",
    initial_balance=100000.0,
    current_balance=100000.0
)

success = await db.add_account(account)
```

### Add Active Trade

```python
from backend.database import ActiveTrade

trade = ActiveTrade(
    account_key="email@example.com:12345",
    channel_id=-1001859598768,  # BillirichyFX
    signal_id="B_12345",
    symbol="XAUUSD",
    direction="BUY",
    entry_price=2650.50,
    sl=2640.00,
    tp=2670.00,
    lot_size=0.1,
    status="filled"
)

trade_id = await db.add_active_trade(trade)
```

### Check Channel Subscription

```python
is_subscribed = await db.is_channel_subscribed(
    account_key="email@example.com:12345",
    channel_id=-1001859598768
)
```

### Close Trade

```python
await db.close_active_trade(
    trade_id=123,
    exit_price=2660.0,
    pnl=95.0,
    outcome="WIN",
    close_reason="TP_HIT"
)
```

## Connection Pooling

The database manager uses asyncpg connection pooling:

- **Min connections**: 5 (always ready)
- **Max connections**: 20 (scales under load)
- **Command timeout**: 60 seconds
- **Auto-reconnect**: On connection failure

## Background Tasks

The database manager runs automatic cleanup tasks every 2 minutes:

1. **Waiting room cleanup**: Removes entries older than 15 minutes
2. **Message cache cleanup**: Removes entries older than 2 minutes

## Troubleshooting

### Connection Failed

**Error**: `Failed to connect to database`

**Solution**:
1. Check DATABASE_URL in .env
2. Verify Neon project is active
3. Check internet connection
4. Verify SSL mode is `require`

### Schema Not Initialized

**Error**: `UndefinedTableError`

**Solution**:
- The schema initializes automatically on first connect
- If it fails, check Neon dashboard for errors
- Try running `test_database.py` again

### Slow Queries

**Solution**:
- All frequently queried columns have indexes
- Connection pooling handles concurrent requests
- Neon auto-scales for performance

## Next Steps

After database is set up:

1. **Add TradeLocker credentials** (via GUI or .env)
2. **Configure risk profiles** (optional, default is Blue Guardian)
3. **Start Telegram listener** (`python telegram_client.py`)
4. **Monitor trades** (via GUI when built)

## Documentation

- **Full schema**: See `backend/database/schema.py`
- **All query methods**: See `backend/database/manager.py`
- **Type models**: See `backend/database/models.py`
- **Complete guide**: See `PHASE4_COMPLETE.md`

---

**Database Layer Status**: ✅ **READY**  
**Next Phase**: Risk Management System
