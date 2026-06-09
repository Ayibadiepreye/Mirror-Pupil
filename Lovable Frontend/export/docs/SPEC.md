# Mirror Pupil Frontend - Complete Rebuild Prompt

## Overview
Build a modern, professional trading bot management interface for Mirror Pupil v5.1. The frontend should be responsive, real-time, and compatible with Flutter web for future mobile app conversion.

### Scope Boundaries
**MUST INCLUDE (Required):**
- All 7 pages listed in this document (Dashboard, Accounts, Active Trades, History, Notifications, Settings, Bot Control)
- All API endpoints as specified (35 endpoints total)
- WebSocket integration for real-time updates
- Manual trade actions (Close, Breakeven, Partial)
- Lagos timezone conversion for trade history
- CSV export functionality
- Notification system with categories and severities
- Knights of the Blood Oath theme colors

**CREATIVE FREEDOM (Encouraged):**
- Component layouts and visual hierarchy
- Animation and transition styles (keep simple for Flutter compatibility)
- Card designs and spacing arrangements
- Icon selections (as long as categories are clear)
- Typography scale adjustments (within Inter/JetBrains Mono families)
- Button styles and hover effects
- Loading state implementations
- Empty state designs
- Form layouts and validation UX
- Dashboard widget arrangements

**DO NOT INCLUDE (Out of Scope):**
- Additional trading features beyond what's specified
- Charting or technical analysis tools
- User authentication/login (handled by backend)
- Multi-language support (English only for now)
- Custom risk calculator widgets
- Social/community features
- Payment processing
- Email integrations
- Mobile push notifications
- Advanced analytics beyond specified statistics

---

## Tech Stack Requirements

### Primary Stack
- **Framework:** React 18+ with TypeScript
- **State Management:** React Query (TanStack Query) for server state
- **Styling:** TailwindCSS with custom theme
- **HTTP Client:** Axios
- **WebSocket:** Native WebSocket API
- **Date Handling:** date-fns
- **Icons:** Lucide React
- **Build Tool:** Vite
- **Routing:** React Router v6

### Flutter Compatibility Considerations
- Use semantic HTML and avoid complex CSS transforms
- Keep component hierarchy simple and flat
- Use standard flexbox/grid layouts (easily maps to Flutter)
- Avoid CSS animations (use opacity/transform only)
- Keep state management patterns simple (Provider/BLoC compatible)
- Use REST API patterns that work identically in Flutter

---

## Design System

### Color Palette (Knights of the Blood Oath Theme)
```javascript
const colors = {
  // Base layers
  base: '#16161a',        // Sidebar/navigation background
  app: '#1e1e24',         // Main content background
  
  // Accent colors
  crimson: '#b22222',     // Guild crimson - headers/tabs
  red: '#e74c3c',         // Interactive elements - buttons/focus
  
  // Text colors
  text: '#e0e0e0',        // Primary text
  textDim: '#a0a0a0',     // Secondary text
  
  // Borders
  border: '#2a2a30',      // Borders and dividers
  
  // Semantic colors
  success: '#10b981',     // Green for wins/positive
  danger: '#ef4444',      // Red for losses/negative
  warning: '#f59e0b',     // Yellow for warnings
  info: '#3b82f6',        // Blue for info
}
```

### Typography
- **Font Family:** Inter (sans-serif) for UI, JetBrains Mono for numbers/prices
- **Font Sizes:** 
  - Headings: 2xl (24px), xl (20px), lg (18px)
  - Body: base (16px), sm (14px), xs (12px)
- **Font Weights:** Normal (400), Medium (500), Semibold (600), Bold (700)

### Spacing
- Use consistent spacing scale: 2, 4, 8, 12, 16, 24, 32, 48, 64px
- Card padding: 16px (mobile), 24px (desktop)
- Section gaps: 24px
- Element gaps: 12px

### Component Patterns
- **Cards:** Rounded corners (8px), subtle shadow, border on base background
- **Buttons:** Rounded (6px), padding 12px 16px, transition on hover
- **Badges:** Small rounded pills (full radius), padding 4px 12px
- **Inputs:** Rounded (6px), border, padding 8px 12px, focus ring

---

## API Integration

### Base Configuration
```typescript
const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000'
const WS_BASE_URL = process.env.VITE_WS_URL || 'ws://localhost:8000'
```

### Required API Endpoints

**CRITICAL: All endpoints below MUST be implemented exactly as specified. These are the ONLY backend endpoints available - do not attempt to create or call additional endpoints.**

#### Accounts (8 endpoints - ALL REQUIRED)
- `GET /api/accounts/` - List all accounts
- `GET /api/accounts/{key}` - Get account details
- `POST /api/accounts/` - Create account
- `PUT /api/accounts/{key}` - Update account
- `DELETE /api/accounts/{key}` - Delete account
- `POST /api/accounts/{key}/pause` - Pause account
- `POST /api/accounts/{key}/resume` - Resume account
- `POST /api/accounts/discover` - Discover TradeLocker accounts
- `POST /api/accounts/bulk-add` - Bulk add accounts

