# Mirror Pupil Mobile (Flutter)

Flutter 3 client mirroring the web app. Same 35 endpoints. Same WebSocket. Same Knights theme. Lagos-time conversion. Confirmation dialogs on every destructive action.

## Setup
```bash
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=https://api.your-backend \
  --dart-define=WS_BASE_URL=wss://api.your-backend
```
Defaults: `http://localhost:8000` / `ws://localhost:8000`.

## Files
- `lib/main.dart` — MaterialApp.router + go_router + radial FAB nav shell
  (bottom-right red FAB; tap to fan 7 circular nav buttons in a quarter-arc
  around it — Dashboard, Accounts, Active, History, Alerts, Bot, Settings.
  Tap the scrim, an item, or the FAB again to collapse.)
- `lib/auth/auth_service.dart` — frontend auth shim (SharedPreferences).
  Replace the two TODOs with calls to your `/auth/login` and `/auth/google`
  endpoints, or wire `package:google_sign_in` directly.
- `lib/screens/login_screen.dart` — Google + email/password sign-in screen.
  Acts as a gate via `GoRouter.redirect`.
- `lib/theme.dart` — Knights palette (Material 3 dark)
- `lib/api/api_client.dart` — typed REST client (MpApi)
- `lib/api/ws_service.dart` — WebSocket service with exponential-backoff reconnect (max 5)
- `lib/models/models.dart` — DTOs + utility functions
- `lib/screens/*.dart` — Dashboard / Accounts / Active Trades / History / Notifications / Settings / Bot Control

## Notes
- No mock layer — always hits real HTTP.
- For production, swap the global `mpApi` / `mpWs` singletons for Riverpod/Provider as needed.
- Drop Inter + JetBrainsMono into `assets/fonts/` and declare them in `pubspec.yaml` to fully theme Android release builds.
