# Mirror Pupil v5.1 — Frontend export bundle

Two production-ready clients built strictly to `docs/SPEC.md`. Both speak the same 35 backend endpoints in `docs/API_QUICK_REFERENCE.md`.

| Target | Location | Stack |
|---|---|---|
| Web | repo root (`src/`) | React 19 + TS + TanStack Router/Query + Tailwind v4 + Axios |
| Mobile | `export/mobile/` | Flutter 3 + go_router + http + web_socket_channel |

No Lovable SDK, no Supabase, no Lovable Cloud. The only runtime dependency is your Mirror Pupil backend at `VITE_API_URL` / `API_BASE_URL`.

## Web (this repo)

```
src/lib/mp/
  api.ts         all 35 endpoints (axios). VITE_USE_MOCK toggles mock store
  types.ts       all DTOs
  utils.ts       formatTimeAgo, formatLagosTime (UTC+1), formatPrice, getPnLColor, ...
  ws.ts          useMirrorPupilWebSocket() — reconnect w/ exponential backoff, max 5
  mock-data.ts   dev-only sample data (never used in prod)
  auth.ts        getSession / setSession / signInWithGoogle / signInWithPassword
                 (frontend shim — wire to your backend; see comments inside)
src/components/mp/
  AppShell.tsx        header (logo + bell-toggle + sign-out) + sidebar (md+)
                      + radial floating-action nav (mobile) + WS indicator
  ConfirmDialog.tsx   useConfirm() for required confirmations
  pages/              Dashboard / Accounts / ActiveTrades / History /
                      Notifications / Settings / BotControl / Login
src/routes/           TanStack file-based routes wiring each page
src/assets/logo.svg   placeholder brand mark — replace with your final logo
                      (square SVG/PNG; imported in AppShell.tsx & LoginPage.tsx)
```

### Authentication
`/login` is the entry route. `__root.tsx` redirects unauthenticated users
there. `src/lib/mp/auth.ts` stores a session in `localStorage` and exposes
`signInWithGoogle()` and `signInWithPassword(email, password)` — replace
the two `TODO` bodies with calls to your real `/auth/google` and
`/auth/login` endpoints. For Google Identity Services, drop the
`accounts.google.com/gsi/client` script into the head and call
`google.accounts.id.initialize` from `LoginPage.tsx` — pass the resulting
`credential` JWT to `signInWithGoogle`.

### Mobile nav (radial FAB)
On screens narrower than `md`, the sidebar collapses into a single red
FAB in the bottom-right corner. Tap it: the 7 nav buttons fan out in a
quarter-circle arc (180°→270°) around the FAB. Tap the FAB again (it
rotates into a close icon), tap outside, or press Escape to collapse.

### Notifications close behaviour
The bell icon in the header acts as a toggle: tapping it on any page
opens `/notifications`; tapping it while already on `/notifications`
returns to the dashboard. The page also has its own circular X close
button in the top-left.

### Run / build
```
bun install
bun run dev      # uses .env -> VITE_USE_MOCK=true
bun run build    # uses .env.production -> VITE_USE_MOCK=false
```

Set `VITE_API_URL` and `VITE_WS_URL` before building for prod. Production builds NEVER include mock data — the only path that returns mocks is `USE_MOCK === true` in `src/lib/mp/api.ts`, and `.env.production` ships it off.

### WebSocket
`useMirrorPupilWebSocket()` connects to `${VITE_WS_URL}/ws/updates`, handles all 4 message types (`connection | trade | balance | notification`), invalidates the matching React Query cache, and reconnects with exponential backoff (1s → 16s, 5 attempts) before falling back to polling. Status reflected in the header dot.

### Lagos timezone
`formatLagosTime()` shifts UTC by +1h and emits `Mon DD, HH:mm`. Used everywhere the spec requires WAT.

## Mobile — `export/mobile/`
```
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=https://api.your-backend \
  --dart-define=WS_BASE_URL=wss://api.your-backend
```
- `lib/api/api_client.dart` — every endpoint typed
- `lib/api/ws_service.dart` — reconnecting WebSocket
- `lib/models/models.dart` — DTOs + helpers (formatTimeAgo, formatLagosTime, formatPrice)
- `lib/theme.dart` — Knights palette (Material 3 dark)
- `lib/screens/*.dart` — 7 screens matching the web routes

## Decoupling from Lovable
Web pages in `src/components/mp/pages/` use only `@tanstack/react-router` for links/route hooks; to migrate to React Router v6 + plain Vite, replace `src/router.tsx` + `src/routes/*` with a `BrowserRouter` + `<Routes>` table (~15 lines). Page components themselves stay untouched.

## Verifying completeness
See `docs/IMPLEMENTATION_CHECKLIST.md` — every endpoint, page, utility, and required feature with a checkbox. All items are wired in this bundle.