#### Channels (8 endpoints - ALL REQUIRED)
- `GET /api/channels/` - List all channels
- `GET /api/channels/{id}` - Get channel details (id = integer)
- `POST /api/channels/` - Create channel
  - Body: `{ channel_id, display_name, signal_prefix, entry_logic_module, management_logic_module, priority, enabled, notes? }`
- `PUT /api/channels/{id}` - Update channel (full replace)
- `PATCH /api/channels/{id}` - Partial update (only changed fields)
- `DELETE /api/channels/{id}` - Delete channel
- `POST /api/channels/{id}/enable` - Enable channel (no body)
- `POST /api/channels/{id}/disable` - Disable channel (no body)

#### Risk Profiles (7 endpoints - ALL REQUIRED)
- `GET /api/risk-profiles/` - List all profiles
- `GET /api/risk-profiles/{id}` - Get profile (id = integer)
- `GET /api/risk-profiles/default` - Get default profile
- `POST /api/risk-profiles/` - Create profile
  - Body: `{ profile_name, is_default, max_risk_per_trade_pct, daily_loss_pct, daily_trailing, overall_loss_pct, overall_trailing, max_concurrent_trades, commission_per_lot, safety_buffer_pct, ... }`
- `PUT /api/risk-profiles/{id}` - Update profile (full replace)
- `PATCH /api/risk-profiles/{id}` - Partial update (only changed fields)
- `DELETE /api/risk-profiles/{id}` - Delete profile

#### Trades (7 endpoints - ALL REQUIRED)
- `GET /api/trades/active` - List all active trades
- `GET /api/trades/active/{account}` - List by account (account = account_key string)
- `POST /api/trades/active/{id}/close` - **Manual close entire position**
  - Body: `{}` (empty)
  - Returns: `{ success: bool, message: string }`
- `POST /api/trades/active/{id}/breakeven` - **Set SL to entry price**
  - Body: `{}` (empty)
  - Returns: `{ success: bool, message: string }`
- `POST /api/trades/active/{id}/partial` - **Take partial profit**
  - Body: `{ percentage: number }` (25, 50, or 75)
  - Returns: `{ success: bool, message: string, remaining_lots: number }`
- `GET /api/trades/history?account_key={key}&limit={n}&offset={n}` - Trade history
  - Query params: account_key (optional), limit (default 50), offset (default 0)
- `GET /api/trades/history/export?account_key={key}` - **Export CSV**
  - Query params: account_key (optional)
  - Returns: CSV file download

#### Notifications (5 endpoints - ALL REQUIRED)
- `GET /api/notifications/?unread_only={bool}&limit={n}` - List notifications
  - Query params: unread_only (default false), limit (default 50)
- `POST /api/notifications/` - Create notification (admin only, optional to implement in UI)
- `PATCH /api/notifications/{id}/read` - Mark as read
  - Body: `{}` (empty)
- `POST /api/notifications/mark-all-read` - Bulk mark all read
  - Body: `{}` (empty)
- `DELETE /api/notifications/{id}` - Delete notification

#### Bot Control (4 endpoints - ALL REQUIRED)
- `GET /api/bot/status` - Get bot status
  - Returns: `{ status, dry_run, active_accounts, paused_accounts, breached_accounts, total_active_trades, allow_weekend_trading, allow_eod_trading }`
- `POST /api/bot/control` - Start/stop bot
  - Body: `{ action: "start" | "stop" }`
- `POST /api/bot/force-close-all` - **Emergency close all positions**
  - Body: `{}` (empty)
  - ⚠️ DESTRUCTIVE: Requires confirmation dialog
- `POST /api/bot/force-close-account/{key}` - **Close all positions for account**
  - Body: `{}` (empty)
  - ⚠️ DESTRUCTIVE: Requires confirmation dialog

**Total: 35 API endpoints (8 + 8 + 7 + 7 + 5 + 4 = 39, but 4 are optional in UI)**

### WebSocket Integration

**CRITICAL: WebSocket is REQUIRED for real-time updates. Must connect on app load and reconnect on disconnect.**

