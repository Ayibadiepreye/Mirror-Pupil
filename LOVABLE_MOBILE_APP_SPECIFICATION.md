# Mirror Pupil Mobile App - Complete Specification for Lovable

**Version**: 5.1.0  
**Date**: June 10, 2026  
**Platform**: React Native (iOS & Android)  
**Backend API**: FastAPI REST + WebSocket  

---

## 📋 TABLE OF CONTENTS

1. [Environment Configuration](#1-environment-configuration)
2. [Firebase Authentication](#2-firebase-authentication)
3. [API Integration](#3-api-integration)
4. [WebSocket Real-time Updates](#4-websocket-real-time-updates)
5. [Data Models & TypeScript Types](#5-data-models--typescript-types)
6. [User Interface Pages](#6-user-interface-pages)
7. [Multi-User Isolation](#7-multi-user-isolation)
8. [Push Notifications](#8-push-notifications)
9. [Offline Support](#9-offline-support)
10. [Theme & Styling](#10-theme--styling)

---

## 1. ENVIRONMENT CONFIGURATION

### 1.1 Required Environment Variables

Create `.env` file in mobile project root:

```env
# Backend API URLs
API_BASE_URL=https://your-backend-domain.com
WS_BASE_URL=wss://your-backend-domain.com

# Firebase Configuration (from Firebase Console)
FIREBASE_API_KEY=AIzaSyAjxKQJFeRdFwHMYybKcNer5QQHp2nVUz8
FIREBASE_AUTH_DOMAIN=mirror-pupil.firebaseapp.com
FIREBASE_PROJECT_ID=mirror-pupil
FIREBASE_STORAGE_BUCKET=mirror-pupil.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=2009963821
FIREBASE_APP_ID=1:2009963821:web:d1dc6133ae10a1fc8747a4
FIREBASE_MEASUREMENT_ID=G-GNS6TYCQCX

# Mock Mode (for development only - MUST be false in production)
USE_MOCK_DATA=false
```

### 1.2 Firebase Project Configuration

**Project Details**:
- **Project ID**: `mirror-pupil`
- **Project Name**: Mirror Pupil
- **Authentication Methods Enabled**:
  - ✅ Email/Password
  - ✅ Google Sign-In
  - **Service Account**: Used by backend for token verification
  - **Key Location**: Backend has `serviceAccountKey.json`

**Important Notes**:
- Firebase handles JWT token generation
- Backend verifies JWT tokens using Firebase Admin SDK
- Tokens expire after 1 hour (auto-refreshed by Firebase client)
- User creation requires backend approval (super admin must approve new users)

---

## 2. FIREBASE AUTHENTICATION

### 2.1 Authentication Flow

```
User Opens App
    ↓
[Check Local Session] → Session exists?
    ↓ NO                     ↓ YES
[Show Login Page]      [Load Dashboard]
    ↓
User chooses:
  • Email/Password
  • Google Sign-In
    ↓
[Firebase Authentication]
    ↓
Success → Get JWT Token
    ↓
[Store Session Locally]
    {
      token: "firebase-jwt-token",
      email: "user@example.com",
      displayName: "User Name",
      provider: "google" | "password"
    }
    ↓
[Attach Token to All API Requests]
    Header: Authorization: Bearer <token>
    ↓
[Backend Verifies Token]
    ↓
Success → [Load User Data]
```

### 2.2 Auth Implementation (React Native)

**Dependencies**:
```json
{
  "@react-native-firebase/app": "^18.x",
  "@react-native-firebase/auth": "^18.x",
  "@react-native-google-signin/google-signin": "^10.x",
  "@react-native-async-storage/async-storage": "^1.x"
}
```

**Auth Service** (`src/services/auth.ts`):
```typescript
import auth from '@react-native-firebase/auth';
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SESSION_KEY = "mp.session.v1";

export interface MpSession {
  token: string;
  email: string;
  displayName: string;
  provider: "google" | "password";
}

// Initialize Google Sign-In
GoogleSignin.configure({
  webClientId: '2009963821-web-client-id.apps.googleusercontent.com', // From Firebase Console
});

export async function getSession(): Promise<MpSession | null> {
  try {
    const raw = await AsyncStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export async function signInWithPassword(email: string, password: string): Promise<MpSession> {
  const userCredential = await auth().signInWithEmailAndPassword(email, password);
  const token = await userCredential.user.getIdToken();
  
  const session: MpSession = {
    token,
    email: userCredential.user.email!,
    displayName: userCredential.user.displayName || email.split("@")[0],
    provider: "password",
  };
  
  await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export async function signInWithGoogle(): Promise<MpSession> {
  const { idToken } = await GoogleSignin.signIn();
  const googleCredential = auth.GoogleAuthProvider.credential(idToken);
  const userCredential = await auth().signInWithCredential(googleCredential);
  const token = await userCredential.user.getIdToken();
  
  const session: MpSession = {
    token,
    email: userCredential.user.email!,
    displayName: userCredential.user.displayName || "",
    provider: "google",
  };
  
  await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export async function signOut() {
  await auth().signOut();
  await AsyncStorage.removeItem(SESSION_KEY);
}

export async function refreshToken(): Promise<string | null> {
  const user = auth().currentUser;
  if (!user) return null;
  
  const token = await user.getIdToken(true);
  const session = await getSession();
  if (session) {
    session.token = token;
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }
  return token;
}
```

---

## 3. API INTEGRATION

### 3.1 Base API Client

**Dependencies**:
```json
{
  "axios": "^1.6.x",
  "@tanstack/react-query": "^5.x"
}
```

**API Client** (`src/services/api.ts`):
```typescript
import axios, { AxiosInstance } from 'axios';
import { getSession, refreshToken } from './auth';
import Config from 'react-native-config';

const API_BASE_URL = Config.API_BASE_URL || 'http://localhost:8000';

const httpClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor - attach JWT token
httpClient.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.token) {
    config.headers.Authorization = `Bearer ${session.token}`;
  }
  return config;
});

// Response interceptor - handle 401 errors
httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const newToken = await refreshToken();
      if (newToken) {
        // Retry original request with new token
        error.config.headers.Authorization = `Bearer ${newToken}`;
        return httpClient(error.config);
      }
      // Token refresh failed - redirect to login
      // Navigation.navigate('Login');
    }
    return Promise.reject(error);
  }
);

export default httpClient;
```

### 3.2 API Endpoints

All endpoints require `Authorization: Bearer <firebase-jwt-token>` header.


#### **Accounts API**

```typescript
// GET /api/accounts/ - Get all accounts for current user
interface AccountResponse {
  account_key: string;
  credential_key: string;
  tl_account_id: string;
  tl_email: string;
  tl_server: string;
  display_name: string | null;
  initial_balance: number;
  current_balance: number;
  highest_banked_balance: number;
  profit_locked: boolean;
  daily_pnl: number;
  daily_start_balance: number;
  paused: boolean;
  breached: boolean;
  risk_profile_id: number | null;
  // NEW FIELDS (v5.1)
  daily_drawdown_pct: number;
  daily_loss_limit_pct: number;
  overall_drawdown_pct: number;
  overall_loss_limit_pct: number;
  consistency_score: number | null;
  profitable_days_count: number;
  total_trading_days: number;
  required_profitable_days: number;
}

// GET /api/accounts/{account_key} - Get specific account
// POST /api/accounts/ - Create new account
// PUT /api/accounts/{account_key} - Update account
// DELETE /api/accounts/{account_key} - Delete account
// POST /api/accounts/{account_key}/pause - Pause account
// POST /api/accounts/{account_key}/resume - Resume account
// POST /api/accounts/discover - Discover TradeLocker accounts
// POST /api/accounts/bulk-add - Add multiple accounts
```

#### **Active Trades API**

```typescript
// GET /api/trades/active - Get all active trades for user
interface ActiveTradeResponse {
  trade_id: number;
  account_key: string;
  channel_id: number;
  channel_name: string | null;
  signal_id: string;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  sl: number | null;
  tp: number | null;
  lot_size: number;
  entry_time: string; // ISO 8601
  tl_position_id: string | null;
  status: string;
  tp1_hit: boolean;
  risk_usd: number | null;
  current_pnl: number | null; // LIVE P&L (updated real-time)
}

// POST /api/trades/active/{trade_id}/close - Close trade
// POST /api/trades/active/{trade_id}/breakeven - Set SL to breakeven
// POST /api/trades/active/{trade_id}/partial - Partial close (25%, 50%, 75%)
```

#### **Trade History API**

```typescript
// GET /api/trades/history - Get trade history
interface TradeHistoryResponse {
  history_id: number;
  account_key: string;
  channel_name: string | null;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  exit_price: number;
  lot_size: number;
  entry_time: string;
  exit_time: string;
  pnl: number;
  outcome: "WIN" | "LOSS" | "BE";
  close_reason: string;
}

// GET /api/trades/history/export - Export CSV
```

#### **Notifications API**

```typescript
// GET /api/notifications/ - Get notifications
// Query Parameters:
//   - account_key?: string (optional - filter by account)
//   - unread_only?: boolean (optional - default false)
//   - limit?: number (optional - default 100, max 1000)
// Example: GET /api/notifications/?unread_only=true&limit=50

interface NotificationResponse {
  notification_id: number;
  account_key: string | null;
  category: "SIGNAL" | "EXECUTION" | "MANAGEMENT" | "BREACH" | "SYSTEM";
  severity: "CRITICAL" | "ERROR" | "WARNING" | "INFO";
  title: string;
  message: string;
  metadata: object | null;
  read: boolean;
  created_at: string;
}

// API Client Implementation:
export const notificationsApi = {
  list: (params?: { account_key?: string; unread_only?: boolean; limit?: number }) =>
    httpClient.get<NotificationResponse[]>('/api/notifications/', { params }).then(r => r.data),
  
  markRead: (id: number) =>
    httpClient.patch(`/api/notifications/${id}/read`).then(r => r.data),
  
  markAllRead: (account_key?: string) =>
    httpClient.post('/api/notifications/mark-all-read', null, { params: { account_key } }).then(r => r.data),
  
  delete: (id: number) =>
    httpClient.delete(`/api/notifications/${id}`).then(r => r.data),
};

// PATCH /api/notifications/{id}/read - Mark as read
// POST /api/notifications/mark-all-read - Mark all as read (optional account_key param)
// DELETE /api/notifications/{id} - Delete notification
```

#### **Bot Control API**

```typescript
// GET /api/bot/status - Get bot status
interface BotStatusResponse {
  status: "running" | "stopped";
  dry_run: boolean;
  active_accounts: number;
  paused_accounts: number;
  breached_accounts: number;
  total_active_trades: number;
  allow_weekend_trading: boolean;
  allow_eod_trading: boolean;
}

// POST /api/bot/control - Start/stop bot
// POST /api/bot/force-close-all - Emergency close all trades
// POST /api/bot/force-close-account/{account_key} - Close trades for account
```

#### **Users API**

```typescript
// GET /api/users/me - Get current user profile
interface UserProfile {
  user_id: string;
  email: string;
  display_name: string;
  is_super_admin: boolean;
  approved: boolean;
  created_at: string;
}

// GET /api/users/pending - Get pending users (super admin only)
// GET /api/users/all - Get all users (super admin only)
// POST /api/users/{user_id}/approve - Approve user (super admin only)
```

---

## 4. WEBSOCKET REAL-TIME UPDATES

### 4.1 WebSocket Connection

**Endpoint**: `wss://your-backend-domain.com/ws/updates`

**Connection Flow**:
```typescript
import { useEffect, useRef, useState } from 'react';
import Config from 'react-native-config';

const WS_BASE_URL = Config.WS_BASE_URL || 'ws://localhost:8000';

export function useWebSocket() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const attemptsRef = useRef(0);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`${WS_BASE_URL}/ws/updates`);
      wsRef.current = ws;

      ws.onopen = () => {
        attemptsRef.current = 0;
        setStatus('connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
      };

      ws.onclose = () => {
        setStatus('disconnected');
        if (attemptsRef.current < 5) {
          const delay = 1000 * Math.pow(2, attemptsRef.current);
          attemptsRef.current += 1;
          setTimeout(connect, delay);
        }
      };
    };

    connect();

    return () => {
      wsRef.current?.close();
    };
  }, []);

  return status;
}
```

### 4.2 Message Types

```typescript
type WebSocketMessage =
  | { type: "connection"; status: string; message: string; timestamp: string }
  | { type: "trade"; data: ActiveTrade; timestamp: string }
  | { type: "balance"; data: { account_key: string; balance: number; pnl: number }; timestamp: string }
  | { type: "notification"; data: Notification; timestamp: string };
```

**Handling Messages**:
- `type: "connection"` → Connection established
- `type: "trade"` → New trade opened/closed → **Refresh active trades list**
- `type: "balance"` → Balance updated → **Refresh account balances**
- `type: "notification"` → New notification → **Show push notification + refresh notifications**

---

## 5. DATA MODELS & TYPESCRIPT TYPES

**Complete Types File** (`src/types/mirror-pupil.ts`):

```typescript
export interface Account {
  account_key: string;
  credential_key: string;
  tl_account_id: string;
  tl_email: string;
  tl_server: string;
  tl_prop_firm: string;
  display_name: string | null;
  initial_balance: number;
  current_balance: number;
  highest_banked_balance: number;
  all_time_high_equity: number | null;
  profit_locked: boolean;
  daily_pnl: number;
  daily_start_balance: number;
  last_synced_balance: number;
  cycle_start_date: string | null;
  cycle_best_day_pnl: number;
  paused: boolean;
  breached: boolean;
  risk_profile_id: number | null;
  max_concurrent_trades_override: number | null;
  lot_size_override: number | null;
  // NEW in v5.1
  daily_drawdown_pct: number;
  daily_loss_limit_pct: number;
  overall_drawdown_pct: number;
  overall_loss_limit_pct: number;
  consistency_score: number | null;
  profitable_days_count: number;
  total_trading_days: number;
  required_profitable_days: number;
}

export interface ActiveTrade {
  trade_id: number;
  account_key: string;
  channel_id: number;
  channel_name: string | null;
  signal_id: string;
  sub_signal_id: string | null;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  sl: number | null;
  tp: number | null;
  lot_size: number;
  entry_time: string;
  tl_order_id: string | null;
  tl_position_id: string | null;
  status: string;
  tp1_hit: boolean;
  risk_usd: number | null;
  current_pnl: number | null; // LIVE P&L
}

export interface TradeHistory {
  history_id: number;
  account_key: string;
  channel_id: number;
  channel_name: string | null;
  signal_id: string;
  sub_signal_id: string | null;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  exit_price: number;
  sl: number | null;
  tp: number | null;
  lot_size: number;
  entry_time: string;
  exit_time: string;
  pnl: number;
  outcome: "WIN" | "LOSS" | "BE";
  close_reason: string;
  manual_action_type: "CLOSE" | "BREAKEVEN" | "PARTIAL" | null;
}

export interface Notification {
  notification_id: number;
  account_key: string | null;
  category: "SIGNAL" | "EXECUTION" | "MANAGEMENT" | "BREACH" | "SYSTEM";
  severity: "CRITICAL" | "ERROR" | "WARNING" | "INFO";
  title: string;
  message: string;
  metadata: unknown;
  read: boolean;
  created_at: string;
}

export interface Channel {
  channel_id: number;
  display_name: string;
  signal_prefix: string;
  entry_logic_module: string;
  management_logic_module: string;
  priority: number;
  enabled: boolean;
  notes: string | null;
}

export interface RiskProfile {
  profile_id: number;
  profile_name: string;
  is_default: boolean;
  max_risk_per_trade_pct: number;
  daily_loss_pct: number;
  daily_trailing: boolean;
  overall_loss_pct: number;
  overall_trailing: boolean;
  overall_trail_from_closed_balance: boolean;
  profit_lock_pct: number | null;
  profit_lock_floor_pct: number | null;
  payout_buffer_pct: number;
  max_concurrent_trades: number;
  commission_per_lot: number;
  safety_buffer_pct: number;
  notes: string | null;
}

export interface BotStatus {
  status: "running" | "stopped";
  dry_run: boolean;
  active_accounts: number;
  paused_accounts: number;
  breached_accounts: number;
  total_active_trades: number;
  allow_weekend_trading: boolean;
  allow_eod_trading: boolean;
}

export interface UserProfile {
  user_id: string;
  email: string;
  display_name: string;
  is_super_admin: boolean;
  approved: boolean;
  created_at: string;
}
```

---

## 6. USER INTERFACE PAGES

### 6.1 Login Page

**Route**: `/login`  
**Auth Required**: ❌ No

**Layout**:
```
┌─────────────────────────────────┐
│      Mirror Pupil Logo          │
│                                 │
│  Email: [_______________]       │
│  Password: [_______________]    │
│  [Sign In with Email]           │
│                                 │
│  ─────── OR ───────            │
│                                 │
│  [🔵 Sign in with Google]       │
│                                 │
│  New user? Contact admin        │
│  for approval                   │
└─────────────────────────────────┘
```

**Features**:
- Email/password authentication
- Google Sign-In button
- Remember session (stored in AsyncStorage)
- Error messages for invalid credentials
- Link to admin contact for new user approval

---

### 6.2 Dashboard Page

**Route**: `/dashboard`  
**Auth Required**: ✅ Yes

**Layout**:
```
┌─────────────────────────────────┐
│ Dashboard            [Profile🔽] │
├─────────────────────────────────┤
│ 📊 Account Summary              │
│ ┌──────┐ ┌──────┐ ┌──────┐     │
│ │Total │ │Active│ │Daily │     │
│ │Balance│ │Trades│ │ P&L  │     │
│ │$50.2K │ │  5  │ │+$347 │     │
│ └──────┘ └──────┘ └──────┘     │
│                                 │
│ 📈 Quick Actions                │
│ [View Accounts] [Active Trades] │
│ [History] [Notifications]       │
│                                 │
│ 🔔 Recent Notifications (3)     │
│ • Trade opened: XAUUSD          │
│ • Balance updated: +$120        │
│ • Warning: Daily drawdown 4.2%  │
│ [View All]                      │
└─────────────────────────────────┘
```

**Data Sources**:
- `GET /api/accounts/` → Total balance, account count
- `GET /api/trades/active` → Active trades count
- `GET /api/notifications/?limit=5` → Recent notifications
- WebSocket → Real-time updates

---

### 6.3 Accounts Page

**Route**: `/accounts`  
**Auth Required**: ✅ Yes

**Layout**:
```
┌─────────────────────────────────┐
│ Accounts         [+ Add Account] │
├─────────────────────────────────┤
│ [Search...] [Filter: All ▾]     │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Account 123456     [●Active]│ │
│ │ user@gmail.com              │ │
│ │ Balance: $10,147.15         │ │
│ │ Daily P&L: +$147.15 (1.47%) │ │
│ │                             │ │
│ │ Daily Drawdown              │ │
│ │ ▓▓░░░░░░░░ 0.0% / 5.0%     │ │
│ │                             │ │
│ │ Max Drawdown                │ │
│ │ ▓▓░░░░░░░░ 0.0% / 10.0%    │ │
│ │                             │ │
│ │ Consistency Score: 18.2%    │ │
│ │ Profitable Days: 15 / 5     │ │
│ │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100%        │ │
│ │                             │ │
│ │ [⏸Pause] [✏Edit] [🗑Delete] │ │
│ └─────────────────────────────┘ │
│                                 │
│ (Repeat for each account...)    │
└─────────────────────────────────┘
```

**NEW FEATURES (v5.1)**:
1. **Daily Drawdown Progress Bar**
   - Shows: `{current_drawdown}% / {limit}%`
   - Color: Green (<70%), Yellow (70-90%), Red (>90%)

2. **Max Drawdown Progress Bar**
   - Shows: `{overall_drawdown}% / {limit}%`
   - Color: Same as daily

3. **Consistency Score**
   - Shows: `{score}%` or "N/A"
   - Color: Green (<18%), Yellow (18-20%), Red (≥20%)

4. **Profitable Days Counter**
   - Shows: `{count} / {required}` with progress bar
   - Example: "15 / 5" (exceeds requirement)

**Data Source**: `GET /api/accounts/`

**Actions**:
- **Add Account**: Opens dialog to discover/manually add TradeLocker accounts
- **Pause**: Stops opening new trades (existing trades continue)
- **Resume**: Re-enables trading
- **Edit**: Modify display name, lot size override, risk profile, max trades
- **Delete**: Remove account (with confirmation)

---

### 6.4 Active Trades Page

**Route**: `/trades/active`  
**Auth Required**: ✅ Yes

**Layout**:
```
┌─────────────────────────────────┐
│ Active Trades (5)     [🔴 LIVE] │
├─────────────────────────────────┤
│ [All Accounts ▾] [Symbol...] [⚙]│
│                                 │
│ ┌─────────────────────────────┐ │
│ │ XAUUSD 📈 BUY               │ │
│ │ Account: 123456             │ │
│ │ Entry: 2650.20              │ │
│ │ SL: 2640.00 | TP: 2670.00   │ │
│ │ Lots: 0.09                  │ │
│ │ P&L: +$177.80 (+1.75%)      │ │ ← LIVE UPDATING
│ │ Time: 2h 15m ago            │ │
│ │                             │ │
│ │ [⚡Close] [↔️BE] [✂️Partial▾] │ │
│ └─────────────────────────────┘ │
│                                 │
│ (Repeat for each trade...)      │
└─────────────────────────────────┘
```

**NEW FEATURE (v5.1): LIVE P&L**
- `current_pnl` field updates every 5 seconds via polling
- WebSocket pushes instant updates on significant changes
- Shows: `+$177.80 (+1.75%)` with color coding:
  - Green: Positive P&L
  - Red: Negative P&L
  - Gray: Breakeven

**Data Source**: 
- `GET /api/trades/active` (polling every 5s when WebSocket disconnected)
- WebSocket `type: "trade"` → Instant updates

**Actions**:
- **Close**: Full position close → Confirmation dialog
- **Breakeven (BE)**: Move SL to entry price → Confirmation
- **Partial**: Dropdown menu:
  - Close 25%
  - Close 50%
  - Close 75%
  Each requires confirmation

**Filters**:
- Account selector (dropdown)
- Symbol search (text input)
- Sort: Newest first, By symbol, By lot size

---

### 6.5 Trade History Page

**Route**: `/trades/history`  
**Auth Required**: ✅ Yes

**Layout**:
```
┌─────────────────────────────────┐
│ Trade History     [📥 Export CSV]│
├─────────────────────────────────┤
│ [All Accounts ▾] [Date Range ▾] │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ ✅ XAUUSD BUY              │ │
│ │ Entry: 2650.20 → Exit: 2670.50│
│ │ P&L: +$91.35               │ │
│ │ Lots: 0.045                │ │
│ │ Opened: Jun 10, 09:15      │ │
│ │ Closed: Jun 10, 11:20      │ │
│ │ Reason: TP1_HIT            │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ ❌ EURUSD SELL             │ │
│ │ Entry: 1.0850 → Exit: 1.0860│
│ │ P&L: -$45.00               │ │
│ │ Lots: 0.1                  │ │
│ │ Opened: Jun 9, 14:30       │ │
│ │ Closed: Jun 9, 15:45       │ │
│ │ Reason: SL_HIT             │ │
│ └─────────────────────────────┘ │
│                                 │
│ [Load More]                     │
└─────────────────────────────────┘
```

**Data Source**: `GET /api/trades/history`

**Features**:
- Pagination (50 records per page)
- Filter by account
- Date range filter
- Win/Loss indicators (✅/❌)
- P&L color coding
- Export to CSV button

**CSV Export**: `GET /api/trades/history/export?account_key={key}`

---

### 6.6 Notifications Page

**Route**: `/notifications`  
**Auth Required**: ✅ Yes

**Layout**:
```
┌─────────────────────────────────┐
│ Notifications   [Mark All Read] │
├─────────────────────────────────┤
│ [All ▾] [Unread ▾] [Filter...] │
│                                 │
│ ┌─────────────────────────────┐ │
│ │🔴 CRITICAL                  │ │
│ │ Account Breached            │ │
│ │ Account 123456 breached     │ │
│ │ daily loss limit            │ │
│ │ 5 min ago          [✓ Read] │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ℹ️ INFO                     │ │
│ │ Trade Opened                │ │
│ │ XAUUSD BUY 0.09 lots @      │ │
│ │ 2650.20                     │ │
│ │ 2h ago             [✓ Read] │ │
│ └─────────────────────────────┘ │
│                                 │
│ (More notifications...)         │
└─────────────────────────────────┘
```

**Data Source**: 
- `GET /api/notifications/` (polling every 30s)
- WebSocket `type: "notification"` → Instant delivery

**Severity Colors**:
- 🔴 CRITICAL: Red background
- ⚠️ ERROR: Orange background
- ⚠️ WARNING: Yellow background
- ℹ️ INFO: Blue background

**Actions**:
- Mark individual as read: `PATCH /api/notifications/{id}/read`
- Mark all as read: `POST /api/notifications/mark-all-read`
- Delete: `DELETE /api/notifications/{id}`

**Categories**:
- SIGNAL: New signal received
- EXECUTION: Trade opened/closed
- MANAGEMENT: Manual action (BE, partial, close)
- BREACH: Risk limit breached
- SYSTEM: Bot status, errors

---

### 6.7 Bot Control Page

**Route**: `/bot/control`  
**Auth Required**: ✅ Yes (Super Admin Only)

**Layout**:
```
┌─────────────────────────────────┐
│ Bot Control        [⚙️ Settings] │
├─────────────────────────────────┤
│ Status: 🟢 RUNNING              │
│ Mode: LIVE (Dry-Run: OFF)       │
│                                 │
│ 📊 Statistics                   │
│ Active Accounts: 12             │
│ Paused Accounts: 3              │
│ Breached Accounts: 1            │
│ Total Active Trades: 27         │
│                                 │
│ ⚙️ Controls                     │
│ [⏸️ Stop Bot] [🔄 Restart]      │
│                                 │
│ 🚨 Emergency Actions            │
│ [⚠️ Force Close All Trades]     │
│ [⚠️ Force Close Account...]     │
│                                 │
│ 🛡️ Trading Hours               │
│ Weekend Trading: OFF            │
│ EOD Trading: OFF                │
│                                 │
│ Next Trading Window:            │
│ Monday 1:00 AM EST              │
└─────────────────────────────────┘
```

**Data Source**: `GET /api/bot/status`

**Actions**:
- **Start/Stop Bot**: `POST /api/bot/control` with `{"action": "start|stop"}`
- **Force Close All**: `POST /api/bot/force-close-all` (requires double confirmation)
- **Force Close Account**: `POST /api/bot/force-close-account/{account_key}`

**Access Control**:
- Only visible to super admin users
- Regular users redirected to dashboard

---

### 6.8 Settings Page

**Route**: `/settings`  
**Auth Required**: ✅ Yes

**Layout**:
```
┌─────────────────────────────────┐
│ Settings                        │
├─────────────────────────────────┤
│ 👤 Profile                      │
│ Email: user@gmail.com           │
│ Display Name: User Name         │
│ [Edit Profile]                  │
│                                 │
│ 🔔 Notifications                │
│ Push Notifications: ON          │
│ Email Notifications: OFF        │
│ [Manage Preferences]            │
│                                 │
│ 🎨 Appearance                   │
│ Theme: Dark                     │
│ [Change Theme]                  │
│                                 │
│ 🔒 Security                     │
│ [Change Password]               │
│ [Enable 2FA]                    │
│                                 │
│ ℹ️ About                        │
│ Version: 5.1.0                  │
│ Backend: Connected              │
│ [Privacy Policy] [Terms]        │
│                                 │
│ 🚪 [Sign Out]                   │
└─────────────────────────────────┘
```

**Features**:
- Profile management
- Push notification settings
- Theme switcher (Light/Dark/System)
- Password change (Firebase)
- Sign out button

---

## 7. MULTI-USER ISOLATION

### 7.1 Data Isolation Rules

**CRITICAL**: All API endpoints filter data by authenticated user's `user_id`.

**Backend Implementation**:
```python
# Every endpoint dependency
from ...core.firebase_auth import get_current_user

@router.get("/api/accounts/")
async def get_accounts(user: dict = Depends(get_current_user)):
    user_id = user['user_id']
    is_super_admin = user.get('is_super_admin', False)
    
    # Super admin sees ALL accounts
    if is_super_admin:
        return await db.get_all_accounts()
    
    # Regular user sees ONLY their accounts
    return await db.get_accounts_by_user(user_id)
```

**What Each User Sees**:
- **Regular User**:
  - ✅ Only their own accounts
  - ✅ Only trades from their accounts
  - ✅ Only notifications for their accounts
  - ❌ Cannot see other users' data
  - ❌ Cannot access bot control page

- **Super Admin**:
  - ✅ ALL accounts (all users)
  - ✅ ALL trades
  - ✅ ALL notifications
  - ✅ Bot control page access
  - ✅ User management (approve new users)

### 7.2 Shared Resources

**Telegram Channels**: All users see signals from enabled channels  
**Risk Profiles**: Shared across all users  
**Trading Hours**: Global settings affect all users

---

## 8. PUSH NOTIFICATIONS

### 8.1 Firebase Cloud Messaging (FCM)

**Dependencies**:
```json
{
  "@react-native-firebase/messaging": "^18.x",
  "@notifee/react-native": "^7.x"
}
```

### 8.2 Notification Categories

**Severity-Based Display**:
- **CRITICAL** (Red): Account breached, forced closure
  - Sound: Loud alert
  - Vibration: Long pattern
  - Priority: High
  
- **ERROR** (Orange): Trade execution failed, API errors
  - Sound: Alert tone
  - Vibration: Medium pattern
  - Priority: High

- **WARNING** (Yellow): Approaching risk limits, withdrawals detected
  - Sound: Soft beep
  - Vibration: Short pattern
  - Priority: Normal

- **INFO** (Blue): Trade opened/closed, balance updates
  - Sound: Silent/subtle
  - Vibration: None
  - Priority: Low

### 8.3 Notification Handling

```typescript
import messaging from '@react-native-firebase/messaging';
import notifee from '@notifee/react-native';

// Request permission (iOS)
async function requestNotificationPermission() {
  const authStatus = await messaging().requestPermission();
  const enabled =
    authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
    authStatus === messaging.AuthorizationStatus.PROVISIONAL;
  
  if (enabled) {
    console.log('Notification permission granted');
  }
}

// Get FCM token
async function getFCMToken(): Promise<string> {
  const token = await messaging().getToken();
  // Send token to backend: POST /api/users/fcm-token
  return token;
}

// Handle foreground messages
messaging().onMessage(async remoteMessage => {
  const notification = remoteMessage.notification;
  const data = remoteMessage.data;
  
  // Display using notifee
  await notifee.displayNotification({
    title: notification?.title,
    body: notification?.body,
    data: data,
    android: {
      channelId: data?.severity || 'default',
      pressAction: {
        id: 'default',
        launchActivity: 'default',
      },
    },
    ios: {
      sound: data?.severity === 'CRITICAL' ? 'alarm.wav' : 'default',
    },
  });
});

// Handle background messages
messaging().setBackgroundMessageHandler(async remoteMessage => {
  console.log('Background message received:', remoteMessage);
});

// Handle notification tap
notifee.onForegroundEvent(({ type, detail }) => {
  if (type === EventType.PRESS) {
    // Navigate to relevant page based on notification data
    const { category } = detail.notification?.data || {};
    
    if (category === 'EXECUTION') {
      navigation.navigate('ActiveTrades');
    } else if (category === 'BREACH') {
      navigation.navigate('Accounts');
    }
  }
});
```

### 8.4 Notification Channels (Android)

Create notification channels on app init:

```typescript
import notifee, { AndroidImportance } from '@notifee/react-native';

async function createNotificationChannels() {
  await notifee.createChannel({
    id: 'CRITICAL',
    name: 'Critical Alerts',
    importance: AndroidImportance.HIGH,
    sound: 'alarm',
    vibration: true,
  });
  
  await notifee.createChannel({
    id: 'ERROR',
    name: 'Errors',
    importance: AndroidImportance.HIGH,
    sound: 'default',
    vibration: true,
  });
  
  await notifee.createChannel({
    id: 'WARNING',
    name: 'Warnings',
    importance: AndroidImportance.DEFAULT,
    sound: 'default',
  });
  
  await notifee.createChannel({
    id: 'INFO',
    name: 'Information',
    importance: AndroidImportance.LOW,
    sound: 'default',
  });
}
```

---

## 9. OFFLINE SUPPORT

### 9.1 React Query Caching

Use React Query for automatic caching and stale-while-revalidate:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: 2,
    },
  },
});

// Wrap app with provider
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NavigationContainer>
        {/* Your app */}
      </NavigationContainer>
    </QueryClientProvider>
  );
}
```

### 9.2 Offline Indicators

Show offline banner when disconnected:

```tsx
import NetInfo from '@react-native-community/netinfo';

function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(false);
  
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOffline(!state.isConnected);
    });
    
    return unsubscribe;
  }, []);
  
  if (!isOffline) return null;
  
  return (
    <View style={{ backgroundColor: '#ff6b6b', padding: 8 }}>
      <Text style={{ color: 'white', textAlign: 'center' }}>
        ⚠️ No internet connection - data may be stale
      </Text>
    </View>
  );
}
```

### 9.3 Cached Data Display

Display cached data with timestamp:

```tsx
function AccountsList() {
  const { data, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['accounts'],
    queryFn: fetchAccounts,
  });
  
  return (
    <View>
      {dataUpdatedAt && (
        <Text style={{ fontSize: 10, color: 'gray' }}>
          Last updated: {new Date(dataUpdatedAt).toLocaleTimeString()}
        </Text>
      )}
      
      {isLoading ? <Spinner /> : <AccountCards accounts={data} />}
    </View>
  );
}
```

---

## 10. THEME & STYLING

### 10.1 Color Palette

**Mirror Pupil Brand Colors**:
```typescript
export const Colors = {
  // Primary
  mpRed: '#E63946',        // Brand red
  mpRedDark: '#C62828',    // Darker red
  
  // Background
  mpBase: '#1A1A1A',       // Dark background
  mpSurface: '#2D2D2D',    // Card background
  mpBorder: '#404040',     // Border color
  
  // Text
  mpText: '#FFFFFF',       // Primary text
  mpTextDim: '#A0A0A0',    // Secondary text
  
  // Status
  mpSuccess: '#4CAF50',    // Green (profit, active)
  mpDanger: '#E63946',     // Red (loss, breach)
  mpWarning: '#FFC107',    // Yellow (warning)
  mpInfo: '#2196F3',       // Blue (info)
  
  // Charts
  mpGreen: '#26C281',      // Profit green
  mpGray: '#95A5A6',       // Neutral gray
};
```

### 10.2 Typography

```typescript
export const Typography = {
  heading1: {
    fontSize: 28,
    fontWeight: '700',
    color: Colors.mpText,
  },
  heading2: {
    fontSize: 22,
    fontWeight: '600',
    color: Colors.mpText,
  },
  heading3: {
    fontSize: 18,
    fontWeight: '600',
    color: Colors.mpText,
  },
  body: {
    fontSize: 14,
    fontWeight: '400',
    color: Colors.mpText,
  },
  caption: {
    fontSize: 12,
    fontWeight: '400',
    color: Colors.mpTextDim,
  },
  mono: {
    fontFamily: 'Courier',
    fontSize: 13,
    color: Colors.mpText,
  },
};
```

### 10.3 Component Styles

**Card Style**:
```typescript
const cardStyle = {
  backgroundColor: Colors.mpSurface,
  borderRadius: 12,
  padding: 16,
  marginVertical: 8,
  borderWidth: 1,
  borderColor: Colors.mpBorder,
  shadowColor: '#000',
  shadowOffset: { width: 0, height: 2 },
  shadowOpacity: 0.25,
  shadowRadius: 4,
  elevation: 5,
};
```

**Button Styles**:
```typescript
const buttonStyles = {
  primary: {
    backgroundColor: Colors.mpRed,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  secondary: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: Colors.mpRed,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  danger: {
    backgroundColor: Colors.mpDanger,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
};
```

**Progress Bar**:
```tsx
function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const percentage = (value / max) * 100;
  
  return (
    <View style={{ height: 6, backgroundColor: '#333', borderRadius: 3, overflow: 'hidden' }}>
      <View 
        style={{ 
          width: `${Math.min(percentage, 100)}%`, 
          height: '100%', 
          backgroundColor: color,
          borderRadius: 3,
        }} 
      />
    </View>
  );
}
```

---

## 11. NAVIGATION STRUCTURE

### 11.1 Navigation Stack

```typescript
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

function AuthStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="Login" component={LoginPage} />
    </Stack.Navigator>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator>
      <Tab.Screen name="Dashboard" component={DashboardPage} 
        options={{ tabBarIcon: () => <Icon name="home" /> }} />
      <Tab.Screen name="Accounts" component={AccountsPage} 
        options={{ tabBarIcon: () => <Icon name="account" /> }} />
      <Tab.Screen name="Trades" component={ActiveTradesPage} 
        options={{ tabBarIcon: () => <Icon name="chart" /> }} />
      <Tab.Screen name="Notifications" component={NotificationsPage} 
        options={{ tabBarIcon: () => <Icon name="bell" />, tabBarBadge: unreadCount }} />
      <Tab.Screen name="Settings" component={SettingsPage} 
        options={{ tabBarIcon: () => <Icon name="cog" /> }} />
    </Tab.Navigator>
  );
}

