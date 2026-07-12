import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../main.dart';
import '../models/models.dart' as models;
import '../theme.dart';
import '../utils.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashData {
  final List<models.Account> accounts;
  final List<models.ActiveTrade> trades;
  final models.BotStatus bot;
  final List<models.Notification> notifs;
  _DashData({required this.accounts, required this.trades, required this.bot, required this.notifs});
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<_DashData> _f;

  @override
  void initState() { super.initState(); _f = _load(); }

  Future<_DashData> _load() async {
    final results = await Future.wait([
      mpApi.listAccounts(),
      mpApi.activeTrades(),
      mpApi.botStatus(),
      mpApi.listNotifications(limit: 10),
    ]);
    return _DashData(
      accounts: results[0] as List<models.Account>,
      trades: results[1] as List<models.ActiveTrade>,
      bot: results[2] as models.BotStatus,
      notifs: results[3] as List<models.Notification>,
    );
  }

  Future<bool> _confirm(String title, {String? desc, bool destructive = false, String confirm = 'Confirm'}) async {
    final r = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
      title: Text(title), content: desc == null ? null : Text(desc),
      actions: [
        TextButton(onPressed: () => dialogContext.pop(false), child: const Text('Cancel')),
        ElevatedButton(
          style: destructive ? ElevatedButton.styleFrom(backgroundColor: MpColors.danger) : null,
          onPressed: () => dialogContext.pop(true),
          child: Text(confirm),
        ),
      ],
    ));
    return r ?? false;
  }

  Future<void> _forceCloseAll() async {
    if (!await _confirm('Force close ALL positions?',
        desc: 'This will immediately close every open trade across every account.',
        destructive: true, confirm: 'Force close all')) {
      return;
    }
    final n = await mpApi.forceCloseAll();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Closed $n positions')));
    setState(() => _f = _load());
  }

  Future<void> _bulk(String kind, List<models.Account> accounts) async {
    if (!await _confirm(kind == 'pause' ? 'Pause all accounts?' : 'Resume all accounts?')) return;
    final targets = accounts.where((a) => kind == 'pause' ? !a.paused : a.paused).toList();
    for (final a in targets) {
      kind == 'pause' ? await mpApi.pauseAccount(a.accountKey) : await mpApi.resumeAccount(a.accountKey);
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${kind == 'pause' ? 'Paused' : 'Resumed'} ${targets.length} account(s)')),
    );
    setState(() => _f = _load());
  }

  void _showTotalBalanceModal(List<models.Account> accounts) {
    final totalBalance = accounts.fold<double>(0, (sum, a) => sum + a.currentBalance);
    showDialog(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: Colors.transparent,
        child: Container(
          constraints: const BoxConstraints(maxWidth: 400),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                MpColors.crimson.withValues(alpha: 0.85),
                MpColors.crimson.withValues(alpha: 0.65),
                MpColors.base.withValues(alpha: 0.95),
              ],
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: MpColors.crimson.withValues(alpha: 0.5), width: 1.5),
            boxShadow: [
              BoxShadow(color: MpColors.crimson.withValues(alpha: 0.3), blurRadius: 24, spreadRadius: 0),
              BoxShadow(color: Colors.black.withValues(alpha: 0.4), blurRadius: 12, offset: const Offset(0, 8)),
            ],
          ),
          child: Stack(
            children: [
              Positioned(
                top: -40, right: -40,
                child: Icon(Icons.account_balance_wallet, size: 160, color: MpColors.crimson.withValues(alpha: 0.12)),
              ),
              Padding(
                padding: const EdgeInsets.all(24),
                child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  const Row(children: [
                    Icon(Icons.account_balance_wallet, size: 28, color: MpColors.success),
                    SizedBox(width: 12),
                    Text('Total Balance', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, letterSpacing: -0.5)),
                  ]),
                  const SizedBox(height: 8),
                  Text('Combined balance across ${accounts.length} account(s)',
                      style: const TextStyle(fontSize: 12, color: MpColors.textDim)),
                  const SizedBox(height: 24),
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [MpColors.success.withValues(alpha: 0.15), MpColors.base],
                      ),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: MpColors.success.withValues(alpha: 0.3)),
                    ),
                    child: Column(children: [
                      const Text('TOTAL BALANCE', 
                          style: TextStyle(fontSize: 11, color: MpColors.textDim, letterSpacing: 2, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 8),
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          formatCurrency(totalBalance),
                          style: kMono.copyWith(fontSize: 36, fontWeight: FontWeight.w800, color: MpColors.success, letterSpacing: -1),
                          maxLines: 2,
                          textAlign: TextAlign.center,
                          softWrap: true,
                        ),
                      ),
                    ]),
                  ),
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: MpColors.app,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: MpColors.border),
                    ),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      const Text('Breakdown by account:', 
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: 0.5)),
                      const SizedBox(height: 12),
                      ...accounts.map((a) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                          Expanded(child: Text(a.displayName ?? a.accountKey,
                              style: const TextStyle(fontSize: 12), maxLines: 1, overflow: TextOverflow.ellipsis)),
                          Text(formatCurrency(a.currentBalance),
                              style: kMono.copyWith(fontSize: 12, fontWeight: FontWeight.w700)),
                        ]),
                      )),
                    ]),
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: () => dialogContext.pop(),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: MpColors.crimson,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: const Text('Close', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                  ),
                ]),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async => setState(() => _f = _load()),
      child: FutureBuilder<_DashData>(
        future: _f,
        builder: (ctx, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          if (snap.hasError) return Center(child: Text('Error: ${snap.error}'));
          final d = snap.data!;
          final dailyPnl = d.accounts.fold<double>(0, (s, a) => s + a.dailyPnl);
          final active = d.accounts.where((a) => !a.paused && !a.breached).length;
          final paused = d.accounts.where((a) => a.paused).length;
          final breached = d.accounts.where((a) => a.breached).length;
          return ListView(padding: const EdgeInsets.all(16), children: [
            const Text('Command Dashboard', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
            const Text('Live overview of the Mirror Pupil bot and your prop accounts.',
                style: TextStyle(fontSize: 12, color: MpColors.textDim)),
            const SizedBox(height: 16),
            GridView.count(
              shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2, childAspectRatio: 1.4,
              crossAxisSpacing: 12, mainAxisSpacing: 12,
              children: [
                _StatCard(label: 'Accounts', value: '${d.accounts.length}', icon: Icons.people,
                  hint: '$active active · $paused paused · $breached breached',
                  gradient: [MpColors.crimson.withValues(alpha: 0.08), MpColors.base]),
                _StatCard(label: 'Active trades', value: '${d.trades.length}', icon: Icons.trending_up,
                  hint: '${d.bot.totalActiveTrades} reported by bot',
                  gradient: [const Color(0xFF1E88E5).withValues(alpha: 0.08), MpColors.base]),
                _StatCard(label: 'P&L today', value: formatCurrency(dailyPnl), icon: Icons.attach_money,
                  valueColor: dailyPnl >= 0 ? MpColors.success : MpColors.danger,
                  hint: 'Across ${d.accounts.length} account(s)',
                  gradient: dailyPnl >= 0 
                    ? [MpColors.success.withValues(alpha: 0.08), MpColors.base]
                    : [MpColors.danger.withValues(alpha: 0.08), MpColors.base]),
                _StatCard(label: 'Bot status', value: d.bot.status, icon: Icons.smart_toy,
                  valueColor: d.bot.status == 'running' ? MpColors.success : MpColors.textDim,
                  hint: d.bot.dryRun ? 'dry-run mode' : 'live trading',
                  gradient: d.bot.status == 'running'
                    ? [MpColors.success.withValues(alpha: 0.08), MpColors.base]
                    : [MpColors.textDim.withValues(alpha: 0.08), MpColors.base]),
              ],
            ),
            const SizedBox(height: 16),
            Card(
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [MpColors.base, MpColors.app],
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                const Text('Quick actions', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 10),
                ElevatedButton.icon(
                  onPressed: () => _showTotalBalanceModal(d.accounts),
                  icon: const Icon(Icons.account_balance_wallet),
                  label: const Text('View total balance'),
                  style: ElevatedButton.styleFrom(backgroundColor: MpColors.info),
                ),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: _forceCloseAll,
                  icon: const Icon(Icons.shield_outlined),
                  label: const Text('Force close all positions'),
                  style: ElevatedButton.styleFrom(backgroundColor: MpColors.danger),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => _bulk('pause', d.accounts),
                  icon: const Icon(Icons.pause_circle_outline),
                  label: const Text('Pause all accounts'),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => _bulk('resume', d.accounts),
                  icon: const Icon(Icons.play_circle_outline),
                  label: const Text('Resume all accounts'),
                ),
                const SizedBox(height: 8),
                Row(children: [
                  Expanded(child: OutlinedButton(
                    onPressed: () => context.go('/trades'),
                    child: const Text('View trades'),
                  )),
                  const SizedBox(width: 8),
                  Expanded(child: OutlinedButton(
                    onPressed: () => context.go('/history'),
                    child: const Text('View history'),
                  )),
                ]),
              ]),
            ),
            ),
            const SizedBox(height: 16),
            Row(children: [
              const Expanded(child: Text('Recent activity', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 16))),
              TextButton(onPressed: () => context.go('/notifications'), child: const Text('View all →')),
            ]),
            const SizedBox(height: 4),
            if (d.notifs.isEmpty)
              const Padding(padding: EdgeInsets.all(16), child: Text('No notifications yet.', style: TextStyle(color: MpColors.textDim))),
            ...d.notifs.map((n) => Card(
              child: Container(
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [MpColors.base, MpColors.app],
                  ),
                  border: Border(left: BorderSide(color: _sevColor(n.severity), width: 4)),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: ListTile(
                  leading: Icon(_iconFor(n.category), color: _sevColor(n.severity)),
                  title: Text(n.title, maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text(n.message, maxLines: 2, overflow: TextOverflow.ellipsis),
                  trailing: Text(formatTimeAgo(n.createdAt),
                      style: const TextStyle(fontSize: 11, color: MpColors.textDim)),
                ),
              ),
            )),
          ]);
        },
      ),
    );
  }
}

