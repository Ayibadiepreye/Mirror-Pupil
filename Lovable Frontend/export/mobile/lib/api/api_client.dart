// Mirror Pupil — REST client for the Flutter app.
import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/models.dart';
import '../auth/auth_service.dart';
import 'mock_data.dart';

class MpConfig {
  /// Override at build time:
  /// flutter run --dart-define=API_BASE_URL=https://api.example.com
  /// flutter run --dart-define=USE_MOCK=true
  static const apiBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: 'https://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil');
  static const wsBaseUrl =
      String.fromEnvironment('WS_BASE_URL', defaultValue: 'wss://win-ka0c6cpkmms.tailc9cd79.ts.net/mirrorpupil');
  static const useMock =
      String.fromEnvironment('USE_MOCK', defaultValue: 'false') == 'true';
}

class ApiException implements Exception {
  final int status;
  final String message;
  ApiException(this.status, this.message);
  @override
  String toString() => 'ApiException($status): $message';
}

class MpApi {
  final http.Client _http;
  final String baseUrl;

  MpApi({http.Client? client, String? baseUrl})
      : _http = client ?? http.Client(),
        baseUrl = baseUrl ?? MpConfig.apiBaseUrl;

  Uri _u(String path, [Map<String, dynamic>? q]) {
    return Uri.parse('$baseUrl$path').replace(
      queryParameters: q?.map((k, v) => MapEntry(k, '$v')),
    );
  }

  Future<dynamic> _send(String method, String path,
      {Object? body, Map<String, dynamic>? query}) async {
    final uri = _u(path, query);
    final headers = {'Content-Type': 'application/json'};
    
    // Add Authorization header with Firebase JWT token
    final session = auth.current;
    if (session != null) {
      headers['Authorization'] = 'Bearer ${session.token}';
    }
    
    late http.Response r;
    switch (method) {
      case 'GET': r = await _http.get(uri, headers: headers); break;
      case 'POST': r = await _http.post(uri, headers: headers, body: jsonEncode(body ?? {})); break;
      case 'PUT': r = await _http.put(uri, headers: headers, body: jsonEncode(body ?? {})); break;
      case 'PATCH': r = await _http.patch(uri, headers: headers, body: jsonEncode(body ?? {})); break;
      case 'DELETE': r = await _http.delete(uri, headers: headers); break;
      default: throw StateError('Unsupported method $method');
    }
    
    // Handle 401 Unauthorized - token expired or invalid
    if (r.statusCode == 401) {
      // Try to refresh token once
      await auth.refreshToken();
      final newSession = auth.current;
      if (newSession != null) {
        headers['Authorization'] = 'Bearer ${newSession.token}';
        // Retry request with new token
        switch (method) {
          case 'GET': r = await _http.get(uri, headers: headers); break;
          case 'POST': r = await _http.post(uri, headers: headers, body: jsonEncode(body ?? {})); break;
          case 'PUT': r = await _http.put(uri, headers: headers, body: jsonEncode(body ?? {})); break;
          case 'PATCH': r = await _http.patch(uri, headers: headers, body: jsonEncode(body ?? {})); break;
          case 'DELETE': r = await _http.delete(uri, headers: headers); break;
        }
      }
    }
    
    if (r.statusCode >= 200 && r.statusCode < 300) {
      if (r.body.isEmpty) return null;
      return jsonDecode(r.body);
    }
    throw ApiException(r.statusCode, r.body);
  }

  Future<T> _delay<T>(T value) async {
    await Future.delayed(const Duration(milliseconds: 120));
    return value;
  }

