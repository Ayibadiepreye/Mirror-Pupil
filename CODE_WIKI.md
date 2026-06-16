# Mirror Pupil Code Wiki

## 1. Purpose And Scope

This document describes the current repository as checked in today. It focuses on:

- overall system architecture
- responsibilities of major modules
- key classes and functions
- dependency relationships
- practical run, build, and test instructions

Mirror Pupil is a multi-surface copy-trading platform centered on a Python backend. It ingests Telegram trading signals, parses them into structured actions, validates them against risk rules, executes them on TradeLocker accounts, stores state in PostgreSQL, and exposes that state to operator-facing clients through REST and WebSocket APIs.

## 2. High-Level System Summary

At runtime, the system works like this:

1. Telegram messages are received by the TDLib-based Telegram client.
2. The channel registry selects the correct channel plugin for the source channel.
3. The plugin parses the raw message into either:
   - an entry signal
   - a management command
   - an incomplete "waiting room" signal that needs follow-up details
4. The trade executor validates bot state, trading hours, subscriptions, risk, and account eligibility.
5. Orders and management actions are sent to TradeLocker through per-account clients.
6. Database records are created or updated for accounts, active trades, history, notifications, and manual actions.
7. The FastAPI app serves the state to the web UI and pushes live changes through WebSocket updates.

## 3. Repository Layout

```text
Mirror Pupil/
|- backend/
|  |- api/                    FastAPI entrypoint, REST routes, WebSocket endpoint
|  |- channels/               Channel plugin framework and channel-specific parsers
|  |- core/                   Trade execution, account management, monitors, notifications
|  |- database/               Pydantic models, schema, migrations, DB access manager
|  |- risk/                   Risk math, validation, trading hours, scheduled protections
|  |- services/               Auxiliary services such as push notifications
|  \- telegram_integration.py Telegram runtime bridge into the backend
|- Lovable Frontend/
|  |- src/
|  |  |- routes/              TanStack file-based routes
|  |  |- components/          App shell, pages, shared UI primitives
|  |  |- lib/                 API client, auth, websocket, shared utilities and types
|  |  |- router.tsx           Router factory
|  |  |- start.ts             TanStack Start bootstrap
|  |  \- server.ts            SSR/server fetch wrapper
|  \- export/mobile/          Flutter/mobile export files and documentation
|- .env.example               Backend environment template
|- requirements.txt           Backend Python dependencies
|- run_backend.py             Convenience backend launcher
|- README.md                  Product and setup overview
\- CODE_WIKI.md               This document
```

## 4. Architecture Overview

```text
Telegram Channels
    |
    v
telegram_client.py
    |
    v
backend/telegram_integration.py
    |
    v
backend/channels/registry.py
    |
    v
backend/channels/base.py + channel-specific parser modules
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
    +--> backend/api/main.py
    +--> backend/api/routes/*
    +--> backend/api/websocket.py
    |
    v
Lovable Frontend web app
```

## 5. Backend Composition Root

The main backend entrypoint is `backend/api/main.py`.

Its `lifespan()` function is the true composition root for the application. On startup it:

1. creates and connects `DatabaseManager`
2. loads stored account credentials into `AccountManager`
3. creates and initializes `TradeExecutor`
4. creates `NotificationService`
5. injects the executor into the channel registry
6. initializes `RiskEnforcer`
7. starts autonomous channel managers and background monitors
8. starts Telegram integration
9. mounts REST and WebSocket routes on the FastAPI app

This is the best single file to read first when tracing backend runtime behavior.

## 6. Major Backend Modules

### 6.1 `backend/api/`

Responsibilities:

- hosts the FastAPI application
- defines the process lifecycle
- exposes REST endpoints for the operator UI
- exposes the WebSocket endpoint used for real-time updates

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

### 6.2 `backend/database/`

Responsibilities:

- defines the core domain models with Pydantic
- owns the PostgreSQL connection pool
- initializes schema and applies default data setup
- provides the persistence API used by nearly every backend subsystem

Important files:

- `backend/database/models.py`
- `backend/database/manager.py`
- `backend/database/schema.py`
- `backend/database/migrations/add_gui_enhancements.sql`
- `backend/database/migrations/add_multi_user_auth.sql`

