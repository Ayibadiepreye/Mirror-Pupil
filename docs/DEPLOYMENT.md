# Mirror Pupil Deployment Guide 🚀

Complete step-by-step guide to deploy Mirror Pupil backend on a VPS and frontend on Vercel.

---

## 📋 Prerequisites

Before starting, you'll need:

### Required Accounts
1. **VPS Provider** (choose one):
   - DigitalOcean (recommended)
   - Vultr
   - Linode
   - AWS Lightsail
   
2. **Vercel Account**: https://vercel.com (free tier works)

3. **Firebase Project**: https://firebase.google.com (free tier works)

4. **TradeLocker Account(s)**: Demo or live accounts

5. **Telegram Account**: For monitoring channels

### Required Services
- PostgreSQL database (can be on VPS or managed service)
- Domain name (optional but recommended)

---

## 🖥️ Part 1: VPS Backend Deployment

### Step 1: Get a VPS

#### Option A: DigitalOcean (Recommended)
1. Go to https://www.digitalocean.com
2. Sign up / Log in
3. Click "Create" → "Droplets"
4. Choose:
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic ($12/month minimum - 2GB RAM)
   - **Datacenter**: Choose closest to you
   - **Authentication**: SSH keys (recommended) or password
5. Click "Create Droplet"
6. Note your droplet's IP address

#### Option B: Other Providers
Similar process - just ensure you get Ubuntu 22.04 with 2GB+ RAM.

### Step 2: Connect to VPS

#### Windows (using PowerShell or CMD)
```bash
ssh root@YOUR_VPS_IP
# Enter password when prompted
```

#### Mac/Linux (using Terminal)
```bash
ssh root@YOUR_VPS_IP
# Enter password when prompted
```

### Step 3: Initial VPS Setup

```bash
# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3.10 python3.10-venv python3-pip postgresql postgresql-contrib git nginx supervisor

# Create a non-root user
adduser mirrorpupil
usermod -aG sudo mirrorpupil

# Switch to new user
su - mirrorpupil
```

### Step 4: Setup PostgreSQL Database

```bash
# Switch back to root temporarily
exit
sudo -u postgres psql

# Inside PostgreSQL prompt:
CREATE DATABASE mirrorpupil;
CREATE USER mirrorpupil WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE mirrorpupil TO mirrorpupil;
\q

# Update PostgreSQL to allow password auth
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Change this line:
# local   all             all                                     peer
# To:
# local   all             all                                     md5

# Restart PostgreSQL
sudo systemctl restart postgresql

# Test connection
psql -U mirrorpupil -d mirrorpupil -h localhost
# Enter password when prompted
# If successful, type \q to quit
```

### Step 5: Clone Repository

```bash
# Switch back to mirrorpupil user
su - mirrorpupil

# Clone your repository
cd ~
git clone YOUR_REPOSITORY_URL
cd "Mirror Pupil"
```

### Step 6: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r backend/api/requirements.txt
```

### Step 7: Configure Environment Variables

```bash
# Create .env file
cp .env.example .env
nano .env
```

Fill in the following (detailed steps below):

```env
# Database
DATABASE_URL=postgresql://mirrorpupil:your_secure_password_here@localhost/mirrorpupil

# Firebase (get from Firebase Console)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour\nPrivate\nKey\nHere\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project-id.iam.gserviceaccount.com

# Telegram API (get from https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+1234567890
TELEGRAM_SESSION_NAME=mirror_pupil_session

# Channels (get channel IDs from Telegram)
BILLIRICHY_CHANNEL_ID=-1001859598768
FIREPIPS_CHANNEL_ID=-1001182913499

# Trading Settings
DEFAULT_LOT_SIZE=0.01
DRY_RUN=false

# Security
SECRET_KEY=generate_a_random_secure_string_here
```

**Press Ctrl+X, then Y, then Enter to save.**

---

## 🔑 Getting Required Credentials

### Firebase Setup

1. **Go to Firebase Console**: https://console.firebase.google.com
2. **Create Project**:
   - Click "Add project"
   - Name it (e.g., "mirror-pupil")
   - Disable Google Analytics (not needed)
   - Click "Create project"

3. **Enable Authentication**:
   - Click "Authentication" in left menu
   - Click "Get started"
   - Click "Email/Password" → Enable → Save

4. **Get Service Account Key**:
   - Click gear icon → "Project settings"
   - Go to "Service accounts" tab
   - Click "Generate new private key"
   - Download the JSON file
   - Open the JSON file and extract:
     - `project_id` → `FIREBASE_PROJECT_ID`
     - `private_key` → `FIREBASE_PRIVATE_KEY` (keep the \n characters)
     - `client_email` → `FIREBASE_CLIENT_EMAIL`

5. **Create First User**:
   - Go to Authentication → Users
   - Click "Add user"
   - Enter email and password
   - Note: First user needs to be made super admin in database (see below)

### Telegram API Credentials

1. **Go to**: https://my.telegram.org
2. **Log in** with your phone number
3. **Go to**: "API development tools"
4. **Create Application**:
   - App title: "Mirror Pupil"
   - Short name: "mirrorpupil"
   - Platform: Other
   - Click "Create application"
5. **Copy**:
   - `api_id` → `TELEGRAM_API_ID`
   - `api_hash` → `TELEGRAM_API_HASH`
6. **Phone Number**: Use your Telegram phone number with country code (e.g., +1234567890)

### Telegram Channel IDs

1. **Forward a message** from the channel to @userinfobot
2. **Copy the Channel ID** (e.g., -1001859598768)
3. **Or use this Python script**:
```python
from telethon import TelegramClient
client = TelegramClient('session', API_ID, API_HASH)
client.start()
async def get_channel_id():
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            print(f"{dialog.name}: {dialog.id}")
client.loop.run_until_complete(get_channel_id())
```

---

## 🗄️ Initialize Database

```bash
# Make sure you're in the project directory with venv activated
cd ~/Mirror\ Pupil
source venv/bin/activate

