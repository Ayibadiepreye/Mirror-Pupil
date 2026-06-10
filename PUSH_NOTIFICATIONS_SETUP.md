# Mirror Pupil v5.1 - Push Notifications Setup Guide

## ✅ What's Already Done

### Backend (Complete)
- ✅ Database migration added `fcm_token` column to users table
- ✅ 3 new database methods added to `DatabaseManager`:
  - `update_user_fcm_token()` - Register/update FCM tokens
  - `get_users_by_account()` - Get users who own specific accounts
  - `get_all_users_with_fcm()` - Get all users with registered tokens
- ✅ Push notification service (`backend/services/push_notifications.py`)
- ✅ FCM token registration endpoint (`/api/users/register-fcm-token`)
- ✅ Notifications API automatically sends push notifications to mobile devices
- ✅ Firebase Admin SDK initialized in backend

### Flutter Mobile App (Complete)
- ✅ FCM service (`lib/services/fcm_service.dart`) with:
  - Token registration & auto-refresh
  - Foreground/background/terminated message handling
  - Local notifications for foreground messages
  - Notification tap handling
  - Permission requests (iOS/Android)
- ✅ API client updated with `registerFcmToken()` method
- ✅ Dependencies added to `pubspec.yaml`:
  - `firebase_messaging: ^14.7.10`
  - `flutter_local_notifications: ^16.3.2`
- ✅ Firebase Authentication fully integrated
- ✅ Logo updated across the app
- ✅ All web platform features ported to mobile (UI models, screens, etc.)

---

## 🔧 What You Need To Do

### Step 1: Firebase Console Setup

1. **Go to Firebase Console**: https://console.firebase.google.com/project/mirror-pupil

