# FCM Push Notifications Setup Guide

This guide explains how push notifications work in Mirror Pupil and how to verify the setup.

## 🎯 Overview

Mirror Pupil uses **Firebase Cloud Messaging (FCM)** to send push notifications from the backend to the Flutter mobile app. When important events occur (signal detection, trade execution, management actions, etc.), the backend creates a notification in the database AND sends a push message to all registered mobile devices.

---

## 📋 Architecture

```
┌─────────────────────┐
│  Backend Event      │ (Trade executed, signal detected, etc.)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ notification_service│ Creates notification in database
│ .create_notification│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ POST /api/          │ Notification creation endpoint
│ notifications/      │
└──────────┬──────────┘
           │
           ├───► Database: INSERT INTO notifications
           │
           ▼
┌─────────────────────┐
│ PushNotification    │ Gets FCM tokens for relevant users
│ Service             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Firebase Cloud      │ Sends push to mobile devices
│ Messaging (FCM)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Flutter App         │ Receives push, displays notification
│ (Mobile Device)     │ Updates unread badge count
└─────────────────────┘
```

---

## ✅ Current Implementation Status

### ✅ Backend (Complete)

- **Database Schema**:
  - `users.fcm_token` column stores FCM tokens
  - `notifications` table stores all notifications
  - Migration file: `backend/database/migrations/add_fcm_support.sql`

- **API Endpoints**:
  - `POST /api/users/register-fcm-token` - Register FCM token
  - `POST /api/notifications/` - Create notification (automatically sends push)
  - `GET /api/notifications/unread-count` - Get unread count

- **Push Notification Service**:
  - `backend/services/push_notifications.py` - Sends FCM messages
  - `get_push_notification_service()` - Singleton instance
  - Automatically sends push when notification is created

- **Notification Points** (22 total):
  - Signal rejections (EOD, weekend, risk, etc.)
  - Signal detection
  - Trade execution (entry, exit)
  - Management detection and execution
  - Autonomous actions (BE, partials, close)
  - Trade closures (TP, SL, manual)

### ✅ Flutter App (Complete)

- **Firebase Configuration**:
  - `lib/firebase_options.dart` - Firebase config for Android/iOS
  - `android/app/google-services.json` - Android FCM config

- **FCM Service**:
  - `lib/services/fcm_service.dart` - Handles FCM tokens and messages
  - `fcmService.initialize()` - Called in `main.dart` after login
  - Registers token with backend automatically

- **UI**:
  - Red notification badge on bell icon
  - Shows unread count (1-99, "99+" for 100+)
  - Polls every 30 seconds + updates via WebSocket
  - Located in `lib/main.dart` (AppBar)

---

## 🔧 Setup Instructions

### 1. Run Database Migration

Add the `fcm_token` column to the `users` table:

```bash
psql -U your_user -d mirror_pupil -f backend/database/migrations/add_fcm_support.sql
```

Or manually:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS fcm_token TEXT;
CREATE INDEX IF NOT EXISTS idx_users_fcm_token ON users(fcm_token) WHERE fcm_token IS NOT NULL;
```

### 2. Configure Firebase Service Account Key

Add your Firebase service account key to the backend `.env` file:

```env
FIREBASE_SERVICE_ACCOUNT_KEY=/path/to/firebase-service-account-key.json
```

To get the service account key:
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (mirror-pupil)
3. Go to **Project Settings** > **Service Accounts**
4. Click **Generate New Private Key**
5. Save the JSON file and update `.env`

### 3. Verify Flutter Firebase Configuration

Ensure these files exist:

- `Lovable Frontend/export/mobile/lib/firebase_options.dart`
- `Lovable Frontend/export/mobile/android/app/google-services.json`

If missing, run:

```bash
cd "Lovable Frontend/export/mobile"
flutterfire configure
```

### 4. Test the Setup

Run the test script to verify everything is configured:

```bash
python test_fcm_setup.py
```

This will check:
- ✅ Database schema (fcm_token column)
- ✅ Backend push service configuration
- ✅ Flutter Firebase configuration
- ✅ User FCM token registration

---

## 🔄 How It Works (User Flow)

### First Time Setup

1. **User opens Flutter app**
2. **User logs in** with Firebase Auth
3. **App initializes FCM** (`fcmService.initialize()`)
4. **App requests notification permissions** (iOS shows prompt)
5. **App gets FCM token** from Firebase
6. **App sends token to backend** (`POST /api/users/register-fcm-token`)
7. **Backend stores token** in `users.fcm_token` column

### Notification Flow

1. **Backend event occurs** (e.g., trade executed)
2. **Backend creates notification** via `notification_service.create_notification()`
3. **API endpoint** (`POST /api/notifications/`) is called
4. **Notification saved to database**
5. **Backend looks up FCM tokens**:
   - If account-specific: gets users who own that account
   - If system-wide: gets all users with FCM tokens
6. **Push service sends FCM message** to all tokens
7. **Flutter app receives push**:
   - **App in foreground**: Shows in-app notification
   - **App in background**: Shows system notification
8. **User taps notification**: App opens notifications screen
9. **Badge updates**: Unread count shown on bell icon

---

## 🧪 Testing Push Notifications

### Option 1: Via Backend Script

Create a test notification:

```python
import asyncio
from backend.database.manager import DatabaseManager
from backend.core.notification_service import get_notification_service