Design note:

`DatabaseManager` is a large repository-and-service layer combined into one class. It handles channels, users, accounts, subscriptions, trades, notifications, settings, and manual action audit records, so it is one of the strongest dependency hubs in the whole backend.

### 6.3 `backend/channels/`

Responsibilities:

- defines the plugin contract for Telegram signal channels
- normalizes raw channel messages into structured trade actions
- loads enabled channels dynamically from the database
- routes messages to the correct parser implementation
- maintains a waiting-room flow for incomplete signals

Important files:

- `backend/channels/base.py`
- `backend/channels/registry.py`
- `backend/channels/billirichy/*`
- `backend/channels/firepips/*`

Design note:

The registry does not hard-code one parser per channel record. Instead, a database channel config specifies the entry and management logic modules, and `DynamicChannelPlugin` composes them at runtime.

### 6.4 `backend/core/`

Responsibilities:

- manages TradeLocker credentials and per-account clients
- executes entry signals and management actions
- reconciles balances and positions
- watches pending orders and trailing-stop conditions
- emits notifications for user-facing events
- tracks operational bot state and account health

Important files:

- `backend/core/trade_executor.py`
- `backend/core/account_manager.py`
- `backend/core/tradelocker_client.py`
- `backend/core/notification_service.py`
- `backend/core/balance_reconciliation.py`
- `backend/core/pending_order_monitor.py`
- `backend/core/position_reconciliation.py`
- `backend/core/trailing_stop_updater.py`
- `backend/core/health_monitor.py`
- `backend/core/firebase_auth.py`
- `backend/core/bot_state.py`

### 6.5 `backend/risk/`

Responsibilities:

- calculates risk in price and USD terms
- validates trades before execution
- enforces daily and overall account rules
- monitors live breaches in the background
- controls trading-hours behavior and scheduled resets/closures

Important files:

- `backend/risk/enforcer.py`
- `backend/risk/calculator.py`
- `backend/risk/trading_hours.py`
- `backend/risk/daily_reset.py`
- `backend/risk/eod_close.py`
- `backend/risk/consistency.py`

### 6.6 `backend/telegram_integration.py`

Responsibilities:

- creates and starts the Telegram client if credentials are configured
- initializes the channel registry using database channel definitions
- registers message handlers for each enabled channel
- runs periodic waiting-room cleanup
- bridges external Telegram events into the backend pipeline

## 7. Frontend Architecture

The web app lives in `Lovable Frontend/` and is a React 19 application built with TanStack Start, TanStack Router, React Query, axios, Firebase Auth, Vite, Tailwind CSS, and Radix-based UI components.

### 7.1 Frontend Bootstrap And Runtime

Important files:

- `Lovable Frontend/src/start.ts`
- `Lovable Frontend/src/server.ts`
- `Lovable Frontend/src/router.tsx`
- `Lovable Frontend/src/routes/__root.tsx`

Responsibilities:

- `start.ts` creates the TanStack Start runtime and installs server middleware
- `server.ts` wraps the generated server entry and normalizes catastrophic SSR failures
- `router.tsx` creates the query client and router
- `__root.tsx` composes global providers, app metadata, auth/session gating, approval gating, error handling, and the shared shell

### 7.2 Frontend Routes

The route layer in `Lovable Frontend/src/routes/` is intentionally thin. Each route mostly maps a URL to a page component:

- `/` -> dashboard
- `/accounts` -> account management
- `/trades` -> active trades
- `/history` -> trade history
- `/bot-control` -> bot operations
- `/notifications` -> notifications center
- `/settings` -> channels, risk profiles, bot settings
- `/users` -> user administration
- `/login` -> authentication screen

### 7.3 Frontend UI Layer

The app-specific UI lives under `Lovable Frontend/src/components/mp/`.

Key pieces:

- `AppShell.tsx` provides the persistent header, sidebar, mobile radial navigation, bot status, websocket status, unread notification badge, and sign-out
- `ConfirmDialog.tsx` supplies shared confirmation flow
- `pages/*` contains the real screen logic for dashboard, accounts, active trades, history, notifications, settings, login, bot control, and users

