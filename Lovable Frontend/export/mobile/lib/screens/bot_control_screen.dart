import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../main.dart';
import '../models/models.dart';
import '../theme.dart';

class BotControlScreen extends StatefulWidget {
  const BotControlScreen({super.key});
  @override
  State<BotControlScreen> createState() => _BotControlScreenState();
}

class _BotControlScreenState extends State<BotControlScreen> {
  late Future<BotStatus> _f;
  late Future<List<Account>> _accountsF;
  String? _forceAccount;

  @override
  void initState() {
    super.initState();
    _f = mpApi.botStatus();
    _accountsF = mpApi.listAccounts();
  }

  void _reload() => setState(() => _f = mpApi.botStatus());

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

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<BotStatus>(
      future: _f,
      builder: (ctx, snap) {
        if (!snap.hasData) return const Center(child: CircularProgressIndicator());
        final b = snap.data!;
        final running = b.status == 'running';
        return RefreshIndicator(
          onRefresh: () async => _reload(),
          child: ListView(padding: const EdgeInsets.all(12), children: [
            const Text('Bot control', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
            const Text('Operate the Mirror Pupil bot and run emergency actions.',
                style: TextStyle(fontSize: 12, color: MpColors.textDim)),
            const SizedBox(height: 12),
            // Status card + controls
            Card(child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(
                    width: 48, height: 48,
                    decoration: BoxDecoration(
                      color: running ? MpColors.success.withOpacity(0.15) : Colors.white10,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(Icons.smart_toy,
                        color: running ? MpColors.success : MpColors.textDim),
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Text('BOT STATUS', style: TextStyle(fontSize: 10, color: MpColors.textDim, letterSpacing: 1)),
                    Text(b.status, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                    if (b.dryRun) const Text('DRY-RUN MODE', style: TextStyle(color: MpColors.warning, fontSize: 10, letterSpacing: 2)),
                  ])),
                ]),
                const SizedBox(height: 12),
                Wrap(spacing: 8, children: [
                  if (!running)
                    ElevatedButton.icon(
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Start'),
                      style: ElevatedButton.styleFrom(backgroundColor: MpColors.success, foregroundColor: Colors.black),
                      onPressed: () async {
                        if (await _confirm('Start bot?', desc: 'Resume processing signals and executing trades.')) {
                          await mpApi.botControl('start'); _reload();
                        }
                      },
                    )
                  else
                    OutlinedButton.icon(
                      icon: const Icon(Icons.pause),
                      label: const Text('Stop'),
                      onPressed: () async {
                        if (await _confirm('Stop bot?', desc: 'Bot will stop accepting signals. Open positions remain.', destructive: true)) {
                          await mpApi.botControl('stop'); _reload();
                        }
                      },
                    ),
                  OutlinedButton.icon(
                    icon: const Icon(Icons.refresh),
                    label: const Text('Restart'),
                    onPressed: () async {
                      if (await _confirm('Restart bot?')) {
                        await mpApi.botControl('stop');
                        await Future.delayed(const Duration(milliseconds: 250));
                        await mpApi.botControl('start');
                        _reload();
                      }
                    },
                  ),
                ]),
                const SizedBox(height: 14),
                GridView.count(
                  shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2, childAspectRatio: 2.3, mainAxisSpacing: 8, crossAxisSpacing: 8,
                  children: [
                    _tile('Active accts', '${b.activeAccounts}'),
                    _tile('Paused accts', '${b.pausedAccounts}'),
                    _tile('Breached accts', '${b.breachedAccounts}', color: MpColors.danger),
                    _tile('Open trades', '${b.totalActiveTrades}'),
                  ],
                ),
              ]),
            )),
            const SizedBox(height: 12),
            // Trading hours
            Card(child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Text('Trading hours', style: TextStyle(fontWeight: FontWeight.w600)),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Allow weekend trading'),
                  value: b.allowWeekendTrading, onChanged: null,
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Allow end-of-day trading'),
                  value: b.allowEodTrading, onChanged: null,
                ),
                const Text('Toggles reflect backend config; flip them in the bot config file or via your admin API.',
                    style: TextStyle(fontSize: 11, color: MpColors.textDim)),
              ]),
            )),
            const SizedBox(height: 12),
            // Emergency
            Card(
              color: MpColors.crimson.withOpacity(0.08),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
                side: BorderSide(color: MpColors.danger.withOpacity(0.4)),
              ),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Row(children: [
                    Icon(Icons.shield_outlined, color: MpColors.danger),
                    SizedBox(width: 6),
                    Text('Emergency actions', style: TextStyle(fontWeight: FontWeight.w600)),
                  ]),
                  const SizedBox(height: 10),
                  ElevatedButton.icon(
                    icon: const Icon(Icons.shield_outlined),
                    label: const Text('Force close all positions'),
                    style: ElevatedButton.styleFrom(backgroundColor: MpColors.danger),
                    onPressed: () async {
                      if (await _confirm('Force close ALL positions?', destructive: true, confirm: 'Force close all')) {
                        final n = await mpApi.forceCloseAll();
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Closed $n positions')));
                        }
                        _reload();
                      }
                    },
                  ),
                  const SizedBox(height: 10),
                  FutureBuilder<List<Account>>(future: _accountsF, builder: (_, accSnap) {
                    final accounts = accSnap.data ?? const <Account>[];
                    return Row(children: [
                      Expanded(child: DropdownButton<String>(
                        value: _forceAccount, isExpanded: true,
                        hint: const Text('Pick account…'),
                        onChanged: (v) => setState(() => _forceAccount = v),
                        items: accounts.map((a) => DropdownMenuItem(
                          value: a.accountKey,
                          child: Text(a.displayName ?? a.tlEmail, overflow: TextOverflow.ellipsis),
                        )).toList(),
                      )),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.shield_outlined),
                        label: const Text('Close account'),
                        onPressed: _forceAccount == null ? null : () async {
                          if (await _confirm('Force close all positions for ${shortenKey(_forceAccount!)}?',
                              destructive: true)) {
                            final n = await mpApi.forceCloseAccount(_forceAccount!);
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Closed $n positions')));
                            }
                            _reload();
                          }
                        },
                      ),
                    ]);
                  }),
                ]),
              ),
            ),
          ]),
        );
      },
    );
  }

  Widget _tile(String label, String value, {Color? color}) => Container(
    padding: const EdgeInsets.all(10),
    decoration: BoxDecoration(color: MpColors.app, borderRadius: BorderRadius.circular(8),
      border: Border.all(color: MpColors.border)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label.toUpperCase(), style: const TextStyle(fontSize: 9, color: MpColors.textDim, letterSpacing: 1)),
      Text(value, style: kMono.copyWith(fontSize: 18, fontWeight: FontWeight.w600, color: color)),
    ]),
  );
}