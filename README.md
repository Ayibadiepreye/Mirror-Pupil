# Mirror Pupil 🎯

**Automated Telegram Trading Signal Mirror for TradeLocker**

Mirror Pupil is a production-ready trading bot that automatically monitors Telegram channels for trading signals and executes them on multiple TradeLocker accounts with advanced risk management, autonomous trade management, and real-time P&L tracking.

---

## 🌟 Features

### Core Functionality
- **Multi-Account Trading**: Manage unlimited TradeLocker accounts simultaneously
- **Telegram Integration**: Monitor multiple signal channels (BillirichyFX, Firepips)
- **Smart Signal Parsing**: Handles entry signals, management updates, and bare signals (waiting room)
- **Order Types**: Market, Limit, and Stop orders with automatic position tracking
- **Live P&L Tracking**: Real-time unrealized P&L updates every 15 seconds

### Risk Management
- **Daily Loss Limits**: Automatic breach detection and account pausing
- **Max Drawdown Protection**: Configurable per-account limits
- **Profit Lock**: Lock in profits based on all-time high equity
- **Trailing Stops**: Automatic trailing stop-loss management
- **Lot Size Control**: Per-account lot size with override capability
- **Trading Hours Validation**: Respects market hours and EOD cutoffs

### Autonomous Management
- **Time-Based Actions**: Automatic breakeven, partial closes, and full closes
- **Waiting Room**: Handles incomplete signals awaiting completion
- **Pending Order Monitoring**: Tracks limit/stop orders until filled or expired
- **Position Reconciliation**: Syncs with TradeLocker every 30 seconds
- **EOD Force Close**: Automatically closes all positions at 4:45 PM EST

### User Interface
- **Web Dashboard**: React-based GUI with real-time updates
- **Mobile App**: Flutter mobile application for iOS/Android
- **Multi-User Support**: Firebase authentication with user/super-admin roles
- **Account Management**: Add/edit accounts, risk profiles, channel subscriptions
- **Live Notifications**: Push notifications for trades, breaches, and updates
- **Trade History**: Export trade history to CSV

---

## 📋 System Requirements

### Backend (Python)
- Python 3.10 or higher
- PostgreSQL 14 or higher
- 2GB+ RAM recommended
- Linux VPS (Ubuntu 22.04 recommended)

### Frontend (React)
- Node.js 18+ or deployment to Vercel
- Modern browser with JavaScript enabled

### Mobile (Flutter)
- Flutter 3.0+
- Android Studio / Xcode for building

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd "Mirror Pupil"
```

### 2. Set Up Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
nano .env
```

### 4. Initialize Database
```bash
python -m backend.database.schema
```

### 5. Run Backend
```bash
python main.py
```

### 6. Set Up Frontend
```bash
cd "Lovable Frontend"
npm install
npm run dev
```

---

## 📦 What's Included

```
Mirror Pupil/
├── backend/                    # Python backend
│   ├── api/                   # FastAPI REST API
│   ├── channels/              # Signal parsing plugins
│   │   ├── billirichy/       # BillirichyFX parser
│   │   └── firepips/         # Firepips parser
│   ├── core/                  # Core business logic
│   │   ├── account_manager.py
│   │   ├── trade_executor.py
│   │   ├── tradelocker_client.py
│   │   ├── pnl_updater.py
│   │   └── pending_order_monitor.py
│   ├── database/              # Database models & queries
│   ├── risk/                  # Risk management
│   └── services/              # Push notifications
├── Lovable Frontend/          # React web app
│   └── src/
│       ├── components/mp/    # Mirror Pupil components
│       └── lib/mp/           # API client
├── Lovable Frontend/export/mobile/  # Flutter mobile app
└── docs/                      # Documentation
    └── DEPLOYMENT.md         # Deployment guide
```

---

## 🔧 Configuration

### Environment Variables
Required variables in `.env`:
- **Database**: `DATABASE_URL`
- **Firebase**: `FIREBASE_PROJECT_ID`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_CLIENT_EMAIL`
- **Telegram**: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`
- **Channels**: Channel IDs for BillirichyFX and Firepips
- **Trading**: `DEFAULT_LOT_SIZE`, `DRY_RUN`

See `.env.example` for full list.

### Risk Profiles
Create risk profiles via GUI or database:
- Daily loss limit (USD)
- Max drawdown (%)
- Profit lock threshold (%)
- Lot size multiplier

### Channel Subscriptions
Link accounts to channels:
1. Add account credentials
2. Subscribe account to channels
3. Configure risk profile

---

## 📊 Database Schema

PostgreSQL tables:
- `accounts` - TradeLocker account credentials
- `channels` - Telegram channel configurations
- `channel_subscriptions` - Account-channel mappings
- `risk_profiles` - Risk management rules
- `active_trades` - Open positions
- `trade_history` - Closed trades
- `waiting_room` - Incomplete signals
- `pending_orders` - Unfilled limit/stop orders
- `notifications` - Push notification queue

---

## 🔒 Security

- **Firebase Authentication**: Secure user login
- **Password Encryption**: TradeLocker passwords encrypted at rest
- **API Rate Limiting**: 5 req/s per account with circuit breakers
- **User Permissions**: Role-based access (user vs super admin)
- **Account Isolation**: Users only see their own accounts

---

## 📈 Performance

- **Concurrent Execution**: Parallel trade execution across accounts
- **Error Isolation**: One account failure doesn't affect others
- **Background Services**: Non-blocking P&L updates, reconciliation, monitoring
- **Rate Limiting**: Prevents API throttling
- **Circuit Breakers**: Auto-recovery from broker failures

---

## 🐛 Troubleshooting

### Backend won't start
- Check PostgreSQL connection
- Verify all environment variables set
- Check Python version (3.10+)
- Review logs in console

### Telegram not connecting
- Verify API credentials
- Check phone number format
- Ensure 2FA code entered correctly
- Check firewall/VPS network settings

### Trades not executing
- Verify account credentials
- Check channel subscriptions
- Ensure bot is running (not stopped)
- Check risk limits not breached
- Review logs for errors

### Frontend can't connect
- Check `VITE_API_BASE_URL` in frontend `.env`
- Verify backend is running
- Check CORS settings in backend
- Ensure Firebase config correct

---

## 📚 Documentation

- **[Deployment Guide](docs/DEPLOYMENT.md)** - VPS and Vercel deployment
- **[API Reference](API_QUICK_REFERENCE.md)** - REST API endpoints
- **Architecture** - System design and flow
- **Channel Plugins** - Adding new signal channels

---

## 🤝 Support

For issues, feature requests, or questions:
1. Check troubleshooting section
2. Review logs for error messages
3. Verify configuration settings
4. Check database for data consistency

---

## ⚠️ Disclaimer

**Trading involves substantial risk of loss. This software is provided "as is" without warranty. Use at your own risk. Past performance does not guarantee future results. Always test thoroughly with demo accounts before live trading.**

---

## 📝 License

Proprietary - All rights reserved

---

## 🎯 Roadmap

- [ ] Additional channel parsers
- [ ] Advanced analytics dashboard
- [ ] Mobile push notifications
- [ ] Webhook integrations
- [ ] Machine learning signal filtering
- [ ] Multi-broker support

---

Built with ❤️ for traders who demand precision and automation.