# Run database initialization
python -m backend.database.schema

# Verify tables created
psql -U mirrorpupil -d mirrorpupil -h localhost
\dt
# Should see: accounts, channels, active_trades, etc.
\q
```

### Make First User Super Admin

```bash
# Connect to database
psql -U mirrorpupil -d mirrorpupil -h localhost

# Update user to super admin (replace with your Firebase user ID)
UPDATE users SET is_super_admin = true WHERE user_id = 'YOUR_FIREBASE_USER_ID';

# To find your Firebase user ID, go to Firebase Console → Authentication → Users
# Copy the "User UID"

\q
```

---

## 🚀 Run Backend with Supervisor

### Step 8: Configure Supervisor

```bash
# Switch to root
exit  # Exit mirrorpupil user
sudo nano /etc/supervisor/conf.d/mirrorpupil.conf
```

Add this configuration:

```ini
[program:mirrorpupil]
directory=/home/mirrorpupil/Mirror Pupil
command=/home/mirrorpupil/Mirror Pupil/venv/bin/python main.py
user=mirrorpupil
autostart=true
autorestart=true
stderr_logfile=/var/log/mirrorpupil.err.log
stdout_logfile=/var/log/mirrorpupil.out.log
environment=PATH="/home/mirrorpupil/Mirror Pupil/venv/bin"
```

**Save and exit (Ctrl+X, Y, Enter)**

```bash
# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start the service
sudo supervisorctl start mirrorpupil

# Check status
sudo supervisorctl status mirrorpupil
# Should show "RUNNING"

# View logs
sudo tail -f /var/log/mirrorpupil.out.log
# Press Ctrl+C to exit logs
```

### Step 9: Setup Nginx Reverse Proxy

```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/mirrorpupil
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

**Save and exit**

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mirrorpupil /etc/nginx/sites-enabled/

# Test Nginx config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Enable Nginx on boot
sudo systemctl enable nginx
```

### Step 10: Setup SSL (Optional but Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Follow prompts
# Choose: Redirect HTTP to HTTPS (option 2)

# Auto-renewal is configured automatically
# Test renewal:
sudo certbot renew --dry-run
```

### Step 11: Setup Firewall

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'

# Enable firewall
sudo ufw enable
# Type 'y' to confirm

# Check status
sudo ufw status
```

---

## 🌐 Part 2: Vercel Frontend Deployment

### Step 1: Prepare Frontend

On your local machine:

```bash
cd "Lovable Frontend"

# Create production .env file
cp .env .env.production

# Edit for production
nano .env.production
```

Update:
```env
VITE_API_BASE_URL=https://your-domain.com
# OR
VITE_API_BASE_URL=http://YOUR_VPS_IP

VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

**Get Firebase Web Config**:
1. Firebase Console → Project Settings
2. Scroll down to "Your apps"
3. Click web icon (</>)
4. Register app (name: "Mirror Pupil Web")
5. Copy the config values

```bash
# Test build locally
npm run build
# Should complete without errors
```

### Step 2: Push to GitHub

```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Prepare for Vercel deployment"

# Create repository on GitHub
# Then:
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### Step 3: Deploy on Vercel

1. **Go to**: https://vercel.com
2. **Sign up / Log in** (use GitHub account)
3. **Import Project**:
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - Select "Lovable Frontend" folder as root directory
4. **Configure**:
   - Framework Preset: Vite
   - Root Directory: `Lovable Frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
5. **Environment Variables**:
   - Add all variables from `.env.production`
   - Click "Add" for each
6. **Deploy**:
   - Click "Deploy"
   - Wait for build to complete
7. **Get URL**:
   - Copy your Vercel URL (e.g., `https://mirror-pupil.vercel.app`)

### Step 4: Update Backend CORS

```bash
# On VPS
ssh root@YOUR_VPS_IP
su - mirrorpupil
cd "Mirror Pupil"
nano .env
```

Add:
```env
CORS_ORIGINS=https://your-vercel-app.vercel.app,http://localhost:5173
```

Restart backend:
```bash
exit  # Back to root
sudo supervisorctl restart mirrorpupil
```

---

## 📱 Part 3: Mobile App (Optional)