### 7.4 Frontend Integration Layer

The frontend service boundary lives under `Lovable Frontend/src/lib/`, especially `src/lib/mp/`.

Important files:

- `Lovable Frontend/src/lib/mp/api.ts`
- `Lovable Frontend/src/lib/mp/types.ts`
- `Lovable Frontend/src/lib/mp/auth.ts`
- `Lovable Frontend/src/lib/mp/auth-context.tsx`
- `Lovable Frontend/src/lib/mp/ws.ts`
- `Lovable Frontend/src/lib/firebase.ts`

Responsibilities:

- `api.ts` centralizes REST calls, auth token attachment, mock-mode behavior, and React Query keys
- `types.ts` mirrors the backend data contract in TypeScript
- `auth-context.tsx` listens to Firebase auth state and enriches it using `/api/users/me`
- `ws.ts` manages websocket reconnection and query invalidation

## 8. Mobile Export Status

The repository contains `Lovable Frontend/export/mobile/`, but the current checkout appears to be an export/scaffolding package rather than a complete in-repo mobile source tree.

What is present:

- Android wrapper files
- Flutter metadata and configuration
- mobile README and setup docs
- a widget test

What is not present in this checkout:

- the `lib/` Dart source files referenced by `export/mobile/README.md`

Implication:

Treat the mobile portion of this repository as documentation and export scaffolding unless the missing Dart source files are restored in a future commit.

## 9. Core Domain Models

The backend models in `backend/database/models.py` define the core data contract.

| Model | Purpose |
| --- | --- |
| `Channel` | Configures a Telegram source channel, parser modules, prefix, priority, and enabled state |
| `RiskProfile` | Stores named account risk rules such as max risk, daily loss, trailing logic, and buffers |
| `Account` | Represents a TradeLocker sub-account plus owner, balance, drawdown, and operational state |
| `ChannelSubscription` | Connects an account to a channel with an enabled flag |
| `ActiveTrade` | Represents an open or pending trade being tracked live |
| `WaitingRoom` | Stores incomplete entry signals awaiting completion details |
| `TradeHistory` | Stores closed-trade history including PnL and close reason |
| `ProfitableDay` | Tracks consistency-related daily performance |
| `MessageCache` | Deduplicates processed Telegram messages |
| `Notification` | Represents a UI-visible event delivered via API/WebSocket |
| `ManualAction` | Audits user-triggered manual operations |

## 10. Key Classes And Functions

### 10.1 Backend Runtime And Orchestration

| Symbol | Location | Role |
| --- | --- | --- |
| `lifespan()` | `backend/api/main.py` | Composes and starts the backend on FastAPI startup, then shuts it down cleanly |
| `TelegramIntegration.start()` | `backend/telegram_integration.py` | Starts the Telegram client, initializes the channel registry, and registers handlers |
| `ChannelRegistry.initialize()` | `backend/channels/registry.py` | Loads enabled channel definitions from the database and builds plugins |
| `ChannelRegistry.route_message()` | `backend/channels/registry.py` | Dispatches a Telegram message to the correct plugin |
| `ChannelPlugin.route_message()` | `backend/channels/base.py` | Default parser routing pipeline for edits, replies, management, waiting-room completion, and entries |

### 10.2 Trading Core

| Symbol | Location | Role |
| --- | --- | --- |
| `TradeExecutor.initialize()` | `backend/core/trade_executor.py` | Lazy-initializes risk enforcement and notification services |
| `TradeExecutor.execute_signal()` | `backend/core/trade_executor.py` | Entry-point for executing a parsed signal across eligible accounts |
| `TradeExecutor._execute_on_account()` | `backend/core/trade_executor.py` | Performs the actual per-account order workflow: instrument resolution, sizing, placement, persistence |
| `TradeExecutor.execute_management()` | `backend/core/trade_executor.py` | Applies parsed management instructions across matching trades/accounts |
| `TradeExecutor._apply_management_action()` | `backend/core/trade_executor.py` | Executes the specific close, BE, TP/SL update, cancel, or partial action |
| `TradeExecutor.execute_manual_close()` | `backend/core/trade_executor.py` | Performs a user-triggered manual close |
| `TradeExecutor.execute_manual_breakeven()` | `backend/core/trade_executor.py` | Performs a user-triggered move-to-breakeven |
| `TradeExecutor.execute_manual_partial()` | `backend/core/trade_executor.py` | Performs a user-triggered partial close |
| `AccountManager.add_credential()` | `backend/core/account_manager.py` | Discovers sub-accounts and creates a dedicated TradeLocker client for each |
| `AccountManager.get_client_for_account()` | `backend/core/account_manager.py` | Returns the runtime broker client for a specific account |

