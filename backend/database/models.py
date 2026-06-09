"""
Mirror Pupil v5.1 - Database Models
Pydantic models for type safety and validation.
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class Channel(BaseModel):
    """Signal source channel."""
    channel_id: int
    display_name: str  # Custom GUI name (required)
    signal_prefix: str
    entry_logic_module: str
    management_logic_module: str
    priority: int = 10
    enabled: bool = True
    created_at: Optional[datetime] = None
    notes: Optional[str] = None


class RiskProfile(BaseModel):
    """Named risk management rule set."""
    profile_id: Optional[int] = None
    profile_name: str
    is_default: bool = False
    user_id: Optional[str] = None  # Owner user ID (None for default profile)
    max_risk_per_trade_pct: float = 1.0
    daily_loss_pct: float = 3.0
    daily_trailing: bool = True
    overall_loss_pct: float = 6.0
    overall_trailing: bool = True
    overall_trail_from_closed_balance: bool = True
    profit_lock_pct: Optional[float] = None
    profit_lock_floor_pct: Optional[float] = None
    payout_buffer_pct: float = 1.0
    max_concurrent_trades: int = 5
    commission_per_lot: float = 6.0
    safety_buffer_pct: float = 10.0
    created_at: Optional[datetime] = None
    notes: Optional[str] = None


class Account(BaseModel):
    """TradeLocker sub-account."""
    account_key: str
    credential_key: str
    tl_account_id: str
    tl_email: str
    tl_password: str  # Should be encrypted
    tl_server: str = "live"  # Environment: "live" or "demo"
    tl_prop_firm: str = ""  # Broker/Prop firm name (e.g., "Blue Guardian")
    display_name: Optional[str] = None  # Custom GUI name
    user_id: Optional[str] = None  # Owner user ID
    lot_size_override: Optional[float] = None  # Per-account lot size
    initial_balance: Optional[float] = None
    current_balance: Optional[float] = None
    highest_banked_balance: Optional[float] = None
    all_time_high_equity: Optional[float] = None
    profit_locked: bool = False
    daily_pnl: float = 0.0
    daily_start_balance: Optional[float] = None
    last_synced_balance: Optional[float] = None
    cycle_start_date: Optional[date] = None
    cycle_best_day_pnl: float = 0.0
    paused: bool = False
    breached: bool = False
    risk_profile_id: Optional[int] = None
    max_concurrent_trades_override: Optional[int] = None


class ChannelSubscription(BaseModel):
    """Per-account channel copy settings."""
    id: Optional[int] = None
    account_key: str
    channel_id: int
    enabled: bool = True


class ActiveTrade(BaseModel):
    """Currently open position."""
    trade_id: Optional[int] = None
    account_key: str
    channel_id: int
    channel_name: Optional[str] = None  # For display without joins
    signal_id: str
    sub_signal_id: Optional[str] = None
    symbol: str
    direction: str  # BUY or SELL
    entry_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    lot_size: float
    entry_time: Optional[datetime] = None
    tl_order_id: Optional[str] = None
    tl_position_id: Optional[str] = None
    status: str  # pending, filled, failed, partially_filled
    tp1_hit: bool = False
    risk_usd: Optional[float] = None


class WaitingRoom(BaseModel):
    """Incomplete signal awaiting completion."""
    id: Optional[int] = None
    channel_id: int
    symbol: str
    direction: str
    entry_msg_id: int
    entry_time: Optional[datetime] = None
    expires_at: datetime


class TradeHistory(BaseModel):
    """Closed trade record."""
    history_id: Optional[int] = None
    account_key: str
    channel_id: int
    channel_name: Optional[str] = None  # For display without joins
    signal_id: str
    sub_signal_id: Optional[str] = None
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    lot_size: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    pnl: float
    outcome: str  # WIN, LOSS, BE
    close_reason: str  # TP_HIT, SL_HIT, MANUAL, AUTONOMOUS, EOD, WEEKEND
    manual_action_type: Optional[str] = None  # MANUAL_CLOSE, MANUAL_BE, MANUAL_PARTIAL


class ProfitableDay(BaseModel):
    """Daily P&L tracking for consistency score."""
    id: Optional[int] = None
    account_key: str
    date: date
    pnl: float
    is_profitable_day: bool


class MessageCache(BaseModel):
    """Ephemeral message deduplication."""
    msg_id: int
    channel_id: int
    processed_at: Optional[datetime] = None


class Notification(BaseModel):
    """Real-time notification for GUI."""
    notification_id: Optional[int] = None
    account_key: Optional[str] = None
    category: str  # SIGNAL, EXECUTION, MANAGEMENT, BREACH, SYSTEM
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    title: str
    message: str
    metadata: Optional[dict] = None  # Additional data
    read: bool = False
    created_at: Optional[datetime] = None


class ManualAction(BaseModel):
    """Audit trail for manual user actions."""
    action_id: Optional[int] = None
    account_key: str
    trade_id: Optional[int] = None
    action_type: str  # MANUAL_CLOSE, MANUAL_BE, MANUAL_PARTIAL_25, etc.
    action_data: Optional[dict] = None  # Additional details
    performed_at: Optional[datetime] = None




class Notification(BaseModel):
    """Real-time notification for GUI display."""
    notification_id: Optional[int] = None
    account_key: Optional[str] = None
    category: str  # SIGNAL, EXECUTION, MANAGEMENT, BREACH, SYSTEM
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    title: str
    message: str
    metadata: Optional[dict] = None
    read: bool = False
    created_at: Optional[datetime] = None


class ManualAction(BaseModel):
    """Audit record for manual user actions."""
    action_id: Optional[int] = None
    account_key: str
    trade_id: Optional[int] = None
    action_type: str  # MANUAL_CLOSE, MANUAL_BE, MANUAL_PARTIAL_25, etc.
    action_data: Optional[dict] = None
    performed_at: Optional[datetime] = None
