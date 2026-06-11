# Mirror Pupil Mobile (Flutter)

Flutter 3 client. **1:1 functional mirror of the web app** — every page, filter,
dialog, CRUD form, and emergency action that exists on the web is implemented
here. Same 35 endpoints. Same WebSocket. Same Knights of the Blood Oath theme.
Lagos-time (UTC+1) conversion. Confirmation dialogs on every destructive action.

## Feature parity with the web
| Screen          | Capabilities |
| --------------- | ------------ |
| Dashboard       | KPI tiles (accounts/trades/PnL/bot), **Total Balance modal** (sum of initial/current/highest-banked + daily P&L across every account), recent activity feed, quick actions: **Force close all**, **Pause/Resume all accounts**, jump to trades/history. |
| Accounts        | Search + status filter (all/active/paused/breached); **Add account** dialog with **Discover** (TradeLocker creds → list discovered accounts → add per row) **and Manual** entry tabs; **Edit account** (display name, lot override, max concurrent override, risk profile dropdown); per-row Pause / Resume / Delete with confirm. |
| Active trades   | Filters: account / channel / symbol / sort (newest / symbol / lot size); cards show direction, TP1 hit pill, entry/SL/TP/lots/risk/signal; per-trade **Close**, **Breakeven**, **Partial 25/50/75%** with confirm. |
| History         | Filters: account, last 7d / 30d / all, symbol, channel; 8-stat header (total, winners + win-rate, losers, total/avg/largest win & loss); paginated list with Lagos time; **Export CSV** to backend `/api/trades/history/export`. |
| Notifications   | Close (✕) button (also closes if you tap the bell while on the page); Unread-only switch; **Critical alerts** call-out section; per-item severity stripe, metadata expand, Mark read, Delete with confirm; **Mark all read**. |
| Bot control     | Status card with Start / Stop / Restart (confirmed); active/paused/breached/open-trades tiles; trading-hours read-only switches; **Emergency**: Force close all + Force close per-account (dropdown). |
| Settings        | **Channels** CRUD (add / edit / delete / enable-toggle) with all fields (id, name, prefix, priority, entry & management logic modules, notes); **Risk profiles** full CRUD with every field the web exposes (per-trade %, daily, daily trailing, overall, overall trailing, trail-from-closed-balance, profit lock & floor, payout buffer, max concurrent, commission/lot, safety buffer, notes), set-default, delete; **Bot settings** info panel. |

## Setup

### 1. Install
```bash
cd export/mobile
flutter pub get
```

### 2. Firebase
The repo ships with a placeholder `lib/firebase_options.dart` matching the
project `mirror-pupil` (from `LOVABLE_MOBILE_APP_SPECIFICATION.md §1`).
Regenerate it with the real IDs/keys before shipping:
```bash
dart pub global activate flutterfire_cli
flutterfire configure --project=mirror-pupil
```
Then drop the real platform files:
- `android/app/google-services.json` (download from Firebase Console)
- `ios/Runner/GoogleService-Info.plist`
- Merge the snippet in `ios/Runner/Info.plist.snippet` into the real
  `Info.plist` (URL scheme for Google Sign-In + remote-notification background mode).

### 3. Run
```bash
# Real backend
flutter run \
  --dart-define=API_BASE_URL=https://api.your-backend \
  --dart-define=WS_BASE_URL=wss://api.your-backend

# UI-only / no backend (mocks every endpoint, skips Firebase, skips WS)
flutter run --dart-define=USE_MOCK=true
```
Defaults: `http://localhost:8000` / `ws://localhost:8000`.

### 4. Production build
```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.mirrorpupil.com \
  --dart-define=WS_BASE_URL=wss://api.mirrorpupil.com
flutter build ios --release \
  --dart-define=API_BASE_URL=https://api.mirrorpupil.com \
  --dart-define=WS_BASE_URL=wss://api.mirrorpupil.com
```
`USE_MOCK` defaults to `false` and **must never be true in production**.

## Files
- `lib/main.dart` — MaterialApp.router + go_router + radial FAB nav shell.
  Initialises Firebase (skipped in mock mode), wires `MpApi → AuthService` for
  Bearer-token injection, and starts the FCM service.
  Bottom-right red FAB; tap to fan **6** circular nav buttons in a wide arc
  (175°→280°, radius 150 — roomy, each button gets its own breathing space)
  around it: Dashboard, Accounts, Active, History, Bot, Settings.
  Notifications open via the bell in the AppBar (just like the web header).
  Tap the scrim, an item, or the FAB again to collapse.
- `lib/auth/auth_service.dart` — Firebase Auth wrapper (email/password, Google
  Sign-In, ID-token refresh, password reset). Exposes `auth.token()` to the
  API client and a `Stream<MpSession?>` for the router redirect.
- `lib/services/fcm_service.dart` — Firebase Cloud Messaging: permission
  request, FCM token fetch + `POST /api/users/register-fcm-token`, refresh
  listener, foreground display via `flutter_local_notifications`.
- `lib/firebase_options.dart` — Firebase platform options stub (regenerate
  with `flutterfire configure`).
- `lib/screens/login_screen.dart` — Google + email/password sign-in screen.
  Acts as a gate via `GoRouter.redirect`.
- `lib/theme.dart` — Knights palette (Material 3 dark)
- `lib/api/api_client.dart` — typed REST client (MpApi). Injects
  `Authorization: Bearer <Firebase JWT>`; force-refreshes + retries once on 401;
  exposes `registerFcmToken()` (POST `/api/users/register-fcm-token`).
- `lib/api/ws_service.dart` — WebSocket service with exponential-backoff
  reconnect (max 5). Skips connection in mock mode.
- `lib/api/mock_data.dart` — inline fixtures used only when `USE_MOCK=true`.
- `lib/models/models.dart` — DTOs (full backend field set incl. highest_banked_balance,
  daily_start_balance, profit_lock_pct/floor, overall_trail_from_closed_balance,
  sub_signal_id, tl_order_id, tl_position_id, etc.) + Lagos time / currency helpers
- `lib/screens/*.dart` — Dashboard / Accounts / Active Trades / History / Notifications / Settings / Bot Control
- `assets/logo.svg` — Mirror Pupil brand mark, rendered via `flutter_svg`.
- `android/` — `build.gradle.kts` (project + app), `AndroidManifest.xml`
  (POST_NOTIFICATIONS + FCM default-channel meta), `MainActivity.kt`,
  `google-services.json.template`.
- `ios/Runner/` — `Info.plist.snippet` (Google Sign-In URL scheme +
  remote-notification background mode) and `GoogleService-Info.plist.template`.

## Notes
- Mock mode (`USE_MOCK=true`) returns inline fixtures and skips Firebase + WS.
  Production builds must omit the flag (it defaults to `false`).
- The backend must accept `Authorization: Bearer <Firebase JWT>` on every
  endpoint and expose `POST /api/users/register-fcm-token { fcm_token,
  device_id?, platform? }` for push delivery.
- For production, swap the global `mpApi` / `mpWs` singletons for Riverpod/Provider as needed.
- Drop Inter + JetBrainsMono into `assets/fonts/` and declare them in `pubspec.yaml` to fully theme Android release builds.