```typescript
// Connect to WebSocket
const ws = new WebSocket(`${WS_BASE_URL}/ws/updates`)

// REQUIRED: Handle all 4 message types below
// Message types received:

// 1. Connection confirmation (initial handshake)
{
  type: 'connection',
  status: 'connected',
  message: 'Mirror Pupil WebSocket connected',
  timestamp: '2026-06-08T20:30:00.000Z'
}

// 2. Trade updates (when trades open/close/update)
{
  type: 'trade',
  data: {
    trade_id: 123,
    symbol: 'EURUSD',
    direction: 'BUY',
    status: 'filled',
    // ... other trade fields from ActiveTrade interface
  },
  timestamp: '2026-06-08T20:30:00.000Z'
}

// 3. Balance updates (when account balance changes)
{
  type: 'balance',
  data: {
    account_key: 'user@email.com:12345',
    balance: 10500.50,
    pnl: 45.20
  },
  timestamp: '2026-06-08T20:30:00.000Z'
}

// 4. Notifications (real-time alerts)
{
  type: 'notification',
  data: {
    notification_id: 456,
    category: 'EXECUTION',
    severity: 'INFO',
    title: 'Trade Opened: EURUSD',
    message: 'Opened BUY 0.10 lots at 1.08500',
    // ... other fields from Notification interface
  },
  timestamp: '2026-06-08T20:30:00.000Z'
}
```

**WebSocket Requirements:**
- ✅ Auto-connect on app initialization
- ✅ Auto-reconnect with exponential backoff (max 5 attempts)
- ✅ Update UI immediately when messages received
- ✅ Show connection status indicator in header
- ✅ Handle disconnections gracefully (show warning toast)
- ✅ Invalidate React Query cache on relevant updates

---

## Type Definitions

### Core Types
```typescript
interface Account {
  account_key: string
  credential_key: string
  tl_account_id: string
  tl_email: string
  tl_server: string
  display_name: string | null
  initial_balance: number
  current_balance: number
  highest_banked_balance: number
  profit_locked: boolean
  daily_pnl: number
  daily_start_balance: number
  last_synced_balance: number
  cycle_start_date: string | null
  cycle_best_day_pnl: number
  paused: boolean
  breached: boolean
  risk_profile_id: number | null
  max_concurrent_trades_override: number | null
  lot_size_override: number | null
}

interface Channel {
  channel_id: number
  display_name: string
  signal_prefix: string
  entry_logic_module: string
  management_logic_module: string
  priority: number
  enabled: boolean
  notes: string | null
}

interface RiskProfile {
  profile_id: number
  profile_name: string
  is_default: boolean
  max_risk_per_trade_pct: number
  daily_loss_pct: number
  daily_trailing: boolean
  overall_loss_pct: number
  overall_trailing: boolean
  overall_trail_from_closed_balance: boolean
  profit_lock_pct: number | null
  profit_lock_floor_pct: number | null
  payout_buffer_pct: number
  max_concurrent_trades: number
  commission_per_lot: number
  safety_buffer_pct: number
  notes: string | null
}

interface ActiveTrade {
  trade_id: number
  account_key: string
  channel_id: number
  channel_name: string | null
  signal_id: string
  sub_signal_id: string | null
  symbol: string
  direction: 'BUY' | 'SELL'
  entry_price: number
  sl: number | null
  tp: number | null
  lot_size: number
  entry_time: string // ISO 8601
  tl_order_id: string | null
  tl_position_id: string | null
  status: string
  tp1_hit: boolean
  risk_usd: number | null
}

interface TradeHistory {
  history_id: number
  account_key: string
  channel_id: number
  channel_name: string | null
  signal_id: string
  sub_signal_id: string | null
  symbol: string
  direction: 'BUY' | 'SELL'
  entry_price: number
  exit_price: number
  sl: number | null
  tp: number | null
  lot_size: number
  entry_time: string // ISO 8601
  exit_time: string // ISO 8601
  pnl: number
  outcome: 'WIN' | 'LOSS' | 'BE'
  close_reason: string
  manual_action_type: string | null
}

interface Notification {
  notification_id: number
  account_key: string | null
  category: 'SIGNAL' | 'EXECUTION' | 'MANAGEMENT' | 'BREACH' | 'SYSTEM'
  severity: 'CRITICAL' | 'ERROR' | 'WARNING' | 'INFO'
  title: string
  message: string
  metadata: any
  read: boolean
  created_at: string // ISO 8601
}

interface BotStatus {
  status: string
  dry_run: boolean
  active_accounts: number
  paused_accounts: number
  breached_accounts: number
  total_active_trades: number
  allow_weekend_trading: boolean
  allow_eod_trading: boolean
}
```

---

## Required Pages & Features

### 1. Dashboard Page (`/`)
**Purpose:** Overview of system status and key metrics

**Components:**
- **Header Stats Cards**
  - Total accounts (active/paused/breached)
  - Total active trades
  - Total P&L today
  - Bot status indicator
  
- **Recent Activity Feed**
  - Last 10 notifications
  - Timestamp with relative time ("5m ago")
  - Category icons and severity colors
  - Click to view details
  
- **Quick Actions**
  - Pause/Resume all accounts
  - Force close all positions
  - View active trades
  - View notifications

**Features:**
- Real-time updates via WebSocket
- Auto-refresh every 10 seconds
- Color-coded status indicators
- Responsive grid layout

---

### 2. Accounts Page (`/accounts`)
**Purpose:** Manage trading accounts

