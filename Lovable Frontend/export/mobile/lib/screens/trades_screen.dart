import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../main.dart';
import '../models/models.dart';
import '../theme.dart';

enum _Sort { time, symbol, lots }

class ActiveTradesScreen extends StatefulWidget {
  const ActiveTradesScreen({super.key});
  @override
  State<ActiveTradesScreen> createState() => _ActiveTradesScreenState();
}

class _ActiveTradesScreenState extends State<ActiveTradesScreen> {
  late Future<List<ActiveTrade>> _f;
  late Future<List<Account>> _accountsF;
  late Future<List<Channel>> _channelsF;
  String _accountKey = 'all';
  String _channelId = 'all';
  String _symbol = '';
  _Sort _sort = _Sort.time;

  @override
  void initState() {
    super.initState();
    _f = mpApi.activeTrades();
    _accountsF = mpApi.listAccounts();
    _channelsF = mpApi.listChannels();
  }

  void _reload() => setState(() => _f = mpApi.activeTrades());

  Future<bool> _confirm(String title, String desc, {bool destructive = false}) async {
    final r = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
      title: Text(title), content: Text(desc),
      actions: [
        TextButton(onPressed: () => dialogContext.pop(false), child: const Text('Cancel')),
        ElevatedButton(
          style: destructive ? ElevatedButton.styleFrom(backgroundColor: MpColors.danger) : null,
          onPressed: () => dialogContext.pop(true),
          child: const Text('Confirm'),
        ),
      ],
    ));
    return r ?? false;
  }

  Future<void> _close(ActiveTrade t) async {
    if (!await _confirm('Close entire position for ${t.symbol}?',
        '${t.direction} ${t.lotSize} lots from ${shortenKey(t.accountKey)}.',
        destructive: true)) {
      return;
    }
    final r = await mpApi.closeTrade(t.tradeId);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(r['message'] ?? 'Closed')));
    }
    _reload();
  }

  Future<void> _be(ActiveTrade t) async {
    if (!await _confirm('Set SL to breakeven for ${t.symbol}?',
        'SL → entry price ${formatPrice(t.entryPrice, t.symbol)}.')) {
      return;
    }
    await mpApi.breakevenTrade(t.tradeId);
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Breakeven set')));
    _reload();
  }

  Future<void> _partial(ActiveTrade t, int pct) async {
    if (!await _confirm('Close $pct% of ${t.symbol}?', '${t.lotSize} lots open.')) return;
    final r = await mpApi.partialTrade(t.tradeId, pct);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Remaining: ${r['remaining_lots']}')));
    }
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      const Padding(
        padding: EdgeInsets.fromLTRB(12, 12, 12, 4),
        child: Align(alignment: Alignment.centerLeft,
          child: Text('Active trades', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600))),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: FutureBuilder<List<Account>>(future: _accountsF, builder: (_, accSnap) {
          return FutureBuilder<List<Channel>>(future: _channelsF, builder: (_, chSnap) {
            return Wrap(spacing: 8, runSpacing: 8, children: [
              DropdownButton<String>(
                value: _accountKey, onChanged: (v) => setState(() => _accountKey = v ?? 'all'),
                items: [
                  const DropdownMenuItem(value: 'all', child: Text('All accounts')),
                  ...?accSnap.data?.map((a) => DropdownMenuItem(value: a.accountKey,
                    child: Text(a.displayName ?? a.tlEmail, overflow: TextOverflow.ellipsis))),
                ],
              ),
              DropdownButton<String>(
                value: _channelId, onChanged: (v) => setState(() => _channelId = v ?? 'all'),
                items: [
                  const DropdownMenuItem(value: 'all', child: Text('All channels')),
                  ...?chSnap.data?.map((c) => DropdownMenuItem(
                    value: c.channelId.toString(), child: Text(c.displayName))),
                ],
              ),
              SizedBox(width: 140, child: TextField(
                decoration: const InputDecoration(hintText: 'Symbol…', isDense: true),
                onChanged: (v) => setState(() => _symbol = v),
              )),
              DropdownButton<_Sort>(
                value: _sort, onChanged: (v) => setState(() => _sort = v ?? _Sort.time),
                items: const [
                  DropdownMenuItem(value: _Sort.time, child: Text('Newest')),
                  DropdownMenuItem(value: _Sort.symbol, child: Text('Symbol')),
                  DropdownMenuItem(value: _Sort.lots, child: Text('Lot size')),
                ],
              ),
            ]);
          });
        }),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: () async => _reload(),
          child: FutureBuilder<List<ActiveTrade>>(
            future: _f,
            builder: (ctx, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              var list = snap.data!.where((t) {
                if (_accountKey != 'all' && t.accountKey != _accountKey) return false;
                if (_channelId != 'all' && t.channelId.toString() != _channelId) return false;
                if (_symbol.isNotEmpty && !t.symbol.toLowerCase().contains(_symbol.toLowerCase())) return false;
                return true;
              }).toList();
              list.sort((a, b) {
                switch (_sort) {
                  case _Sort.symbol: return a.symbol.compareTo(b.symbol);
                  case _Sort.lots:   return b.lotSize.compareTo(a.lotSize);
                  case _Sort.time:   return b.entryTime.compareTo(a.entryTime);
                }
              });
              if (list.isEmpty) return const Center(child: Text('No active trades.'));
              return ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: list.length,
                itemBuilder: (_, i) => _TradeCard(
                  t: list[i],
                  onClose: () => _close(list[i]),
                  onBe: () => _be(list[i]),
                  onPartial: (pct) => _partial(list[i], pct),
                ),
              );
            },
          ),
        ),
      ),
    ]);
  }
}

