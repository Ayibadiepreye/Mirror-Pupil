# Mirror Pupil - Complete Flutter Mobile App Specification

## Project Overview
Rebuild the **Mirror Pupil** Flutter mobile app from scratch with production-quality architecture, responsive design, proper error handling, and seamless backend integration.

**App Name**: Mirror Pupil  
**Package Name**: `com.kirito.mirrorpupil`  
**Tagline**: Knights of the Blood Oath  
**Purpose**: Professional trading bot management and monitoring for prop firm accounts

---

## 🎨 Design System - Knights of the Blood Oath Theme

### Color Palette (Exact Values - Must Match 1:1)
```dart
class MpColors {
  static const base = Color(0xFF16161A);        // Base Layer (cards/navigation)
  static const app = Color(0xFF1E1E24);          // App Layer (background)
  static const crimson = Color(0xFFB22222);      // Accent (headers/badges)
  static const red = Color(0xFFE74C3C);          // Interactive (buttons/focus)
  static const text = Color(0xFFE0E0E0);         // Primary text
  static const textDim = Color(0xFFA0A0A0);      // Secondary text
  static const border = Color(0xFF2A2A30);       // Borders/dividers
  static const success = Color(0xFF10B981);      // Green (profit/active)
  static const danger = Color(0xFFEF4444);       // Red (loss/breach)
  static const warning = Color(0xFFF59E0B);      // Orange (warnings)
  static const info = Color(0xFF3B82F6);         // Blue (info)
}
```

### Gradient Usage
**All cards, tiles, and containers MUST use this gradient:**
```dart
decoration: BoxDecoration(
  gradient: LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [MpColors.base, MpColors.app],  // #16161A → #1E1E24
  ),
  borderRadius: BorderRadius.circular(12),
  border: Border.all(color: MpColors.border),
),
```

### Typography
- **Primary Font**: Inter (sans-serif, weights: 400, 500, 600, 700)
- **Monospace Font**: JetBrains Mono (for numbers, prices, timestamps)

### Spacing & Sizing
- **Border Radius**: 8-12px for cards, 8px for buttons
- **Padding**: 12-16px standard, 8px compact
- **Touch Targets**: Minimum 48x48 logical pixels
- **Card Elevation**: 0 (use borders + gradients instead)

---

## 🏗️ Architecture & Structure

### Project Structure
```
lib/
├── main.dart                 # App entry point, routing, navigation shell
├── theme.dart                # Theme definition with MpColors
├── firebase_options.dart     # Firebase configuration (provided)
│
├── auth/
│   └── auth_service.dart     # Firebase Authentication service
│
├── api/
│   ├── api_client.dart       # REST API client
│   ├── ws_service.dart       # WebSocket service
│   └── mock_data.dart        # Mock data for development/testing
│
├── services/
│   └── fcm_service.dart      # Firebase Cloud Messaging service
│
├── models/
│   └── models.dart           # All data models (Account, Trade, etc.)
│
├── screens/
│   ├── login_screen.dart     # Authentication screen
│   ├── dashboard_screen.dart # Main overview
│   ├── accounts_screen.dart  # Account management
│   ├── trades_screen.dart    # Active trades
│   ├── history_screen.dart   # Trade history
│   ├── notifications_screen.dart
│   ├── settings_screen.dart
│   └── bot_control_screen.dart
│
└── widgets/
    └── common/               # Reusable widgets (optional)
```

### Key Packages (pubspec.yaml)
```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # Firebase
  firebase_core: ^3.8.1
  firebase_auth: ^5.3.3
  firebase_messaging: ^15.1.5
  google_sign_in: ^6.2.2
  
  # Networking
  http: ^1.2.0
  web_socket_channel: ^3.0.0
  
  # State & Navigation
  go_router: ^14.6.2
  
  # UI
  flutter_svg: ^2.0.10
  
  # Platform
  device_info_plus: ^10.1.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^5.0.0
```

---

## 🔐 Firebase Configuration