function AppNavigator() {
  const { isAuthenticated } = useAuth();
  
  return (
    <NavigationContainer>
      {isAuthenticated ? <MainTabs /> : <AuthStack />}
    </NavigationContainer>
  );
}
```

---

## 12. DEPLOYMENT CHECKLIST

### 12.1 Pre-Production Steps

- [ ] Set `USE_MOCK_DATA=false` in production build
- [ ] Configure production Firebase project (separate from dev)
- [ ] Set correct `API_BASE_URL` and `WS_BASE_URL` for production backend
- [ ] Enable Proguard/R8 obfuscation (Android)
- [ ] Configure app signing keys (Android & iOS)
- [ ] Set up FCM server key in backend environment
- [ ] Test on physical devices (not just simulators)
- [ ] Enable error tracking (Sentry/Bugsnag)
- [ ] Set up analytics (Firebase Analytics)
- [ ] Create privacy policy and terms of service
- [ ] Submit to App Store / Play Store

### 12.2 Backend Connection Test

Add connection test screen on first launch:

```tsx
async function testBackendConnection() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`);
    if (response.data.status === 'healthy') {
      return { success: true, message: 'Backend connected' };
    }
  } catch (error) {
    return { success: false, message: 'Backend unreachable' };
  }
}
```

---

## 13. SUMMARY OF NEW FEATURES (v5.1)

