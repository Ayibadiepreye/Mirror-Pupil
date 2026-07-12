# 🚀 VPS DATABASE MIGRATION GUIDE

**Migration:** Neon PostgreSQL → VPS PostgreSQL  
**Date:** July 12, 2026  
**Target:** `100.126.60.57:5432`  

---

## 📋 PRE-MIGRATION CHECKLIST

### VPS Database Setup
- [x] PostgreSQL installed on VPS
- [x] Database created: `mirror_pupil`
- [x] User created: `kirito` with password `Mirrorpupil2026`
- [x] User has full privileges on `mirror_pupil` database
- [x] PostgreSQL accepting remote connections (port 5432)
- [x] Firewall allows connections from your IP

### Local Environment
- [ ] Python dependencies installed (`asyncpg`)
- [ ] Current Neon database accessible
- [ ] Backup of current data (optional but recommended)

---

## 🔧 STEP 1: TEST VPS DATABASE CONNECTION

**Purpose:** Verify you can connect to the VPS database before migrating.

```bash
# Test connection only (no migration)
py migrate_to_vps.py --test-only
```

**Expected Output:**
```
✓ Successfully connected to VPS database
✓ PostgreSQL version: PostgreSQL 15.x
✓ Database is empty (ready for schema creation)
```

**If connection fails:**
- Check VPS IP address is correct: `100.126.60.57`
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check firewall allows port 5432: `sudo ufw status`
- Verify pg_hba.conf allows remote connections
- Test with psql: `psql -h 100.126.60.57 -U kirito -d mirror_pupil`

---

## 📊 STEP 2: RUN DATABASE MIGRATION

**Purpose:** Copy all data from Neon to VPS PostgreSQL.

```bash
# Run full migration
py migrate_to_vps.py
```

**You'll be prompted:**
```
⚠️  WARNING: This will migrate ALL data to the VPS database.
Proceed with migration? (yes/no):
```

Type `yes` and press Enter.

**Migration Process:**
1. Connects to source (Neon) database ✓
2. Connects to target (VPS) database ✓
3. Reads schema from source ✓
4. Creates schema on target ✓
5. Migrates data table by table ✓
6. Verifies row counts match ✓

**Expected Tables Migrated:**
- `risk_profiles`
- `users`
- `accounts`
- `channel_subscriptions`
- `active_trades`
- `trade_history`
- `notifications`

**Expected Output:**
```
[1/6] Connecting to source database (Neon)...
✓ Connected to source database

[2/6] Connecting to target database (VPS)...
✓ Connected to target database

[3/6] Reading schema from source database...
✓ Found 7 tables: accounts, active_trades, channel_subscriptions, ...

[4/6] Creating schema on target database...
✓ Schema created successfully

[5/6] Migrating data...
  Migrating table: risk_profiles
    Source rows: 1
    ✓ Migrated 1 rows
  
  Migrating table: users
    Source rows: 2
    ✓ Migrated 2 rows
  
  Migrating table: accounts
    Source rows: 5
    ✓ Migrated 5 rows
  
  ... (continues for all tables)

[6/6] Verifying migration...
  ✓ risk_profiles: 1 rows (match)
  ✓ users: 2 rows (match)
  ✓ accounts: 5 rows (match)
  ✓ channel_subscriptions: 10 rows (match)
  ✓ active_trades: 0 rows (match)
  ✓ trade_history: 150 rows (match)
  ✓ notifications: 0 rows (match)

✅ MIGRATION COMPLETED SUCCESSFULLY

Next steps:
1. Update .env file with new DATABASE_URL
2. Restart backend services
3. Test connection and functionality
```

**If migration fails:**
- Check error message in output
- Verify both databases are accessible
- Check for network interruptions
- Retry migration (script handles conflicts)

---

## 🔐 STEP 3: UPDATE TELEGRAM SESSION STRING

**Purpose:** Generate a new session for the VPS environment.

### Option A: Let Backend Generate Session (Recommended)

1. **Update .env with new database URL** (see Step 4)

2. **Delete old session files:**
   ```bash
   # On your local machine
   del /s /q tdlib_data
   ```

3. **Start backend on VPS:**
   ```bash
   # On VPS
   cd /path/to/mirror-pupil
   python -m backend.telegram_integration
   ```

4. **Follow authentication prompts:**
   - Enter phone number: +2347016797259
   - Enter code from Telegram
   - Session will be saved to `tdlib_data/`

