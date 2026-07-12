// Mock data — used ONLY when USE_MOCK === "true" at build time.
// Production builds (USE_MOCK unset/false) always hit the real backend.

import '../models/models.dart';

final now = DateTime.now().toUtc();
DateTime ago(int ms) => now.subtract(Duration(milliseconds: ms));

final mockAccounts = <Account>[
  Account(
    accountKey: 'trader1@example.com:48721',
    credentialKey: 'trader1@example.com',
    tlAccountId: '48721',
    tlEmail: 'trader1@example.com',
    tlServer: 'FTMO-Demo',
    tlPropFirm: 'FTMO',
    displayName: 'FTMO 100K Challenge',
    initialBalance: 100000,
    currentBalance: 102450.25,
    highestBankedBalance: 103200,
    allTimeHighEquity: 103200,
    profitLocked: false,
    dailyPnl: 245.75,
    dailyStartBalance: 102204.5,
    lastSyncedBalance: 102450.25,
    cycleStartDate: ago(86400000 * 14).toIso8601String(),
    cycleBestDayPnl: 980,
    paused: false,
    breached: false,
    riskProfileId: 1,
    maxConcurrentTradesOverride: null,
    lotSizeOverride: null,
    profitCapEnabled: false,
    profitCapType: null,
    profitCapValue: null,
    profitCapBufferPct: 2.0,
    profitCapFrozen: false,
    dailyDrawdownPct: 2.4,
    dailyLossLimitPct: 5,
    overallDrawdownPct: 2.45,
    overallLossLimitPct: 10,
    consistencyScore: 72.5,
    profitableDaysCount: 8,
    totalTradingDays: 14,
    requiredProfitableDays: 5,
  ),
  Account(
    accountKey: 'trader2@example.com:33910',
    credentialKey: 'trader2@example.com',
    tlAccountId: '33910',
    tlEmail: 'trader2@example.com',
    tlServer: 'MFF-Live',
    tlPropFirm: 'MFF',
    displayName: 'MFF Funded 50K',
    initialBalance: 50000,
    currentBalance: 49120.4,
    highestBankedBalance: 50880,
    allTimeHighEquity: 50880,
    profitLocked: true,
    dailyPnl: -120.6,
    dailyStartBalance: 49241,
    lastSyncedBalance: 49120.4,
    cycleStartDate: ago(86400000 * 5).toIso8601String(),
    cycleBestDayPnl: 410,
    paused: true,
    breached: false,
    riskProfileId: 2,
    maxConcurrentTradesOverride: 3,
    lotSizeOverride: 0.5,
    profitCapEnabled: true,
    profitCapType: 'percentage',
    profitCapValue: 10.0,
    profitCapBufferPct: 2.0,
    profitCapFrozen: false,
    dailyDrawdownPct: 4.8,
    dailyLossLimitPct: 5,
    overallDrawdownPct: 1.76,
    overallLossLimitPct: 10,
    consistencyScore: null,
    profitableDaysCount: 3,
    totalTradingDays: 5,
    requiredProfitableDays: 5,
  ),
  Account(
    accountKey: 'trader3@example.com:88412',
    credentialKey: 'trader3@example.com',
    tlAccountId: '88412',
    tlEmail: 'trader3@example.com',
    tlServer: 'TFT-Demo',
    tlPropFirm: 'TFT',
    displayName: 'TFT Phase 1',
    initialBalance: 25000,
    currentBalance: 22100,
    highestBankedBalance: 25400,
    allTimeHighEquity: null,
    profitLocked: false,
    dailyPnl: 0,
    dailyStartBalance: 22100,
    lastSyncedBalance: 22100,
    cycleStartDate: ago(86400000 * 22).toIso8601String(),
    cycleBestDayPnl: 220,
    paused: false,
    breached: true,
    riskProfileId: 1,
    maxConcurrentTradesOverride: null,
    lotSizeOverride: null,
    profitCapEnabled: false,
    profitCapType: null,
    profitCapValue: null,
    profitCapBufferPct: 2.0,
    profitCapFrozen: false,
    dailyDrawdownPct: 0,
    dailyLossLimitPct: 5,
    overallDrawdownPct: 11.6,
    overallLossLimitPct: 10,
    consistencyScore: 0,
    profitableDaysCount: 2,
    totalTradingDays: 22,
    requiredProfitableDays: 5,
  ),
];