### 13.1 Backend API Changes
✅ All accounts endpoints now return 8 additional fields:
- `daily_drawdown_pct`
- `daily_loss_limit_pct`
- `overall_drawdown_pct`
- `overall_loss_limit_pct`
- `consistency_score`
- `profitable_days_count`
- `total_trading_days`
- `required_profitable_days`

### 13.2 Frontend UI Changes
✅ Accounts Page:
- Daily drawdown progress bar with percentage
- Max drawdown progress bar with percentage
- Consistency score display (color-coded)
- Profitable days counter with progress bar

✅ Active Trades Page:
- Live P&L display (`current_pnl` field)
- Updates every 5 seconds (polling) + WebSocket

✅ Multi-User Support:
- Firebase authentication (email/password + Google)
- User-specific data isolation
- Super admin can see all users
- Regular users see only their own data

✅ Real-Time Updates:
- WebSocket connection for instant updates
- Trade execution notifications
- Balance change notifications
- System alerts

---

## 14. API ERROR CODES

Handle these error codes in the mobile app:

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Display success message |
| 401 | Unauthorized | Refresh token → Redirect to login |
| 403 | Forbidden | Show "Access denied" |
| 404 | Not Found | Show "Resource not found" |
| 422 | Validation Error | Display field-specific errors |
| 500 | Server Error | Show "Server error, try again" |