### Android Configuration
**File**: `android/app/google-services.json`
```json
{
  "project_info": {
    "project_number": "2009963821",
    "project_id": "mirror-pupil",
    "storage_bucket": "mirror-pupil.firebasestorage.app"
  },
  "client": [
    {
      "client_info": {
        "mobilesdk_app_id": "1:2009963821:android:fd5b9bd344ecf9448747a4",
        "android_client_info": {
          "package_name": "com.kirito.mirrorpupil"
        }
      },
      "oauth_client": [
        {
          "client_id": "2009963821-54ud1a5dc0l0a9fpugksecqqias9tgsc.apps.googleusercontent.com",
          "client_type": 3
        }
      ],
      "api_key": [
        {
          "current_key": "AIzaSyBl0qkRtlFLLKugwu6qTWXRF5suZj0cRos"
        }
      ],
      "services": {
        "appinvite_service": {
          "other_platform_oauth_client": [
            {
              "client_id": "2009963821-54ud1a5dc0l0a9fpugksecqqias9tgsc.apps.googleusercontent.com",
              "client_type": 3
            }
          ]
        }
      }
    }
  ],
  "configuration_version": "1"
}
```

**File**: `android/app/build.gradle.kts`
```kotlin
android {
    namespace = "com.kirito.mirrorpupil"
    compileSdk = 34
    
    defaultConfig {
        applicationId = "com.kirito.mirrorpupil"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }
    
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
        isCoreLibraryDesugaringEnabled = true
    }
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4")
}
```

**File**: `android/build.gradle.kts`
```kotlin
plugins {
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.1.0" apply false
    id("com.google.gms.google-services") version "4.4.2" apply false
}
```

**File**: `android/app/src/main/AndroidManifest.xml`
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.kirito.mirrorpupil">
    
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    
    <application
        android:label="Mirror Pupil"
        android:icon="@mipmap/ic_launcher"
        android:enableOnBackInvokedCallback="true">
        
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            
            <meta-data
              android:name="io.flutter.embedding.android.NormalTheme"
              android:resource="@style/NormalTheme" />
            
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
        
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="high_importance_channel" />
    </application>
</manifest>
```

**File**: `android/app/src/main/kotlin/com/kirito/mirrorpupil/MainActivity.kt`
```kotlin
package com.kirito.mirrorpupil

import io.flutter.embedding.android.FlutterActivity