**Components:**
- **Accounts List**
  - Display name (editable)
  - Account key
  - Current balance
  - Daily P&L
  - Status badges (paused/breached)
  - Actions: Edit, Pause/Resume, Delete
  
- **Add Account Button**
  - Opens modal with two options:
    1. Discover & Add: Enter credentials, discover accounts, select to add
    2. Manual Add: Enter all details manually
  
- **Account Details Modal**
  - Edit display name
  - Edit lot size override
  - Assign risk profile
  - Set max concurrent trades
  - View statistics
  - Account history

**Features:**
- Bulk add accounts from TradeLocker
- Filter by status (active/paused/breached)
- Search by email or account key
- Sort by balance, P&L, name
- Real-time balance updates

---

### 3. Active Trades Page (`/trades`)
**Purpose:** Monitor and manage open positions

**REQUIRED Components:**
- **Trade Cards** (one per trade) - MUST include:
  - Symbol with BUY/SELL badge (green for BUY, red for SELL)
  - Channel name badge
  - Entry price, SL, TP (monospace font)
  - Lot size and risk amount
  - **Time since entry** ("3m ago", "2h ago") - REQUIRED
  - TP1 hit indicator (if tp1_hit === true)
  - Account key (shortened, e.g., "user@...com:12345")
  
  **Action Buttons (ALL REQUIRED):**
  - 🔴 **Close** - Calls `POST /api/trades/active/{id}/close`
    - Confirmation: "Close entire position for {symbol}?"
    - On success: Show toast, refresh trade list
  - ⚖️ **Breakeven** - Calls `POST /api/trades/active/{id}/breakeven`
    - Confirmation: "Set stop loss to breakeven for {symbol}?"
    - On success: Show toast, refresh trade list
  - 💰 **Partial** - Dropdown with 25%, 50%, 75% options
    - Each calls `POST /api/trades/active/{id}/partial` with `{ percentage: 25|50|75 }`
    - Confirmation: "Close {percentage}% of {symbol} position?"
    - On success: Show toast with remaining lots, refresh trade list
  
- **Filter Bar (REQUIRED)**
  - Filter by account (dropdown)
  - Filter by symbol (search input)
  - Filter by channel (dropdown)
  - Sort by: time (default), symbol, P&L

**REQUIRED Features:**
- ✅ Real-time updates via WebSocket (trade messages)
- ✅ Fallback: Poll API every 5 seconds if WebSocket disconnected
- ✅ Confirmation dialogs for ALL actions (Close, Breakeven, Partial)
- ✅ Loading states during API calls (disable buttons)
- ✅ Error handling with toast notifications
- ✅ Empty state when no trades ("No active trades")
- ✅ Responsive card grid (1 col mobile, 2 col tablet, 3 col desktop)

**Visual Design (Creative Freedom):**
- Gradient backgrounds for cards (your choice of style)
- Hover effects and transitions (keep simple for Flutter)
- Action button layouts (horizontal or vertical)
- Card spacing and shadows
- Badge designs

---

### 4. Trade History Page (`/history`)
**Purpose:** View completed trades and performance

**REQUIRED Components:**
- **Filter Bar (ALL REQUIRED)**
  - Account dropdown filter (all accounts)
  - Date range picker: Last 7 days, Last 30 days, All time (default)
  - Symbol search input
  - Channel filter dropdown
  
- **Export Button (REQUIRED)**
  - Calls `GET /api/trades/history/export?account_key={key}`
  - Downloads CSV file
  - Filename format: `trade_history_YYYY-MM-DD.csv`
  - Shows loading spinner during download
  
- **History Table (REQUIRED, ALL COLUMNS)**
  Columns (in order):
  1. **Exit Time** - MUST use Lagos timezone (WAT = UTC+1)
     - Format: "Jun 08, 21:30" or "MM/DD HH:mm"
  2. **Channel Name** - Badge with channel display_name
  3. **Symbol** - e.g., "EURUSD"
  4. **Direction** - Badge (BUY green, SELL red)
  5. **Entry Price** - Monospace font, 5 decimals
  6. **Exit Price** - Monospace font, 5 decimals
  7. **Lot Size** - e.g., "0.10"
  8. **P&L** - MUST be colored (green if positive, red if negative, gray if zero)
     - Format: "+$45.20" or "-$12.50"
  9. **Outcome** - Badge: WIN (green), LOSS (red), BE (gray)
  10. **Close Reason** - e.g., "TP_HIT", "SL_HIT", "MANUAL"
  11. **Manual Action** - Badge if manual_action_type !== null
      - Show type: "CLOSE", "BREAKEVEN", "PARTIAL"
  
- **Summary Statistics Cards (REQUIRED)**
  - **Total Trades** - Count
  - **Winners** - Count and win rate % (e.g., "45 (65%)")
  - **Losers** - Count
  - **Total P&L** - Colored sum (green/red)
  - **Average Win** - $ amount
  - **Average Loss** - $ amount
  - **Largest Win** - $ amount
  - **Largest Loss** - $ amount