---

## 15. TESTING GUIDE

### 15.1 Test User Accounts

Create test accounts with different roles:
- **Regular User**: `test@mirrorpupil.com`
- **Super Admin**: `admin@mirrorpupil.com`

### 15.2 Test Scenarios

1. **Authentication Flow**:
   - Sign in with email/password
   - Sign in with Google
   - Sign out and verify session cleared
   - Token refresh on 401 error

2. **Data Isolation**:
   - Create multiple users
   - Verify each user sees only their accounts
   - Verify super admin sees all accounts

3. **Real-Time Updates**:
   - Connect WebSocket
   - Open trade via Telegram signal
   - Verify trade appears in Active Trades immediately
   - Verify balance updates in real-time

4. **Offline Mode**:
   - Enable airplane mode
   - Verify cached data is displayed
   - Verify offline banner appears
   - Re-enable connection and verify data syncs

5. **Push Notifications**:
   - Open trade → Verify notification received
   - Breach risk limit → Verify critical notification
   - Tap notification → Verify navigation to correct page

---

## 16. CONTACT & SUPPORT

**Backend API Documentation**: `/docs` (Swagger UI)  
**Issue Tracking**: GitHub Issues  
**Support Email**: support@mirrorpupil.com

---

**END OF SPECIFICATION**

This document contains ALL information needed to build the complete Mirror Pupil mobile app with zero additional changes required to the backend.