final mockChannels = <Channel>[
  Channel(
    channelId: -1001234567890,
    displayName: 'Apex Signals',
    signalPrefix: 'APEX',
    entryLogicModule: 'logic.entry.standard',
    managementLogicModule: 'logic.manage.trail_be',
    priority: 10,
    enabled: true,
    notes: 'Primary morning London session feed.',
  ),
  Channel(
    channelId: -1009876543210,
    displayName: 'NY Scalps',
    signalPrefix: 'NYS',
    entryLogicModule: 'logic.entry.scalp',
    managementLogicModule: 'logic.manage.tp1_partial',
    priority: 20,
    enabled: true,
    notes: null,
  ),
  Channel(
    channelId: -1005554443332,
    displayName: 'Swing Desk',
    signalPrefix: 'SWG',
    entryLogicModule: 'logic.entry.swing',
    managementLogicModule: 'logic.manage.runner',
    priority: 30,
    enabled: false,
    notes: 'Paused pending review.',
  ),
];

final mockRiskProfiles = <RiskProfile>[
  RiskProfile(
    profileId: 1,
    profileName: 'Standard Funded',
    isDefault: true,
    maxRiskPerTradePct: 0.5,
    dailyLossPct: 4,
    dailyTrailing: true,
    overallLossPct: 8,
    overallTrailing: true,
    overallTrailFromClosedBalance: true,
    profitLockPct: 5,
    profitLockFloorPct: 2,
    payoutBufferPct: 1,
    maxConcurrentTrades: 5,
    commissionPerLot: 7,
    safetyBufferPct: 0.5,
    notes: 'Default profile for funded prop accounts.',
  ),
  RiskProfile(
    profileId: 2,
    profileName: 'Aggressive Phase 1',
    isDefault: false,
    maxRiskPerTradePct: 1.5,
    dailyLossPct: 4.5,
    dailyTrailing: false,
    overallLossPct: 9,
    overallTrailing: false,
    overallTrailFromClosedBalance: false,
    profitLockPct: null,
    profitLockFloorPct: null,
    payoutBufferPct: 0.5,
    maxConcurrentTrades: 8,
    commissionPerLot: 7,
    safetyBufferPct: 0.25,
    notes: null,
  ),
];

final mockActiveTrades = <ActiveTrade>[
  ActiveTrade(
    tradeId: 9001,
    accountKey: 'trader1@example.com:48721',
    channelId: -1001234567890,
    channelName: 'Apex Signals',
    signalId: 'APEX-2410',
    subSignalId: null,
    symbol: 'EURUSD',
    direction: 'BUY',
    entryPrice: 1.08545,
    sl: 1.0834,
    tp: 1.0895,
    lotSize: 0.5,
    entryTime: ago(15 * 60000),
    tlOrderId: 'ord-1',
    tlPositionId: 'pos-1',
    status: 'filled',
    tp1Hit: false,
    riskUsd: 102.5,
    currentPnl: 45.75,
  ),
  ActiveTrade(
    tradeId: 9002,
    accountKey: 'trader1@example.com:48721',
    channelId: -1009876543210,
    channelName: 'NY Scalps',
    signalId: 'NYS-883',
    subSignalId: 'B',
    symbol: 'XAUUSD',
    direction: 'SELL',
    entryPrice: 2342.55,
    sl: 2349.0,
    tp: 2330.0,
    lotSize: 0.25,
    entryTime: ago(2 * 3600000 + 12 * 60000),
    tlOrderId: 'ord-2',
    tlPositionId: 'pos-2',
    status: 'filled',
    tp1Hit: true,
    riskUsd: 161.25,
    currentPnl: -23.50,
  ),
  ActiveTrade(
    tradeId: 9003,
    accountKey: 'trader2@example.com:33910',
    channelId: -1001234567890,
    channelName: 'Apex Signals',
    signalId: 'APEX-2411',
    subSignalId: null,
    symbol: 'GBPJPY',
    direction: 'BUY',
    entryPrice: 198.245,
    sl: 197.8,
    tp: 199.1,
    lotSize: 0.3,
    entryTime: ago(42 * 60000),
    tlOrderId: 'ord-3',
    tlPositionId: 'pos-3',
    status: 'filled',
    tp1Hit: false,
    riskUsd: 89.1,
    currentPnl: 12.30,
  ),
];

final _symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'GBPJPY'];
final _closeReasons = ['TP_HIT', 'SL_HIT', 'MANUAL', 'EOD', 'BREACH'];