class MainActivity: FlutterActivity()
```

---

## 📱 Screen Specifications

### 1. Login Screen (`login_screen.dart`)

**Layout**:
- Radial gradient background (crimson fade)
- Centered card with shadow
- Logo with gradient (shield icon)
- Title: "Mirror Pupil"
- Subtitle: "KNIGHTS OF THE BLOOD OATH"
- Segmented control: Sign In / Sign Up (with gradient on selected)
- Google Sign-In button with official 4-color logo
- Email/Password fields
- Gradient submit button (crimson → red)
- Disclaimer text

**Functionality**:
- Firebase Authentication (Email/Password + Google Sign-In)
- Form validation
- Error handling with user-friendly messages
- Loading states
- Auto-navigate to Dashboard on success

**Mock Mode**: Bypass authentication entirely, create fake session

---

### 2. Dashboard Screen (`dashboard_screen.dart`)

**Layout**:
- 2x2 grid of stat cards:
  - Accounts (total / active / paused / breached)
  - Active Trades (count)
  - P&L Today (with color based on positive/negative)
  - Bot Status (running/stopped with color)
- Quick Actions card:
  - Force Close All Positions (red danger button)
  - Pause All Accounts
  - Resume All Accounts
  - View Trades / View History buttons
- Recent Activity (notifications list, max 10)

**Responsive Design**:
- Grid: `childAspectRatio: 1.4` (prevents collapse)
- Text overflow: ellipsis
- Min height for cards: 120px

**Functionality**:
- Pull-to-refresh
- Real-time data updates
- Navigation to other screens
- Confirmation dialogs for dangerous actions

---

### 3. Accounts Screen (`accounts_screen.dart`)

**Layout**:
- List of account cards, each showing:
  - Display name / email
  - Account key (shortened)
  - Server + prop firm
  - Current balance (large, bold)
  - Daily P&L (colored)
  - Risk profile name
  - Daily drawdown progress bar (red if >80%)
  - Max drawdown progress bar (red if >80%)
  - Consistency score + profitable days
  - Status badge (ACTIVE / PAUSED / BREACHED)
  - Action buttons: Pause/Resume, Edit

**Filters**:
- Server dropdown (Live / Demo / All)
- Status filter (Active / Paused / Breached / All)

**Responsive Design**:
- Single-column list
- Cards expand/shrink based on content
- Progress bars: full width, height 8px

**Functionality**:
- Create new account (modal with form)
- Edit account (modal)
- Pause/Resume toggle
- Delete account (confirmation dialog)
- Discover accounts (auto-fetch from TradeLocker)

---

### 4. Trades Screen (`trades_screen.dart`)

**Layout**:
- List of trade cards, each showing:
  - Direction badge (BUY green / SELL red)
  - Symbol (large, monospace)
  - Channel name badge
  - TP1 Hit badge (if applicable)
  - Time ago (11m ago, 2h ago)
  - Entry / SL / TP prices
  - Lot size / Risk USD / **Live P&L** (colored, updating)
  - Account key (shortened)
  - Actions: Close, Breakeven, Partial (25% / 50% / 75%)

**Filters**:
- Account dropdown
- Channel dropdown
- Symbol search field
- Sort: Newest / Symbol / Lot Size

**Responsive Design**:
- Single-column list
- Min card height: 180px
- Action buttons wrap on small screens

**Functionality**:
- Close trade (confirmation)
- Set breakeven (confirmation)
- Partial close (confirmation with percentage)
- Real-time P&L updates (if WebSocket connected)

---

### 5. History Screen (`history_screen.dart`)

**Layout**:
- Export CSV button (top-right)
- Filters: Account / Date Range (7d / 30d / All) / Symbol / Channel
- Metrics grid (3 columns, compact):
  - Total Trades
  - Winners (win rate %)
  - Losers
  - Total P&L (colored)
  - Avg Win (green)
  - Avg Loss (red)
  - Largest Win
  - Largest Loss
- Trade history list (paginated, 50 per page)
- Pagination controls: Previous / Page X/Y / Next

**Responsive Design**:
- Metrics: `crossAxisCount: 3`, `childAspectRatio: 1.5`
- Cards: expandable ListTile
- Min tile height: 80px

**Functionality**:
- Filter/search
- CSV export (download)
- Pagination
- Pull-to-refresh

---

### 6. Notifications Screen (`notifications_screen.dart`)

**Layout**:
- "Mark All Read" button (top-right)
- Critical notifications banner (if any)
- List of notification cards:
  - Icon (based on category)
  - Title
  - Message (2 lines max)
  - Time ago
  - Colored left border (severity)
  - Read/unread indicator

**Filters**:
- All / Unread Only

**Functionality**:
- Mark individual read (tap)
- Mark all read
- Delete notification
- Filter

---

### 7. Settings Screen (`settings_screen.dart`)

**Layout**:
- User info card (email, sign-out button)
- API Connection card (URL, status)
- Risk Profiles list (view/edit/delete)
- Channels list (view/edit/enable/disable)
- About section (version, license)

**Functionality**:
- Sign out
- Manage risk profiles
- Manage channels
- View app info

---

### 8. Bot Control Screen (`bot_control_screen.dart`)

**Layout**:
- Bot status card (running/stopped, dry-run mode)
- Control buttons: Start / Stop / Restart
- Settings toggles:
  - Allow Weekend Trading
  - Allow EOD Trading
- Emergency section:
  - Force Close All Positions (red danger button)
- Statistics: Active accounts / trades

**Functionality**:
- Start/stop bot
- Toggle settings
- Emergency close all

---

## 🔧 Navigation Shell

**Implementation**: Single FAB (FloatingActionButton) with radial popup menu

**Requirements**:
- FAB positioned: `bottom: 16, right: 16`
- Container size: `400x400` (to accommodate button spread)
- 6 navigation buttons arranged in a 105° arc (175° to 280°)
- Button size: 56x56 (good touch target)
- Button positioning: `Positioned` with `right/bottom` coordinates relative to FAB
- Overlay: full-screen semi-transparent black, **below** buttons in z-order
- FAB rotates 45° when open
- Buttons appear/disappear instantly (no animation delay blocking taps)
- Each button has: icon, label (tooltip), colored border when active

**CRITICAL**: Buttons must be positioned using `Positioned(right: ..., bottom: ...)` within a Stack that has enough space. Do NOT use `AnimatedPositioned` or complex animations that block pointer events.

**Navigation Items**:
1. Dashboard (`/`)
2. Accounts (`/accounts`)
3. Active Trades (`/trades`)
4. History (`/history`)
5. Bot Control (`/bot-control`)
6. Settings (`/settings`)

---

## 🔌 Backend API Integration

### Base Configuration
```dart
class MpConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000'
  );
  static const wsBaseUrl = String.fromEnvironment(
    'WS_BASE_URL',
    defaultValue: 'ws://localhost:8000'
  );
  static const useMock = String.fromEnvironment(
    'USE_MOCK',
    defaultValue: 'false'
  ) == 'true';
}
```

### Authentication
- **All API requests MUST include**: `Authorization: Bearer <firebase_jwt_token>`
- **401 Response Handling**: Refresh Firebase token, retry request once
- **Token Refresh**: Call `auth.refreshToken()` before retrying

### API Endpoints

#### Accounts
- `GET /api/accounts/` - List all accounts
- `GET /api/accounts/:key` - Get single account
- `POST /api/accounts/` - Create account
- `PUT /api/accounts/:key` - Update account
- `DELETE /api/accounts/:key` - Delete account
- `POST /api/accounts/:key/pause` - Pause account
- `POST /api/accounts/:key/resume` - Resume account
- `POST /api/accounts/discover` - Discover accounts from TradeLocker

#### Channels
- `GET /api/channels/` - List channels
- `POST /api/channels/` - Create channel
- `PUT /api/channels/:id` - Update channel
- `PATCH /api/channels/:id` - Partial update
- `DELETE /api/channels/:id` - Delete channel
- `POST /api/channels/:id/enable` - Enable channel
- `POST /api/channels/:id/disable` - Disable channel

#### Risk Profiles
- `GET /api/risk-profiles/` - List profiles
- `GET /api/risk-profiles/default` - Get default profile
- `POST /api/risk-profiles/` - Create profile
- `PUT /api/risk-profiles/:id` - Update profile
- `PATCH /api/risk-profiles/:id` - Partial update
- `DELETE /api/risk-profiles/:id` - Delete profile

#### Trades
- `GET /api/trades/active` - List all active trades
- `GET /api/trades/active/:account_key` - Active trades for account
- `POST /api/trades/active/:id/close` - Close trade
- `POST /api/trades/active/:id/breakeven` - Set breakeven
- `POST /api/trades/active/:id/partial` - Partial close (body: `{percentage: 25}`)
- `GET /api/trades/history?account_key=&limit=50&offset=0` - Trade history
- `GET /api/trades/history/export?account_key=` - Export CSV

#### Notifications
- `GET /api/notifications/?unread_only=false&limit=50` - List notifications
- `PATCH /api/notifications/:id/read` - Mark read
- `POST /api/notifications/mark-all-read` - Mark all read
- `DELETE /api/notifications/:id` - Delete notification

#### Bot
- `GET /api/bot/status` - Bot status
- `POST /api/bot/control` - Control bot (body: `{action: 'start' | 'stop'}`)
- `POST /api/bot/force-close-all` - Force close all positions
- `POST /api/bot/force-close-account/:key` - Force close account positions

#### FCM
- `POST /api/users/register-fcm-token` - Register FCM token (body: `{fcm_token: '...'}`)

### WebSocket
- **URL**: `ws://localhost:8000/ws/updates`
- **Purpose**: Real-time updates for trades, balances, notifications
- **Mock Mode**: Skip connection entirely if `MpConfig.useMock == true`