**REQUIRED Features:**
- ✅ Pagination (50 per page) with Previous/Next buttons
- ✅ Sort by any column (click header to sort)
- ✅ **Lagos timezone conversion (UTC+1)** - CRITICAL
- ✅ Manual action indicators (badge in dedicated column)
- ✅ Export applies current filters
- ✅ Responsive table (horizontal scroll on mobile)
- ✅ Real-time updates: Poll API every 10 seconds
- ✅ Statistics recalculate when filters change

**Visual Design (Creative Freedom):**
- Table styling (borders, row hover, alternating colors)
- Statistics card layouts and gradients
- Badge designs for outcomes
- Loading skeleton for table rows

---

### 5. Notifications Page (`/notifications`)
**Purpose:** View and manage system notifications

**REQUIRED Components:**
- **Header (ALL REQUIRED)**
  - Unread count display (e.g., "12 unread")
  - "Mark All Read" button - Calls `POST /api/notifications/mark-all-read`
  - "Unread Only" toggle filter
  
- **Critical Alerts Banner (CONDITIONAL)**
  - Show ONLY if any notifications have severity === 'CRITICAL'
  - Red gradient background
  - Prominent display at top
  - List all critical notifications
  - Dismiss button for each
  
- **Notifications List (REQUIRED, ALL FIELDS)**
  Each notification card MUST include:
  - **Category icon** (different per category):
    - SIGNAL: ⚡ Zap icon
    - EXECUTION: ✓ CheckCheck icon  
    - MANAGEMENT: ℹ️ Info icon
    - BREACH: ⚠️ AlertTriangle icon
    - SYSTEM: 🔔 AlertCircle icon
  - **Title** (bold, e.g., "Trade Opened: EURUSD")
  - **Message** (full text)
  - **Badges**: Severity + Category
  - **Timestamp** - MUST use relative time ("3m ago", "2h ago", "5d ago")
  - **Account key** (if not null, show shortened)
  - **Unread indicator** - Red dot or border if read === false
  - **Action buttons**:
    - "Mark Read" - Calls `PATCH /api/notifications/{id}/read`
    - "Delete" - Calls `DELETE /api/notifications/{id}`
  - **Expandable metadata** (optional, click to expand JSON)
  
**REQUIRED Severity Color Coding:**
- CRITICAL: Red left border (4px)
- ERROR: Orange left border (4px)
- WARNING: Yellow left border (4px)
- INFO: Blue left border (4px)

**REQUIRED Features:**
- ✅ Real-time updates via WebSocket (notification messages)
- ✅ Fallback: Poll API every 5 seconds if WebSocket disconnected
- ✅ Filter: Show unread only (toggle)
- ✅ Mark as read (individual or bulk)
- ✅ Delete notification (with confirmation)
- ✅ Expandable metadata (collapsible JSON viewer)
- ✅ Empty state when no notifications ("No notifications")
- ✅ Auto-scroll to top when new notification arrives

**Visual Design (Creative Freedom):**
- Card layouts and spacing
- Animation for new notifications
- Unread indicator style (dot, border, background)
- Expand/collapse animation
- Button styles and positions

---

### 6. Settings Page (`/settings`)
**Purpose:** Configure channels, risk profiles, and system settings

**Tabs:**

#### Channels Tab
- **Channel List**
  - Display name (editable)
  - Channel ID
  - Signal prefix
  - Priority
  - Enabled toggle
  - Actions: Edit, Delete, Enable/Disable
  
- **Add Channel Button**
  - Opens modal with form:
    - Channel ID (Telegram numeric ID)
    - Display name
    - Signal prefix
    - Entry logic module
    - Management logic module
    - Priority (1-100)
    - Enabled toggle
    - Notes (optional)

#### Risk Profiles Tab
- **Profile List**
  - Profile name
  - Default indicator
  - Key limits (daily %, overall %)
  - Max concurrent trades
  - Actions: Edit, Delete, Set Default
  
- **Add Profile Button**
  - Opens modal with comprehensive form:
    - Profile name
    - Is default toggle
    - Max risk per trade %
    - Daily loss % (with trailing toggle)
    - Overall loss % (with trailing toggle)
    - Profit lock % (optional)
    - Profit lock floor % (optional)
    - Payout buffer %
    - Max concurrent trades
    - Commission per lot
    - Safety buffer %
    - Notes

#### Bot Settings Tab
- **Trading Hours**
  - Allow weekend trading toggle
  - Allow end-of-day trading toggle
  
- **Emergency Actions**
  - Force close all positions button
  - Pause all accounts button
  - Resume all accounts button
  
- **System Info**
  - Bot version
  - API version
  - Database status
  - WebSocket status
  - Active connections count

**Features:**
- Real-time status updates
- Confirmation dialogs for destructive actions
- Form validation
- Error handling
- Success/failure toast notifications

