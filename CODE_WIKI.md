# Mirror Pupil Code Wiki

## 1. Project Overview

Mirror Pupil is a multi-surface copy-trading system built around a Python backend, a React web control panel, and a Flutter mobile client.

At a high level, the system:

1. Ingests Telegram channel messages.
2. Parses them into structured trading signals or management commands.
3. Validates them against account-level risk rules.
4. Executes trades on TradeLocker accounts.
5. Persists state in PostgreSQL.
6. Pushes state changes to web and mobile clients through REST, WebSocket, and push notifications.

## 2. Repository Layout

```text
Mirror Pupil/
|- backend/
|  |- api/                  # FastAPI app, REST routes, WebSocket endpoint
|  |- channels/             # Channel plugin system and channel-specific parsing logic
|  |- core/                 # Trade execution, account management, monitors, notifications
|  |- database/             # Models, schema, migrations, async DB manager
|  |- risk/                 # Risk calculations, limit enforcement, trading-hour controls
|  |- services/             # Supporting services such as push notifications
|  \- telegram_integration.py
|- Lovable Frontend/        # React + TanStack web client
|  |- src/
|  |  |- routes/            # File-based route entries
|  |  |- components/        # App shell, pages, shared UI
|  |  \- lib/               # API client, auth, websocket, utilities, types
|  \- export/mobile/        # Flutter mobile client
|- README.md
|- .env.example
|- requirements.txt
|- run_backend.py
\- CODE_WIKI.md
```

## 3. System Architecture

```text
Telegram Channels
    |
    v
telegram_client.py / backend/telegram_integration.py
    |
    v
backend/channels/registry.py
    |
    v
backend/channels/base.py + channel-specific parsers
    |
    v
backend/core/trade_executor.py
    |
    +--> backend/risk/enforcer.py
    +--> backend/core/account_manager.py
    +--> backend/core/tradelocker_client.py
    +--> backend/database/manager.py
    +--> backend/core/notification_service.py
    |
    v
TradeLocker + PostgreSQL
    |
    +--> FastAPI REST routes
    +--> WebSocket updates
    +--> Push notifications
    |
    v
React Web App / Flutter Mobile App
```

## 4. Runtime Composition

The main backend composition root is `backend/api/main.py`.

During startup it:

1. Loads environment variables.
2. Connects to PostgreSQL through `DatabaseManager`.
3. Hydrates `AccountManager` with stored TradeLocker credentials.
4. Creates and initializes `TradeExecutor`.
5. Creates the notification service.
6. Injects the executor into the channel registry.
7. Starts risk enforcement and background monitors.
8. Starts Telegram integration.
9. Mounts REST and WebSocket routes.

This makes `backend/api/main.py` the best place to start when tracing backend behavior.

## 5. Backend Architecture

### 5.1 API Layer

Location: `backend/api/`

Purpose:

- Exposes REST endpoints for accounts, channels, risk profiles, trades, bot control, notifications, and users.
- Exposes the WebSocket endpoint used by the frontend and mobile app.
- Provides the backend process lifecycle through FastAPI lifespan hooks.

Important files:

- `backend/api/main.py`
- `backend/api/websocket.py`
- `backend/api/routes/accounts.py`
- `backend/api/routes/channels.py`
- `backend/api/routes/risk_profiles.py`
- `backend/api/routes/trades.py`
- `backend/api/routes/bot_control.py`
- `backend/api/routes/notifications.py`
- `backend/api/routes/users.py`

Mounted route groups:

- `/api/accounts`
- `/api/channels`
- `/api/risk-profiles`
- `/api/trades`
- `/api/bot`
- `/api/notifications`
- `/api/users`
- `/ws`

### 5.2 Database Layer

Location: `backend/database/`

Purpose:

- Owns the PostgreSQL connection pool.
- Initializes schema and default data.
- Implements most data-access operations for channels, accounts, users, trades, notifications, and settings.
- Acts as a repository layer for almost the entire backend.

Important files:

- `backend/database/manager.py`
- `backend/database/models.py`
- `backend/database/schema.py`
- `backend/database/migrations/`

Key design note:

`DatabaseManager` is a major dependency hub. Many backend services call it directly instead of using smaller repositories, so it is central to both persistence and orchestration.

### 5.3 Channel Parsing Layer

Location: `backend/channels/`

Purpose:

- Defines the plugin interface for Telegram signal channels.
- Loads enabled channel definitions from the database.
- Routes Telegram messages to the correct parser.
- Converts raw messages into structured entry or management instructions.

Important files:

- `backend/channels/base.py`
- `backend/channels/registry.py`
- `backend/channels/billirichy/`
- `backend/channels/firepips/`

Key design note:

The registry loads channels dynamically from database configuration and builds `DynamicChannelPlugin` instances using configured entry and management logic modules.

### 5.4 Trading Core

Location: `backend/core/`

Purpose:

- Manages TradeLocker credentials and account clients.
- Executes entry signals and management actions.
- Reconciles balances and positions.
- Monitors pending orders and trailing stops.
- Emits user-facing notifications.

Important files:

- `backend/core/account_manager.py`
- `backend/core/trade_executor.py`
- `backend/core/tradelocker_client.py`
- `backend/core/notification_service.py`
- `backend/core/balance_reconciliation.py`
- `backend/core/pending_order_monitor.py`
- `backend/core/position_reconciliation.py`
- `backend/core/trailing_stop_updater.py`
- `backend/core/health_monitor.py`
- `backend/core/firebase_auth.py`
- `backend/core/bot_state.py`

### 5.5 Risk Layer

Location: `backend/risk/`

Purpose:

- Calculates trade risk and account floors.
- Prevents new trades that would violate account rules.
- Detects breaches and can trigger protective behavior.
- Enforces trading-hour constraints.
- Runs daily reset and end-of-day close schedulers.

Important files:

- `backend/risk/enforcer.py`
- `backend/risk/calculator.py`
- `backend/risk/trading_hours.py`
- `backend/risk/daily_reset.py`
- `backend/risk/eod_close.py`

### 5.6 Telegram Integration

Key files:

- `telegram_client.py`
- `backend/telegram_integration.py`

Purpose:

- Connects to Telegram using TDLib through `pytdbot`.
- Subscribes to configured channels.
- Forwards incoming channel messages into the channel registry.

## 6. Frontend Architecture

Location: `Lovable Frontend/`

The web application is a React 19 app using TanStack Router, TanStack Start, React Query, axios, Firebase Auth, and a Radix/shadcn-style UI stack.

### 6.1 Composition and Bootstrap

Important files:

- `Lovable Frontend/src/start.ts`
- `Lovable Frontend/src/server.ts`
- `Lovable Frontend/src/router.tsx`
- `Lovable Frontend/src/routes/__root.tsx`

Responsibilities:

- `start.ts` boots the TanStack Start app.
- `server.ts` exports the server fetch handler for the app runtime.
- `router.tsx` creates the app router from generated routes.
- `__root.tsx` composes global providers, error boundaries, auth gating, app shell, and toaster notifications.

### 6.2 Route Layer

Location: `Lovable Frontend/src/routes/`

Responsibilities:

- Defines URL-to-page mappings.
- Keeps route files thin by delegating real UI logic to page components.

Examples:

- `index.tsx`
- `accounts.tsx`
- `trades.tsx`
- `notifications.tsx`
- `settings.tsx`
- `login.tsx`
- `users.tsx`

### 6.3 Application UI Layer

Location: `Lovable Frontend/src/components/mp/`

Responsibilities:

- Provides the main shell and navigation.
- Hosts page-level components for dashboard, accounts, trades, notifications, settings, login, and users.
- Provides shared app-specific components such as confirmation dialogs.

Important files:

- `Lovable Frontend/src/components/mp/AppShell.tsx`
- `Lovable Frontend/src/components/mp/ConfirmDialog.tsx`
- `Lovable Frontend/src/components/mp/pages/DashboardPage.tsx`
- `Lovable Frontend/src/components/mp/pages/AccountsPage.tsx`
- `Lovable Frontend/src/components/mp/pages/ActiveTradesPage.tsx`
- `Lovable Frontend/src/components/mp/pages/SettingsPage.tsx`
- `Lovable Frontend/src/components/mp/pages/LoginPage.tsx`
- `Lovable Frontend/src/components/mp/pages/UsersPage.tsx`

### 6.4 Data and Integration Layer

Location: `Lovable Frontend/src/lib/mp/`

Responsibilities:

- Encapsulates all REST calls.
- Manages auth/session state.
- Manages WebSocket connection and cache invalidation.
- Defines shared frontend types and optional mock data.

Important files:

- `Lovable Frontend/src/lib/mp/api.ts`
- `Lovable Frontend/src/lib/mp/ws.ts`
- `Lovable Frontend/src/lib/mp/auth.ts`
- `Lovable Frontend/src/lib/mp/auth-context.tsx`
- `Lovable Frontend/src/lib/mp/types.ts`
- `Lovable Frontend/src/lib/firebase.ts`

Key design note:

`api.ts` is the main frontend service boundary. Most page components depend on it directly or indirectly.

## 7. Mobile Architecture

Location: `Lovable Frontend/export/mobile/`

The Flutter app mirrors the backend contract used by the web client and provides a mobile-native interface for the same operational workflows.

Important files:

- `Lovable Frontend/export/mobile/lib/main.dart`
- `Lovable Frontend/export/mobile/lib/api/api_client.dart`
- `Lovable Frontend/export/mobile/lib/api/ws_service.dart`
- `Lovable Frontend/export/mobile/lib/auth/auth_service.dart`
- `Lovable Frontend/export/mobile/lib/services/fcm_service.dart`
- `Lovable Frontend/export/mobile/lib/screens/`

Responsibilities:

- Bootstraps Firebase, auth, API client, WebSocket client, and router.
- Reuses the same backend endpoints and WebSocket channel as the web client.
- Adds mobile-specific behavior such as FCM push notification registration.

## 8. Major Modules and Responsibilities

| Module | Responsibility | Key Dependencies |
| --- | --- | --- |
| `backend/api/main.py` | Process composition root, startup/shutdown lifecycle, router mounting | `DatabaseManager`, `TradeExecutor`, monitors, Telegram integration |
| `backend/database/manager.py` | Database pool, schema init, application data access | `asyncpg`, schema/models, secret vault |
| `backend/channels/registry.py` | Loads enabled channel plugins and routes Telegram messages | `DatabaseManager`, channel plugins, `TradeExecutor` |
| `backend/channels/base.py` | Shared plugin contract and generic routing logic | Channel-specific parser modules, `TradeExecutor` |
| `backend/core/account_manager.py` | Discovers and manages TradeLocker sub-accounts and clients | `TradeLockerClient` |
| `backend/core/trade_executor.py` | Executes signals, management actions, and trade lifecycle operations | `AccountManager`, `RiskEnforcer`, `DatabaseManager`, notifications |
| `backend/core/tradelocker_client.py` | Broker API wrapper with auth, retries, and trading operations | TradeLocker SDK |
| `backend/risk/enforcer.py` | Pre-trade validation and breach monitoring | `RiskCalculator`, `DatabaseManager`, notifications |
| `backend/core/notification_service.py` | Persists and broadcasts notifications | `DatabaseManager`, WebSocket manager |
| `Lovable Frontend/src/routes/__root.tsx` | Global provider composition and auth gate | React Query, auth context, app shell |
| `Lovable Frontend/src/lib/mp/api.ts` | Browser API client and query-key hub | axios, session storage |
| `Lovable Frontend/src/lib/mp/ws.ts` | Real-time sync and cache invalidation | browser WebSocket, React Query |
| `Lovable Frontend/src/components/mp/AppShell.tsx` | Shared web navigation and runtime status UI | route state, bot status, notifications, websocket status |
| `Lovable Frontend/export/mobile/lib/api/api_client.dart` | Mobile API service layer | HTTP, auth token handling |
| `Lovable Frontend/export/mobile/lib/api/ws_service.dart` | Mobile WebSocket wrapper | WebSocket channel |

## 9. Key Classes and Functions

### 9.1 Backend Core

#### `DatabaseManager`

Location: `backend/database/manager.py`

Role:

- Creates the async PostgreSQL pool.
- Initializes and migrates schema.
- Provides CRUD/query helpers across almost every domain table.

Important methods:

- `connect()`
- `disconnect()`
- `initialize_schema()`
- `get_all_channels()`
- `get_risk_profiles_by_user()`
- `get_all_accounts()`
- `get_active_trades()`
- notification and user-management helpers used by API routes and services

#### `TradeExecutor`

Location: `backend/core/trade_executor.py`

Role:

- Main orchestration class for trading actions.
- Executes entry signals across subscribed accounts.
- Executes management commands such as breakeven, partial close, and close-all behavior.

Important methods:

- `initialize()`
- `execute_signal()`
- `_execute_on_account_with_limit_check()`
- `_execute_on_account()`
- `execute_management()`

#### `AccountManager`

Location: `backend/core/account_manager.py`

Role:

- Discovers TradeLocker sub-accounts for a credential.
- Maintains one client per sub-account.
- Exposes live account/runtime broker access to the rest of the backend.

Important methods:

- `add_credential()`
- `get_account()`
- `get_client_for_account()`
- `get_all_accounts()`
- `update_account_balance()`
- `get_open_positions()`
- `close_all_positions()`

#### `RiskEnforcer`

Location: `backend/risk/enforcer.py`

Role:

- Validates proposed trades before execution.
- Monitors accounts for breaches in the background.
- Applies daily, overall, and concurrent trade restrictions.

Important methods:

- `start_breach_monitoring()`
- `stop_breach_monitoring()`
- `validate_trade()`
- `check_risk_limits()`

#### `NotificationService`

Location: `backend/core/notification_service.py`

Role:

- Creates notification records.
- Broadcasts user-visible events through WebSocket.
- Acts as the bridge between backend events and real-time UI updates.

### 9.2 Channel Abstractions

#### `ParsedSignal`

Location: `backend/channels/base.py`

Role:

- Structured output for a parsed entry signal.
- Captures normalized symbol, direction, prices, order type, and message metadata.

#### `ParsedManagement`

Location: `backend/channels/base.py`

Role:

- Structured output for a parsed management command.
- Captures actions such as breakeven, stop-loss changes, take-profit changes, or partial close instructions.

#### `ChannelPlugin`

Location: `backend/channels/base.py`

Role:

- Abstract parser interface for all Telegram channels.
- Defines symbol normalization, entry parsing, management parsing, and generic message routing behavior.

#### `DynamicChannelPlugin`

Location: `backend/channels/base.py`

Role:

- Runtime-configurable plugin implementation.
- Loads entry and management logic modules based on database channel configuration.

#### `ChannelRegistry`

Location: `backend/channels/registry.py`

Role:

- Registry and dispatcher for channel plugins.
- Connects Telegram channel IDs to parser/execution logic.

Important methods:

- `initialize()`
- `inject_trade_executor()`
- `get_plugin()`
- `route_message()`

### 9.3 Frontend Key Functions and Components

#### `Route` in `src/routes/__root.tsx`

Role:

- Defines the root route tree configuration.
- Applies provider composition, error handling, and the authentication gate.

#### `AppShell`

Location: `Lovable Frontend/src/components/mp/AppShell.tsx`

Role:

- Provides the persistent UI shell, navigation, and runtime indicators used by authenticated screens.

#### `accountsApi`, `channelsApi`, `riskProfilesApi`, `tradesApi`, `notificationsApi`, `botApi`, `usersApi`

Location: `Lovable Frontend/src/lib/mp/api.ts`

Role:

- Group REST operations by domain.
- Provide one consistent browser-side API layer across the app.

#### `useMirrorPupilWebSocket()`

Location: `Lovable Frontend/src/lib/mp/ws.ts`

Role:

- Opens the live WebSocket connection.
- Invalidates cached queries when trade, balance, or notification messages arrive.
- Falls back gracefully when the connection drops.

#### `AuthProvider`

Location: `Lovable Frontend/src/lib/mp/auth-context.tsx`

Role:

- Tracks Firebase auth state.
- Fetches approval and admin metadata from the backend.

## 10. Dependency Relationships

### 10.1 Backend

```text
FastAPI main
  -> DatabaseManager
  -> AccountManager
  -> TradeExecutor
     -> RiskEnforcer
     -> AccountManager
     -> DatabaseManager
     -> NotificationService
     -> TradeLockerClient
  -> ChannelRegistry
     -> DynamicChannelPlugin
     -> TradeExecutor
  -> TelegramIntegration
     -> ChannelRegistry
  -> Background monitors
     -> DatabaseManager
     -> AccountManager / TradeExecutor / NotificationService
```

### 10.2 Web Client

```text
TanStack route/page
  -> React Query hooks/mutations
  -> api.ts domain clients
  -> FastAPI REST endpoints

WebSocket hook
  -> /ws/updates
  -> React Query cache invalidation
  -> toast notifications
```

### 10.3 Mobile Client

```text
Screen widgets
  -> api_client.dart
  -> FastAPI REST endpoints

ws_service.dart
  -> /ws/updates

auth_service.dart
  -> Firebase Auth
  -> backend user endpoints
```

## 11. End-to-End Data Flow

### 11.1 Signal Execution Flow

