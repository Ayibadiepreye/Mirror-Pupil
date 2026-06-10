# Mirror Pupil Mobile (Flutter)

Flutter 3 client. **1:1 functional mirror of the web app** — every page, filter,
dialog, CRUD form, and emergency action that exists on the web is implemented
here. Same 35 endpoints. Same WebSocket. Same Knights of the Blood Oath theme.
Lagos-time (UTC+1) conversion. Confirmation dialogs on every destructive action.

## Feature parity with the web
| Screen          | Capabilities |
| --------------- | ------------ |
| Dashboard       | KPI tiles (accounts/trades/PnL/bot), recent activity feed, quick actions: **Force close all**, **Pause/Resume all accounts**, jump to trades/history. |
| Accounts        | Search + status filter (all/active/paused/breached); **Add account** dialog with **Discover** (TradeLocker creds → list discovered accounts → add per row) **and Manual** entry tabs; **Edit account** (display name, lot override, max concurrent override, risk profile dropdown); per-row Pause / Resume / Delete with confirm. |
| Active trades   | Filters: account / channel / symbol / sort (newest / symbol / lot size); cards show direction, TP1 hit pill, entry/SL/TP/lots/risk/signal; per-trade **Close**, **Breakeven**, **Partial 25/50/75%** with confirm. |
| History         | Filters: account, last 7d / 30d / all, symbol, channel; 8-stat header (total, winners + win-rate, losers, total/avg/largest win & loss); paginated list with Lagos time; **Export CSV** to backend `/api/trades/history/export`. |
| Notifications   | Close (✕) button (also closes if you tap the bell while on the page); Unread-only switch; **Critical alerts** call-out section; per-item severity stripe, metadata expand, Mark read, Delete with confirm; **Mark all read**. |
| Bot control     | Status card with Start / Stop / Restart (confirmed); active/paused/breached/open-trades tiles; trading-hours read-only switches; **Emergency**: Force close all + Force close per-account (dropdown). |
| Settings        | **Channels** CRUD (add / edit / delete / enable-toggle) with all fields (id, name, prefix, priority, entry & management logic modules, notes); **Risk profiles** full CRUD with every field the web exposes (per-trade %, daily, daily trailing, overall, overall trailing, trail-from-closed-balance, profit lock & floor, payout buffer, max concurrent, commission/lot, safety buffer, notes), set-default, delete; **Bot settings** info panel. |

## Setup
```bash
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=https://api.your-backend \
  --dart-define=WS_BASE_URL=wss://api.your-backend
```
Defaults: `http://localhost:8000` / `ws://localhost:8000`.

## Files
- `lib/main.dart` — MaterialApp.router + go_router + radial FAB nav shell.
  Bottom-right red FAB; tap to fan **6** circular nav buttons in a wide arc
  (175°→280°, radius 150 — roomy, each button gets its own breathing space)
  around it: Dashboard, Accounts, Active, History, Bot, Settings.
  Notifications open via the bell in the AppBar (just like the web header).
  Tap the scrim, an item, or the FAB again to collapse.
- `lib/auth/auth_service.dart` — frontend auth shim (SharedPreferences).
  Replace the two TODOs with calls to your `/auth/login` and `/auth/google`
  endpoints, or wire `package:google_sign_in` directly.
- `lib/screens/login_screen.dart` — Google + email/password sign-in screen.
  Acts as a gate via `GoRouter.redirect`.
- `lib/theme.dart` — Knights palette (Material 3 dark)
- `lib/api/api_client.dart` — typed REST client (MpApi)
- `lib/api/ws_service.dart` — WebSocket service with exponential-backoff reconnect (max 5)
- `lib/models/models.dart` — DTOs (full backend field set incl. highest_banked_balance,
  daily_start_balance, profit_lock_pct/floor, overall_trail_from_closed_balance,
  sub_signal_id, tl_order_id, tl_position_id, etc.) + Lagos time / currency helpers
- `lib/screens/*.dart` — Dashboard / Accounts / Active Trades / History / Notifications / Settings / Bot Control

## Notes
- No mock layer — always hits real HTTP.
- For production, swap the global `mpApi` / `mpWs` singletons for Riverpod/Provider as needed.
- Drop Inter + JetBrainsMono into `assets/fonts/` and declare them in `pubspec.yaml` to fully theme Android release builds.
