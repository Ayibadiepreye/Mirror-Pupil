# Mirror Pupil - Windows VPS/Server Deployment Guide 🪟

Complete guide to deploy Mirror Pupil on Windows Server or Windows VPS with automatic startup and background service.

---

## 📋 Prerequisites

### Required Software
1. **Windows Server 2019/2022** or **Windows 10/11 Pro** with VPS
2. **Python 3.10+**: https://www.python.org/downloads/
3. **PostgreSQL 14+**: https://www.postgresql.org/download/windows/
4. **Git**: https://git-scm.com/download/win
5. **NSSM** (for Windows service): https://nssm.cc/download

### Required Accounts
- Firebase Project
- Telegram API credentials
- TradeLocker accounts
- Vercel account (for frontend)

---

## 🖥️ Part 1: Windows Server Setup

### Step 1: Install Required Software

#### Install Python
1. Download Python 3.10+ from https://www.python.org/downloads/windows/
2. Run installer
3. ✅ **IMPORTANT**: Check "Add Python to PATH"
4. Click "Install Now"
5. Verify installation:
```powershell
python --version
# Should show: Python 3.10.x or higher

pip --version
# Should show pip version
```

#### Install PostgreSQL
1. Download from https://www.postgresql.org/download/windows/
2. Run installer
3. During installation:
   - Password: Choose a secure password (remember this!)
   - Port: 5432 (default)
   - Locale: Default
4. Finish installation
5. Add to PATH (if not automatic):
   - Right-click "This PC" → Properties
   - Advanced system settings → Environment Variables
   - Under System Variables, find "Path"
   - Add: `C:\Program Files\PostgreSQL\14\bin`

#### Install Git
1. Download from https://git-scm.com/download/win
2. Run installer with default options
3. Verify:
```powershell
git --version
```

#### Install NSSM (for Windows Service)
1. Download from https://nssm.cc/download
2. Extract ZIP file
3. Copy `nssm.exe` from `win64` folder to `C:\Windows\System32`
4. Verify:
```powershell
nssm --version
```

### Step 2: Setup PostgreSQL Database

#### Open Command Prompt as Administrator

```powershell
# Navigate to PostgreSQL bin folder
cd "C:\Program Files\PostgreSQL\14\bin"

# Create database and user
psql -U postgres

# Inside PostgreSQL prompt, run these commands:
CREATE DATABASE mirrorpupil;
CREATE USER mirrorpupil WITH PASSWORD 'YourSecurePassword123!';
GRANT ALL PRIVILEGES ON DATABASE mirrorpupil TO mirrorpupil;
\q
```

#### Test Connection
```powershell
psql -U mirrorpupil -d mirrorpupil -h localhost
# Enter password when prompted
# If successful, type \q to exit
```

### Step 3: Clone Repository

```powershell
# Create project directory
cd C:\
mkdir Projects
cd Projects

# Clone repository
git clone YOUR_REPOSITORY_URL
cd "Mirror Pupil"
```

### Step 4: Setup Python Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r backend\api\requirements.txt

# Deactivate for now
deactivate
```

### Step 5: Configure Environment Variables

```powershell
# Copy example .env file
copy .env.example .env

# Edit with Notepad
notepad .env
```

Fill in your configuration:

```env
# Database - Use your PostgreSQL password
DATABASE_URL=postgresql://mirrorpupil:YourSecurePassword123!@localhost/mirrorpupil

# Firebase Credentials (from Firebase Console)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour\nPrivate\nKey\nHere\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com

# Telegram API (from https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+1234567890
TELEGRAM_SESSION_NAME=mirror_pupil_session

# Channel IDs (from Telegram)
BILLIRICHY_CHANNEL_ID=-1001859598768
FIREPIPS_CHANNEL_ID=-1001182913499

# Trading Settings
DEFAULT_LOT_SIZE=0.01
DRY_RUN=false

# Security
SECRET_KEY=generate_random_secure_string_here

