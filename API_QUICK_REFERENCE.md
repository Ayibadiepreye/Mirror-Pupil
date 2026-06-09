# Mirror Pupil API - Quick Reference

Fast reference for all 35 API endpoints. Keep this open while coding!

**Base URL:** `http://localhost:8000`  
**WebSocket:** `ws://localhost:8000/ws/updates`

---

## 📊 Accounts (8)

```typescript
// List all accounts
GET /api/accounts/
Response: Account[]

// Get account details
GET /api/accounts/{account_key}
Response: Account

// Create account
POST /api/accounts/
Body: { tl_email, tl_password, tl_prop_firm, tl_server, tl_account_id, display_name?, lot_size_override?, risk_profile_id? }
Response: Account

// Update account
PUT /api/accounts/{account_key}
Body: Same as POST
Response: Account

// Delete account
DELETE /api/accounts/{account_key}
Response: { success: boolean }

// Pause account
POST /api/accounts/{account_key}/pause
Body: {}
Response: { success: boolean }

// Resume account
POST /api/accounts/{account_key}/resume
Body: {}
Response: { success: boolean }

// Discover TradeLocker accounts
POST /api/accounts/discover
Body: { email, password, server, prop_firm }
Response: { accounts: Account[] }
```

---

## 📡 Channels (8)

```typescript
// List all channels
GET /api/channels/
Response: Channel[]

// Get channel
GET /api/channels/{channel_id}
Response: Channel

// Create channel
POST /api/channels/
Body: { channel_id: number, display_name, signal_prefix, entry_logic_module, management_logic_module, priority, enabled, notes? }
Response: Channel

// Update channel (full)
PUT /api/channels/{channel_id}
Body: Same as POST
Response: Channel

// Partial update
PATCH /api/channels/{channel_id}
Body: { display_name?, enabled?, priority?, ... }
Response: Channel

// Delete channel
DELETE /api/channels/{channel_id}
Response: { success: boolean }

// Enable channel
POST /api/channels/{channel_id}/enable
Body: {}
Response: { success: boolean }

// Disable channel
POST /api/channels/{channel_id}/disable
Body: {}
Response: { success: boolean }
```

---

## ⚠️ Risk Profiles (7)

```typescript
// List all profiles
GET /api/risk-profiles/
Response: RiskProfile[]

// Get profile
GET /api/risk-profiles/{profile_id}
Response: RiskProfile

// Get default profile
GET /api/risk-profiles/default
Response: RiskProfile

// Create profile
POST /api/risk-profiles/
Body: { 
  profile_name, is_default, max_risk_per_trade_pct, 
  daily_loss_pct, daily_trailing, overall_loss_pct, 
  overall_trailing, max_concurrent_trades, 
  commission_per_lot, safety_buffer_pct, ... 
}
Response: RiskProfile

// Update profile (full)
PUT /api/risk-profiles/{profile_id}
Body: Same as POST
Response: RiskProfile

// Partial update
PATCH /api/risk-profiles/{profile_id}
Body: { profile_name?, max_concurrent_trades?, ... }
Response: RiskProfile

// Delete profile
DELETE /api/risk-profiles/{profile_id}
Response: { success: boolean }
```

---

## 📈 Trades (7)

```typescript
// List all active trades
GET /api/trades/active
Response: ActiveTrade[]

// List active trades by account
GET /api/trades/active/{account_key}
Response: ActiveTrade[]

// CLOSE ENTIRE POSITION ⚠️
POST /api/trades/active/{trade_id}/close
Body: {}
Response: { success: boolean, message: string }

// SET SL TO BREAKEVEN ⚠️
POST /api/trades/active/{trade_id}/breakeven
Body: {}
Response: { success: boolean, message: string }

// TAKE PARTIAL PROFIT ⚠️
POST /api/trades/active/{trade_id}/partial
Body: { percentage: 25 | 50 | 75 }
Response: { success: boolean, message: string, remaining_lots: number }

// Get trade history
GET /api/trades/history?account_key={key}&limit={n}&offset={n}
Query: account_key (optional), limit (default 50), offset (default 0)
Response: { trades: TradeHistory[], total: number }

// EXPORT CSV 📥
GET /api/trades/history/export?account_key={key}
Query: account_key (optional)
Response: CSV file download
```

---

## 🔔 Notifications (5)

```typescript
// List notifications
GET /api/notifications/?unread_only={bool}&limit={n}
Query: unread_only (default false), limit (default 50)
Response: Notification[]

// Create notification (optional)
POST /api/notifications/
Body: { category, severity, title, message, account_key?, metadata? }
Response: Notification

// Mark as read
PATCH /api/notifications/{notification_id}/read
Body: {}
Response: { success: boolean }

// Mark all as read
POST /api/notifications/mark-all-read
Body: {}
Response: { success: boolean, count: number }

// Delete notification
DELETE /api/notifications/{notification_id}
Response: { success: boolean }
```

---

## 🤖 Bot Control (4)