2. **Add Android App** (if not already added):
   - Click "Add app" → Android icon
   - Package name: `com.example.mirrorpupil` (or your custom package)
   - App nickname: "Mirror Pupil Android"
   - Click "Register app"
   - **Download `google-services.json`** (you'll need this)
   - Click "Next" → "Next" → "Continue to console"

3. **Add iOS App** (if not already added):
   - Click "Add app" → iOS icon
   - Bundle ID: `com.example.mirrorpupil` (or your custom bundle)
   - App nickname: "Mirror Pupil iOS"
   - Click "Register app"
   - **Download `GoogleService-Info.plist`** (you'll need this)
   - Click "Next" → "Next" → "Continue to console"

4. **Get App IDs**:
   - Go to Project Settings → General
   - Under "Your apps":
     - **Android App ID**: Copy the value (looks like `1:2009963821:android:abc123...`)
     - **iOS App ID**: Copy the value (looks like `1:2009963821:ios:xyz789...`)
     - **iOS Client ID**: Under iOS app → "GoogleService-Info.plist" → find `CLIENT_ID`

5. **Enable Cloud Messaging**:
   - Go to Project Settings → Cloud Messaging
   - Verify Cloud Messaging API is enabled
   - For iOS: Upload your APNs authentication key (if not done)

---

### Step 2: Update Flutter Configuration Files

#### 2.1 Update `firebase_options.dart`

Open: `Lovable Frontend/export/mobile/lib/firebase_options.dart`

Replace the placeholder values:

```dart
static const FirebaseOptions android = FirebaseOptions(
  apiKey: 'AIzaSyAjxKQJFeRdFwHMYybKcNer5QQHp2nVUz8',
  appId: '1:2009963821:android:YOUR_ANDROID_APP_ID',  // ← Paste your Android App ID
  messagingSenderId: '2009963821',
  projectId: 'mirror-pupil',
  storageBucket: 'mirror-pupil.firebasestorage.app',
);

static const FirebaseOptions ios = FirebaseOptions(
  apiKey: 'AIzaSyAjxKQJFeRdFwHMYybKcNer5QQHp2nVUz8',
  appId: '1:2009963821:ios:YOUR_IOS_APP_ID',  // ← Paste your iOS App ID
  messagingSenderId: '2009963821',
  projectId: 'mirror-pupil',
  storageBucket: 'mirror-pupil.firebasestorage.app',
  iosClientId: 'YOUR_IOS_CLIENT_ID.apps.googleusercontent.com',  // ← Paste iOS client ID
  iosBundleId: 'com.example.mirrorpupil',  // ← Your bundle ID
);
```

#### 2.2 Add `google-services.json` (Android)

1. Copy the downloaded `google-services.json` file
2. Paste it to: `Lovable Frontend/export/mobile/android/app/google-services.json`

#### 2.3 Update `android/build.gradle`

Open: `Lovable Frontend/export/mobile/android/build.gradle`

Add Google services plugin:

```gradle
buildscript {
    dependencies {
        // Add this line
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

#### 2.4 Update `android/app/build.gradle`

Open: `Lovable Frontend/export/mobile/android/app/build.gradle`

Add at the BOTTOM of the file:

```gradle
apply plugin: 'com.google.android.gms.google-services'
```

#### 2.5 Add `GoogleService-Info.plist` (iOS)

1. Copy the downloaded `GoogleService-Info.plist` file
2. Open Xcode: `Lovable Frontend/export/mobile/ios/Runner.xcworkspace`
3. Right-click "Runner" folder → "Add Files to Runner"
4. Select `GoogleService-Info.plist`
5. **Check "Copy items if needed"**
6. Click "Add"

#### 2.6 Update `ios/Runner/Info.plist` (iOS)

Add Firebase URL schemes (for Firebase Auth):

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>YOUR_IOS_CLIENT_ID</string>
    </array>
  </dict>
</array>
```

---

### Step 3: Backend Firebase Service Account

The backend already has Firebase Admin SDK initialized. Verify your service account:

1. **Go to Firebase Console** → Project Settings → Service Accounts
2. Click "Generate new private key"
3. Download the JSON file
4. Save it as: `firebase-service-account.json` in your project root
5. Verify `.env` has:
   ```
   FIREBASE_SERVICE_ACCOUNT_KEY=./firebase-service-account.json
   ```

---

### Step 4: Flutter Dependencies & Build

Run these commands:

```bash
cd "Lovable Frontend/export/mobile"

# Install dependencies
flutter pub get

# Clean build (recommended)
flutter clean
flutter pub get

# Test on Android
flutter run -d android

# Test on iOS (macOS only)
flutter run -d ios
```

---

## 🧪 Testing Push Notifications

### Test 1: Register FCM Token
1. Build and run the Flutter app
2. Sign in with your Firebase account
3. Check backend logs - should see: `✓ Registered FCM token for user <user_id>`

### Test 2: Manual Push via API

Use Postman or curl:

```bash
curl -X POST http://localhost:8000/api/notifications/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "category": "SYSTEM",
    "severity": "INFO",
    "title": "Test Notification",
    "message": "Testing push notifications!"
  }'
```

You should receive a push notification on your phone.

### Test 3: Signal Notification

1. Add a trading account in the app
2. Trigger a signal from Telegram (or manually via backend)
3. You should receive a push notification with signal details

---

## 🎯 How Push Notifications Work

### Flow:
1. **User signs in** → Flutter FCM service gets token → Registers with backend
2. **Backend receives notification event** (signal, breach, etc.)
3. **Backend calls** `create_notification()` API
4. **API stores notification in DB** → Queries users who should receive it
5. **Push service sends FCM messages** to all registered tokens
6. **Mobile devices receive** → Show notification → User taps → Navigate to details

### Notification Categories:
- **SIGNAL**: New trade signals from channels
- **EXECUTION**: Trade executed, modified, closed
- **MANAGEMENT**: Autonomous management actions
- **BREACH**: Risk profile violations
- **SYSTEM**: Bot status, account issues

---

## 🐛 Troubleshooting

### "FCM token not registered"
- Check Firebase Console → Cloud Messaging is enabled
- Verify `google-services.json` / `GoogleService-Info.plist` are in correct locations
- Run `flutter clean && flutter pub get`

### "Failed to register FCM token with backend"
- Check backend is running: `http://localhost:8000/health`
- Verify JWT token is valid (not expired)
- Check backend logs for errors

### "Push notifications not received"
- Verify token was registered: Check backend logs or database `users.fcm_token`
- Test with manual API call (see Test 2 above)
- Check Firebase Console → Cloud Messaging → Usage for delivery status

### iOS not receiving notifications
- Verify APNs authentication key is uploaded in Firebase Console
- Check `Info.plist` has correct URL schemes
- Ensure notification permissions were granted

### Android not receiving notifications
- Verify `google-services.json` is in `android/app/`
- Check `android/app/build.gradle` has `apply plugin: 'com.google.android.gms.google-services'`
- Ensure battery optimization is disabled for the app

---

## ✅ Verification Checklist

- [ ] Firebase Console: Android app added with `google-services.json` downloaded
- [ ] Firebase Console: iOS app added with `GoogleService-Info.plist` downloaded
- [ ] `firebase_options.dart` updated with real Android/iOS App IDs
- [ ] `google-services.json` placed in `android/app/`
- [ ] `GoogleService-Info.plist` added to Xcode project
- [ ] `android/build.gradle` has Google services plugin
- [ ] `android/app/build.gradle` applies Google services plugin
- [ ] Backend `firebase-service-account.json` exists and `.env` points to it
- [ ] `flutter pub get` ran successfully
- [ ] App builds and runs without errors
- [ ] Sign in shows "✓ Registered FCM token" in backend logs
- [ ] Manual push test via API received on phone
- [ ] Signal notification received when trade signal triggered

---

## 📝 Summary

**Backend**: Fully configured and ready. Just ensure `firebase-service-account.json` is in place.

**Mobile**: Needs Firebase Console setup + config files placement + dependencies install.

**Testing**: Use manual API calls first, then test with real trading signals.

Once you complete the Firebase Console steps and add the config files, push notifications will work automatically across the entire app!