### 10.3 Risk And Protection

| Symbol | Location | Role |
| --- | --- | --- |
| `RiskEnforcer.start_breach_monitoring()` | `backend/risk/enforcer.py` | Starts the periodic background breach-check loop |
| `RiskEnforcer.validate_trade()` | `backend/risk/enforcer.py` | Verifies concurrent-trade, combined-risk, daily-room, and overall-room constraints |
| `RiskEnforcer.check_risk_limits()` | `backend/risk/enforcer.py` | Detects breaches and triggers protective follow-up |

### 10.4 Persistence And Realtime

| Symbol | Location | Role |
| --- | --- | --- |
| `DatabaseManager.connect()` | `backend/database/manager.py` | Opens the async PostgreSQL pool and initializes schema state |
| `DatabaseManager.get_all_accounts()` | `backend/database/manager.py` | Returns configured accounts for startup and UI flows |
| `DatabaseManager.is_channel_subscribed()` | `backend/database/manager.py` | Filters signal execution targets by subscription |
| `DatabaseManager.add_active_trade()` | `backend/database/manager.py` | Persists newly opened trades |
| `DatabaseManager.close_active_trade()` | `backend/database/manager.py` | Closes live trades and updates state |
| `DatabaseManager.get_trade_history()` | `backend/database/manager.py` | Provides trade-history data for the UI |
| `DatabaseManager.add_notification()` | `backend/database/manager.py` | Persists notification records |

### 10.5 Frontend Runtime

| Symbol | Location | Role |
| --- | --- | --- |
| `Route` | `Lovable Frontend/src/routes/__root.tsx` | Root route that defines metadata, providers, shell usage, and error/404 handling |
| `AuthProvider` | `Lovable Frontend/src/lib/mp/auth-context.tsx` | Tracks Firebase auth and backend approval/super-admin state |
| `useMirrorPupilWebSocket()` | `Lovable Frontend/src/lib/mp/ws.ts` | Connects to `/ws/updates` and invalidates React Query caches on live events |
| `AppShell` | `Lovable Frontend/src/components/mp/AppShell.tsx` | Shared operator shell with nav, status badges, and notifications entry point |
| `accountsApi`, `channelsApi`, `riskProfilesApi`, `tradesApi`, `notificationsApi`, `botApi`, `usersApi` | `Lovable Frontend/src/lib/mp/api.ts` | Typed frontend service boundary for backend routes |

## 11. Major Module Responsibilities

| Module | Responsibility | Main Dependencies |
| --- | --- | --- |
| `backend/api/main.py` | Composes the whole backend process | `DatabaseManager`, `TradeExecutor`, `RiskEnforcer`, monitors, `TelegramIntegration` |
| `backend/channels/registry.py` | Loads configured channel plugins and routes messages | `DatabaseManager`, `DynamicChannelPlugin`, `TradeExecutor` |
| `backend/channels/base.py` | Defines parser models and default routing behavior | channel-specific entry and management modules |
| `backend/core/trade_executor.py` | Orchestrates execution and management actions | `AccountManager`, `RiskEnforcer`, `DatabaseManager`, notification service |
| `backend/core/account_manager.py` | Maintains per-account broker clients | `TradeLockerClient` |
| `backend/core/tradelocker_client.py` | Wraps TradeLocker operations | TradeLocker SDK |
| `backend/risk/enforcer.py` | Enforces pre-trade and runtime risk rules | `RiskCalculator`, `DatabaseManager`, notification service |
| `backend/database/manager.py` | Data access for nearly all domains | `asyncpg`, schema, Pydantic models |
| `backend/telegram_integration.py` | Bridges Telegram into backend execution | `HumanLikeTelegramClient`, `ChannelRegistry` |
| `Lovable Frontend/src/routes/__root.tsx` | Global app composition and access gating | React Query, auth context, app shell |
| `Lovable Frontend/src/lib/mp/api.ts` | REST client, auth headers, mock layer, query keys | axios, browser session state |
| `Lovable Frontend/src/lib/mp/ws.ts` | Realtime connection and cache invalidation | browser WebSocket, React Query, notifications |
| `Lovable Frontend/src/components/mp/AppShell.tsx` | Shared authenticated layout | route state, bot API, notifications API, websocket hook |

