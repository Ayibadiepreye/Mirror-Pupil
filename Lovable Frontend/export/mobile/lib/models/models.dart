// Mirror Pupil — Dart models mirroring the backend JSON schemas.
// 1:1 mirror of the web TypeScript types in src/lib/mp/types.ts.

double _d(dynamic v) => (v as num).toDouble();
double? _dn(dynamic v) => v == null ? null : (v as num).toDouble();

class Account {
  final String accountKey;
  final String credentialKey;
  final String tlAccountId;
  final String tlEmail;
  final String tlServer;
  final String tlPropFirm;
  final String? displayName;
  final double initialBalance;
  final double currentBalance;
  final double highestBankedBalance;
  final double? allTimeHighEquity;
  final bool profitLocked;
  final double dailyPnl;
  final double dailyStartBalance;
  final double lastSyncedBalance;
  final String? cycleStartDate;
  final double cycleBestDayPnl;
  final bool paused;
  final bool breached;
  final int? riskProfileId;
  final int? maxConcurrentTradesOverride;
  final double? lotSizeOverride;
  final double dailyDrawdownPct;
  final double dailyLossLimitPct;
  final double overallDrawdownPct;
  final double overallLossLimitPct;
  final double? consistencyScore;
  final int profitableDaysCount;
  final int totalTradingDays;
  final int requiredProfitableDays;
  final bool profitCapEnabled;
  final String? profitCapType;
  final double? profitCapValue;
  final double profitCapBufferPct;
  final bool profitCapFrozen;

  Account({
    required this.accountKey, required this.credentialKey, required this.tlAccountId,
    required this.tlEmail, required this.tlServer, required this.tlPropFirm, this.displayName,
    required this.initialBalance, required this.currentBalance,
    required this.highestBankedBalance, this.allTimeHighEquity, required this.profitLocked,
    required this.dailyPnl, required this.dailyStartBalance, required this.lastSyncedBalance,
    this.cycleStartDate, required this.cycleBestDayPnl,
    required this.paused, required this.breached, this.riskProfileId,
    this.maxConcurrentTradesOverride, this.lotSizeOverride,
    required this.dailyDrawdownPct, required this.dailyLossLimitPct,
    required this.overallDrawdownPct, required this.overallLossLimitPct,
    this.consistencyScore, required this.profitableDaysCount,
    required this.totalTradingDays, required this.requiredProfitableDays,
    required this.profitCapEnabled, this.profitCapType, this.profitCapValue,
    required this.profitCapBufferPct, required this.profitCapFrozen,
  });

  factory Account.fromJson(Map<String, dynamic> j) => Account(
    accountKey: j['account_key'],
    credentialKey: j['credential_key'] ?? '',
    tlAccountId: j['tl_account_id'].toString(),
    tlEmail: j['tl_email'],
    tlServer: j['tl_server'],
    tlPropFirm: j['tl_prop_firm'] ?? '',
    displayName: j['display_name'],
    initialBalance: _d(j['initial_balance']),
    currentBalance: _d(j['current_balance']),
    highestBankedBalance: _d(j['highest_banked_balance'] ?? j['current_balance']),
    allTimeHighEquity: _dn(j['all_time_high_equity']),
    profitLocked: j['profit_locked'] ?? false,
    dailyPnl: _d(j['daily_pnl']),
    dailyStartBalance: _d(j['daily_start_balance'] ?? j['current_balance']),
    lastSyncedBalance: _d(j['last_synced_balance'] ?? j['current_balance']),
    cycleStartDate: j['cycle_start_date'],
    cycleBestDayPnl: _d(j['cycle_best_day_pnl'] ?? 0),
    paused: j['paused'] ?? false,
    breached: j['breached'] ?? false,
    riskProfileId: j['risk_profile_id'],
    maxConcurrentTradesOverride: j['max_concurrent_trades_override'],
    lotSizeOverride: _dn(j['lot_size_override']),
    dailyDrawdownPct: _d(j['daily_drawdown_pct'] ?? 0),
    dailyLossLimitPct: _d(j['daily_loss_limit_pct'] ?? 5),
    overallDrawdownPct: _d(j['overall_drawdown_pct'] ?? 0),
    overallLossLimitPct: _d(j['overall_loss_limit_pct'] ?? 10),
    consistencyScore: _dn(j['consistency_score']),
    profitableDaysCount: j['profitable_days_count'] ?? 0,
    totalTradingDays: j['total_trading_days'] ?? 0,
    requiredProfitableDays: j['required_profitable_days'] ?? 5,
    profitCapEnabled: j['profit_cap_enabled'] ?? false,
    profitCapType: j['profit_cap_type'],
    profitCapValue: _dn(j['profit_cap_value']),
    profitCapBufferPct: _d(j['profit_cap_buffer_pct'] ?? 2.0),
    profitCapFrozen: j['profit_cap_frozen'] ?? false,
  );
}