### Option B: Pre-generate Session Locally

1. **Run session generator:**
   ```bash
   py generate_telegram_session.py
   ```

2. **Follow prompts and authenticate**

3. **Copy `tdlib_data/` folder to VPS:**
   ```bash
   scp -r tdlib_data/ user@100.126.60.57:/path/to/mirror-pupil/
   ```

**Note:** The session string is stored in the `tdlib_data/` directory. TDLib handles session persistence automatically.

---

## ⚙️ STEP 4: UPDATE .ENV FILE

**Purpose:** Point backend to new VPS database.

**Old DATABASE_URL (Neon):**
```env
DATABASE_URL=postgresql://neondb_owner:npg_vAt9yIXHwV6i@ep-raspy-forest-aqjyqp6v-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

**New DATABASE_URL (VPS):**
```env
DATABASE_URL=postgresql://kirito:Mirrorpupil2026@100.126.60.57:5432/mirror_pupil
```

**Update command:**
```bash
# Open .env file
notepad .env

# Replace DATABASE_URL line with new VPS URL
# Save and close
```

**Or use this script to update automatically:**
```bash
py update_env_database.py
```

---

## 🧪 STEP 5: TEST CONNECTION WITH NEW DATABASE

**Purpose:** Verify backend can connect to VPS database.

```bash
# Test database connection
py test_database_connection.py
```

**Expected Output:**
```
Testing connection to: postgresql://kirito:***@100.126.60.57:5432/mirror_pupil
✓ Connected successfully
✓ Database version: PostgreSQL 15.x
✓ Found 7 tables
✓ Found 5 accounts
✓ Found 150 trade history records
✓ All profit cap columns exist

Connection test PASSED ✅
```

---

## 🚀 STEP 6: DEPLOY TO VPS

**Purpose:** Deploy backend to VPS and start services.

### A. Transfer Code to VPS

```bash
# From your local machine
# Zip the project (excluding large folders)
tar -czf mirror-pupil.tar.gz \
  --exclude=node_modules \
  --exclude=tdlib_data \
  --exclude=__pycache__ \
  --exclude=.git \
  .

# Copy to VPS
scp mirror-pupil.tar.gz user@100.126.60.57:/tmp/

# SSH into VPS
ssh user@100.126.60.57

# Extract
cd /opt
sudo mkdir -p mirror-pupil
sudo tar -xzf /tmp/mirror-pupil.tar.gz -C mirror-pupil
cd mirror-pupil
```

### B. Install Dependencies on VPS

```bash
# Install Python dependencies
pip install -r backend/api/requirements.txt

# Install additional dependencies
pip install asyncpg python-dotenv loguru
```

### C. Copy .env File

```bash
# Copy updated .env from local to VPS
scp .env user@100.126.60.57:/opt/mirror-pupil/
```

### D. Start Backend Services

```bash
# Start API server
nohup python -m backend.api.main > logs/api.log 2>&1 &

# Start Telegram integration
nohup python -m backend.telegram_integration > logs/telegram.log 2>&1 &

# Check processes
ps aux | grep python

# Check logs
tail -f logs/api.log
tail -f logs/telegram.log
```

**Expected in logs:**
```
✓ Connected to database
✓ Started breach monitoring (60s interval)
✓ Started profit cap monitoring (10s interval)
✓ Telegram client initialized
✓ Listening to channels: ...
```

---

## ✅ STEP 7: VERIFICATION

**Purpose:** Ensure everything works on VPS.

### Test API Endpoint

```bash
# From VPS
curl http://localhost:8000/health

# Expected:
{"status":"healthy","database":"connected"}
```

### Test from Local Machine

```bash
# Test API accessibility
curl http://100.126.60.57:8000/health

# If using domain
curl https://your-domain.com/health
```

### Check Database

```bash
# SSH into VPS
ssh user@100.126.60.57

# Connect to database
psql -h 100.126.60.57 -U kirito -d mirror_pupil

# Run queries
SELECT COUNT(*) FROM accounts;
SELECT COUNT(*) FROM trade_history;
SELECT account_key, profit_cap_enabled FROM accounts;

# Exit
\q
```

### Test Telegram Bot

1. Send a test signal to one of your monitored channels
2. Check logs: `tail -f logs/telegram.log`
3. Verify signal was received and processed
4. Check database for new active_trade record

---

## 🔄 STEP 8: UPDATE FRONTEND CONFIG

**Purpose:** Point mobile/web apps to new VPS backend.

### Flutter Mobile App

**Update API URL in .env:**
```env
# Lovable Frontend/export/mobile/.env
API_BASE_URL=http://100.126.60.57:8000