```typescript
// Get bot status
GET /api/bot/status
Response: BotStatus
{
  status: string,
  dry_run: boolean,
  active_accounts: number,
  paused_accounts: number,
  breached_accounts: number,
  total_active_trades: number,
  allow_weekend_trading: boolean,
  allow_eod_trading: boolean
}

// Start/Stop bot
POST /api/bot/control
Body: { action: "start" | "stop" }
Response: { success: boolean, status: string }

// FORCE CLOSE ALL POSITIONS ⚠️⚠️⚠️
POST /api/bot/force-close-all
Body: {}
Response: { success: boolean, closed_count: number }

// FORCE CLOSE ACCOUNT POSITIONS ⚠️⚠️
POST /api/bot/force-close-account/{account_key}
Body: {}
Response: { success: boolean, closed_count: number }
```

---

## 🌐 WebSocket Messages

```typescript
// Connect
const ws = new WebSocket('ws://localhost:8000/ws/updates')

// MESSAGE TYPE 1: Connection confirmation
{
  type: 'connection',
  status: 'connected',
  message: 'Mirror Pupil WebSocket connected',
  timestamp: '2026-06-08T20:30:00.000Z'
}

// MESSAGE TYPE 2: Trade update
{
  type: 'trade',
  data: {
    trade_id: 123,
    symbol: 'EURUSD',
    direction: 'BUY',
    status: 'filled',
    // ... all ActiveTrade fields
  },
  timestamp: '2026-06-08T20:30:00.000Z'
}

// MESSAGE TYPE 3: Balance update
{
  type: 'balance',
  data: {
    account_key: 'user@email.com:12345',
    balance: 10500.50,
    pnl: 45.20
  },
  timestamp: '2026-06-08T20:30:00.000Z'
}

// MESSAGE TYPE 4: Notification
{
  type: 'notification',
  data: {
    notification_id: 456,
    category: 'EXECUTION',
    severity: 'INFO',
    title: 'Trade Opened: EURUSD',
    message: 'Opened BUY 0.10 lots at 1.08500',
    // ... all Notification fields
  },
  timestamp: '2026-06-08T20:30:00.000Z'
}
```

---

## 🎯 Common Patterns

### React Query Mutation (Close Trade)
```typescript
const closeTradeMutation = useMutation({
  mutationFn: (tradeId: number) => 
    axios.post(`/api/trades/active/${tradeId}/close`, {}),
  onSuccess: () => {
    queryClient.invalidateQueries(['active-trades'])
    toast.success('Trade closed successfully')
  },
  onError: (error) => {
    toast.error('Failed to close trade')
  }
})

// Usage
<button onClick={() => closeTradeMutation.mutate(trade.trade_id)}>
  Close
</button>
```

### Confirmation Dialog Pattern
```typescript
const handleClose = async (tradeId: number) => {
  const confirmed = await confirm(
    `Close entire position for ${trade.symbol}?`
  )
  if (confirmed) {
    closeTradeMutation.mutate(tradeId)
  }
}
```

### WebSocket Handler
```typescript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  
  switch (message.type) {
    case 'trade':
      queryClient.invalidateQueries(['active-trades'])
      break
    case 'balance':
      queryClient.invalidateQueries(['accounts'])
      break
    case 'notification':
      queryClient.invalidateQueries(['notifications'])
      toast.info(message.data.title)
      break
  }
}
```

---

## 🚨 Important Notes

1. **Lagos Timezone:** Trade history exit_time must be converted from UTC to UTC+1 (Lagos/WAT)
2. **Confirmations:** ALL manual actions (close, breakeven, partial) require confirmation dialogs
3. **Time-Ago:** Active trades and notifications must show relative time ("3m ago")
4. **CSV Export:** Returns file download, not JSON
5. **WebSocket:** Must implement auto-reconnect with exponential backoff
6. **Notification Categories:** SIGNAL, EXECUTION, MANAGEMENT, BREACH, SYSTEM
7. **Notification Severities:** CRITICAL, ERROR, WARNING, INFO
8. **Partial Profit:** Only 25%, 50%, or 75% allowed

---

## 📱 HTTP Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `404` - Not Found
- `500` - Internal Server Error

---

## 🔑 TypeScript Types

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
  daily_pnl: number
  paused: boolean
  breached: boolean
  risk_profile_id: number | null
  lot_size_override: number | null
  max_concurrent_trades_override: number | null
  // ... more fields
}

interface ActiveTrade {
  trade_id: number
  account_key: string
  channel_id: number
  channel_name: string | null
  signal_id: string
  symbol: string
  direction: 'BUY' | 'SELL'
  entry_price: number
  sl: number | null
  tp: number | null
  lot_size: number
  entry_time: string // ISO 8601
  status: string
  risk_usd: number | null
  current_pnl: number | null  // Live unrealized P&L from TradeLocker
  // ... more fields
}

interface TradeHistory {
  history_id: number
  account_key: string
  channel_name: string | null
  symbol: string
  direction: 'BUY' | 'SELL'
  entry_price: number
  exit_price: number
  lot_size: number
  entry_time: string // ISO 8601
  exit_time: string // ISO 8601 (convert to Lagos UTC+1)
  pnl: number
  outcome: 'WIN' | 'LOSS' | 'BE'
  close_reason: string
  manual_action_type: string | null // 'CLOSE' | 'BREAKEVEN' | 'PARTIAL' | null
  // ... more fields
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
```

---

**Quick Tip:** Keep this reference open in a split screen while coding! 🚀

*Mirror Pupil v5.1 API Quick Reference*