## 12. Dependency Relationships

### 12.1 Backend Dependency Graph

```text
FastAPI app
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
     -> HumanLikeTelegramClient
     -> ChannelRegistry
  -> Background monitors
     -> DatabaseManager
     -> AccountManager / TradeExecutor / NotificationService
```

### 12.2 Frontend Dependency Graph

```text
TanStack route
  -> page component
  -> React Query
  -> api.ts domain client
  -> FastAPI REST endpoint

AppShell
  -> botApi.status()
  -> notificationsApi.list()
  -> useMirrorPupilWebSocket()

useMirrorPupilWebSocket()
  -> /ws/updates
  -> React Query cache invalidation
  -> toast notifications
```

### 12.3 Auth Relationship

```text
Firebase Auth
  -> frontend auth-context
  -> token stored in session
  -> axios Authorization header
  -> backend /api/users/me and protected routes
  -> approval and super-admin state
```

## 13. End-To-End Runtime Flows

### 13.1 Signal Execution Flow

1. A Telegram signal message arrives.
2. `telegram_client.py` receives it through TDLib.
3. `TelegramIntegration` passes it to `ChannelRegistry`.
4. The matching plugin parses it into `ParsedSignal`, `ParsedManagement`, or waiting-room state.
5. `TradeExecutor.execute_signal()` checks bot state and trading hours.
6. Subscribed, unpaused, non-breached accounts are selected.
7. `RiskEnforcer.validate_trade()` validates per-account safety.
8. `AccountManager` provides the correct TradeLocker client.
9. `TradeLockerClient` places the order.
10. `DatabaseManager` persists active-trade state and related changes.
11. `NotificationService` emits notifications.
12. Web clients update through REST polling plus websocket invalidation.

### 13.2 Management Flow

1. A Telegram management message or UI manual action targets an existing trade.
2. The backend resolves the affected trade(s) and account(s).
3. `TradeExecutor.execute_management()` or a manual execution helper applies the action.
4. Database state is updated.
5. Notifications and websocket events push the result to clients.

### 13.3 Frontend Data Flow

1. Page components call domain APIs from `src/lib/mp/api.ts`.
2. The axios client attaches the stored auth token.
3. Responses populate React Query caches.
4. `useMirrorPupilWebSocket()` invalidates affected caches when live backend events arrive.
5. The UI re-renders from fresh query data.

## 14. Running The Project

### 14.1 Prerequisites

- Python 3.11+
- Node.js 18+ or newer
- PostgreSQL
- Telegram API credentials
- TradeLocker credentials
- Firebase project credentials if auth is enabled

### 14.2 Backend Setup

From the repository root:

```bash
pip install -r requirements.txt
```

Create `.env` from the template:

```bash
cp .env.example .env
```

Important backend environment variables:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_PHONE`
- `TDLIB_ENCRYPTION_KEY`
- `DATABASE_URL`
- `DRY_RUN`
- `DEFAULT_LOT_SIZE`
- `API_HOST`
- `API_PORT`
- `FIREBASE_SERVICE_ACCOUNT_KEY`
- `AUTH_DISABLED`
- `SUPER_ADMIN_EMAIL`
- `ENCRYPTION_KEY`

Start the backend with either:

```bash
uvicorn backend.api.main:app --reload --port 8000
```

or:

```bash
python run_backend.py
```

Useful URLs:

- `http://localhost:8000/`
- `http://localhost:8000/health`
- `http://localhost:8000/docs`