async def test():
    db = DatabaseManager()
    await db.initialize()
    
    service = get_notification_service(db)
    await service.create_notification(
        account_key=None,  # System-wide
        category='SYSTEM',
        severity='INFO',
        title='Test Notification',
        message='Push notification test from backend',
        metadata={'test': True}
    )

asyncio.run(test())
```

### Option 2: Via API

```bash
curl -X POST https://your-api.com/api/notifications/ \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "SYSTEM",
    "severity": "INFO",
    "title": "Test Push",
    "message": "Testing push notifications"
  }'
```

### Option 3: Trigger Real Event

- Open a trade in the system
- System will automatically send notifications for:
  - Signal detection
  - Trade execution
  - Trade closure

---

## 📱 Flutter App Behavior

### Notification Permissions

- **Android**: Automatically granted (API level < 33)
- **iOS**: User must grant permission (prompt shown on first launch)

### Notification Display

- **Foreground**: Firebase automatically displays notification banner
- **Background**: System notification appears in tray
- **Terminated**: Notification wakes app, stored for later

### Badge Update

- **Timer**: Polls `/api/notifications/unread-count` every 30 seconds
- **WebSocket**: Updates immediately when notification is created
- **Display**: Shows "1-99" or "99+" for 100+

---

## 🐛 Troubleshooting

### Push Notifications Not Sending

1. **Check backend .env**:
   - Ensure `FIREBASE_SERVICE_ACCOUNT_KEY` is set
   - Verify file path is correct

2. **Check database**:
   ```sql
   SELECT user_id, email, fcm_token FROM users;
   ```
   - Ensure users have `fcm_token` values

3. **Check backend logs**:
   ```
   ✓ Registered FCM token for user <user_id>
   ✓ Push notification sent: <message_id>
   ```

### Flutter App Not Receiving

1. **Check Firebase configuration**:
   - Ensure `firebase_options.dart` exists
   - Ensure `google-services.json` is in `android/app/`

2. **Check permissions**:
   - iOS: User must grant notification permission
   - Android: Should be automatic

3. **Check FCM token registration**:
   - Look for: `FCM token registered with backend` in Flutter logs
   - If not present, check network connectivity

### Badge Not Updating

1. **Check API endpoint**:
   ```bash
   curl https://your-api.com/api/notifications/unread-count \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. **Check WebSocket connection**:
   - Ensure `mpWs.connect()` is called in `main.dart`
   - Check for WebSocket connection errors

---

## 📚 Code Reference

### Backend Files

- `backend/services/push_notifications.py` - Push service
- `backend/api/routes/notifications.py` - Notification API
- `backend/core/notification_service.py` - Notification helper
- `backend/database/manager.py` - Database methods
- `backend/database/migrations/add_fcm_support.sql` - Migration

### Flutter Files

- `lib/services/fcm_service.dart` - FCM service
- `lib/api/api_client.dart` - API client (registerFcmToken)
- `lib/main.dart` - Badge UI and initialization
- `lib/firebase_options.dart` - Firebase config
- `android/app/google-services.json` - Android FCM config

---

## ✨ Features Implemented

✅ **22 notification points** covering all important events  
✅ **Push notifications** sent automatically when notifications are created  
✅ **Red badge** on bell icon showing unread count  
✅ **Real-time updates** via WebSocket + polling  
✅ **Lazy imports** to avoid circular dependencies  
✅ **Non-blocking** notification sending  
✅ **FCM token management** (register, cleanup invalid tokens)  
✅ **Multi-user support** (push to multiple devices)  
✅ **Account-specific notifications** (only relevant users)  
✅ **System-wide notifications** (all users with tokens)  

---

## 🚀 Next Steps

1. **Run migration** to add `fcm_token` column
2. **Add Firebase service account key** to backend `.env`
3. **Build Flutter app** and install on device
4. **Log in** to register FCM token
5. **Test** by triggering a notification event

Your push notifications should now be fully functional! 🎉