### Build Flutter App

```bash
cd "Lovable Frontend/export/mobile"

# Update API URL
nano lib/api/api_client.dart
# Change baseUrl to your production API

# For Android
flutter build apk --release

# For iOS (requires Mac)
flutter build ios --release
```

Distribut via:
- **Android**: Upload APK to Google Play or distribute directly
- **iOS**: Upload to App Store Connect

---

## ✅ Verification Checklist

### Backend Health Check

```bash
# Check if backend is running
curl http://YOUR_VPS_IP:8000/health
# Should return: {"status": "healthy"}

# Check logs
sudo tail -f /var/log/mirrorpupil.out.log

# Check database connection
psql -U mirrorpupil -d mirrorpupil -h localhost
SELECT COUNT(*) FROM accounts;
\q
```

### Frontend Check

1. Open your Vercel URL in browser
2. Try to log in with Firebase user
3. Check browser console for errors (F12)
4. Verify API calls are reaching backend

### Telegram Check

```bash
# Check if Telegram session is active
cd ~/Mirror\ Pupil
ls -la
# Should see .session file

# Check logs for Telegram connection
sudo tail -f /var/log/mirrorpupil.out.log | grep -i telegram
```

---

## 🔧 Maintenance Commands

### Backend Commands

```bash
# View logs
sudo tail -f /var/log/mirrorpupil.out.log

# Restart backend
sudo supervisorctl restart mirrorpupil

# Stop backend
sudo supervisorctl stop mirrorpupil

# Start backend
sudo supervisorctl start mirrorpupil

# Update code
cd ~/Mirror\ Pupil
git pull
source venv/bin/activate
pip install -r backend/api/requirements.txt
exit
sudo supervisorctl restart mirrorpupil
```

### Database Commands

```bash
# Backup database
pg_dump -U mirrorpupil mirrorpupil > backup_$(date +%Y%m%d).sql

# Restore database
psql -U mirrorpupil mirrorpupil < backup_20240101.sql

# View tables
psql -U mirrorpupil -d mirrorpupil -h localhost
\dt

# View active trades
SELECT * FROM active_trades;

# View accounts
SELECT account_key, current_balance, breached FROM accounts;
```

### Frontend Updates

```bash
# Push changes to GitHub
git add .
git commit -m "Update frontend"
git push

# Vercel auto-deploys from GitHub
# Check deployment status at vercel.com
```

---

## 🐛 Troubleshooting

### Backend Issues

**Problem**: Backend not starting
```bash
# Check logs
sudo tail -100 /var/log/mirrorpupil.err.log

# Check if port 8000 is in use
sudo netstat -tulpn | grep 8000

# Restart
sudo supervisorctl restart mirrorpupil
```

**Problem**: Database connection failed
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U mirrorpupil -d mirrorpupil -h localhost

# Check .env DATABASE_URL
cat .env | grep DATABASE_URL
```

**Problem**: Telegram not connecting
```bash
# Delete session and reconnect
cd ~/Mirror\ Pupil
rm *.session
sudo supervisorctl restart mirrorpupil

# Check logs for 2FA code
sudo tail -f /var/log/mirrorpupil.out.log
```

### Frontend Issues

**Problem**: Can't reach API
- Check `VITE_API_BASE_URL` in Vercel environment variables
- Verify backend CORS settings
- Check backend logs for requests

**Problem**: Firebase auth not working
- Verify all Firebase env variables are set in Vercel
- Check Firebase Console for user
- Check browser console for errors

### Performance Issues

**Problem**: Slow response
```bash
# Check CPU/Memory
htop

# Check database connections
psql -U mirrorpupil -d mirrorpupil -h localhost
SELECT COUNT(*) FROM pg_stat_activity;

# Restart if needed
sudo supervisorctl restart mirrorpupil
```

---

## 🔒 Security Best Practices

1. **Change default passwords**:
   - PostgreSQL
   - VPS root user
   - Create non-root SSH user

2. **Enable firewall**:
```bash
sudo ufw enable
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
```

3. **Regular updates**:
```bash
sudo apt update && sudo apt upgrade -y
```

4. **Backup regularly**:
```bash
# Add to crontab
crontab -e
# Add: 0 2 * * * pg_dump -U mirrorpupil mirrorpupil > /home/mirrorpupil/backups/backup_$(date +\%Y\%m\%d).sql
```

5. **Monitor logs**:
```bash
sudo tail -f /var/log/mirrorpupil.out.log
```

---

## 📞 Support

If you encounter issues not covered here:
1. Check logs: `sudo tail -f /var/log/mirrorpupil.err.log`
2. Verify all environment variables are set
3. Test database connection
4. Check Telegram session

---

## 🎉 Congratulations!

Your Mirror Pupil trading bot is now deployed and ready to trade! 

**Next Steps**:
1. Add your TradeLocker accounts via GUI
2. Configure risk profiles
3. Subscribe accounts to channels
4. Start with DRY_RUN=true to test
5. Monitor logs and trades
6. Switch to live trading when confident

**Happy Trading! 🚀📈**