---

### 7. Bot Control Page (`/bot-control`)
**Purpose:** Monitor and control bot operations

**Components:**
- **Status Dashboard**
  - Bot status (Running/Stopped)
  - Dry run mode indicator
  - Active accounts count
  - Paused accounts count
  - Breached accounts count
  - Total active trades
  - Last update timestamp
  
- **Control Panel**
  - Start Bot button (if stopped)
  - Stop Bot button (if running)
  - Restart Bot button
  
- **Emergency Actions**
  - Force Close All Positions
    - Confirmation: "This will close ALL open positions. Continue?"
  - Pause All Accounts
  - Resume All Accounts
  
- **Settings Quick Toggles**
  - Allow Weekend Trading
  - Allow End-of-Day Trading
  
- **Activity Log** (last 20 events)
  - Timestamp
  - Event type
  - Description
  - Status

**Features:**
- Real-time status updates
- Confirmation dialogs
- Loading states
- Auto-refresh every 10 seconds
- Color-coded status indicators

---

## Layout & Navigation

### App Shell
```
┌─────────────────────────────────────────────┐
│ Header (sticky)                             │
│  - Logo & Title                             │
│  - Notification bell (with badge count)     │
│  - Bot status indicator                     │
└─────────────────────────────────────────────┘
│                                             │
│ Main Content Area                           │
│  (scrollable)                               │
│                                             │
│                                             │
└─────────────────────────────────────────────┘
│ Bottom Navigation (fixed, mobile)           │
│  - Dashboard | Accounts | Trades |          │
│    History | Bot | Settings                 │
└─────────────────────────────────────────────┘
```

### Navigation Items
- 🏠 **Dashboard** - `/`
- 👥 **Accounts** - `/accounts`
- 📈 **Active** - `/trades`
- 📊 **History** - `/history`
- ⚙️ **Settings** - `/settings`
- 🤖 **Bot** - `/bot-control`
- 🔔 **Notifications** - `/notifications` (accessed via header bell icon)

### Responsive Behavior
- **Mobile (< 768px)**
  - Floating Action Button (bottom-right, signature MP red).
    Tap to expand a vertical rail of spaced, pill-shaped nav buttons floating
    along the right edge (Dashboard, Accounts, Active, History, Alerts, Bot,
    Settings). Tap a button to navigate, tap the scrim or the FAB again (it
    rotates into an X / close icon) to collapse. No bottom bar.
  - Single column layout
  - Stacked cards
  - Horizontal scrolling tables
  
- **Tablet (768px - 1024px)**
  - Side navigation (collapsible)
  - Two column layout
  - Grid cards
  
- **Desktop (> 1024px)**
  - Persistent side navigation
  - Three column layout where applicable
  - Full tables
  - Enhanced hover states

---

## Utility Functions

**REQUIRED: Implement these exact utility functions. They are used throughout the application.**

### Time Utilities (BOTH REQUIRED)
```typescript
/**
 * Convert to relative time
 * REQUIRED: Used in Active Trades and Notifications
 * @param date - ISO 8601 string or Date object
 * @returns "just now", "3m ago", "2h ago", "5d ago", etc.
 */
function formatTimeAgo(date: Date | string): string {
  const now = new Date()
  const then = typeof date === 'string' ? new Date(date) : date
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000)
  
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

/**
 * Convert UTC to Lagos time (WAT = UTC+1)
 * CRITICAL: Used in Trade History page
 * @param date - ISO 8601 string or Date object
 * @returns "Jun 08, 21:30" in Lagos timezone
 */
function formatLagosTime(date: Date | string): string {
  const utcDate = typeof date === 'string' ? new Date(date) : date
  // Add 1 hour to UTC for Lagos time (WAT = UTC+1)
  const lagosDate = new Date(utcDate.getTime() + (1 * 60 * 60 * 1000))
  
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const month = months[lagosDate.getUTCMonth()]
  const day = lagosDate.getUTCDate().toString().padStart(2, '0')
  const hours = lagosDate.getUTCHours().toString().padStart(2, '0')
  const minutes = lagosDate.getUTCMinutes().toString().padStart(2, '0')
  
  return `${month} ${day}, ${hours}:${minutes}`
}
```

### Currency Utilities (BOTH REQUIRED)
```typescript
/**
 * Format currency with specified decimals
 * @param value - Number to format
 * @param decimals - Decimal places (default 2)
 * @returns "1234.56"
 */
function formatCurrency(value: number, decimals: number = 2): string {
  return value.toFixed(decimals)
}

/**
 * Format price based on symbol type
 * REQUIRED: Use for all price displays
 * @param value - Price value
 * @param symbol - Trading symbol (e.g., "EURUSD", "XAUUSD")
 * @returns Formatted price with correct decimals
 */
function formatPrice(value: number, symbol: string): string {
  // Forex pairs: 5 decimals
  if (symbol.length === 6 && !symbol.startsWith('XAG') && !symbol.startsWith('XAU')) {
    return value.toFixed(5)
  }
  // Metals and indices: 2 decimals
  return value.toFixed(2)
}
```

