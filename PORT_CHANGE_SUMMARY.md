# Backend Port Change Summary
**Date**: 2026-07-30  
**Change**: API port changed from 8000 to 8675

---

## ✅ Changes Complete

Backend API port changed from **8000** to **8675** to avoid conflicts on your server.

---

## 📝 Files Modified:

1. **`.env`** - Changed `API_PORT=8000` → `API_PORT=8675`
2. **`.env.example`** - Changed `API_PORT=8000` → `API_PORT=8675`
3. **`backend/api/main.py`** - Updated default port from 8000 to 8675
4. **`run_backend.py`** - Updated port from 8000 to 8675
5. **`add_account_via_api.py`** - Updated help text from 8000 to 8675

---

## 🚀 How to Use:

### Starting the Backend:

```bash
# Option 1: Using run_backend.py (recommended)
py run_backend.py
# Now runs on http://0.0.0.0:8675

# Option 2: Direct uvicorn
py -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8675
```

### Accessing the API:

- **Local**: http://localhost:8675
- **Network**: http://0.0.0.0:8675
- **Health Check**: http://localhost:8675/health

### API Documentation:

- **Swagger UI**: http://localhost:8675/docs
- **ReDoc**: http://localhost:8675/redoc

---

## ✅ No Frontend Changes Needed

The frontend connects via reverse proxy path `/mirrorpupil`, not directly to the port, so:
- ✅ Web frontend: No changes needed
- ✅ Mobile app: No changes needed
- ✅ All API calls: Work as before

---

## 🔍 Verification:

After starting the backend, check:

```bash
# 1. Check if port 8675 is listening
netstat -an | findstr "8675"

# 2. Test health endpoint
curl http://localhost:8675/health

# Expected response:
# {"status":"healthy","timestamp":"2026-07-30T..."}
```

---

## 📊 Port 8675 Benefits:

- ✅ **Uncommon port** - Less likely to be used by other services
- ✅ **Above 1024** - No root/admin required
- ✅ **Easy to remember** - 867-5309 (Jenny's number reference)
- ✅ **Avoids conflicts** - Port 8000 often used by development servers

---

## ⚠️ Firewall/Security:

If you need external access, open port 8675:

```bash
# Windows Firewall
netsh advfirewall firewall add rule name="Mirror Pupil API" dir=in action=allow protocol=TCP localport=8675

# Linux (if deploying to VPS)
sudo ufw allow 8675/tcp
```

---

## 🎉 Ready!

Backend will now run on port **8675** instead of 8000.

Just restart the bot and everything will work on the new port!
