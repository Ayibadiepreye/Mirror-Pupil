// Mirror Pupil shared type definitions. Mirrors backend exactly.

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
  daily_drawdown_pct: number;
  daily_loss_limit_pct: number;
  overall_drawdown_pct: number;
  overall_loss_limit_pct: number;
  consistency_score: number | null;
  profitable_days_count: number;
  total_trading_days: number;
  required_profitable_days: number;
  profit_cap_enabled: boolean;
  profit_cap_type: string | null;
  profit_cap_value: number | null;
  profit_cap_buffer_pct: number;
  profit_cap_frozen: boolean;
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
  current_pnl: number | null;
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

export type NotificationCategory =
  | "SIGNAL"
  | "EXECUTION"
  | "MANAGEMENT"
  | "BREACH"
  | "SYSTEM";
export type NotificationSeverity = "CRITICAL" | "ERROR" | "WARNING" | "INFO";

export interface Notification {
  notification_id: number;
  account_key: string | null;
  category: NotificationCategory;
  severity: NotificationSeverity;
  title: string;
  message: string;
  metadata: unknown;
  read: boolean;
  created_at: string;
}

export interface BotStatus {
  status: string;
  dry_run: boolean;
  active_accounts: number;
  paused_accounts: number;
  breached_accounts: number;
  total_active_trades: number;
  allow_weekend_trading: boolean;
  allow_eod_trading: boolean;
}

export type WsMessage =
  | { type: "connection"; status: string; message: string; timestamp: string }
  | { type: "trade"; data: ActiveTrade; timestamp: string }
  | {
      type: "balance";
      data: { account_key: string; balance: number; pnl: number };
      timestamp: string;
    }
  | { type: "notification"; data: Notification; timestamp: string };

export interface User {
  user_id: string;
  email: string;
  display_name: string | null;
  is_super_admin: boolean;
  is_approved: boolean;
  created_at: string;
}