# CORS (add your frontend URL later)
CORS_ORIGINS=http://localhost:5173,https://your-app.vercel.app
```

**Save and close Notepad**

---

## 🔑 Getting Required Credentials

### Firebase Setup

1. **Firebase Console**: https://console.firebase.google.com
2. **Create Project** → Name it → Disable Analytics → Create
3. **Enable Authentication**:
   - Authentication → Get started
   - Email/Password → Enable → Save
4. **Service Account Key**:
   - Project Settings → Service accounts
   - Generate new private key → Download JSON
5. **Extract from JSON**:
   - `project_id` → `FIREBASE_PROJECT_ID`
   - `private_key` → `FIREBASE_PRIVATE_KEY`
   - `client_email` → `FIREBASE_CLIENT_EMAIL`
6. **Create First User**:
   - Authentication → Users → Add user
   - Note the User UID

### Telegram API

1. Go to: https://my.telegram.org
2. Log in → API development tools
3. Create Application:
   - App title: "Mirror Pupil"
   - Platform: Desktop
4. Copy:
   - `api_id` → `TELEGRAM_API_ID`
   - `api_hash` → `TELEGRAM_API_HASH`

### Telegram Channel IDs

Forward a message from the channel to @userinfobot to get the channel ID.

---

## 🗄️ Initialize Database

```powershell
# Make sure you're in project directory
cd C:\Projects\Mirror Pupil

# Activate virtual environment
.\venv\Scripts\activate

# Initialize database
python -m backend.database.schema

# Verify
cd "C:\Program Files\PostgreSQL\14\bin"
psql -U mirrorpupil -d mirrorpupil -h localhost
\dt
# Should see all tables
\q

# Go back to project directory
cd C:\Projects\Mirror Pupil
```

### Make First User Super Admin

```powershell
# Connect to database
cd "C:\Program Files\PostgreSQL\14\bin"
psql -U mirrorpupil -d mirrorpupil -h localhost

# Update user (replace with your Firebase User UID)
UPDATE users SET is_super_admin = true WHERE user_id = 'YOUR_FIREBASE_USER_UID';

\q
```

---

## 🚀 Method 1: Run as Windows Service (Recommended)

This method makes the bot start automatically with Windows and run in the background.

### Create Windows Service with NSSM

```powershell
# Open Command Prompt as Administrator

# Navigate to project directory
cd C:\Projects\Mirror Pupil

# Install service
nssm install MirrorPupil "C:\Projects\Mirror Pupil\venv\Scripts\python.exe" "C:\Projects\Mirror Pupil\main.py"

# Configure service
nssm set MirrorPupil AppDirectory "C:\Projects\Mirror Pupil"
nssm set MirrorPupil DisplayName "Mirror Pupil Trading Bot"
nssm set MirrorPupil Description "Automated Telegram trading signal mirror for TradeLocker"
nssm set MirrorPupil Start SERVICE_AUTO_START

# Set up logging
nssm set MirrorPupil AppStdout "C:\Projects\Mirror Pupil\logs\output.log"
nssm set MirrorPupil AppStderr "C:\Projects\Mirror Pupil\logs\error.log"

# Create logs directory
mkdir logs

# Start service
nssm start MirrorPupil
```

### Service Management Commands

```powershell
# Check status
nssm status MirrorPupil

# Start service
nssm start MirrorPupil

# Stop service
nssm stop MirrorPupil

# Restart service
nssm restart MirrorPupil

# Remove service (if needed)
nssm remove MirrorPupil confirm

# View logs
type logs\output.log
type logs\error.log
```

### Alternative: Using Windows Services GUI

1. Press `Win + R`
2. Type `services.msc` and press Enter
3. Find "Mirror Pupil Trading Bot"
4. Right-click → Properties
5. Set Startup type: Automatic
6. Click Start

---

## 🚀 Method 2: Run with Task Scheduler

Alternative method using Windows Task Scheduler for automatic startup.

### Create Startup Script

Create `start_mirrorpupil.bat`:

```batch
@echo off
cd C:\Projects\Mirror Pupil
call venv\Scripts\activate.bat
python main.py
pause
```

Save as: `C:\Projects\Mirror Pupil\start_mirrorpupil.bat`

### Setup Task Scheduler

1. Press `Win + R`, type `taskschd.msc`, press Enter
2. Click "Create Task" (not Basic Task)
3. **General Tab**:
   - Name: Mirror Pupil Trading Bot
   - Description: Automated trading bot
   - ✅ Run whether user is logged on or not
   - ✅ Run with highest privileges
4. **Triggers Tab**:
   - New → Begin the task: At startup
   - OK
5. **Actions Tab**:
   - New → Action: Start a program
   - Program: `C:\Projects\Mirror Pupil\start_mirrorpupil.bat`
   - OK
6. **Conditions Tab**:
   - ❌ Uncheck "Start the task only if the computer is on AC power"
7. **Settings Tab**:
   - ✅ Allow task to be run on demand
   - ✅ If the task fails, restart every: 1 minute
8. Click OK
9. Enter Windows password when prompted

### Test Task

Right-click task → Run

Check logs:
```powershell
type C:\Projects\Mirror Pupil\logs\output.log
```

---

## 🚀 Method 3: Manual Run (Development/Testing)

For testing or manual control:

```powershell
# Open Command Prompt or PowerShell
cd C:\Projects\Mirror Pupil

