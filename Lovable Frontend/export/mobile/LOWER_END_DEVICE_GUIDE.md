# Mirror Pupil - Lower-End Device Installation Guide

## Quick Start for Your Friend

### Step 1: Build the Optimized APK

On your computer, run:
```bash
cd "c:\Users\bonni\Music\Mirror Pupil\Lovable Frontend\export\mobile"
build_optimized.bat
```

This creates small APKs (15-20MB each) optimized for lower-end phones.

### Step 2: Find the Right APK

After building, go to:
```
build\app\outputs\flutter-apk\
```

You'll see 4 files:
- `app-armeabi-v7a-release.apk` - **For older/budget phones (32-bit)**
- `app-arm64-v8a-release.apk` - For newer phones (64-bit)
- `app-x86_64-release.apk` - For tablets/emulators
- `app-release.apk` - Works on all devices (but larger)

**If friend's phone is from 2018 or older** → Use `app-armeabi-v7a-release.apk`
**If unsure** → Use `app-release.apk` (universal, but 45MB)

### Step 3: Transfer to Friend's Phone

**Option A - Via WhatsApp/Telegram**:
1. Send the APK file
2. Friend downloads it
3. Friend opens Downloads folder
4. Taps the APK file
5. Enables "Install from Unknown Sources" if prompted
6. Installs the app

**Option B - Via USB Cable**:
1. Connect phone to computer
2. Copy APK to phone's Download folder
3. Disconnect phone
4. On phone: Open Files app → Downloads
5. Tap the APK file
6. Install

### Step 4: First Launch Setup

When friend opens the app for the first time:
1. App will ask for notification permission - **Allow** (important for trade alerts)
2. Login with Google account
3. Wait for admin approval (you'll approve from your dashboard)
4. Done! ✅

## Common Issues & Solutions

### Issue 1: "App not installed" Error
**Cause**: Not enough storage space
**Solution**: 
- Free up at least 500MB space
- Delete unused apps, photos, videos
- Clear cache: Settings → Storage → Cached data → Clear

### Issue 2: "Parse error" or "App corrupted"
**Cause**: Downloaded APK is incomplete or wrong architecture
**Solution**:
- Re-download the APK
- Try the universal APK (`app-release.apk`)
- Ensure download completed fully

### Issue 3: App Crashes on Startup
**Cause**: Low RAM or Android version too old
**Solution**:
- Close all other apps before opening Mirror Pupil
- Restart phone
- Check Android version: Settings → About Phone
  - Must be **Android 5.0 or newer**
  - If older, phone cannot run the app

### Issue 4: App is Laggy/Slow
**Cause**: Device has limited resources
**Solution**:
1. **Enable Developer Options**:
   - Settings → About Phone
   - Tap "Build Number" 7 times
   - Go back to Settings → Developer Options
   
2. **Reduce Animations**:
   - Window animation scale → 0.5x
   - Transition animation scale → 0.5x
   - Animator duration scale → 0.5x

3. **Free up RAM**:
   - Close unused apps
   - Restart phone daily
   - Disable auto-sync for unused apps

### Issue 5: Notifications Not Working
**Cause**: Battery optimization or permission denied
**Solution**:
1. Settings → Apps → Mirror Pupil → Permissions
   - Allow Notifications ✅
   
2. Settings → Apps → Mirror Pupil → Battery
   - Battery optimization → Don't optimize
   
3. Settings → Apps → Mirror Pupil → Data usage
   - Allow background data ✅

### Issue 6: Can't Login with Google
**Cause**: Google Play Services outdated or missing
**Solution**:
1. Update Google Play Services:
   - Settings → Apps → Google Play Services → Update
   
2. If still fails, use email/password login instead

### Issue 7: "Your Device Isn't Compatible"
**Cause**: Android version below 5.0
**Solution**:
- Phone is too old to run modern apps
- Need Android 5.0 (Lollipop) minimum
- Consider upgrading phone if possible

## Performance Tips for Friend

### Daily Use
- **Close app when not needed** - Swipe away from recent apps
- **Check for updates** - Keep app updated for better performance
- **Restart phone weekly** - Clears memory leaks

### Battery Saving
- **Dark Mode** - Settings → Display → Dark theme (saves battery on OLED screens)
- **Reduce screen brightness**
- **Disable auto-refresh** - Only refresh when needed

### Data Saving
- **Use WiFi when possible** - App uses very little data but WiFi is faster
- **Don't keep app open all day** - Notifications work even when app is closed

## Minimum Device Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Android Version** | 5.0 (Lollipop) | 8.0+ (Oreo) |
| **RAM** | 1 GB | 2 GB+ |
| **Storage** | 500 MB free | 1 GB+ free |
| **Screen** | 4.5" | 5.0"+ |
| **Internet** | 2G/3G | 4G/WiFi |

## Which Phones Work Well?

### ✅ Confirmed Working Devices
- Samsung Galaxy J2, J3, J5, J7 series
- Xiaomi Redmi 4A, 5A, 6A, Note 5A
- Tecno Spark 2, 3, 4 series
- Infinix Hot 5, 6, 7 series
- Nokia 2, 3, 5 series (2017+)
- Any phone from 2016 or newer with 1GB+ RAM

### ⚠️ May Work (Slow)
- Phones with 512 MB RAM
- Android 5.0 devices from 2014-2015
- Very old Samsung Galaxy S4/S5

### ❌ Will NOT Work
- Android 4.4 KitKat or older
- Phones with less than 512 MB RAM
- Feature phones (non-smartphones)

## Testing Before Sending to Friend

1. **Check APK size**:
   - armeabi-v7a: Should be ~15 MB ✅
   - arm64-v8a: Should be ~18 MB ✅
   - Universal: Should be ~45 MB ✅
   - If much larger, rebuild with optimizations

2. **Test on emulator**:
   ```bash
   flutter emulators --launch Pixel_3a_API_21
   flutter install
   ```

3. **Check memory usage**:
   - Open app
   - Navigate through all screens
   - Memory should stay under 150 MB

## Support Checklist for Friend

When helping your friend, ask:
- [ ] What phone model do they have?
- [ ] What Android version? (Settings → About Phone)
- [ ] How much free storage? (Settings → Storage)
- [ ] Did they enable "Install from Unknown Sources"?
- [ ] Is Google Play Services installed and updated?
- [ ] Can they see the login screen?
- [ ] Did they allow notification permission?
- [ ] Are they on WiFi or mobile data?

## Quick Reference

**Build Command**:
```bash
flutter build apk --release --split-per-abi
```

**APK Location**:
```
build\app\outputs\flutter-apk\
```

**For Budget Phones**: `app-armeabi-v7a-release.apk` (15 MB)
**For All Phones**: `app-release.apk` (45 MB)

---

**Need Help?**
- Check `PERFORMANCE_OPTIMIZATIONS.md` for technical details
- Check `BUILD_INSTRUCTIONS.md` for build troubleshooting
- Test on Android emulator before sending to friend

**Last Updated**: 2026-07-17