  // ───── Accounts ─────
  Future<List<Account>> listAccounts() async {
    if (MpConfig.useMock) return _delay(mockStore.accounts);
    final l = await _send('GET', '/api/accounts/') as List;
    return l.map((j) => Account.fromJson(j)).toList();
  }
  Future<Account> getAccount(String key) async {
    if (MpConfig.useMock) {
      return _delay(mockStore.accounts.firstWhere((a) => a.accountKey == key));
    }
    return Account.fromJson(await _send('GET', '/api/accounts/${Uri.encodeComponent(key)}'));
  }
  Future<Account> createAccount(Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      final acc = Account.fromJson({...body, 'account_key': 'mock-${DateTime.now().millisecondsSinceEpoch}'});
      mockStore.accounts.add(acc);
      return _delay(acc);
    }
    return Account.fromJson(await _send('POST', '/api/accounts/', body: body));
  }
  Future<Account> updateAccount(String key, Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      final idx = mockStore.accounts.indexWhere((a) => a.accountKey == key);
      // For mock mode, just return the updated body as an account
      // In real implementation, Account would need a toJson() method
      return _delay(mockStore.accounts[idx]);
    }
    return Account.fromJson(await _send('PUT', '/api/accounts/${Uri.encodeComponent(key)}', body: body));
  }
  Future<void> deleteAccount(String key) async {
    if (MpConfig.useMock) {
      mockStore.accounts.removeWhere((a) => a.accountKey == key);
      return _delay(null);
    }
    return _send('DELETE', '/api/accounts/${Uri.encodeComponent(key)}');
  }
  Future<void> pauseAccount(String key) async {
    if (MpConfig.useMock) {
      // In mock mode, we'd need to rebuild the account with paused=true
      // Since Account is immutable and has no copyWith, we just keep it as-is
      return _delay(null);
    }
    return _send('POST', '/api/accounts/${Uri.encodeComponent(key)}/pause');
  }
  Future<void> resumeAccount(String key) async {
    if (MpConfig.useMock) {
      // In mock mode, we'd need to rebuild the account with paused=false
      // Since Account is immutable and has no copyWith, we just keep it as-is
      return _delay(null);
    }
    return _send('POST', '/api/accounts/${Uri.encodeComponent(key)}/resume');
  }
  
  Future<Account> updateProfitCap(String key, Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      return _delay(mockStore.accounts.firstWhere((a) => a.accountKey == key));
    }
    return Account.fromJson(await _send('POST', '/api/accounts/${Uri.encodeComponent(key)}/profit-cap', body: body));
  }
  
  Future<Account> unfreezeProfitCap(String key) async {
    if (MpConfig.useMock) {
      return _delay(mockStore.accounts.firstWhere((a) => a.accountKey == key));
    }
    return Account.fromJson(await _send('POST', '/api/accounts/${Uri.encodeComponent(key)}/unfreeze-profit-cap'));
  }
  
  Future<List<Map<String, dynamic>>> discoverAccounts(Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      return _delay([
        {'id': '123456', 'number': 'ACC-001', 'balance': 10000.0},
        {'id': '789012', 'number': 'ACC-002', 'balance': 5000.0}
      ]);
    }
    final r = await _send('POST', '/api/accounts/discover', body: body);
    return List<Map<String, dynamic>>.from(r['accounts']);
  }

  // ───── Channels ─────
  Future<List<Channel>> listChannels() async {
    if (MpConfig.useMock) return _delay(mockStore.channels);
    final l = await _send('GET', '/api/channels/') as List;
    return l.map((j) => Channel.fromJson(j)).toList();
  }
  Future<Channel> createChannel(Channel c) async {
    if (MpConfig.useMock) {
      mockStore.channels.add(c);
      return _delay(c);
    }
    return Channel.fromJson(await _send('POST', '/api/channels/', body: c.toJson()));
  }
  Future<Channel> updateChannel(int id, Channel c) async {
    if (MpConfig.useMock) {
      final idx = mockStore.channels.indexWhere((ch) => ch.channelId == id);
      mockStore.channels[idx] = c;
      return _delay(c);
    }
    return Channel.fromJson(await _send('PUT', '/api/channels/$id', body: c.toJson()));
  }
  Future<Channel> patchChannel(int id, Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      final idx = mockStore.channels.indexWhere((ch) => ch.channelId == id);
      final updated = mockStore.channels[idx].copyWith(
        enabled: body['enabled'] ?? mockStore.channels[idx].enabled,
      );
      mockStore.channels[idx] = updated;
      return _delay(updated);
    }
    return Channel.fromJson(await _send('PATCH', '/api/channels/$id', body: body));
  }
  Future<void> deleteChannel(int id) async {
    if (MpConfig.useMock) {
      mockStore.channels.removeWhere((ch) => ch.channelId == id);
      return _delay(null);
    }
    return _send('DELETE', '/api/channels/$id');
  }
  Future<void> enableChannel(int id) async {
    if (MpConfig.useMock) {
      final idx = mockStore.channels.indexWhere((ch) => ch.channelId == id);
      mockStore.channels[idx] = mockStore.channels[idx].copyWith(enabled: true);
      return _delay(null);
    }
    return _send('POST', '/api/channels/$id/enable');
  }
  Future<void> disableChannel(int id) async {
    if (MpConfig.useMock) {
      final idx = mockStore.channels.indexWhere((ch) => ch.channelId == id);
      mockStore.channels[idx] = mockStore.channels[idx].copyWith(enabled: false);
      return _delay(null);
    }
    return _send('POST', '/api/channels/$id/disable');
  }

  // ───── Risk Profiles ─────
  Future<List<RiskProfile>> listProfiles() async {
    if (MpConfig.useMock) return _delay(mockStore.profiles);
    final l = await _send('GET', '/api/risk-profiles/') as List;
    return l.map((j) => RiskProfile.fromJson(j)).toList();
  }
  Future<RiskProfile> defaultProfile() async {
    if (MpConfig.useMock) return _delay(mockStore.profiles.firstWhere((p) => p.isDefault));
    return RiskProfile.fromJson(await _send('GET', '/api/risk-profiles/default'));
  }
  Future<RiskProfile> createProfile(Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      final prof = RiskProfile.fromJson({...body, 'profile_id': mockStore.profiles.length + 1});
      mockStore.profiles.add(prof);
      return _delay(prof);
    }
    return RiskProfile.fromJson(await _send('POST', '/api/risk-profiles/', body: body));
  }
  Future<RiskProfile> updateProfile(int id, Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      final idx = mockStore.profiles.indexWhere((p) => p.profileId == id);
      final updated = RiskProfile.fromJson({...body, 'profile_id': id});
      mockStore.profiles[idx] = updated;
      return _delay(updated);
    }
    return RiskProfile.fromJson(await _send('PUT', '/api/risk-profiles/$id', body: body));
  }
  Future<RiskProfile> patchProfile(int id, Map<String, dynamic> body) async {
    if (MpConfig.useMock) {
      final idx = mockStore.profiles.indexWhere((p) => p.profileId == id);
      final current = mockStore.profiles[idx].toJson();
      final updated = RiskProfile.fromJson({...current, ...body, 'profile_id': id});
      mockStore.profiles[idx] = updated;
      return _delay(updated);
    }
    return RiskProfile.fromJson(await _send('PATCH', '/api/risk-profiles/$id', body: body));
  }
  Future<void> deleteProfile(int id) async {
    if (MpConfig.useMock) {
      mockStore.profiles.removeWhere((p) => p.profileId == id);
      return _delay(null);
    }
    return _send('DELETE', '/api/risk-profiles/$id');
  }

  // ───── Trades ─────
  Future<List<ActiveTrade>> activeTrades({String? accountKey}) async {
    if (MpConfig.useMock) {
      final filtered = accountKey == null
          ? mockStore.trades
          : mockStore.trades.where((t) => t.accountKey == accountKey).toList();
      return _delay(filtered);
    }
    final path = accountKey == null
        ? '/api/trades/active'
        : '/api/trades/active/${Uri.encodeComponent(accountKey)}';
    final l = await _send('GET', path) as List;
    return l.map((j) => ActiveTrade.fromJson(j)).toList();
  }
  Future<Map<String, dynamic>> closeTrade(int id) async {
    if (MpConfig.useMock) {
      mockStore.trades.removeWhere((t) => t.tradeId == id);
      return _delay({'success': true, 'message': 'Closed trade $id'});
    }
    return (await _send('POST', '/api/trades/active/$id/close', body: {
      'action_type': 'MANUAL_CLOSE',
      'reason': 'User initiated close'
    })) as Map<String, dynamic>;
  }
  Future<Map<String, dynamic>> breakevenTrade(int id) async {
    if (MpConfig.useMock) {
      final idx = mockStore.trades.indexWhere((t) => t.tradeId == id);
      final trade = mockStore.trades[idx];
      mockStore.trades[idx] = ActiveTrade.fromJson({
        ...{
          'trade_id': trade.tradeId,
          'account_key': trade.accountKey,
          'channel_id': trade.channelId,
          'channel_name': trade.channelName,
          'signal_id': trade.signalId,
          'symbol': trade.symbol,
          'direction': trade.direction,
          'entry_price': trade.entryPrice,
          'tp': trade.tp,
          'lot_size': trade.lotSize,
          'entry_time': trade.entryTime.toIso8601String(),
          'status': trade.status,
          'tp1_hit': trade.tp1Hit,
        },
        'sl': trade.entryPrice,
      });
      return _delay({'success': true, 'message': 'Breakeven set on $id'});
    }
    return (await _send('POST', '/api/trades/active/$id/breakeven', body: {
      'action_type': 'MANUAL_BE',
      'reason': 'User set breakeven'
    })) as Map<String, dynamic>;
  }
  Future<Map<String, dynamic>> partialTrade(int id, int percentage) async {
    if (MpConfig.useMock) {
      final idx = mockStore.trades.indexWhere((t) => t.tradeId == id);
      final trade = mockStore.trades[idx];
      final newLots = (trade.lotSize * (1 - percentage / 100)).toStringAsFixed(2);
      mockStore.trades[idx] = ActiveTrade.fromJson({
        'trade_id': trade.tradeId,
        'account_key': trade.accountKey,
        'channel_id': trade.channelId,
        'channel_name': trade.channelName,
        'signal_id': trade.signalId,
        'symbol': trade.symbol,
        'direction': trade.direction,
        'entry_price': trade.entryPrice,
        'sl': trade.sl,
        'tp': trade.tp,
        'lot_size': double.parse(newLots),
        'entry_time': trade.entryTime.toIso8601String(),
        'status': trade.status,
        'tp1_hit': trade.tp1Hit,
      });
      return _delay({'success': true, 'message': 'Closed $percentage% of $id', 'remaining_lots': double.parse(newLots)});
    }
    return (await _send('POST', '/api/trades/active/$id/partial', body: {
      'action_type': 'MANUAL_PARTIAL_$percentage',
      'reason': 'User closed $percentage%',
      'percentage': percentage
    })) as Map<String, dynamic>;
  }
  Future<({List<TradeHistory> trades, int total})> tradeHistory({
    String? accountKey, int limit = 50, int offset = 0,
  }) async {
    if (MpConfig.useMock) {
      final filtered = accountKey == null
          ? mockStore.history
          : mockStore.history.where((t) => t.accountKey == accountKey).toList();
      final paginated = filtered.skip(offset).take(limit).toList();
      return _delay((trades: paginated, total: filtered.length));
    }
    final r = await _send('GET', '/api/trades/history', query: {
      if (accountKey != null) 'account_key': accountKey,
      'limit': limit, 'offset': offset,
    }) as Map<String, dynamic>;
    return (
      trades: (r['trades'] as List).map((j) => TradeHistory.fromJson(j)).toList(),
      total: r['total'] as int,
    );
  }
  String historyExportUrl({String? accountKey}) {
    final q = accountKey == null ? '' : '?account_key=${Uri.encodeComponent(accountKey)}';
    return '$baseUrl/api/trades/history/export$q';
  }
  Future<List<int>> historyExportBytes({String? accountKey}) async {
    if (MpConfig.useMock) {
      // Generate CSV from mock data
      final filtered = accountKey == null
          ? mockStore.history
          : mockStore.history.where((t) => t.accountKey == accountKey).toList();
      const header = 'history_id,account_key,channel_name,symbol,direction,entry_price,exit_price,lot_size,entry_time,exit_time,pnl,outcome,close_reason,manual_action_type\n';
      final rows = filtered.map((t) => '${t.historyId},${t.accountKey},${t.channelName},${t.symbol},${t.direction},${t.entryPrice},${t.exitPrice},${t.lotSize},${t.entryTime},${t.exitTime},${t.pnl},${t.outcome},${t.closeReason},${t.manualActionType ?? ''}').join('\n');
      return _delay((header + rows).codeUnits);
    }
    final r = await _http.get(Uri.parse(historyExportUrl(accountKey: accountKey)));
    if (r.statusCode >= 200 && r.statusCode < 300) return r.bodyBytes;
    throw ApiException(r.statusCode, r.body);
  }

  // ───── Notifications ─────
  Future<List<Notification>> listNotifications({bool unreadOnly = false, int limit = 50}) async {
    if (MpConfig.useMock) {
      final filtered = unreadOnly
          ? mockStore.notifications.where((n) => !n.read).toList()
          : mockStore.notifications;
      return _delay(filtered.take(limit).toList());
    }
    final l = await _send('GET', '/api/notifications/', query: {
      'unread_only': unreadOnly, 'limit': limit,
    }) as List;
    return l.map((j) => Notification.fromJson(j)).toList();
  }
  Future<void> markNotificationRead(int id) async {
    if (MpConfig.useMock) {
      final idx = mockStore.notifications.indexWhere((n) => n.notificationId == id);
      if (idx >= 0) {
        final n = mockStore.notifications[idx];
        mockStore.notifications[idx] = Notification.fromJson({
          'notification_id': n.notificationId,
          'account_key': n.accountKey,
          'category': n.category,
          'severity': n.severity,
          'title': n.title,
          'message': n.message,
          'metadata': n.metadata,
          'read': true,
          'created_at': n.createdAt.toIso8601String(),
        });
      }
      return _delay(null);
    }
    return _send('PATCH', '/api/notifications/$id/read');
  }
  Future<int> markAllNotificationsRead() async {
    if (MpConfig.useMock) {
      final count = mockStore.notifications.where((n) => !n.read).length;
      mockStore.notifications = mockStore.notifications.map((n) => Notification.fromJson({
        'notification_id': n.notificationId,
        'account_key': n.accountKey,
        'category': n.category,
        'severity': n.severity,
        'title': n.title,
        'message': n.message,
        'metadata': n.metadata,
        'read': true,
        'created_at': n.createdAt.toIso8601String(),
      })).toList();
      return _delay(count);
    }
    final r = await _send('POST', '/api/notifications/mark-all-read') as Map<String, dynamic>;
    return r['count'] ?? 0;
  }
  Future<void> deleteNotification(int id) async {
    if (MpConfig.useMock) {
      mockStore.notifications.removeWhere((n) => n.notificationId == id);
      return _delay(null);
    }
    return _send('DELETE', '/api/notifications/$id');
  }

  // ───── Bot ─────
  Future<BotStatus> botStatus() async {
    if (MpConfig.useMock) return _delay(mockStore.bot);
    return BotStatus.fromJson(await _send('GET', '/api/bot/status'));
  }
  Future<void> botControl(String action) async {
    if (MpConfig.useMock) {
      mockStore.bot = BotStatus.fromJson({
        'status': action == 'start' ? 'running' : 'stopped',
        'dry_run': mockStore.bot.dryRun,
        'active_accounts': mockStore.bot.activeAccounts,
        'paused_accounts': mockStore.bot.pausedAccounts,
        'breached_accounts': mockStore.bot.breachedAccounts,
        'total_active_trades': mockStore.bot.totalActiveTrades,
        'allow_weekend_trading': mockStore.bot.allowWeekendTrading,
        'allow_eod_trading': mockStore.bot.allowEodTrading,
      });
      return _delay(null);
    }
    return _send('POST', '/api/bot/control', body: {'action': action});
  }
  Future<int> forceCloseAll() async {
    if (MpConfig.useMock) {
      final count = mockStore.trades.length;
      mockStore.trades.clear();
      mockStore.bot = BotStatus.fromJson({
        'status': mockStore.bot.status,
        'dry_run': mockStore.bot.dryRun,
        'active_accounts': mockStore.bot.activeAccounts,
        'paused_accounts': mockStore.bot.pausedAccounts,
        'breached_accounts': mockStore.bot.breachedAccounts,
        'total_active_trades': 0,
        'allow_weekend_trading': mockStore.bot.allowWeekendTrading,
        'allow_eod_trading': mockStore.bot.allowEodTrading,
      });
      return _delay(count);
    }
    final r = await _send('POST', '/api/bot/force-close-all') as Map<String, dynamic>;
    return r['closed_count'] ?? 0;
  }
  Future<int> forceCloseAccount(String key) async {
    if (MpConfig.useMock) {
      final count = mockStore.trades.where((t) => t.accountKey == key).length;
      mockStore.trades.removeWhere((t) => t.accountKey == key);
      mockStore.bot = BotStatus.fromJson({
        'status': mockStore.bot.status,
        'dry_run': mockStore.bot.dryRun,
        'active_accounts': mockStore.bot.activeAccounts,
        'paused_accounts': mockStore.bot.pausedAccounts,
        'breached_accounts': mockStore.bot.breachedAccounts,
        'total_active_trades': mockStore.trades.length,
        'allow_weekend_trading': mockStore.bot.allowWeekendTrading,
        'allow_eod_trading': mockStore.bot.allowEodTrading,
      });
      return _delay(count);
    }
    final r = await _send('POST', '/api/bot/force-close-account/${Uri.encodeComponent(key)}')
        as Map<String, dynamic>;
    return r['closed_count'] ?? 0;
  }

  // ───── FCM Token Registration ─────
  Future<void> registerFcmToken(String token) async {
    if (MpConfig.useMock) return _delay(null);
    await _send('POST', '/api/users/register-fcm-token', body: {'fcm_token': token});
  }

  // ───── Users ─────
  Future<User> me() async {
    if (MpConfig.useMock) {
      return _delay(User.fromJson({
        'user_id': 'mock-user-1',
        'email': 'mock@example.com',
        'display_name': 'Mock User',
        'is_super_admin': true,
        'is_approved': true,
        'created_at': DateTime.now().toIso8601String(),
      }));
    }
    return User.fromJson(await _send('GET', '/api/users/me'));
  }
  Future<List<User>> pendingUsers() async {
    if (MpConfig.useMock) return _delay([]);
    final l = await _send('GET', '/api/users/pending') as List;
    return l.map((j) => User.fromJson(j)).toList();
  }
  Future<List<User>> allUsers() async {
    if (MpConfig.useMock) return _delay([]);
    final l = await _send('GET', '/api/users/all') as List;
    return l.map((j) => User.fromJson(j)).toList();
  }
  Future<Map<String, dynamic>> approveUser(String userId) async {
    if (MpConfig.useMock) return _delay({'success': true, 'message': 'User approved'});
    return (await _send('POST', '/api/users/$userId/approve')) as Map<String, dynamic>;
  }

  void close() => _http.close();
}