### P&L Utilities (BOTH REQUIRED)
```typescript
/**
 * Calculate unrealized P&L for active positions
 * OPTIONAL: Implement if you want live P&L on active trades
 * Requires current market price (not provided by API, would need price feed)
 */
function calculateUnrealizedPnL(
  direction: 'BUY' | 'SELL',
  entryPrice: number,
  currentPrice: number,
  lotSize: number,
  symbol: string
): number {
  // This is OPTIONAL - backend doesn't provide live prices
  // You can skip this and just show entry price + targets
}

/**
 * Get color class for P&L display
 * REQUIRED: Used in Trade History
 * @param pnl - P&L value
 * @returns Tailwind color class
 */
function getPnLColor(pnl: number): string {
  if (pnl > 0) return 'text-green-400'
  if (pnl < 0) return 'text-red-400'
  return 'text-gray-400'
}
```

---

## State Management

### React Query Configuration
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5000, // 5 seconds
    },
  },
})
```

### Query Keys
```typescript
// Use consistent query key patterns
const QUERY_KEYS = {
  accounts: ['accounts'],
  account: (key: string) => ['account', key],
  channels: ['channels'],
  riskProfiles: ['risk-profiles'],
  activeTrades: ['active-trades'],
  tradeHistory: (accountKey?: string) => ['trade-history', accountKey],
  notifications: (unreadOnly: boolean) => ['notifications', unreadOnly],
  botStatus: ['bot-status'],
}
```

### Mutations
```typescript
// Example mutation for closing trade
const closeTradeMutation = useMutation({
  mutationFn: (tradeId: number) => api.closeTrade(tradeId),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.activeTrades })
    toast.success('Trade closed successfully')
  },
  onError: (error) => {
    toast.error('Failed to close trade')
  },
})
```

---

## Error Handling

### API Errors
```typescript
// Show user-friendly error messages
try {
  await api.closeTrade(tradeId)
} catch (error) {
  if (error.response?.status === 404) {
    toast.error('Trade not found')
  } else if (error.response?.status === 500) {
    toast.error('Server error. Please try again.')
  } else {
    toast.error('Failed to close trade')
  }
}
```

### WebSocket Reconnection
```typescript
// Implement automatic reconnection
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 5

function connectWebSocket() {
  const ws = new WebSocket(WS_URL)
  
  ws.onclose = () => {
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      setTimeout(() => {
        reconnectAttempts++
        connectWebSocket()
      }, 2000 * reconnectAttempts) // Exponential backoff
    }
  }
  
  ws.onopen = () => {
    reconnectAttempts = 0
    toast.success('Connected to server')
  }
}
```

---

## Performance Optimizations

### Code Splitting
```typescript
// Lazy load routes
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Accounts = lazy(() => import('./pages/Accounts'))
const ActiveTrades = lazy(() => import('./pages/ActiveTrades'))
// ... etc
```

### Memoization
```typescript
// Memoize expensive calculations
const statistics = useMemo(() => {
  return calculateTradeStatistics(history)
}, [history])
```

### Virtualization
```typescript
// For large lists (100+ items), use virtualization
import { FixedSizeList } from 'react-window'
```

---

## Accessibility

### Requirements
- All interactive elements must be keyboard accessible
- Use semantic HTML (button, nav, main, etc.)
- Provide ARIA labels for icon buttons
- Ensure color contrast ratio meets WCAG AA (4.5:1)
- Add focus indicators
- Use proper heading hierarchy (h1 -> h2 -> h3)

### Example
```tsx
<button
  onClick={handleClose}
  aria-label="Close trade"
  className="focus:ring-2 focus:ring-red-500"
>
  <X size={16} />
</button>
```

---

## Loading States

### Skeletons
Use skeleton loaders for better UX:
```tsx
// Card skeleton
<div className="card animate-pulse">
  <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
  <div className="h-4 bg-gray-700 rounded w-1/2"></div>
</div>
```

### Spinners
For button actions:
```tsx
<button disabled={isLoading}>
  {isLoading ? <Spinner /> : 'Close Trade'}
</button>
```

---

## Toast Notifications

### Library: React Hot Toast or Sonner
```typescript
// Success
toast.success('Trade closed successfully', {
  duration: 3000,
  position: 'top-right',
})

// Error
toast.error('Failed to close trade', {
  duration: 5000,
  position: 'top-right',
})

// Info
toast.info('WebSocket connected', {
  duration: 2000,
  position: 'top-right',
})
```

---

## Testing Requirements

### Unit Tests
- Test utility functions
- Test API client functions
- Test state management logic

### Integration Tests
- Test complete user flows
- Test form submissions
- Test error handling

### E2E Tests (Optional)
- Test critical paths
- Test real-time updates
- Test manual actions

---

## Environment Variables

### `.env.example`
```bash
# API Configuration
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# Feature Flags
VITE_ENABLE_WEBSOCKET=true
VITE_ENABLE_NOTIFICATIONS=true

