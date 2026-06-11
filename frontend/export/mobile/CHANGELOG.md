# Mirror Pupil Mobile — Changelog

## 5.1.0 — 2026-06-11

### Added
- **Firebase Authentication** (`firebase_auth` + `google_sign_in`) — replaces
  the SharedPreferences shim. Email/password sign-in & sign-up, Google sign-in
  via Firebase credentials, automatic ID-token refresh, password reset.
- **Firebase Cloud Messaging** push notifications (`lib/services/fcm_service.dart`):
  permission request, FCM token fetch + auto-registration with
  `POST /api/users/register-fcm-token`, refresh listener, and in-foreground
  display via `flutter_local_notifications`.
- **Bearer-token API client** — `MpApi` injects `Authorization: Bearer <JWT>`
  on every request and force-refreshes the Firebase token + retries once on 401.
- **Mock mode** — `--dart-define=USE_MOCK=true` short-circuits auth, WebSocket,
  and every API endpoint to inline fixtures so the UI runs without a backend.
- **Command Dashboard → Total Balance modal** — bottom-sheet that sums initial,
  current, and highest-banked balances plus daily P&L across all accounts.
- **Logo asset** — `assets/logo.svg` rendered via `flutter_svg` in AppBar + Login.
- **Android platform config** — `build.gradle.kts` (project + app),
  `MainActivity.kt`, `AndroidManifest.xml` (POST_NOTIFICATIONS + default
  channel meta-data), and `google-services.json.template`.
- **iOS platform config** — `Info.plist.snippet` and
  `GoogleService-Info.plist.template`.
- **Firebase options stub** — `lib/firebase_options.dart` matching the IDs in
  `LOVABLE_MOBILE_APP_SPECIFICATION.md §1`; regenerate via `flutterfire configure`.

### Changed
- WebSocket service skips connecting entirely when `USE_MOCK=true`.
- Bell icon in `AppBar` toggles notifications open/close (matches the web header).
- Radial FAB nav uses a roomier 105° arc (175°→280°) at radius 150.

### Removed
- Hard-coded shield-icon placeholders (web + mobile use the uploaded logo).

## 5.0.0 — 2026-06-09
- Initial Flutter port of the web Mirror Pupil dashboard (35 REST endpoints,
  reconnecting WebSocket, 7 screens, radial-arc nav, confirmation dialogs).