---

## 🧪 Mock Mode

**Purpose**: Develop and test UI without backend

**Activation**: `flutter run --dart-define=USE_MOCK=true`

**Behavior**:
- All API calls return mock data (120ms delay for realism)
- WebSocket connection skipped
- Firebase authentication bypassed (fake session created)
- Mock data includes:
  - 3 accounts (1 active, 1 paused, 1 breached)
  - 3 active trades
  - 84 history trades
  - 5 notifications
  - 2 channels
  - 1 risk profile

**Implementation**: Check `MpConfig.useMock` at the start of every API method

---

## 🚨 Critical Issues to Avoid

### 1. Dialog Black Screen Issue
**Problem**: Tapping "Cancel" in confirmation dialogs causes blank/black screen

**Solution**:
- **NEVER** use `Navigator.pop(context, false)` without checking if the context is still valid
- Always check `if (!mounted) return;` before any navigation after async operations
- Use `Navigator.of(context, rootNavigator: false).pop(false)` to ensure proper scope
- For go_router, ensure dialogs don't interfere with route stack

**Example**:
```dart
Future<bool> _confirm(String title) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: Text(title),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Confirm'),
        ),
      ],
    ),
  );
  return result ?? false;
}

Future<void> _someAction() async {
  if (!await _confirm('Are you sure?')) return;
  // ... perform action
  if (!mounted) return; // CHECK BEFORE ANY NAVIGATION
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Done')),
  );
}
```

### 2. Navigation Button Issues
**Problem**: Radial menu buttons not clickable

**Solution**:
- Use large container (`400x400`) to hold button Stack
- Position buttons with `right/bottom` coordinates (NOT `left/top`)
- Place overlay BELOW buttons in z-order
- Ensure buttons have size 56x56 minimum
- **No** `IgnorePointer`, **no** conditional `onTap: null`