# Activate virtual environment
.\venv\Scripts\activate

# Run bot
python main.py

# To stop: Press Ctrl+C
```

### Keep Window Open After Reboot

Create shortcut:
1. Right-click Desktop → New → Shortcut
2. Location: `C:\Projects\Mirror Pupil\start_mirrorpupil.bat`
3. Name: "Mirror Pupil Bot"
4. Finish
5. Copy shortcut to: `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp`

---

## 🌐 Configure Windows Firewall

### Allow Backend Port (if accessing from other machines)

```powershell
# Open PowerShell as Administrator

# Allow port 8000 (backend API)
New-NetFirewallRule -DisplayName "Mirror Pupil API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

Or using GUI:
1. Windows Defender Firewall → Advanced settings
2. Inbound Rules → New Rule
3. Port → TCP → 8000
4. Allow the connection
5. Name: "Mirror Pupil API"

---

## ✅ Verification

### Check Backend Health

```powershell
# If accessing from same machine
curl http://localhost:8000/health

# Or open browser
start http://localhost:8000/health
# Should show: {"status": "healthy"}
```

### Check Service Status

```powershell
# For NSSM service
nssm status MirrorPupil

# View recent logs
type logs\output.log | more
```

### Check Database

```powershell
cd "C:\Program Files\PostgreSQL\14\bin"
psql -U mirrorpupil -d mirrorpupil -h localhost

SELECT COUNT(*) FROM accounts;
SELECT COUNT(*) FROM active_trades;
\q
```

### Monitor in Real-Time

Use **PowerShell** to tail logs:

```powershell
Get-Content -Path "C:\Projects\Mirror Pupil\logs\output.log" -Wait -Tail 50
```

---

## 🔧 Maintenance & Updates

### Update Code

```powershell
# Stop service
nssm stop MirrorPupil

# Update code
cd C:\Projects\Mirror Pupil
git pull

# Update dependencies
.\venv\Scripts\activate
pip install -r backend\api\requirements.txt
deactivate

# Restart service
nssm start MirrorPupil
```

### Backup Database

```powershell
# Create backup
cd "C:\Program Files\PostgreSQL\14\bin"
pg_dump -U mirrorpupil mirrorpupil > "C:\Projects\Mirror Pupil\backups\backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql"

# Restore backup
psql -U mirrorpupil mirrorpupil < "C:\Projects\Mirror Pupil\backups\backup_20240101.sql"
```

### Scheduled Database Backup

Create `backup.bat`:

```batch
@echo off
cd "C:\Program Files\PostgreSQL\14\bin"
set BACKUP_FILE=C:\Projects\Mirror Pupil\backups\backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql
pg_dump -U mirrorpupil mirrorpupil > %BACKUP_FILE%
```

Add to Task Scheduler (daily at 2 AM):
1. Task Scheduler → Create Task
2. Name: Mirror Pupil Database Backup
3. Trigger: Daily at 2:00 AM
4. Action: Start program → `C:\Projects\Mirror Pupil\backup.bat`

---

## 🐛 Troubleshooting

### Service Won't Start

```powershell
# Check status
nssm status MirrorPupil

# View error logs
type logs\error.log

# Check if Python is in PATH
python --version

# Check if port 8000 is in use
netstat -ano | findstr :8000
```

### Database Connection Failed

```powershell
# Check if PostgreSQL is running
# Services → Look for "PostgreSQL"

# Or via PowerShell
Get-Service -Name "postgresql*"

# Test connection
cd "C:\Program Files\PostgreSQL\14\bin"
psql -U mirrorpupil -d mirrorpupil -h localhost

# Check .env file
type .env | findstr DATABASE_URL
```

### Telegram Session Issues

```powershell
# Delete session files
cd C:\Projects\Mirror Pupil
del *.session

# Restart service
nssm restart MirrorPupil

# Check logs for 2FA code
type logs\output.log | findstr -i "telegram code"
```

