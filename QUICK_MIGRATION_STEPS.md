# 🚀 QUICK MIGRATION - 5 STEPS

**From:** Neon PostgreSQL  
**To:** VPS PostgreSQL (100.126.60.57)  

---

## STEP 1: Test VPS Connection ⚡

```bash
py migrate_to_vps.py --test-only
```

**Expected:** ✓ Successfully connected to VPS database

---

## STEP 2: Run Migration 📊

```bash
py migrate_to_vps.py
```

**When prompted, type:** `yes`

**Expected:** ✅ MIGRATION COMPLETED SUCCESSFULLY

---

## STEP 3: Update .env File ⚙️

```bash
py update_env_database.py
```

**Expected:** ✓ Updated .env with new VPS database URL

---

## STEP 4: Test New Connection 🧪

```bash
py test_database_connection.py
```

**Expected:** ✅ CONNECTION TEST PASSED

---

## STEP 5: Deploy to VPS 🚀

### A. Copy code to VPS

```bash
# Create archive (exclude large folders)
tar -czf mirror-pupil.tar.gz ^
  --exclude=node_modules ^
  --exclude=tdlib_data ^
  --exclude=__pycache__ ^
  --exclude=.git ^
  --exclude=Lovable* ^
  .

# Copy to VPS
scp mirror-pupil.tar.gz user@100.126.60.57:/tmp/
```

### B. On VPS - Extract and setup

```bash
# SSH into VPS
ssh user@100.126.60.57

# Extract
sudo mkdir -p /opt/mirror-pupil
cd /opt/mirror-pupil
sudo tar -xzf /tmp/mirror-pupil.tar.gz

# Install dependencies
pip install -r backend/api/requirements.txt
pip install asyncpg python-dotenv loguru python-telegram-bot

# Copy .env from local to VPS
# (use scp from local machine)
```

### C. On VPS - Start services

```bash
cd /opt/mirror-pupil

# Create logs directory
mkdir -p logs

# Start API
nohup python -m backend.api.main > logs/api.log 2>&1 &

# Start Telegram bot
nohup python -m backend.telegram_integration > logs/telegram.log 2>&1 &

# Check logs
tail -f logs/api.log
tail -f logs/telegram.log
```

**Expected in logs:**
```
✓ Connected to database
✓ Started breach monitoring (60s interval)
✓ Started profit cap monitoring (10s interval)
```

---

## ✅ VERIFICATION

```bash
# Test API (on VPS)
curl http://localhost:8000/health

# Test API (from local)
curl http://100.126.60.57:8000/health

# Expected:
{"status":"healthy","database":"connected"}
```

---

## 📱 UPDATE FRONTEND

### Mobile App

```bash
cd "Lovable Frontend/export/mobile"

# Update .env
echo "API_BASE_URL=http://100.126.60.57:8000" > .env

# Rebuild
flutter clean
flutter build apk --release
```

### Web App

```bash
cd "Lovable Frontend"

# Update .env
echo "VITE_API_URL=http://100.126.60.57:8000" > .env

# Rebuild
npm run build
```

---

## 🎉 DONE!

Your Mirror Pupil bot is now running on your VPS with:
- ✅ All data migrated
- ✅ New PostgreSQL database
- ✅ Backend services running
- ✅ Profit caps enabled
- ✅ Telegram bot listening

**Start trading!** 🚀

---

## 🆘 TROUBLESHOOTING

**Migration fails?**
- Check VPS IP: `100.126.60.57`
- Verify PostgreSQL running: `sudo systemctl status postgresql`
- Test connection: `psql -h 100.126.60.57 -U kirito -d mirror_pupil`

**Backend won't start?**
- Check .env copied to VPS
- Verify DATABASE_URL updated
- Check logs: `tail -f logs/api.log`

**Can't connect from local?**
- Check VPS firewall: `sudo ufw status`
- Allow port 8000: `sudo ufw allow 8000`
- Test: `curl http://100.126.60.57:8000/health`

---

**For detailed guide, see: VPS_MIGRATION_GUIDE.md**
