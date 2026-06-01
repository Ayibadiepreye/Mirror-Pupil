<div align="center">

# 🪞 Mirror Pupil v5.1

### *Production-Ready Telegram Copy Trading Bot*

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-Private-red.svg)]()

**Mirror Telegram signal channels to TradeLocker accounts with advanced risk management, autonomous trade management, and a beautiful mobile-first GUI.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation) • [Screenshots](#-screenshots)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Trading Core
- ✅ **Multi-Channel Support** - BillirichyFX & Firepips
- ✅ **Smart Signal Parsing** - 25+ symbols, 12+ actions
- ✅ **Context Matching** - 8-level & 9-level matching
- ✅ **Re-Entry Detection** - 7-level parent matching
- ✅ **Multi-Account Execution** - Parallel trade execution
- ✅ **TradeLocker Integration** - Rate-limited, circuit breaker

</td>
<td width="50%">

### 🛡️ Risk Management
- ✅ **Profile-Based System** - Blue Guardian Instant Standard
- ✅ **Daily Loss Limits** - 3% static intraday floor
- ✅ **Overall Loss Limits** - 6% trailing from closed balance
- ✅ **Profit Lock** - +6% balance → floor locks at initial
- ✅ **Breach Monitoring** - Real-time enforcement
- ✅ **Withdrawal Detection** - Automatic balance reconciliation

</td>
</tr>
<tr>
<td width="50%">

### 🤖 Autonomous Management
- ✅ **Auto TP Assignment** - 15-min for incomplete signals
- ✅ **Breakeven Rules** - 1-hour profit-based
- ✅ **Partial Close** - 50% at 2 hours
- ✅ **Full Close** - 4-hour time limit
- ✅ **Trailing Stops** - After TP1 hit
- ✅ **Pending Order Monitor** - 2-hour expiry

</td>
<td width="50%">

### 🎨 Modern GUI
- ✅ **Telegram Web App** - Mobile-first design
- ✅ **Knights of the Blood Oath Theme** - Custom dark theme
- ✅ **Real-Time Updates** - 5-second auto-refresh
- ✅ **Dashboard** - Combined metrics across accounts
- ✅ **Active Trades** - Live trade monitoring
- ✅ **Settings** - Full control panel

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (Neon recommended)
- Telegram API credentials
- TradeLocker account

### 1️⃣ Clone & Install

```bash
# Clone the repository
git clone <your-repo-url>
cd mirror-pupil

# Install backend dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 2️⃣ Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required credentials:**

| Service | Variables | Get From |
|---------|-----------|----------|
| **Telegram** | `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE` | https://my.telegram.org/apps |
| **TDLib** | `TDLIB_ENCRYPTION_KEY` | Generate: `openssl rand -hex 32` |
| **Database** | `DATABASE_URL` | Your Neon dashboard |
| **TradeLocker** | `TL_EMAIL_1`, `TL_PASSWORD_1`, `TL_SERVER_1` | Your trading account |

### 3️⃣ Start Backend

```bash
# Start FastAPI server
uvicorn backend.api.main:app --reload --port 8000
```

**Backend will be available at:**
- 🌐 API: http://localhost:8000
- 📚 Docs: http://localhost:8000/docs
- ❤️ Health: http://localhost:8000/health

### 4️⃣ Start Frontend

```bash
# Start React dev server
cd frontend
npm run dev
```

**Frontend will be available at:**
- 🎨 GUI: http://localhost:3000

### 5️⃣ Test the System

1. Open browser to http://localhost:3000
2. View Dashboard with combined metrics
3. Check Accounts page
4. Monitor Active Trades
5. Configure Settings

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Channels                        │
│              (BillirichyFX, Firepips, etc.)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Telegram Client (Pytdbot)                   │
│         • Anti-ban features  • Auto-reconnect                │
│         • Multi-channel      • Health checks                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Signal Parsers                            │
│    ┌──────────────────┐        ┌──────────────────┐        │
│    │  BillirichyFX    │        │    Firepips      │        │
│    │  • 25+ symbols   │        │  • 15+ symbols   │        │
│    │  • 12 actions    │        │  • 8 actions     │        │
│    │  • 8-level match │        │  • 9-level match │        │
│    └──────────────────┘        └──────────────────┘        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Risk Management                            │
│  • Profile-based rules    • Daily/overall limits             │
│  • Profit lock system     • Breach monitoring                │
│  • Balance reconciliation • Withdrawal detection             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Trade Executor                             │
│  • Multi-account execution  • Retry logic                    │
│  • Channel subscriptions    • Status tracking                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  TradeLocker API                             │
│  • Rate limiting (5 req/s)  • Circuit breaker                │
│  • Instrument caching       • Token refresh                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Trading Accounts                            │
│              (Multiple accounts supported)                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Autonomous Managers                         │
│  • Auto TP (15 min)      • Breakeven (1 hour)               │
│  • Partial close (2h)    • Full close (4 hours)             │
│  • Trailing stops        • Pending order monitor            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  • REST API (20+ endpoints)  • WebSocket server              │
│  • CORS for TWA              • Swagger docs                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  React GUI (Telegram Web App)                │
│  • Dashboard  • Accounts  • Trades  • History  • Settings   │
│  • Mobile-first  • Real-time updates  • KOB Theme           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
mirror-pupil/
├── 📱 frontend/                    # React GUI (Telegram Web App)
│   ├── src/
│   │   ├── components/            # Reusable UI components
│   │   │   ├── Layout.tsx         # Main layout with navigation
│   │   │   ├── AccountCard.tsx    # Account display card
│   │   │   └── StatCard.tsx       # Dashboard stat card
│   │   ├── pages/                 # Application pages
│   │   │   ├── Dashboard.tsx      # Main dashboard
│   │   │   ├── Accounts.tsx       # Account management
│   │   │   ├── ActiveTrades.tsx   # Live trades view
│   │   │   ├── TradeHistory.tsx   # Historical trades
│   │   │   └── Settings.tsx       # Configuration
│   │   ├── lib/
│   │   │   └── api.ts             # API client (axios)
│   │   ├── types/
│   │   │   └── index.ts           # TypeScript types
│   │   ├── App.tsx                # Router setup
│   │   ├── main.tsx               # Entry point
│   │   └── index.css              # Global styles + KOB theme
│   ├── package.json               # Dependencies
│   ├── vite.config.ts             # Vite configuration
│   ├── tailwind.config.js         # Tailwind + theme
│   └── tsconfig.json              # TypeScript config
│
├── 🐍 backend/                     # Python backend
│   ├── api/                       # FastAPI application
│   │   ├── main.py                # FastAPI app + lifespan
│   │   ├── websocket.py           # WebSocket server
│   │   ├── requirements.txt       # API dependencies
│   │   └── routes/                # API endpoints
│   │       ├── accounts.py        # Account CRUD
│   │       ├── channels.py        # Channel CRUD
│   │       ├── risk_profiles.py   # Risk profiles
│   │       ├── trades.py          # Active trades
│   │       ├── bot_control.py     # Bot status
│   │       └── notifications.py   # Notifications
│   │
│   ├── channels/                  # Signal parsers
│   │   ├── base.py                # Base plugin class
│   │   ├── registry.py            # Channel registry
│   │   ├── billirichy/            # BillirichyFX parser
│   │   │   ├── plugin.py          # Main plugin
│   │   │   ├── entry.py           # Entry signal parser
│   │   │   ├── management.py      # Management actions
│   │   │   ├── context_matcher.py # 8-level matching
│   │   │   ├── reentry_matcher.py # 7-level re-entry
│   │   │   ├── autonomous.py      # Autonomous manager
│   │   │   └── symbol_map.py      # Symbol mappings
│   │   └── firepips/              # Firepips parser
│   │       ├── plugin.py          # Main plugin
│   │       ├── entry.py           # Entry signal parser
│   │       ├── management.py      # Management actions
│   │       ├── context_matcher.py # 9-level matching
│   │       ├── autonomous.py      # Autonomous manager
│   │       └── symbol_map.py      # Symbol mappings
│   │
│   ├── core/                      # Core trading logic
│   │   ├── tradelocker_client.py  # TradeLocker wrapper
│   │   ├── account_manager.py     # Multi-account manager
│   │   ├── trade_executor.py      # Trade execution
│   │   ├── trailing_stop_updater.py # Trailing stops
│   │   ├── pending_order_monitor.py # Pending orders
│   │   └── balance_reconciliation.py # Balance sync
│   │
│   ├── database/                  # Database layer
│   │   ├── manager.py             # Database manager
│   │   ├── models.py              # Data models
│   │   └── schema.py              # Schema v5
│   │
│   └── risk/                      # Risk management
│       ├── calculator.py          # Price delta calculations
│       ├── enforcer.py            # Risk enforcement
│       ├── daily_reset.py         # Daily reset (5pm EST)
│       ├── eod_close.py           # EOD close (4:45pm EST)
│       └── consistency.py         # 20% rule calculator
│
├── 📄 Documentation
│   ├── README.md                  # This file
│   ├── mirror_pupil_spec_v5.md    # Complete specification
│   ├── FINAL_SYSTEM_AUDIT_REPORT.md # System audit
│   ├── BUILD_COMPLETE_SUMMARY.md  # Build summary
│   ├── PHASE7_8_COMPLETE.md       # Phase 7 & 8 docs
│   └── QUICKSTART_GUI.md          # GUI quick start
│
├── 🔧 Configuration
│   ├── .env.example               # Environment template
│   ├── .env                       # Your config (git-ignored)
│   ├── .gitignore                 # Git ignore rules
│   └── requirements.txt           # Python dependencies
│
└── 📊 Data (git-ignored)
    ├── tdlib_data/                # TDLib session data
    └── logs/                      # Application logs
```

---

## 🎨 Knights of the Blood Oath Theme

The GUI features a custom dark theme inspired by the Knights of the Blood Oath guild:

<table>
<tr>
<td width="25%"><b>Base Layer</b><br><code>#16161a</code></td>
<td width="75%">Sidebar, bottom navigation, modal backdrops</td>
</tr>
<tr>
<td width="25%"><b>App Layer</b><br><code>#1e1e24</code></td>
<td width="75%">Main content background, cards, inputs</td>
</tr>
<tr>
<td width="25%"><b>Guild Crimson</b><br><code>#b22222</code></td>
<td width="75%">Headers, section dividers, scrollbars</td>
</tr>
<tr>
<td width="25%"><b>Vibrant Red</b><br><code>#e74c3c</code></td>
<td width="75%">Active states, buttons, focus indicators</td>
</tr>
</table>

**Visual Hierarchy:**
```
┌─────────────────────────────────────┐
│  Mirror Pupil v5.1          KOB     │ ← Guild Crimson (#b22222)
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Account 1                  │   │ ← Base Layer (#16161a)
│  │  Balance: $10,000           │   │
│  │  P&L: +$250 (2.5%) ↑       │   │
│  └─────────────────────────────┘   │
│                                     │ ← App Layer (#1e1e24)
│  ┌─────────────────────────────┐   │
│  │  Account 2                  │   │
│  │  Balance: $5,000            │   │
│  │  P&L: -$50 (-1.0%) ↓       │   │
│  └─────────────────────────────┘   │
│                                     │
├─────────────────────────────────────┤
│ [🏠] [👥] [📈] [📜] [⚙️]          │ ← Base Layer (#16161a)
│  ^                                  │
│  └─ Vibrant Red (#e74c3c) when active
└─────────────────────────────────────┘
```

---

## 🎯 Implementation Status

<table>
<tr>
<th width="20%">Phase</th>
<th width="40%">Component</th>
<th width="20%">Status</th>
<th width="20%">Completion</th>
</tr>
<tr>
<td><b>Phase 1</b></td>
<td>Telegram Client (Pytdbot/TDLib)</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td><b>Phase 2</b></td>
<td>Signal Parsers (BillirichyFX, Firepips)</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td><b>Phase 3</b></td>
<td>TradeLocker Integration</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td><b>Phase 4</b></td>
<td>Database Layer (Neon PostgreSQL)</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td><b>Phase 5</b></td>
<td>Risk Management System</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td><b>Phase 6</b></td>
<td>Autonomous Management</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td><b>Phase 7</b></td>
<td>FastAPI Backend (REST + WebSocket)</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td><b>Phase 8</b></td>
<td>React GUI (Telegram Web App)</td>
<td>✅ Complete</td>
<td>100%</td>
</tr>
<tr>
<td colspan="2"><b>Overall System</b></td>
<td><b>✅ Production Ready</b></td>
<td><b>100%</b></td>
</tr>
</table>

---

## 📊 API Endpoints

### Accounts
```http
GET    /api/accounts/              # Get all accounts
GET    /api/accounts/{key}         # Get specific account
POST   /api/accounts/              # Create account
PUT    /api/accounts/{key}         # Update account
DELETE /api/accounts/{key}         # Delete account
POST   /api/accounts/{key}/pause   # Pause account
POST   /api/accounts/{key}/resume  # Resume account
```

### Channels
```http
GET  /api/channels/                # Get all channels
GET  /api/channels/{id}            # Get specific channel
POST /api/channels/                # Create channel
POST /api/channels/{id}/enable     # Enable channel
POST /api/channels/{id}/disable    # Disable channel
```

### Risk Profiles
```http
GET  /api/risk-profiles/           # Get all profiles
GET  /api/risk-profiles/default    # Get default profile
```

### Trades
```http
GET  /api/trades/active            # Get all active trades
GET  /api/trades/active/{key}      # Get trades for account
```

### Bot Control
```http
GET  /api/bot/status               # Get bot status
```

### WebSocket
```http
WS   /ws/updates                   # Real-time updates
```

**API Documentation:** http://localhost:8000/docs (Swagger UI)

---

## 🔐 Security Features

<table>
<tr>
<td width="50%">

### Telegram Security
- ✅ **TDLib Official Library** - Telegram's official client
- ✅ **Anti-Ban Measures** - Human-like behavior
- ✅ **Random Delays** - 0.5-2.0s between actions
- ✅ **Mark as Read** - Automatic message reading
- ✅ **Typing Indicators** - Shows "typing..." status
- ✅ **Health Checks** - 30-second connection verification
- ✅ **Auto-Reconnect** - Exponential backoff (10 attempts)

</td>
<td width="50%">

### Trading Security
- ✅ **Encrypted Credentials** - Database encryption
- ✅ **Rate Limiting** - 5 req/s to TradeLocker
- ✅ **Circuit Breaker** - 3 failures → 120s cooldown
- ✅ **Retry Logic** - 3 attempts with backoff
- ✅ **Risk Validation** - Pre-trade checks
- ✅ **Breach Monitoring** - Real-time enforcement
- ✅ **Audit Logging** - Complete trade history

</td>
</tr>
</table>

---

## 🤖 Autonomous Management Rules

### BillirichyFX

| Time | Action | Condition |
|------|--------|-----------|
| **15 min** | Auto TP Assignment | If no TP set: TP = entry ± 2× SL distance |
| **1 hour** | Breakeven | If profit ≥ 15 pips (XAUUSD) or 8 pips (forex) |
| **2 hours** | Partial Close 50% | If in profit |
| **4 hours** | Full Close | Any state (profit or loss) |
| **Continuous** | Trailing Stop | After TP1 hit: trail by 15 pips (XAUUSD) or 8 pips (forex) |

### Firepips

| Time | Action | Condition |
|------|--------|-----------|
| **1 hour** | Breakeven | If floating P&L > 0 |
| **2 hours** | Partial Close 50% | If in profit |
| **4 hours** | Full Close | Any state (profit or loss) |
| **Continuous** | Trailing Stop | After TP1 hit: trail by 8 pips (forex) |

### Pending Orders

| Time | Action |
|------|--------|
| **2 hours** | Cancel expired LIMIT and STOP orders |

**Check Intervals:**
- Autonomous managers: Every 60 seconds
- Trailing stops: Every 60 seconds
- Pending orders: Every 10 minutes
- Balance reconciliation: Every 5 minutes

---

## 📈 Risk Management

### Blue Guardian Instant Standard (Default Profile)

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Daily Loss Limit** | 3% | Static intraday floor from daily start balance |
| **Overall Loss Limit** | 6% | Trailing from closed balance (highest banked) |
| **Profit Lock** | +6% | When balance reaches +6%, floor locks at initial |
| **Payout Buffer** | 1% | Safety margin above floor before breach |
| **Max Concurrent Trades** | 5 | Maximum open positions per account |
| **Commission** | $6/lot | Included in risk calculations |
| **Safety Buffer** | 10% | Extra margin for risk calculations |

### Risk Calculation

```python
# Daily Loss Floor
daily_floor = daily_start_balance * (1 - 0.03)

# Overall Loss Floor (trailing)
overall_floor = highest_banked_balance * (1 - 0.06)

# Profit Lock (when balance ≥ initial * 1.06)
if current_balance >= initial_balance * 1.06:
    overall_floor = initial_balance  # Lock at initial

# Effective Floor (highest of the two)
effective_floor = max(daily_floor, overall_floor)

# Payout Buffer
payout_floor = effective_floor * 1.01

# Breach Check
if current_balance < payout_floor:
    # BREACH - Stop all trading
```

### Withdrawal Handling

When a withdrawal is detected (balance drop > $0.50):
1. ✅ Update `current_balance` and `last_synced_balance`
2. ✅ **DO NOT** update `highest_banked_balance` (keeps trailing floor)
3. ✅ **DO NOT** update `daily_start_balance` (keeps daily floor)
4. ✅ Send WARNING notification with new headroom
5. ✅ Broadcast WebSocket event for GUI update

---

## 🎮 GUI Pages

### 📊 Dashboard
- **Combined Metrics** - Total balance, P&L, trades, accounts
- **Account Cards** - Scrollable list with key metrics
- **Real-Time Updates** - 5-second auto-refresh
- **Trend Indicators** - Up/down arrows for P&L

### 👥 Accounts
- **Account List** - All connected accounts
- **Status Badges** - ACTIVE / PAUSED / BREACHED
- **Risk Metrics** - Initial, peak, profit lock, headroom
- **Quick Actions** - Pause/resume buttons

### 📈 Active Trades
- **Live Trade List** - All open positions
- **Trade Details** - Symbol, direction, entry, SL, TP
- **Time Tracking** - Time since entry
- **Risk Display** - Lot size, risk USD
- **Status Badges** - PENDING / FILLED / PARTIAL

### 📜 Trade History
- **Historical Trades** - Closed positions
- **Filters** - By account, channel, date range
- **Export** - CSV/Excel export (planned)
- **P&L Summary** - Win rate, total P&L

### ⚙️ Settings
- **Bot Status** - Running/stopped, live/dry-run
- **Channel Management** - Enable/disable channels
- **Risk Profiles** - View and manage profiles
- **Account Settings** - Credentials, risk profile assignment

---

## 🛠️ Development

### Backend Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn backend.api.main:app --reload --port 8000

# Run tests (when implemented)
pytest tests/

# Check code style
black backend/
flake8 backend/
```

### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npm run type-check

# Lint
npm run lint
```

### Database Migrations

```bash
# Create new migration
python -m backend.database.migrate create "description"

# Run migrations
python -m backend.database.migrate up

# Rollback migration
python -m backend.database.migrate down
```

---

## 🧪 Testing

### Dry-Run Mode

Before going live, test with `DRY_RUN=true` in your `.env` file:

```bash
# In .env
DRY_RUN=true
```

**Dry-run behavior:**
- ✅ Parse all signals normally
- ✅ Calculate risk and validate trades
- ✅ Log what would have been executed
- ❌ **DO NOT** place any real orders
- ❌ **DO NOT** modify positions
- ❌ **DO NOT** cancel orders

**Recommendation:** Run in dry-run for at least 3 trading days before going live.

### Demo Accounts

1. Create demo accounts on TradeLocker
2. Add credentials to `.env`
3. Test with real signals but demo money
4. Verify all features work correctly

### Test Checklist

- [ ] Telegram connection works
- [ ] Signals are parsed correctly
- [ ] Risk calculations are accurate
- [ ] Trades execute successfully
- [ ] Management actions work
- [ ] Autonomous rules trigger
- [ ] Balance reconciliation detects withdrawals
- [ ] Trailing stops update correctly
- [ ] Pending orders expire
- [ ] GUI displays correct data
- [ ] WebSocket updates work
- [ ] All API endpoints respond

---

## 📱 Telegram Web App Deployment

### 1. Build Frontend

```bash
cd frontend
npm run build
```

This creates a production build in `frontend/dist/`.

### 2. Deploy to HTTPS Server

**Options:**
- **Vercel**: `vercel deploy`
- **Netlify**: `netlify deploy`
- **GitHub Pages**: Push to `gh-pages` branch
- **Custom Server**: Upload `dist/` folder

**Requirements:**
- ✅ Must use HTTPS (Telegram requirement)
- ✅ Must be publicly accessible
- ✅ Must serve `index.html` for all routes

### 3. Create Telegram Bot

1. Message [@BotFather](https://t.me/BotFather)
2. Create new bot: `/newbot`
3. Set web app URL: `/setmenubutton`
4. Paste your frontend URL

### 4. Test in Telegram

1. Open your bot in Telegram
2. Click the menu button
3. GUI opens in Telegram Web App
4. Test all features

---

## 🚨 Troubleshooting

<details>
<summary><b>Backend won't start</b></summary>

**Check:**
- ✅ All dependencies installed: `pip install -r requirements.txt`
- ✅ `.env` file exists with all required variables
- ✅ Database URL is correct and accessible
- ✅ Port 8000 is not already in use

**Solution:**
```bash
# Check if port is in use
netstat -ano | findstr :8000

# Kill process if needed
taskkill /PID <PID> /F

# Restart backend
uvicorn backend.api.main:app --reload --port 8000
```
</details>

<details>
<summary><b>Frontend won't start</b></summary>

**Check:**
- ✅ Node.js 18+ installed: `node --version`
- ✅ Dependencies installed: `npm install`
- ✅ Port 3000 is not already in use

**Solution:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Restart frontend
npm run dev
```
</details>

<details>
<summary><b>Telegram connection fails</b></summary>

**Check:**
- ✅ API_ID and API_HASH are correct
- ✅ Phone number includes country code (e.g., `+1234567890`)
- ✅ Internet connection is stable
- ✅ Firewall allows TDLib connections

**Solution:**
```bash
# Delete TDLib session and re-authenticate
rm -rf tdlib_data/

# Restart backend
uvicorn backend.api.main:app --reload --port 8000

# Enter verification code when prompted
```
</details>

<details>
<summary><b>TradeLocker API errors</b></summary>

**Check:**
- ✅ Credentials are correct
- ✅ Server URL is correct (e.g., `https://demo.tradelocker.com`)
- ✅ Account is not locked or suspended
- ✅ Rate limit not exceeded (5 req/s)

**Solution:**
```bash
# Check logs for specific error
tail -f logs/mirror_pupil.log

# Verify credentials in .env
cat .env | grep TL_

# Test authentication manually
python -c "from backend.core.tradelocker_client import TradeLockerClient; client = TradeLockerClient(...); print(client.authenticate())"
```
</details>

<details>
<summary><b>GUI shows no data</b></summary>

**Check:**
- ✅ Backend is running: http://localhost:8000/health
- ✅ API URL is correct in frontend `.env`
- ✅ CORS is configured correctly
- ✅ Database has data

**Solution:**
```bash
# Check backend health
curl http://localhost:8000/health

# Check API response
curl http://localhost:8000/api/accounts/

# Check browser console for errors
# Open DevTools (F12) → Console tab
```
</details>

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[mirror_pupil_spec_v5.md](mirror_pupil_spec_v5.md)** | Complete system specification (v5.1) |
| **[FINAL_SYSTEM_AUDIT_REPORT.md](FINAL_SYSTEM_AUDIT_REPORT.md)** | Comprehensive system audit with verification |
| **[BUILD_COMPLETE_SUMMARY.md](BUILD_COMPLETE_SUMMARY.md)** | Build summary for all 8 phases |
| **[PHASE7_8_COMPLETE.md](PHASE7_8_COMPLETE.md)** | Phase 7 & 8 implementation details |
| **[QUICKSTART_GUI.md](QUICKSTART_GUI.md)** | GUI quick start guide |
| **[Pytdbot Docs](https://pytdbot.readthedocs.io/)** | Telegram client library documentation |
| **[TradeLocker API](https://tradelocker.com/api-docs)** | TradeLocker API documentation |
| **[Neon Docs](https://neon.tech/docs)** | Neon PostgreSQL documentation |
| **[FastAPI Docs](https://fastapi.tiangolo.com/)** | FastAPI framework documentation |
| **[React Docs](https://react.dev/)** | React library documentation |

---

## 🎯 Supported Channels

### BillirichyFX

**Symbols:** XAUUSD, GBPUSD, EURUSD, USDJPY, GBPJPY, EURJPY, AUDUSD, NZDUSD, USDCAD, USDCHF, EURGBP, EURAUD, EURNZD, GBPAUD, GBPNZD, AUDNZD, AUDCAD, AUDCHF, NZDCAD, NZDCHF, CADCHF, US30, USOIL

**Actions:**
1. Entry signals (MARKET, LIMIT, STOP)
2. BREAKEVEN
3. PARTIAL_CLOSE_33
4. PARTIAL_CLOSE_50
5. PARTIAL_CLOSE_75
6. CLOSE_ALL
7. TP1_HIT, TP2_HIT, TP3_HIT
8. SL_HIT
9. MODIFY_SL
10. MODIFY_TP
11. COMPOUND (close 33% + breakeven)
12. Re-entry signals

**Context Matching:** 8-level hierarchy
**Re-Entry Matching:** 7-level parent matching
**Autonomous Rules:** 15min/1h/2h/4h

### Firepips

**Symbols:** XAUUSD, GBPUSD, EURUSD, USDJPY, GBPJPY, EURJPY, AUDUSD, NZDUSD, USDCAD, USDCHF, EURGBP, US30, USOIL

**Actions:**
1. Entry signals (MARKET, LIMIT, STOP)
2. CLOSE_ALL (profit)
3. CLOSE_ALL (loss)
4. SL_HIT
5. MODIFY_SL
6. MODIFY_TP
7. BREAKEVEN
8. CANCEL_PENDING
9. IMPLIED_CLOSE (profit announcement)

**Context Matching:** 9-level hierarchy (includes "all trades" fallback)
**Autonomous Rules:** 1h/2h/4h

---

## 🔌 Adding New Channels

### Via GUI (Recommended)

1. Open Settings page
2. Click "Add Channel"
3. Enter channel ID and display name
4. Select logic modules (entry, management, autonomous)
5. Save

### Via Database (Manual)

```sql
-- Insert channel
INSERT INTO channels (channel_id, display_name, priority, enabled, entry_module, management_module, autonomous_module)
VALUES (-1001234567890, 'My Channel', 3, true, 'mychannel.entry', 'mychannel.management', 'mychannel.autonomous');

-- Enable for all accounts
INSERT INTO channel_subscriptions (account_key, channel_id, enabled)
SELECT account_key, -1001234567890, true FROM accounts;
```

### Create Plugin

```python
# backend/channels/mychannel/plugin.py
from backend.channels.base import ChannelPlugin

class MyChannelPlugin(ChannelPlugin):
    def __init__(self):
        super().__init__(
            channel_id=-1001234567890,
            display_name="My Channel",
            priority=3
        )
    
    async def parse_entry(self, message):
        # Parse entry signals
        pass
    
    async def parse_management(self, message):
        # Parse management actions
        pass
    
    async def autonomous_manager(self):
        # Autonomous rules
        pass
```

---

## 🤝 Contributing

This is a private project. If you're working on it:

1. **Always test in dry-run mode first**
2. **Never commit real credentials**
3. **Document any changes to the spec**
4. **Test with both BillirichyFX and Firepips**
5. **Follow the existing code style**
6. **Write clear commit messages**

### Code Style

**Python:**
- Use Black for formatting: `black backend/`
- Use flake8 for linting: `flake8 backend/`
- Follow PEP 8 guidelines
- Type hints for all functions

**TypeScript:**
- Use Prettier for formatting
- Follow Airbnb style guide
- Type everything (no `any`)
- Use functional components

---

## ⚠️ Disclaimer

**This bot is for educational and personal use only.**

Trading involves significant risk. Always:
- ✅ Start with demo accounts
- ✅ Test thoroughly in dry-run mode
- ✅ Understand the risk management rules
- ✅ Never risk more than you can afford to lose
- ✅ Comply with your prop firm's rules
- ✅ Monitor the bot regularly
- ✅ Have a backup plan

**The developers are not responsible for any trading losses.**

---

## 📞 Support

For issues or questions:

1. Check this README
2. Read the [full spec](mirror_pupil_spec_v5.md)
3. Check the [audit report](FINAL_SYSTEM_AUDIT_REPORT.md)
4. Review logs in `./logs/` and `./tdlib_data/tdlib.log`
5. Check API docs at http://localhost:8000/docs

---

## 📜 License

**Private Project** - All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

---

<div align="center">

## 🎉 Ready to Trade!

**Mirror Pupil v5.1** is production-ready with all 8 phases complete.

Start testing today and take your copy trading to the next level.

---

**Version:** 5.1  
**Status:** ✅ Production Ready (All 8 Phases Complete)  
**Last Updated:** May 31, 2026

**Built with ❤️ using Python, FastAPI, React, TypeScript, and the Knights of the Blood Oath theme**

[⬆ Back to Top](#-mirror-pupil-v51)

</div>