# Or if using domain
API_BASE_URL=https://your-domain.com
```

**Rebuild app:**
```bash
cd "Lovable Frontend/export/mobile"
flutter clean
flutter pub get
flutter build apk --release
```

### Web Frontend

**Update API URL:**
```env
# Lovable Frontend/.env
VITE_API_URL=http://100.126.60.57:8000

# Or if using domain
VITE_API_URL=https://your-domain.com
```

**Rebuild:**
```bash
cd "Lovable Frontend"
npm run build
```

---

## 📊 MIGRATION SUMMARY

**What was migrated:**
- ✅ All database tables and schema
- ✅ All user accounts
- ✅ All TradeLocker account configurations
- ✅ All trade history
- ✅ All risk profiles
- ✅ All channel subscriptions
- ✅ Profit cap settings
- ✅ Current PnL columns

**What needs new setup:**
- ⚠️ Telegram session (generate on VPS)
- ⚠️ Backend services (start on VPS)
- ⚠️ Frontend config (point to VPS)
- ⚠️ SSL/Domain setup (optional)

**What stays the same:**
- ✅ Telegram API credentials
- ✅ TradeLocker account credentials (encrypted)
- ✅ Firebase authentication
- ✅ Encryption keys
- ✅ All other .env settings

---

## 🆘 TROUBLESHOOTING

### Migration Issues

**"Connection refused"**
- Check VPS IP: `ping 100.126.60.57`
- Check PostgreSQL running: `sudo systemctl status postgresql`
- Check firewall: `sudo ufw status`

**"Authentication failed"**
- Verify username: `kirito`
- Verify password: `Mirrorpupil2026`
- Check pg_hba.conf allows password auth

**"Table count mismatch"**
- Re-run migration (script handles conflicts)
- Check source and target row counts manually
- Verify network stability during migration

### Backend Issues

**"Cannot connect to database"**
- Verify DATABASE_URL in .env is correct
- Test with psql: `psql $DATABASE_URL`
- Check VPS firewall allows your IP

**"Telegram authentication failed"**
- Delete `tdlib_data/` folder
- Re-run authentication flow
- Check TELEGRAM_API_ID and TELEGRAM_API_HASH

**"Profit cap not working"**
- Check logs: `grep "profit cap" logs/api.log`
- Verify columns exist: `\d accounts` in psql
- Check monitoring started in logs

---

## 🔒 SECURITY CHECKLIST

After migration:

- [ ] Change default PostgreSQL password
- [ ] Configure firewall to limit database access
- [ ] Set up SSL for database connections
- [ ] Use environment variables for credentials
- [ ] Regular database backups scheduled
- [ ] Monitor database access logs
- [ ] Set up fail2ban for SSH
- [ ] Configure HTTPS for API (Let's Encrypt)

---

## 📞 SUPPORT

**Documentation:**
- Migration script: `migrate_to_vps.py`
- This guide: `VPS_MIGRATION_GUIDE.md`
- Profit cap docs: `PROFIT_CAP_DEPLOYMENT_READY.md`

**Useful Commands:**
```bash
# Check VPS database
psql -h 100.126.60.57 -U kirito -d mirror_pupil

# Check backend logs
tail -f /opt/mirror-pupil/logs/*.log

# Restart services
sudo systemctl restart mirror-pupil-*

# Check processes
ps aux | grep python
```

---

## ✅ POST-MIGRATION CHECKLIST

- [ ] Migration script ran successfully
- [ ] All tables migrated with matching row counts
- [ ] .env file updated with new DATABASE_URL
- [ ] Telegram session generated on VPS
- [ ] Backend services running on VPS
- [ ] API health check passes
- [ ] Database queries work
- [ ] Telegram bot receiving signals
- [ ] Frontend apps updated with new API URL
- [ ] Mobile app rebuilt and tested
- [ ] Web app rebuilt and deployed
- [ ] All accounts visible in UI
- [ ] Trade history displays correctly
- [ ] Profit caps configured and working
- [ ] First live trade tested successfully

---

**Migration Date:** _____________  
**Completed By:** _____________  
**Verification Status:** _____________  

🎉 **Congratulations! Your Mirror Pupil bot is now running on your VPS!** 🚀