IconData _iconFor(String c) {
  switch (c) {
    case 'SIGNAL': return Icons.flash_on;
    case 'EXECUTION': return Icons.check_circle_outline;
    case 'MANAGEMENT': return Icons.info_outline;
    case 'BREACH': return Icons.warning_amber;
    default: return Icons.notifications_active_outlined;
  }
}

Color _sevColor(String s) {
  switch (s) {
    case 'CRITICAL': return MpColors.danger;
    case 'ERROR':
    case 'WARNING': return MpColors.warning;
    default: return MpColors.info;
  }
}

class _StatCard extends StatelessWidget {
  final String label, value;
  final IconData icon;
  final Color? valueColor;
  final String? hint;
  final List<Color>? gradient;
  const _StatCard({required this.label, required this.value, required this.icon, this.valueColor, this.hint, this.gradient});
  @override
  Widget build(BuildContext context) => Card(
    child: Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: gradient ?? const [MpColors.base, MpColors.app],
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Expanded(child: Text(label.toUpperCase(), 
            style: const TextStyle(fontSize: 10, color: MpColors.textDim, letterSpacing: 1),
            maxLines: 1, overflow: TextOverflow.ellipsis)),
          Icon(icon, size: 16, color: MpColors.textDim),
        ]),
        const SizedBox(height: 4),
        Text(value, 
          style: kMono.copyWith(fontSize: 16, fontWeight: FontWeight.w600, color: valueColor),
          maxLines: 1, overflow: TextOverflow.ellipsis),
        if (hint != null) ...[
          const SizedBox(height: 2),
          Text(hint!, 
            style: const TextStyle(fontSize: 9, color: MpColors.textDim),
            maxLines: 1, overflow: TextOverflow.ellipsis),
        ],
      ]),
    ),
  );
}