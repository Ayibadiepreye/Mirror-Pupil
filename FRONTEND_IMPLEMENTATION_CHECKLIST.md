# Mirror Pupil Frontend - Implementation Checklist

Use this checklist to verify your implementation is complete and matches the backend API.

---

## 🔌 API Endpoints (35 total)

### Accounts (8 endpoints)
- [ ] `GET /api/accounts/` - List all accounts
- [ ] `GET /api/accounts/{key}` - Get account details
- [ ] `POST /api/accounts/` - Create account
- [ ] `PUT /api/accounts/{key}` - Update account
- [ ] `DELETE /api/accounts/{key}` - Delete account
- [ ] `POST /api/accounts/{key}/pause` - Pause account
- [ ] `POST /api/accounts/{key}/resume` - Resume account
- [ ] `POST /api/accounts/discover` - Discover TradeLocker accounts

### Channels (8 endpoints)
- [ ] `GET /api/channels/` - List all channels
- [ ] `GET /api/channels/{id}` - Get channel details
- [ ] `POST /api/channels/` - Create channel
- [ ] `PUT /api/channels/{id}` - Update channel
- [ ] `PATCH /api/channels/{id}` - Partial update
- [ ] `DELETE /api/channels/{id}` - Delete channel
- [ ] `POST /api/channels/{id}/enable` - Enable channel
- [ ] `POST /api/channels/{id}/disable` - Disable channel

### Risk Profiles (7 endpoints)
- [ ] `GET /api/risk-profiles/` - List all profiles
- [ ] `GET /api/risk-profiles/{id}` - Get profile
- [ ] `GET /api/risk-profiles/default` - Get default profile
- [ ] `POST /api/risk-profiles/` - Create profile
- [ ] `PUT /api/risk-profiles/{id}` - Update profile
- [ ] `PATCH /api/risk-profiles/{id}` - Partial update
- [ ] `DELETE /api/risk-profiles/{id}` - Delete profile

### Trades (7 endpoints)
- [ ] `GET /api/trades/active` - List all active trades
- [ ] `GET /api/trades/active/{account}` - List by account
- [ ] `POST /api/trades/active/{id}/close` - Manual close
- [ ] `POST /api/trades/active/{id}/breakeven` - Set to breakeven
- [ ] `POST /api/trades/active/{id}/partial` - Take partial profit
- [ ] `GET /api/trades/history` - Trade history with pagination
- [ ] `GET /api/trades/history/export` - Export CSV

### Notifications (5 endpoints)
- [ ] `GET /api/notifications/` - List notifications with filters
- [ ] `PATCH /api/notifications/{id}/read` - Mark as read
- [ ] `POST /api/notifications/mark-all-read` - Bulk mark read
- [ ] `DELETE /api/notifications/{id}` - Delete notification
- [ ] `POST /api/notifications/` - Create notification (optional)

---

## 📱 Pages (7 required)

### 1. Dashboard (`/`)
- [ ] Header stats cards (accounts, trades, P&L, bot status)
- [ ] Recent activity feed (last 10 notifications)
- [ ] Quick actions panel
- [ ] Real-time updates via WebSocket
- [ ] Auto-refresh every 10 seconds

### 2. Accounts (`/accounts`)
- [ ] Accounts list with all fields
- [ ] Add account button (discover + manual)
- [ ] Edit account modal
- [ ] Pause/Resume actions
- [ ] Delete account (with confirmation)
- [ ] Filter and search functionality
- [ ] Real-time balance updates

### 3. Active Trades (`/trades`)
- [ ] Trade cards with all fields
- [ ] **Close button** (with confirmation)
- [ ] **Breakeven button** (with confirmation)
- [ ] **Partial button** with 25%/50%/75% dropdown (with confirmation)
- [ ] **Time-ago display** ("3m ago")
- [ ] Channel name badge
- [ ] Filter bar (account, symbol, channel)
- [ ] Real-time updates via WebSocket
- [ ] Empty state

### 4. Trade History (`/history`)
- [ ] History table with all 11 columns
- [ ] **Lagos timezone conversion (UTC+1)** - CRITICAL
- [ ] **Export CSV button**
- [ ] Filter bar (account, date range, symbol, channel)
- [ ] Summary statistics cards (8 metrics)
- [ ] Pagination (50 per page)
- [ ] Sort by any column
- [ ] Manual action indicators
- [ ] Colored P&L display

### 5. Notifications (`/notifications`)
- [ ] Notifications list with all fields
- [ ] **Category icons** (Signal, Execution, Management, Breach, System)
- [ ] **Severity color coding** (left border)
- [ ] **Time-ago display** ("3m ago")
- [ ] Critical alerts banner (if any critical)
- [ ] Unread count display
- [ ] Mark all read button
- [ ] Unread only filter toggle
- [ ] Individual mark read/delete buttons
- [ ] Expandable metadata
- [ ] Real-time updates via WebSocket
- [ ] Empty state