class Channel {
  final int channelId;
  final String displayName;
  final String signalPrefix;
  final String entryLogicModule;
  final String managementLogicModule;
  final int priority;
  final bool enabled;
  final String? notes;

  Channel({
    required this.channelId, required this.displayName, required this.signalPrefix,
    required this.entryLogicModule, required this.managementLogicModule,
    required this.priority, required this.enabled, this.notes,
  });

  factory Channel.fromJson(Map<String, dynamic> j) => Channel(
    channelId: j['channel_id'],
    displayName: j['display_name'],
    signalPrefix: j['signal_prefix'],
    entryLogicModule: j['entry_logic_module'],
    managementLogicModule: j['management_logic_module'],
    priority: j['priority'],
    enabled: j['enabled'],
    notes: j['notes'],
  );

  Map<String, dynamic> toJson() => {
    'channel_id': channelId, 'display_name': displayName, 'signal_prefix': signalPrefix,
    'entry_logic_module': entryLogicModule, 'management_logic_module': managementLogicModule,
    'priority': priority, 'enabled': enabled, 'notes': notes,
  };

  Channel copyWith({
    int? channelId, String? displayName, String? signalPrefix,
    String? entryLogicModule, String? managementLogicModule,
    int? priority, bool? enabled, String? notes,
  }) => Channel(
    channelId: channelId ?? this.channelId,
    displayName: displayName ?? this.displayName,
    signalPrefix: signalPrefix ?? this.signalPrefix,
    entryLogicModule: entryLogicModule ?? this.entryLogicModule,
    managementLogicModule: managementLogicModule ?? this.managementLogicModule,
    priority: priority ?? this.priority,
    enabled: enabled ?? this.enabled,
    notes: notes ?? this.notes,
  );
}

class RiskProfile {
  final int profileId;
  final String profileName;
  final bool isDefault;
  final double maxRiskPerTradePct;
  final double dailyLossPct;
  final bool dailyTrailing;
  final double overallLossPct;
  final bool overallTrailing;
  final bool overallTrailFromClosedBalance;
  final double? profitLockPct;
  final double? profitLockFloorPct;
  final double payoutBufferPct;
  final int maxConcurrentTrades;
  final double commissionPerLot;
  final double safetyBufferPct;
  final String? notes;

  RiskProfile({
    required this.profileId, required this.profileName, required this.isDefault,
    required this.maxRiskPerTradePct, required this.dailyLossPct, required this.dailyTrailing,
    required this.overallLossPct, required this.overallTrailing,
    required this.overallTrailFromClosedBalance,
    this.profitLockPct, this.profitLockFloorPct,
    required this.payoutBufferPct, required this.maxConcurrentTrades,
    required this.commissionPerLot, required this.safetyBufferPct, this.notes,
  });

  factory RiskProfile.fromJson(Map<String, dynamic> j) => RiskProfile(
    profileId: j['profile_id'] ?? 0,
    profileName: j['profile_name'],
    isDefault: j['is_default'] ?? false,
    maxRiskPerTradePct: _d(j['max_risk_per_trade_pct']),
    dailyLossPct: _d(j['daily_loss_pct']),
    dailyTrailing: j['daily_trailing'] ?? false,
    overallLossPct: _d(j['overall_loss_pct']),
    overallTrailing: j['overall_trailing'] ?? false,
    overallTrailFromClosedBalance: j['overall_trail_from_closed_balance'] ?? false,
    profitLockPct: _dn(j['profit_lock_pct']),
    profitLockFloorPct: _dn(j['profit_lock_floor_pct']),
    payoutBufferPct: _d(j['payout_buffer_pct'] ?? 1),
    maxConcurrentTrades: j['max_concurrent_trades'] ?? 5,
    commissionPerLot: _d(j['commission_per_lot'] ?? 7),
    safetyBufferPct: _d(j['safety_buffer_pct'] ?? 0.5),
    notes: j['notes'],
  );