### Python Module Not Found

```powershell
# Reinstall dependencies
cd C:\Projects\Mirror Pupil
.\venv\Scripts\activate
pip install --upgrade -r backend\api\requirements.txt
deactivate

# Restart service
nssm restart MirrorPupil
```

### High Memory/CPU Usage

```powershell
# Open Task Manager (Ctrl+Shift+Esc)
# Find "python.exe" under MirrorPupil service

# Check process details
Get-Process -Name python

# Restart service if needed
nssm restart MirrorPupil
```

---

## 🔒 Security Best Practices

### 1. Secure PostgreSQL

```powershell
# Edit pg_hba.conf
notepad "C:\Program Files\PostgreSQL\14\data\pg_hba.conf"

# Change this line:
# host    all             all             127.0.0.1/32            trust
# To:
# host    all             all             127.0.0.1/32            md5

# Restart PostgreSQL service
Restart-Service postgresql*
```

### 2. Strong Passwords

- Use complex passwords for PostgreSQL
- Use strong SECRET_KEY in .env
- Change default Windows admin password

### 3. Windows Updates

```powershell
# Check for updates
# Settings → Update & Security → Windows Update
```

### 4. Firewall Rules

- Only open necessary ports
- Restrict access to trusted IPs if possible

### 5. Backup Regularly

Set up automated backups (see Maintenance section)

---

## 📊 Monitoring

### View Live Logs

```powershell
# PowerShell (tail equivalent)
Get-Content -Path "C:\Projects\Mirror Pupil\logs\output.log" -Wait -Tail 50

# Or use third-party tools:
# - BareTail (free log viewer)
# - Notepad++ with "Monitor tail" plugin
```

### Resource Monitoring

```powershell
# Task Manager (Ctrl+Shift+Esc)
# Performance tab → CPU, Memory, Network

# Or PowerShell
Get-Process python | Select-Object CPU, WorkingSet, Name
```

### Database Monitoring

```powershell
cd "C:\Program Files\PostgreSQL\14\bin"
psql -U mirrorpupil -d mirrorpupil -h localhost

-- Check active connections
SELECT COUNT(*) FROM pg_stat_activity;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

\q
```

---

## 🌐 Remote Access Setup (Optional)

### Using Remote Desktop

1. Enable Remote Desktop:
   - Settings → System → Remote Desktop → Enable
2. Connect from another PC:
   - Run `mstsc`
   - Enter VPS IP address
   - Log in with credentials

### Using Ngrok (for API access)

1. Download ngrok: https://ngrok.com/download
2. Extract to `C:\Projects\ngrok`
3. Run:
```powershell
cd C:\Projects\ngrok
ngrok http 8000
```
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. Use this URL in frontend `VITE_API_BASE_URL`

---

## 🎉 Success Checklist

- [ ] PostgreSQL installed and running
- [ ] Python environment set up
- [ ] Repository cloned
- [ ] .env file configured with all credentials
- [ ] Database initialized
- [ ] First user created and made super admin
- [ ] Windows service created and running
- [ ] Firewall configured (if needed)
- [ ] Logs show successful startup
- [ ] Health endpoint responds: http://localhost:8000/health
- [ ] Telegram connected (check logs)
- [ ] Frontend deployed to Vercel
- [ ] Test trade executed successfully

---

## 🚀 Next Steps

1. **Add TradeLocker Accounts**: Via web GUI
2. **Configure Risk Profiles**: Set loss limits and rules
3. **Subscribe to Channels**: Link accounts to signal channels
4. **Test with DRY_RUN=true**: Verify signals are parsed
5. **Monitor Logs**: Watch first trades execute
6. **Switch to Live**: Set DRY_RUN=false when ready

---

## 📞 Support

**Common Issues**:
- Service won't start: Check logs in `logs\error.log`
- Database errors: Verify PostgreSQL is running
- Telegram issues: Delete .session files and restart
- Import errors: Reinstall requirements.txt

**Helpful Commands**:
```powershell
# Service status
nssm status MirrorPupil

# View logs
type logs\output.log | more

# Check database
psql -U mirrorpupil -d mirrorpupil -h localhost

# Restart everything
nssm restart MirrorPupil
```

---

## 🎯 Congratulations!

Your Mirror Pupil trading bot is now running on Windows as a background service! It will automatically start with Windows and run 24/7.

**Happy Trading! 🚀📈**