class _TradeCard extends StatelessWidget {
  final ActiveTrade t;
  final VoidCallback onClose, onBe;
  final ValueChanged<int> onPartial;
  const _TradeCard({required this.t, required this.onClose, required this.onBe, required this.onPartial});

  @override
  Widget build(BuildContext context) {
    final isBuy = t.direction == 'BUY';
    final dirColor = isBuy ? MpColors.success : MpColors.danger;
    return Card(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isBuy 
              ? [MpColors.success.withValues(alpha: 0.08), MpColors.base]
              : [MpColors.danger.withValues(alpha: 0.08), MpColors.base],
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: dirColor.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
              child: Text(t.direction, style: TextStyle(color: dirColor, fontSize: 11, fontWeight: FontWeight.w600)),
            ),
            const SizedBox(width: 8),
            Text(t.symbol, style: kMono.copyWith(fontWeight: FontWeight.w600, fontSize: 16)),
            if (t.status == 'pending') ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: Colors.orange.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                child: const Text('PENDING', style: TextStyle(fontSize: 10, color: Colors.orange, fontWeight: FontWeight.w600)),
              ),
            ],
            if (t.tp1Hit) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: MpColors.success.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                child: const Text('TP1', style: TextStyle(fontSize: 10, color: MpColors.success, fontWeight: FontWeight.w600)),
              ),
            ],
            const Spacer(),
            Text(formatTimeAgo(t.entryTime), style: const TextStyle(fontSize: 11, color: MpColors.textDim)),
          ]),
          if (t.channelName != null) Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: MpColors.crimson.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
              child: Text(t.channelName!, style: const TextStyle(fontSize: 10)),
            ),
          ),
          const SizedBox(height: 8),
          Row(children: [
            _kv('Entry', formatPrice(t.entryPrice, t.symbol)),
            _kv('SL', t.sl == null ? '—' : formatPrice(t.sl!, t.symbol)),
            _kv('TP', t.tp == null ? '—' : formatPrice(t.tp!, t.symbol)),
          ]),
          const SizedBox(height: 4),
          Row(children: [
            _kv('Lots', t.lotSize.toStringAsFixed(2)),
            _kv('Risk', t.riskUsd == null ? '—' : formatCurrency(-t.riskUsd!)),
            _kv('P&L', t.currentPnl == null ? '—' : formatCurrency(t.currentPnl!),
                color: t.currentPnl != null && t.currentPnl != 0 ? (t.currentPnl! > 0 ? MpColors.success : MpColors.danger) : null),
          ]),
          const SizedBox(height: 8),
          Text(shortenKey(t.accountKey), style: kMono.copyWith(fontSize: 10, color: MpColors.textDim)),
          const SizedBox(height: 10),
          Wrap(spacing: 8, children: [
            OutlinedButton.icon(
              icon: const Icon(Icons.close, size: 14, color: MpColors.danger),
              label: const Text('Close', style: TextStyle(color: MpColors.danger)),
              onPressed: onClose,
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.balance, size: 14),
              label: const Text('Breakeven'),
              onPressed: t.status == 'filled' ? onBe : null,
            ),
            PopupMenuButton<int>(
              onSelected: t.status == 'filled' ? onPartial : null,
              itemBuilder: (_) => const [
                PopupMenuItem(value: 25, child: Text('Close 25%')),
                PopupMenuItem(value: 50, child: Text('Close 50%')),
                PopupMenuItem(value: 75, child: Text('Close 75%')),
              ],
              child: OutlinedButton.icon(
                icon: const Icon(Icons.content_cut, size: 14),
                label: const Text('Partial'),
                onPressed: null,
              ),
            ),
          ]),
        ]),
      ),
    );
  }

  Widget _kv(String k, String v, {Color? color}) => Expanded(child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(k.toUpperCase(), style: const TextStyle(fontSize: 9, color: MpColors.textDim, letterSpacing: 1)),
      Text(v, style: kMono.copyWith(fontSize: 12, color: color)),
    ],
  ));
}