# 🚀 Mirror Pupil v5.1 - GUI Quick Start

**Get the GUI running in 5 minutes!**

---

## 📋 Prerequisites

- Python 3.10+ installed
- Node.js 18+ installed
- PostgreSQL database (Neon) configured
- Existing Mirror Pupil backend working

---

## ⚡ Quick Start

### Step 1: Install Backend API Dependencies

```bash
cd "c:\Users\bonni\Music\Mirror Pupil"
pip install fastapi uvicorn websockets pydantic python-multipart
```

### Step 2: Install Frontend Dependencies

```bash
cd frontend
npm install
```

### Step 3: Start Backend Server

Open a terminal and run:

```bash
cd "c:\Users\bonni\Music\Mirror Pupil"
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

**You should see:**
```
🚀 Starting Mirror Pupil FastAPI Backend...
✓ Database connected
✓ Trade executor initialized
✓ Risk enforcer initialized
✓ BillirichyFX autonomous manager started
✓ Firepips autonomous manager started
✓ Balance reconciliation started
✓ Trailing stop updater started
✓ Pending order monitor started
✅ Mirror Pupil Backend Ready
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Start Frontend Dev Server

Open a **new terminal** and run:

```bash
cd "c:\Users\bonni\Music\Mirror Pupil\frontend"
npm run dev
```

**You should see:**
```
  VITE v5.0.11  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

### Step 5: Open the GUI

Open your browser to: **http://localhost:3000**

You should see the Mirror Pupil dashboard with the Knights of the Blood Oath theme!

---

## 🎨 What You'll See

### Dashboard
- Total balance across all accounts
- Daily P&L with trend indicators
- Active trades count
- Account cards with metrics

### Navigation
Bottom bar with 5 tabs:
- 🏠 **Dashboard** - Overview
- 👥 **Accounts** - Account management
- 📈 **Trades** - Active trades
- 📜 **History** - Trade history
- ⚙️ **Settings** - Configuration

### Theme
Knights of the Blood Oath colors:
- Dark backgrounds (#16161a, #1e1e24)
- Crimson accents (#b22222)
- Vibrant red highlights (#e74c3c)

---

## 🔍 Testing the API

### Swagger UI

Visit: **http://localhost:8000/docs**

You can test all API endpoints directly from the browser!

### Health Check

Visit: **http://localhost:8000/health**

Should return:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Get Accounts

```bash
curl http://localhost:8000/api/accounts/
```

### Get Active Trades

```bash
curl http://localhost:8000/api/trades/active
```

---

## 🐛 Troubleshooting

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Fix:**
```bash
pip install fastapi uvicorn websockets pydantic python-multipart
```

### Frontend won't start

**Error:** `Cannot find module 'react'`

**Fix:**
```bash
cd frontend
npm install
```

### Can't connect to database

**Error:** `Failed to connect to database`

**Fix:**
1. Check `.env` file has correct `DATABASE_URL`
2. Verify Neon database is running
3. Check network connection

### API calls fail

**Error:** `Network Error` in browser console

**Fix:**
1. Make sure backend is running on port 8000
2. Check CORS configuration in `backend/api/main.py`
3. Verify frontend proxy in `frontend/vite.config.ts`

### Theme not loading

**Error:** Colors look wrong

**Fix:**
1. Make sure Tailwind CSS is installed: `npm install -D tailwindcss`
2. Check `frontend/tailwind.config.js` exists
3. Restart frontend dev server

---

## 📱 Mobile Testing

The GUI is mobile-first! Test on your phone:

1. Find your computer's IP address:
   ```bash
   ipconfig
   ```

2. Start frontend with host flag:
   ```bash
   npm run dev -- --host
   ```

3. Open on phone:
   ```
   http://YOUR_IP:3000
   ```

---

## 🚀 Next Steps

### Add Your First Account

1. Go to **Settings** page
2. Click **Add Account** (coming soon)
3. Enter TradeLocker credentials
4. Save

### View Active Trades

1. Go to **Trades** page
2. See all open positions
3. Auto-refreshes every 5 seconds

### Monitor Performance

1. Go to **Dashboard**
2. View combined metrics
3. Check individual account cards

---

## 📚 Documentation

- **Full Spec:** `mirror_pupil_spec_v5.md`
- **API Docs:** http://localhost:8000/docs
- **Phase 7 & 8 Details:** `PHASE7_8_COMPLETE.md`

---

## ✅ Success Checklist

- [ ] Backend starts without errors
- [ ] Frontend starts without errors
- [ ] Can access http://localhost:3000
- [ ] Can access http://localhost:8000/docs
- [ ] Dashboard loads with accounts
- [ ] Navigation works between pages
- [ ] Theme colors look correct
- [ ] Active trades page shows trades
- [ ] Settings page shows channels

---

**You're ready to use Mirror Pupil v5.1 GUI!** 🎉

For production deployment, see `PHASE7_8_COMPLETE.md`