### 3. Overflow Issues
**Problem**: Text overflows on various screen sizes

**Solution**:
- **Always** wrap text in `Flexible` or `Expanded` where needed
- **Always** add `overflow: TextOverflow.ellipsis` to Text widgets
- Use appropriate `childAspectRatio` for GridView:
  - Dashboard cards: `1.4`
  - History metrics: `1.5`
- Test on small screens (360dp width)

### 4. Gradient Colors
**Problem**: Wrong colors used for gradients

**Solution**:
- **ALWAYS** use `[MpColors.base, MpColors.app]`
- **NEVER** use hardcoded `Color(0xFF...)` for gradients
- Gradients MUST match web platform exactly

---

## ✅ Testing Checklist

Before submitting the app:

### Visual
- [ ] All gradients use `[MpColors.base, MpColors.app]`
- [ ] All cards have rounded corners (12px)
- [ ] All buttons have min 48x48 touch targets
- [ ] No text overflow on small screens (360dp width)
- [ ] Progress bars are visible and colored correctly
- [ ] Status badges are colored (green/red/orange)
- [ ] P&L values are colored (green positive, red negative)

### Functional
- [ ] Login with email/password works
- [ ] Login with Google works
- [ ] Sign out works
- [ ] Navigation buttons all work (no blank screens)
- [ ] All confirmation dialogs work (Cancel doesn't crash)
- [ ] Pull-to-refresh works on all list screens
- [ ] Filters work correctly
- [ ] Search fields filter results
- [ ] Pagination works (Previous/Next buttons)
- [ ] CSV export downloads file
- [ ] FCM token registration succeeds
- [ ] Push notifications appear

### Responsive
- [ ] App works on small screens (360x640)
- [ ] App works on large screens (1080x1920)
- [ ] Landscape mode is handled gracefully
- [ ] No widgets overflow on any screen size
- [ ] Cards resize properly
- [ ] Grid layouts adjust correctly

### Mock Mode
- [ ] `USE_MOCK=true` works without backend
- [ ] All screens show mock data
- [ ] No WebSocket errors in console
- [ ] Authentication is bypassed
- [ ] All interactions work (simulated)

### Error Handling
- [ ] API errors show user-friendly messages
- [ ] Network errors are handled gracefully
- [ ] Loading states are shown
- [ ] Empty states are shown (no data)
- [ ] 401 errors trigger token refresh

---

## 🚀 Build Commands

### Development (Mock Mode)
```bash
flutter run --dart-define=USE_MOCK=true -d <device>
```

### Development (Real Backend)
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 -d <device>
```

### Production Build
```bash
flutter build apk --release --dart-define=API_BASE_URL=https://api.mirrorpupil.com --dart-define=WS_BASE_URL=wss://api.mirrorpupil.com
```

### iOS Build
```bash
flutter build ios --release --dart-define=API_BASE_URL=https://api.mirrorpupil.com --dart-define=WS_BASE_URL=wss://api.mirrorpupil.com
```

---

## 📋 Deliverables

1. **Complete Flutter project** following this specification
2. **All screens implemented** with responsive layouts
3. **Firebase authentication** configured and working
4. **Push notifications** configured and working
5. **Mock mode** fully functional
6. **No overflow issues** on any screen size
7. **No navigation bugs** (dialogs work correctly)
8. **Gradients match** web platform exactly
9. **README.md** with:
   - Setup instructions
   - Build commands
   - Firebase configuration steps
   - API endpoint documentation
10. **CHANGELOG.md** documenting all features

---

## 🎯 Success Criteria

The app rebuild is successful when:
1. ✅ All screens render correctly without overflow
2. ✅ Navigation buttons work perfectly (no blank screens)
3. ✅ Confirmation dialogs work (Cancel button doesn't crash)
4. ✅ Gradients match web platform (base → app)
5. ✅ Firebase authentication works (email + Google)
6. ✅ Push notifications work
7. ✅ Mock mode works without backend
8. ✅ App is responsive on all screen sizes
9. ✅ All API endpoints are integrated correctly
10. ✅ Error handling is robust and user-friendly

---

## 📞 Support

For questions or clarifications:
- Refer to existing codebase: `Lovable Frontend/export/mobile/`
- Check web platform for visual reference: `Lovable Frontend/src/`
- Backend API reference: `backend/api/routes/`

**End of Specification**