final mockTradeHistory = List.generate(84, (i) {
  final symbol = _symbols[i % _symbols.length];
  final dir = i % 2 == 0 ? 'BUY' : 'SELL';
  final entry = 1 + ((i * 13) % 200) / 1000;
  final pnl = ((i * 37) % 280) - 120.0;
  final outcome = pnl > 0 ? 'WIN' : pnl < 0 ? 'LOSS' : 'BE';
  final manual = i % 11 == 0 ? 'PARTIAL' : i % 17 == 0 ? 'CLOSE' : null;
  return TradeHistory(
    historyId: 7000 + i,
    accountKey: i % 3 == 0
        ? 'trader1@example.com:48721'
        : i % 3 == 1
            ? 'trader2@example.com:33910'
            : 'trader3@example.com:88412',
    channelId: i % 2 == 1 ? -1001234567890 : -1009876543210,
    channelName: i % 2 == 1 ? 'Apex Signals' : 'NY Scalps',
    signalId: 'SIG-${7000 + i}',
    subSignalId: null,
    symbol: symbol,
    direction: dir,
    entryPrice: entry,
    exitPrice: entry + (dir == 'BUY' ? pnl / 10000 : -pnl / 10000),
    sl: entry - 0.002,
    tp: entry + 0.003,
    lotSize: 0.1 + (i % 5) * 0.1,
    entryTime: ago((i + 1) * 3600000),
    exitTime: ago(i * 3600000),
    pnl: pnl,
    outcome: outcome,
    closeReason: _closeReasons[i % _closeReasons.length],
    manualActionType: manual,
  );
});

final mockNotifications = <Notification>[
  Notification(
    notificationId: 5001,
    accountKey: 'trader1@example.com:48721',
    category: 'EXECUTION',
    severity: 'INFO',
    title: 'Trade Opened: EURUSD',
    message: 'Opened BUY 0.50 lots at 1.08545',
    metadata: {'trade_id': 9001},
    read: false,
    createdAt: ago(3 * 60000),
  ),
  Notification(
    notificationId: 5002,
    accountKey: 'trader3@example.com:88412',
    category: 'BREACH',
    severity: 'CRITICAL',
    title: 'Daily loss limit breached',
    message: 'Account TFT Phase 1 hit -\$2,900 daily loss. Trading suspended.',
    metadata: {'account': 'trader3@example.com:88412', 'loss': -2900},
    read: false,
    createdAt: ago(8 * 60000),
  ),
  Notification(
    notificationId: 5003,
    accountKey: null,
    category: 'SYSTEM',
    severity: 'WARNING',
    title: 'TradeLocker reconnect',
    message: 'Lost session to MFF-Live. Reconnected after 14s.',
    metadata: {},
    read: false,
    createdAt: ago(35 * 60000),
  ),
  Notification(
    notificationId: 5004,
    accountKey: 'trader1@example.com:48721',
    category: 'MANAGEMENT',
    severity: 'INFO',
    title: 'Breakeven set',
    message: 'XAUUSD #9002 SL moved to entry after TP1.',
    metadata: {},
    read: true,
    createdAt: ago(2 * 3600000),
  ),
  Notification(
    notificationId: 5005,
    accountKey: null,
    category: 'SIGNAL',
    severity: 'INFO',
    title: 'Signal received: APEX-2411',
    message: 'BUY GBPJPY @ 198.245 SL 197.8 TP 199.1',
    metadata: {},
    read: true,
    createdAt: ago(50 * 60000),
  ),
];

final mockBotStatus = BotStatus(
  status: 'running',
  dryRun: false,
  activeAccounts: 2,
  pausedAccounts: 1,
  breachedAccounts: 1,
  totalActiveTrades: 3,
  allowWeekendTrading: false,
  allowEodTrading: true,
);

// ─── In-memory store for mock mutations ────────────────────────────────

class MockStore {
  List<Account> accounts = List.from(mockAccounts);
  List<Channel> channels = List.from(mockChannels);
  List<RiskProfile> profiles = List.from(mockRiskProfiles);
  List<ActiveTrade> trades = List.from(mockActiveTrades);
  List<TradeHistory> history = List.from(mockTradeHistory);
  List<Notification> notifications = List.from(mockNotifications);
  BotStatus bot = mockBotStatus;

  void reset() {
    accounts = List.from(mockAccounts);
    channels = List.from(mockChannels);
    profiles = List.from(mockRiskProfiles);
    trades = List.from(mockActiveTrades);
    history = List.from(mockTradeHistory);
    notifications = List.from(mockNotifications);
    bot = mockBotStatus;
  }
}

final mockStore = MockStore();