  Map<String, dynamic> toJson() => {
    'profile_name': profileName,
    'is_default': isDefault,
    'max_risk_per_trade_pct': maxRiskPerTradePct,
    'daily_loss_pct': dailyLossPct,
    'daily_trailing': dailyTrailing,
    'overall_loss_pct': overallLossPct,
    'overall_trailing': overallTrailing,
    'overall_trail_from_closed_balance': overallTrailFromClosedBalance,
    'profit_lock_pct': profitLockPct,
    'profit_lock_floor_pct': profitLockFloorPct,
    'payout_buffer_pct': payoutBufferPct,
    'max_concurrent_trades': maxConcurrentTrades,
    'commission_per_lot': commissionPerLot,
    'safety_buffer_pct': safetyBufferPct,
    'notes': notes,
  };
}

class ActiveTrade {
  final int tradeId;
  final String accountKey;
  final int channelId;
  final String? channelName;
  final String signalId;
  final String? subSignalId;
  final String symbol;
  final String direction; // BUY | SELL
  final double entryPrice;
  final double? sl;
  final double? tp;
  final double lotSize;
  final DateTime entryTime;
  final String? tlOrderId;
  final String? tlPositionId;
  final String status;
  final bool tp1Hit;
  final double? riskUsd;
  final double? currentPnl;

  ActiveTrade({
    required this.tradeId, required this.accountKey, required this.channelId,
    this.channelName, required this.signalId, this.subSignalId, required this.symbol,
    required this.direction, required this.entryPrice, this.sl, this.tp,
    required this.lotSize, required this.entryTime, this.tlOrderId, this.tlPositionId,
    required this.status, required this.tp1Hit, this.riskUsd, this.currentPnl,
  });

  factory ActiveTrade.fromJson(Map<String, dynamic> j) => ActiveTrade(
    tradeId: j['trade_id'],
    accountKey: j['account_key'],
    channelId: j['channel_id'],
    channelName: j['channel_name'],
    signalId: j['signal_id'],
    subSignalId: j['sub_signal_id'],
    symbol: j['symbol'],
    direction: j['direction'],
    entryPrice: _d(j['entry_price']),
    sl: _dn(j['sl']),
    tp: _dn(j['tp']),
    lotSize: _d(j['lot_size']),
    entryTime: DateTime.parse(j['entry_time']).toUtc(),
    tlOrderId: j['tl_order_id'],
    tlPositionId: j['tl_position_id'],
    status: j['status'] ?? 'OPEN',
    tp1Hit: j['tp1_hit'] ?? false,
    riskUsd: _dn(j['risk_usd']),
    currentPnl: _dn(j['current_pnl']),
  );
}

class TradeHistory {
  final int historyId;
  final String accountKey;
  final int channelId;
  final String? channelName;
  final String signalId;
  final String? subSignalId;
  final String symbol;
  final String direction;
  final double entryPrice;
  final double exitPrice;
  final double? sl;
  final double? tp;
  final double lotSize;
  final DateTime entryTime;
  final DateTime exitTime;
  final double pnl;
  final String outcome; // WIN | LOSS | BE
  final String closeReason;
  final String? manualActionType;

  TradeHistory({
    required this.historyId, required this.accountKey, required this.channelId,
    this.channelName, required this.signalId, this.subSignalId,
    required this.symbol, required this.direction,
    required this.entryPrice, required this.exitPrice, this.sl, this.tp,
    required this.lotSize, required this.entryTime, required this.exitTime,
    required this.pnl, required this.outcome, required this.closeReason,
    this.manualActionType,
  });

  factory TradeHistory.fromJson(Map<String, dynamic> j) => TradeHistory(
    historyId: j['history_id'],
    accountKey: j['account_key'],
    channelId: j['channel_id'],
    channelName: j['channel_name'],
    signalId: j['signal_id'] ?? '',
    subSignalId: j['sub_signal_id'],
    symbol: j['symbol'],
    direction: j['direction'],
    entryPrice: _d(j['entry_price']),
    exitPrice: _d(j['exit_price']),
    sl: _dn(j['sl']),
    tp: _dn(j['tp']),
    lotSize: _d(j['lot_size']),
    entryTime: DateTime.parse(j['entry_time']).toUtc(),
    exitTime: DateTime.parse(j['exit_time']).toUtc(),
    pnl: _d(j['pnl']),
    outcome: j['outcome'],
    closeReason: j['close_reason'],
    manualActionType: j['manual_action_type'],
  );
}