1. A Telegram signal arrives.
2. `backend/telegram_integration.py` forwards it to `ChannelRegistry`.
3. The matching channel plugin parses it into `ParsedSignal`.
4. The plugin hands execution to `TradeExecutor`.
5. `TradeExecutor` checks bot state and trading hours.
6. `RiskEnforcer` validates the trade for each target account.
7. `AccountManager` provides the correct TradeLocker client.
8. `TradeLockerClient` places the order.
9. `DatabaseManager` records the active trade and related state.
10. `NotificationService` emits updates.
11. Web and mobile clients refresh via REST polling and WebSocket invalidation.

### 11.2 Trade Management Flow

1. A management message arrives from Telegram or a user action arrives from the UI.
2. The backend resolves the target active trade or trade set.
3. `TradeExecutor` performs the requested action.
4. Database state and notifications are updated.
5. Clients observe the change through the same real-time channel.

## 12. How To Run The Project

### 12.1 Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database
- Telegram API credentials
- TradeLocker credentials
- Firebase project credentials if auth and mobile push features are needed

### 12.2 Backend Setup

From the repository root:

```bash
pip install -r requirements.txt
```

Copy the environment template:

```bash
cp .env.example .env
```

Important environment values include:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_PHONE`
- `DATABASE_URL`
- `DRY_RUN`
- `DEFAULT_LOT_SIZE`
- `FIREBASE_SERVICE_ACCOUNT_KEY`

Start the backend with either command:

```bash
uvicorn backend.api.main:app --reload --port 8000
```

or:

```bash
python run_backend.py
```

Useful URLs:

- API root: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 12.3 Frontend Setup

The actual frontend directory in this repository is `Lovable Frontend/`.

```bash
cd "Lovable Frontend"
npm install
npm run dev
```

Other useful commands:

```bash
npm run build
npm run preview
npm run lint
npm run format
```

Default backend connection values in the frontend are:

- API: `http://localhost:8000`
- WebSocket: `ws://localhost:8000`

These can be overridden with frontend environment variables such as `VITE_API_URL`, `VITE_WS_URL`, and `VITE_USE_MOCK`.

### 12.4 Mobile Setup

From the mobile export directory:

```bash
cd "Lovable Frontend/export/mobile"
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000 --dart-define=WS_BASE_URL=ws://localhost:8000
```

For remote deployments, replace those `dart-define` values with your hosted API and WebSocket URLs.

## 13. External Dependencies

### 13.1 Backend

Notable Python dependencies from `requirements.txt`:

- `pytdbot[tdjson]`
- `tradelocker`
- `asyncpg`
- `sqlalchemy`
- `fastapi`
- `uvicorn[standard]`
- `websockets`
- `firebase-admin`
- `pandas`

### 13.2 Frontend

Notable web dependencies from `Lovable Frontend/package.json`:

- `react`
- `@tanstack/react-query`
- `@tanstack/react-router`
- `@tanstack/react-start`
- `axios`
- `firebase`
- `zod`
- `sonner`
- `lucide-react`
- many `@radix-ui/*` packages

### 13.3 Mobile

Notable Flutter dependencies from `Lovable Frontend/export/mobile/pubspec.yaml`:

- `http`
- `web_socket_channel`
- `go_router`
- `shared_preferences`
- `firebase_core`
- `firebase_auth`
- `firebase_messaging`
- `google_sign_in`
- `flutter_svg`

## 14. Suggested Reading Order

For new contributors, a good reading path is:

1. `README.md`
2. `backend/api/main.py`
3. `backend/channels/base.py`
4. `backend/channels/registry.py`
5. `backend/core/trade_executor.py`
6. `backend/risk/enforcer.py`
7. `backend/database/manager.py`
8. `Lovable Frontend/src/routes/__root.tsx`
9. `Lovable Frontend/src/lib/mp/api.ts`
10. `Lovable Frontend/src/components/mp/AppShell.tsx`

## 15. Architectural Observations

- The backend is intentionally centralized around a few heavy orchestrators: `DatabaseManager`, `TradeExecutor`, and `ChannelRegistry`.
- The parser/execution split is clean: channel plugins parse, while the trading core executes.
- The frontend and mobile apps both depend on the same backend contract, which keeps feature parity straightforward.
- Real-time UX is implemented as a hybrid model: REST remains the source for most screen data, while WebSocket events trigger refreshes and notifications.
- The repository contains multiple operational surfaces, but the FastAPI backend is the true system center.