# Polling Intervals (milliseconds)
VITE_TRADES_REFRESH=5000
VITE_NOTIFICATIONS_REFRESH=5000
VITE_DASHBOARD_REFRESH=10000
```

---

## Deployment Checklist

- [ ] Environment variables configured
- [ ] API endpoints verified
- [ ] WebSocket connection tested
- [ ] All routes accessible
- [ ] Responsive on mobile/tablet/desktop
- [ ] Loading states implemented
- [ ] Error handling in place
- [ ] Toast notifications working
- [ ] Real-time updates functional
- [ ] Manual actions tested
- [ ] CSV export working
- [ ] Lagos timezone conversion correct
- [ ] Performance optimized (< 3s load time)
- [ ] Accessibility verified
- [ ] Browser compatibility (Chrome, Firefox, Safari, Edge)

---

## Flutter Conversion Notes

### Easy Migration Points
1. **API Client** - Same REST endpoints work in Flutter (use `dio` or `http`)
2. **State Management** - Convert React Query to Provider/BLoC/Riverpod
3. **WebSocket** - Use `web_socket_channel` package
4. **UI Components** - Convert React components to Flutter Widgets
5. **Routing** - Use `go_router` or `auto_route`

### Layout Mapping
- **div** → Container / Column / Row
- **Flexbox** → Flex / Expanded / Flexible
- **Grid** → GridView
- **Card** → Card widget
- **Button** → ElevatedButton / TextButton / IconButton
- **Input** → TextField
- **Modal** → showDialog / showModalBottomSheet

### Styling Mapping
- **TailwindCSS classes** → Flutter style properties
- **Colors** → Define in theme
- **Spacing** → EdgeInsets / SizedBox
- **Borders** → BoxDecoration
- **Shadows** → BoxShadow

---

## Summary

This prompt provides **everything needed** to rebuild the Mirror Pupil frontend with **clear boundaries**:

### ✅ MUST IMPLEMENT (Non-Negotiable)
- ✅ All 7 pages (Dashboard, Accounts, Active Trades, History, Notifications, Settings, Bot Control)
- ✅ All 35 API endpoints exactly as specified
- ✅ WebSocket integration with 4 message types
- ✅ Manual trade actions (Close, Breakeven, Partial with confirmations)
- ✅ Lagos timezone conversion (UTC+1) for trade history
- ✅ CSV export functionality
- ✅ Notification system with 5 categories and 4 severities
- ✅ Time-ago display ("3m ago") for active trades and notifications
- ✅ Knights of the Blood Oath theme colors
- ✅ Utility functions as provided
- ✅ TypeScript type definitions as provided
- ✅ React Query for state management
- ✅ Error handling and loading states
- ✅ Confirmation dialogs for destructive actions
- ✅ Real-time updates via WebSocket (with polling fallback)

### 🎨 CREATIVE FREEDOM (Your Design Choices)
- 🎨 Component layouts and visual hierarchy
- 🎨 Animation styles (keep Flutter-compatible)
- 🎨 Card designs, shadows, and spacing
- 🎨 Icon selections (as long as meaning is clear)
- 🎨 Typography scale adjustments (within Inter/JetBrains Mono)
- 🎨 Button styles and hover effects
- 🎨 Loading skeleton designs
- 🎨 Empty state illustrations
- 🎨 Form layouts
- 🎨 Dashboard widget arrangements
- 🎨 Navigation structure (sidebar vs bottom bar vs tabs)
- 🎨 Modal designs and transitions

### ❌ OUT OF SCOPE (Do Not Add)
- ❌ Additional trading features beyond specs
- ❌ Charting or technical analysis
- ❌ User authentication UI
- ❌ Multi-language support
- ❌ Custom risk calculators
- ❌ Social features
- ❌ Payment processing
- ❌ Email integrations
- ❌ Advanced analytics beyond specified statistics
- ❌ Any additional API endpoints not listed

### 📊 Stats
- **35 API endpoints** (all documented with request/response)
- **7 pages** (all requirements specified)
- **4 WebSocket message types** (all handlers required)
- **5 notification categories** (all icons specified)
- **4 severity levels** (all colors specified)
- **6 utility functions** (all implementations provided)
- **10 TypeScript interfaces** (all fields documented)

**Build a modern, professional, real-time trading interface that:**
1. **Connects perfectly** to the existing backend (all endpoints specified)
2. **Looks amazing** (creative freedom on visual design)
3. **Works seamlessly** on web and can convert to Flutter mobile
4. **Stays in scope** (clear boundaries on what not to add)

---

*End of Frontend Rebuild Prompt - Version 1.1 (Scoped & Specific)*