class Notification {
  final int notificationId;
  final String? accountKey;
  final String category; // SIGNAL | EXECUTION | MANAGEMENT | BREACH | SYSTEM
  final String severity; // CRITICAL | ERROR | WARNING | INFO
  final String title;
  final String message;
  final Map<String, dynamic> metadata;
  final bool read;
  final DateTime createdAt;

  Notification({
    required this.notificationId, this.accountKey, required this.category,
    required this.severity, required this.title, required this.message,
    required this.metadata, required this.read, required this.createdAt,
  });

  factory Notification.fromJson(Map<String, dynamic> j) => Notification(
    notificationId: j['notification_id'],
    accountKey: j['account_key'],
    category: j['category'],
    severity: j['severity'],
    title: j['title'],
    message: j['message'],
    metadata: (j['metadata'] is Map)
        ? Map<String, dynamic>.from(j['metadata'])
        : <String, dynamic>{},
    read: j['read'] ?? false,
    createdAt: DateTime.parse(j['created_at']).toUtc(),
  );
}

class BotStatus {
  final String status;
  final bool dryRun;
  final int activeAccounts;
  final int pausedAccounts;
  final int breachedAccounts;
  final int totalActiveTrades;
  final bool allowWeekendTrading;
  final bool allowEodTrading;

  BotStatus({
    required this.status, required this.dryRun,
    required this.activeAccounts, required this.pausedAccounts,
    required this.breachedAccounts, required this.totalActiveTrades,
    required this.allowWeekendTrading, required this.allowEodTrading,
  });

  factory BotStatus.fromJson(Map<String, dynamic> j) => BotStatus(
    status: j['status'],
    dryRun: j['dry_run'] ?? false,
    activeAccounts: j['active_accounts'] ?? 0,
    pausedAccounts: j['paused_accounts'] ?? 0,
    breachedAccounts: j['breached_accounts'] ?? 0,
    totalActiveTrades: j['total_active_trades'] ?? 0,
    allowWeekendTrading: j['allow_weekend_trading'] ?? false,
    allowEodTrading: j['allow_eod_trading'] ?? false,
  );
}

class User {
  final String userId;
  final String email;
  final String? displayName;
  final bool isSuperAdmin;
  final bool isApproved;
  final DateTime createdAt;

  User({
    required this.userId,
    required this.email,
    this.displayName,
    required this.isSuperAdmin,
    required this.isApproved,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> j) => User(
    userId: j['user_id'],
    email: j['email'],
    displayName: j['display_name'],
    isSuperAdmin: j['is_super_admin'] ?? false,
    isApproved: j['is_approved'] ?? false,
    createdAt: DateTime.parse(j['created_at']).toUtc(),
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────

String formatTimeAgo(DateTime time) {
  final diff = DateTime.now().toUtc().difference(time.toUtc());
  if (diff.inSeconds < 60) return 'just now';
  if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
  if (diff.inHours < 24) return '${diff.inHours}h ago';
  return '${diff.inDays}d ago';
}

// Lagos time using timezone package (requires timezone package)
String formatLagosTime(DateTime utc) {
  try {
    // Using intl package DateFormat with timezone support would be ideal,
    // but for simplicity, we use UTC+1 (WAT doesn't observe DST)
    final lagos = utc.toUtc().add(const Duration(hours: 1));
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    final m = months[lagos.month - 1];
    final d = lagos.day.toString().padLeft(2, '0');
    final h = lagos.hour.toString().padLeft(2, '0');
    final min = lagos.minute.toString().padLeft(2, '0');
    return '$m $d, $h:$min';
  } catch (e) {
    return utc.toString();
  }
}

String formatCurrency(double v) {
  final sign = v > 0 ? '+' : v < 0 ? '-' : '';
  return '$sign\$${v.abs().toStringAsFixed(2)}';
}

String formatBalance(double v) => '\$${v.toStringAsFixed(2)}';

String formatPrice(double v, String symbol) {
  if (symbol.length == 6 && !symbol.startsWith('XAG') && !symbol.startsWith('XAU')) {
    return v.toStringAsFixed(5);
  }
  return v.toStringAsFixed(2);
}

String shortenKey(String key) {
  final parts = key.split(':');
  if (parts.length == 2 && parts[0].length > 12) {
    return '${parts[0].substring(0, 4)}…${parts[0].substring(parts[0].length - 4)}:${parts[1]}';
  }
  return key;
}