### 6. Settings (`/settings`)
- [ ] Channels tab (list, add, edit, delete, enable/disable)
- [ ] Risk profiles tab (list, add, edit, delete, set default)
- [ ] Bot settings tab (trading hours, emergency actions)
- [ ] Confirmation dialogs for destructive actions
- [ ] Form validation

### 7. Bot Control (`/bot-control`)
- [ ] Status dashboard with all metrics
- [ ] Start/Stop bot buttons
- [ ] Emergency actions (force close all, pause all)
- [ ] Settings quick toggles
- [ ] Real-time status updates
- [ ] Confirmation dialogs

---

## 🌐 WebSocket Integration

- [ ] Connect to `/ws/updates` on app load
- [ ] Handle `connection` message type
- [ ] Handle `trade` message type (update active trades)
- [ ] Handle `balance` message type (update account balances)
- [ ] Handle `notification` message type (add to notification list)
- [ ] Auto-reconnect with exponential backoff (max 5 attempts)
- [ ] Show connection status indicator in header
- [ ] Invalidate React Query cache on updates
- [ ] Graceful degradation (polling fallback)

---

## 🛠️ Utility Functions

- [ ] `formatTimeAgo()` - Relative time display
- [ ] `formatLagosTime()` - Lagos timezone conversion (UTC+1)
- [ ] `formatCurrency()` - Currency formatting
- [ ] `formatPrice()` - Price formatting with correct decimals
- [ ] `getPnLColor()` - P&L color class

---

## 🎨 Design System

- [ ] Knights of the Blood Oath colors (crimson, red, base, app)
- [ ] Inter font for UI
- [ ] JetBrains Mono for numbers/prices
- [ ] Consistent spacing scale (2, 4, 8, 12, 16, 24, 32, 48, 64px)
- [ ] Card component pattern (rounded 8px, shadow, border)
- [ ] Button component pattern (rounded 6px, padding 12px 16px)
- [ ] Badge component pattern (full radius, padding 4px 12px)

---

## 🔒 Required Features

- [ ] Confirmation dialogs for ALL destructive actions
- [ ] Loading states during API calls (disable buttons)
- [ ] Error handling with toast notifications
- [ ] Success toast notifications
- [ ] Empty states for all lists
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Keyboard accessibility
- [ ] ARIA labels for icon buttons
- [ ] Focus indicators

---

## ⚡ Performance

- [ ] React Query configured (5s stale time, no refetch on focus)
- [ ] Code splitting (lazy load routes)
- [ ] Memoization for expensive calculations
- [ ] Load time < 3 seconds

---

## 🧪 Testing Verification

### Manual Trade Actions
- [ ] Close trade → Position closed in backend
- [ ] Breakeven → SL set to entry price in backend
- [ ] Partial 25% → 75% lots remain
- [ ] Partial 50% → 50% lots remain
- [ ] Partial 75% → 25% lots remain

### Timezone Conversion
- [ ] Trade history shows Lagos time (UTC+1)
- [ ] Time is exactly 1 hour ahead of UTC
- [ ] Format is correct ("Jun 08, 21:30")

### WebSocket Real-Time
- [ ] New trade appears in active trades list
- [ ] Closed trade disappears from active trades
- [ ] Notification appears in notification list
- [ ] Balance updates in accounts list

### CSV Export
- [ ] File downloads successfully
- [ ] Filename format: `trade_history_YYYY-MM-DD.csv`
- [ ] Contains all filtered trades
- [ ] All columns present

---

## 📋 TypeScript Types

- [ ] `Account` interface (20 fields)
- [ ] `Channel` interface (8 fields)
- [ ] `RiskProfile` interface (15 fields)
- [ ] `ActiveTrade` interface (16 fields)
- [ ] `TradeHistory` interface (17 fields)
- [ ] `Notification` interface (8 fields)
- [ ] `BotStatus` interface (7 fields)

---

## ✅ Final Verification

- [ ] All 35 API endpoints implemented
- [ ] All 7 pages implemented
- [ ] WebSocket connected and working
- [ ] Lagos timezone conversion correct
- [ ] CSV export working
- [ ] Manual actions working with confirmations
- [ ] Real-time updates working
- [ ] Theme colors correct
- [ ] Responsive on all screen sizes
- [ ] No console errors
- [ ] No TypeScript errors
- [ ] Performance < 3s load time

---

## 🚀 Deployment Ready

Once all items above are checked, the frontend is **ready for production** and will connect seamlessly to the Mirror Pupil backend!

**Backend API Base:** `http://localhost:8000` (development)  
**WebSocket URL:** `ws://localhost:8000/ws/updates`

---

*Mirror Pupil v5.1 Frontend Implementation Checklist*
