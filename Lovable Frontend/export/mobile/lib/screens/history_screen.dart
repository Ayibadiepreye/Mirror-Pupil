import 'package:flutter/material.dart';
import '../main.dart';
import '../models/models.dart';
import '../theme.dart';

enum _Range { d7, d30, all }

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late Future<({List<TradeHistory> trades, int total})> _f;
  late Future<List<Account>> _accountsF;
  late Future<List<Channel>> _channelsF;
  String _accountKey = 'all';
  _Range _range = _Range.all;
  String _symbol = '';
  String _channelId = 'all';
  int _offset = 0;
  static const _limit = 50;

  @override
  void initState() {
    super.initState();
    _f = mpApi.tradeHistory(limit: 5000, offset: 0);
    _accountsF = mpApi.listAccounts();
    _channelsF = mpApi.listChannels();
  }

  void _reload() => setState(() {
    _f = mpApi.tradeHistory(
      accountKey: _accountKey == 'all' ? null : _accountKey,
      limit: 5000, offset: 0,
    );
  });

  Future<void> _export() async {
    try {
      await mpApi.historyExportBytes(accountKey: _accountKey == 'all' ? null : _accountKey);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('CSV downloaded')),
      );
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Export failed: $e')));
    }
  }

  List<TradeHistory> _filter(List<TradeHistory> all) {
    final now = DateTime.now();
    return all.where((t) {
      if (_range != _Range.all) {
        final days = _range == _Range.d7 ? 7 : 30;
        if (t.exitTime.isBefore(now.subtract(Duration(days: days)))) return false;
      }
      if (_channelId != 'all' && t.channelId.toString() != _channelId) return false;
      if (_symbol.isNotEmpty && !t.symbol.toLowerCase().contains(_symbol.toLowerCase())) return false;
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
        child: Row(children: [
          const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Trade history', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
            Text('Times shown in Lagos (WAT, UTC+1).', style: TextStyle(fontSize: 11, color: MpColors.textDim)),
          ])),
          ElevatedButton.icon(
            icon: const Icon(Icons.download, size: 16),
            label: const Text('Export CSV'),
            style: ElevatedButton.styleFrom(backgroundColor: MpColors.crimson),
            onPressed: _export,
          ),
        ]),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: FutureBuilder<List<Account>>(future: _accountsF, builder: (_, accSnap) {
          return FutureBuilder<List<Channel>>(future: _channelsF, builder: (_, chSnap) {
            return Wrap(spacing: 8, runSpacing: 8, children: [
              DropdownButton<String>(
                value: _accountKey,
                onChanged: (v) { setState(() { _accountKey = v ?? 'all'; _offset = 0; }); _reload(); },
                items: [
                  const DropdownMenuItem(value: 'all', child: Text('All accounts')),
                  ...?accSnap.data?.map((a) => DropdownMenuItem(value: a.accountKey,
                    child: Text(a.displayName ?? a.tlEmail, overflow: TextOverflow.ellipsis))),
                ],
              ),
              DropdownButton<_Range>(
                value: _range, onChanged: (v) => setState(() => _range = v ?? _Range.all),
                items: const [
                  DropdownMenuItem(value: _Range.d7, child: Text('Last 7 days')),
                  DropdownMenuItem(value: _Range.d30, child: Text('Last 30 days')),
                  DropdownMenuItem(value: _Range.all, child: Text('All time')),
                ],
              ),
              SizedBox(width: 130, child: TextField(
                decoration: const InputDecoration(hintText: 'Symbol…', isDense: true),
                onChanged: (v) => setState(() => _symbol = v),
              )),
              DropdownButton<String>(
                value: _channelId, onChanged: (v) => setState(() => _channelId = v ?? 'all'),
                items: [
                  const DropdownMenuItem(value: 'all', child: Text('All channels')),
                  ...?chSnap.data?.map((c) => DropdownMenuItem(
                    value: c.channelId.toString(), child: Text(c.displayName))),
                ],
              ),
            ]);
          });
        }),
      ),
      Expanded(child: FutureBuilder(
        future: _f,
        builder: (ctx, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final all = snap.data!.trades;
          final filtered = _filter(all);
          final wins = filtered.where((t) => t.outcome == 'WIN').toList();
          final losses = filtered.where((t) => t.outcome == 'LOSS').toList();
          final sumPnl = filtered.fold<double>(0, (s, t) => s + t.pnl);
          final avgWin = wins.isEmpty ? 0.0 : wins.fold<double>(0, (s, t) => s + t.pnl) / wins.length;
          final avgLoss = losses.isEmpty ? 0.0 : losses.fold<double>(0, (s, t) => s + t.pnl) / losses.length;
          final largestWin = wins.fold<double>(0, (m, t) => t.pnl > m ? t.pnl : m);
          final largestLoss = losses.fold<double>(0, (m, t) => t.pnl < m ? t.pnl : m);
          final winRate = filtered.isEmpty ? 0 : (wins.length * 100 / filtered.length).round();
          final pageRows = filtered.skip(_offset).take(_limit).toList();
          final pages = (filtered.length / _limit).ceil().clamp(1, 99999);
          return Column(children: [
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: GridView.count(
                shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: 3, childAspectRatio: 1.5,
                crossAxisSpacing: 8, mainAxisSpacing: 8,
                children: [
                  _Tile('Total', '${filtered.length}'),
                  _Tile('Winners', '${wins.length} ($winRate%)', color: MpColors.success),
                  _Tile('Losers', '${losses.length}', color: MpColors.danger),
                  _Tile('Total P&L', formatCurrency(sumPnl), color: sumPnl >= 0 ? MpColors.success : MpColors.danger),
                  _Tile('Avg win', formatCurrency(avgWin), color: MpColors.success),
                  _Tile('Avg loss', formatCurrency(avgLoss), color: MpColors.danger),
                  _Tile('Largest win', formatCurrency(largestWin), color: MpColors.success),
                  _Tile('Largest loss', formatCurrency(largestLoss), color: MpColors.danger),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Expanded(child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              itemCount: pageRows.length,
              itemBuilder: (_, i) {
                final t = pageRows[i];
                return Card(
                  margin: const EdgeInsets.only(bottom: 6),
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [MpColors.base, MpColors.app],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: ListTile(
                    dense: true,
                    title: Row(children: [
                      Text(t.symbol, style: kMono.copyWith(fontWeight: FontWeight.w600)),
                      const SizedBox(width: 6),
                      Text(t.direction, style: TextStyle(
                        fontSize: 10, fontWeight: FontWeight.w600,
                        color: t.direction == 'BUY' ? MpColors.success : MpColors.danger,
                      )),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(color: MpColors.crimson.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                        child: Text(t.channelName ?? '#${t.channelId}', style: const TextStyle(fontSize: 9)),
                      ),
                      const Spacer(),
                      Text(formatCurrency(t.pnl), style: kMono.copyWith(
                        color: t.pnl >= 0 ? MpColors.success : MpColors.danger,
                        fontWeight: FontWeight.w600)),
                    ]),
                    subtitle: Wrap(spacing: 6, children: [
                      Text(formatLagosTime(t.exitTime), style: kMono.copyWith(fontSize: 11, color: MpColors.textDim)),
                      Text('· ${formatPrice(t.entryPrice, t.symbol)} → ${formatPrice(t.exitPrice, t.symbol)}',
                          style: kMono.copyWith(fontSize: 11, color: MpColors.textDim)),
                      Text('· ${t.lotSize.toStringAsFixed(2)} lots', style: kMono.copyWith(fontSize: 11, color: MpColors.textDim)),
                      Text('· ${t.closeReason}', style: const TextStyle(fontSize: 11, color: MpColors.textDim)),
                      if (t.manualActionType != null)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                          decoration: BoxDecoration(color: MpColors.warning.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(3)),
                          child: Text(t.manualActionType!, style: const TextStyle(fontSize: 9, color: MpColors.warning)),
                        ),
                    ]),
                  ),
                ),
                );
              },
            )),
            Padding(
              padding: const EdgeInsets.all(8),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                OutlinedButton(
                  onPressed: _offset == 0 ? null : () => setState(() => _offset = (_offset - _limit).clamp(0, 999999)),
                  child: const Text('Previous'),
                ),
                const SizedBox(width: 8),
                Text('${(_offset / _limit).floor() + 1} / $pages', style: kMono),
                const SizedBox(width: 8),
                OutlinedButton(
                  onPressed: _offset + _limit >= filtered.length ? null : () => setState(() => _offset += _limit),
                  child: const Text('Next'),
                ),
              ]),
            ),
          ]);
        },
      )),
    ]);
  }
}

class _Tile extends StatelessWidget {
  final String label, value;
  final Color? color;
  const _Tile(this.label, this.value, {this.color});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(8),
    decoration: BoxDecoration(
      gradient: const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [MpColors.base, MpColors.app],
      ),
      border: Border.all(color: MpColors.border),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
      Text(label.toUpperCase(), 
        style: const TextStyle(fontSize: 8, color: MpColors.textDim, letterSpacing: 1),
        maxLines: 1, overflow: TextOverflow.ellipsis),
      const SizedBox(height: 2),
      Text(value, 
        style: kMono.copyWith(fontSize: 10, fontWeight: FontWeight.w600, color: color),
        maxLines: 1, overflow: TextOverflow.ellipsis),
    ]),
  );
}