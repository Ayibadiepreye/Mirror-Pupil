# 🚀 Quick Start Guide

Get Mirror Pupil's Telegram client running in 5 minutes.

---

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed pytdbot-0.8.5 tradelocker-1.0.0 asyncpg-0.29.0 ...
```

---

## Step 2: Run Setup

```bash
python setup.py
```

This will:
- Create necessary directories
- Generate `.env` file with random encryption keys
- Check dependencies

**Expected output:**
```
✓ Created 9 directories
✓ Created .env file with auto-generated encryption keys
✓ All required packages installed
```

---

## Step 3: Get Telegram Credentials

### 3.1 Get API ID and Hash

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Click "API development tools"
4. Fill in the form (app name can be anything)
5. Copy your `api_id` and `api_hash`

### 3.2 Edit .env File

Open `.env` and fill in:

```bash
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+1234567890
```

**Important:**
- `TELEGRAM_PHONE` must include country code (e.g., `+1` for USA)
- Don't add quotes around values

---

## Step 4: Test Configuration

```bash
python test_setup.py
```

**Expected output:**
```
✓ PASS    Environment File
✓ PASS    Dependencies
✓ PASS    Directories
✓ PASS    Telegram Config
⚠️  FAIL   Database Config  (OK for now - we'll set this up later)

🎉 All tests passed!
```

---

## Step 5: Run Telegram Client

```bash
python telegram_client.py
```

### First Run (Authorization)

You'll see:
```
Starting Telegram client...
Please enter the code you received: _
```

**What to do:**
1. Check your Telegram app
2. You'll receive a login code (e.g., `12345`)
3. Enter the code
4. Press Enter

### Successful Connection

You'll see:
```
✓ Applied Pytdbot monkey patches successfully
Starting Telegram client...
✓ Connected as: Your Name (@username)
  Phone: +1234567890
  User ID: 123456789
Registered handler for channel -1001859598768
Registered handler for channel -1001182913499
👂 Listening to 2 channel(s)...
```

### When Messages Arrive

```
📨 New message in channel -1001859598768: ID=12345
[NEW] Message ID: 12345
[NEW] Chat ID: -1001859598768
[NEW] Date: 2025-01-15 14:30:00
[NEW] Text: GOLD BUY @ 2650 SL 2640 TP 2680...
--------------------------------------------------------------------------------
```

---

## Step 6: Stop the Client

Press `Ctrl+C` to stop:

```
^C
Received interrupt signal
Stopping Telegram client...
✓ Client stopped
```

---

## ✅ Success!

You now have:
- ✅ Telegram client connected
- ✅ Listening to BillirichyFX and Firepips
- ✅ Human-like behavior active (delays, mark as read, typing)
- ✅ Auto-reconnect enabled
- ✅ Session saved (no need to re-authorize next time)

---

## 🔧 Troubleshooting

### "Missing required environment variables"

**Problem:** `.env` file not configured

**Fix:**
```bash
python setup.py
# Then edit .env with your credentials
```

---

### "Failed to start Telegram client"

**Problem:** Invalid API credentials

**Fix:**
1. Double-check your API_ID and API_HASH from https://my.telegram.org/apps
2. Make sure there are no quotes or spaces
3. Verify phone number includes country code

---

### "Please enter the code you received" (but no code arrives)

**Problem:** Phone number format incorrect

**Fix:**
- Must start with `+`
- Must include country code
- Example: `+1234567890` (not `1234567890`)

---

### "Connection state: connectionStateFailed"

**Problem:** Network/firewall issue

**Fix:**
1. Check internet connection
2. Try disabling VPN/proxy temporarily
3. Check firewall settings

---

### Messages not appearing

**Problem:** Not a member of the channels

**Fix:**
1. Join BillirichyFX: https://t.me/+[invite_link]
2. Join Firepips: https://t.me/+[invite_link]
3. Restart the client

---

## 📚 Next Steps

Now that your Telegram client is working:

1. **Let it run** - Watch messages for a few hours to verify stability
2. **Check logs** - Look in `tdlib_data/tdlib.log` for TDLib logs
3. **Build database** - Next phase is the database layer
4. **Read the spec** - See `mirror_pupil_spec_v5.md` for full details

---

## 🎯 What's Working

| Feature | Status |
|---|---|
| Connect to Telegram | ✅ |
| Listen to channels | ✅ |
| Receive messages | ✅ |
| Human-like delays | ✅ |
| Mark as read | ✅ |
| Typing indicators | ✅ |
| Health checks | ✅ |
| Auto-reconnect | ✅ |
| Session persistence | ✅ |

---

## 🚧 What's Next

| Feature | Status |
|---|---|
| Parse signals | 🚧 Coming |
| Store in database | 🚧 Coming |
| Execute trades | 🚧 Coming |
| Risk management | 🚧 Coming |
| Web GUI | 🚧 Coming |

---

## 💡 Tips

1. **Keep it running** - The client will auto-reconnect if connection drops
2. **Check health** - Look for "Health check OK" messages every 30s
3. **Session saved** - After first authorization, you won't need to enter code again
4. **Multiple accounts** - To use a different Telegram account, delete `tdlib_data/` folder

---

## 📞 Need Help?

1. Check `README.md` for detailed documentation
2. Check `PROGRESS.md` for build status
3. Check logs in `tdlib_data/tdlib.log`
4. Review the full spec in `mirror_pupil_spec_v5.md`

---

**Version**: 5.1  
**Phase**: 1 of 8 (Telegram Client) ✅ Complete  
**Next**: Database Layer