### 14.3 Frontend Setup

The actual frontend directory in this repository is `Lovable Frontend/`.

```bash
cd "Lovable Frontend"
npm install
npm run dev
```

Frontend environment variables come from `Lovable Frontend/.env.example`:

- `VITE_API_URL`
- `VITE_WS_URL`
- `VITE_USE_MOCK`

Common frontend commands:

```bash
npm run build
npm run preview
npm run lint
npm run format
```

Notes:

- `VITE_USE_MOCK=true` makes the UI use in-memory mock data instead of the real backend
- default local endpoints are `http://localhost:8000` and `ws://localhost:8000`

### 14.4 Mobile Export Setup

If you are working with the exported mobile package:

```bash
cd "Lovable Frontend/export/mobile"
flutter pub get
flutter run --dart-define=API_BASE_URL=http://localhost:8000 --dart-define=WS_BASE_URL=ws://localhost:8000
```

Use this cautiously: the current checkout contains mobile export/config files, but not the `lib/` Dart sources described in the mobile README.

## 15. Build, Test, And Validation

### 15.1 Backend Tests

The repository contains root-level Python test files such as:

- `test_auth_setup.py`
- `test_comprehensive_system.py`
- `test_database.py`
- `test_parsers.py`
- `test_risk.py`
- `test_tradelocker.py`

Run them from the repository root:

```bash
pytest
```

Important caution:

Some tests appear integration-oriented and may require real services, valid credentials, database access, or live TradeLocker connectivity. `test_comprehensive_system.py` is clearly a live system validation script, not a lightweight unit test.

### 15.2 Frontend Validation

```bash
cd "Lovable Frontend"
npm run lint
npm run build
```

### 15.3 Docker

No `Dockerfile`, `docker-compose.yml`, `compose.yaml`, or related Docker setup was found in the current repository.

## 16. External Dependencies

### 16.1 Backend

Notable Python dependencies from `requirements.txt`:

- `pytdbot[tdjson]`
- `tradelocker`
- `asyncpg`
- `psycopg2-binary`
- `sqlalchemy`
- `fastapi`
- `uvicorn[standard]`
- `websockets`
- `aiohttp`
- `httpx`
- `python-dotenv`
- `pydantic`
- `cryptography`
- `loguru`
- `pandas`
- `pytest`
- `pytest-asyncio`

### 16.2 Frontend

Notable web dependencies from `Lovable Frontend/package.json`:

- `react`
- `react-dom`
- `@tanstack/react-query`
- `@tanstack/react-router`
- `@tanstack/react-start`
- `axios`
- `firebase`
- `tailwindcss`
- `@tailwindcss/vite`
- `@radix-ui/*`
- `zod`
- `vite`
- `typescript`

## 17. Notable Repository Observations

- The root `README.md` still uses `frontend/` in some examples, but the actual directory name in this checkout is `Lovable Frontend/`.
- The existing web app is current and fully represented in source.
- The mobile export README describes a richer Flutter source tree than is currently present in the repository.
- `DatabaseManager` is intentionally broad and central, which simplifies orchestration but increases coupling.
- Real-time updates are additive rather than standalone: the frontend still depends on regular API fetches, with WebSocket events mostly used to invalidate cached queries.

## 18. Where To Start Reading

If you are onboarding to the codebase, this order gives the fastest architectural understanding:

1. `backend/api/main.py`
2. `backend/telegram_integration.py`
3. `backend/channels/base.py`
4. `backend/channels/registry.py`
5. `backend/core/trade_executor.py`
6. `backend/database/models.py`
7. `backend/database/manager.py`
8. `backend/risk/enforcer.py`
9. `Lovable Frontend/src/routes/__root.tsx`
10. `Lovable Frontend/src/lib/mp/api.ts`
11. `Lovable Frontend/src/lib/mp/ws.ts`
12. `Lovable Frontend/src/components/mp/AppShell.tsx`

This path follows the real runtime flow from external signal ingestion to execution, persistence, and operator UI.
