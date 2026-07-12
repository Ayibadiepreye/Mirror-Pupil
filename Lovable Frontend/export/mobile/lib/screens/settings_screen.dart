import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../main.dart';
import '../models/models.dart';
import '../theme.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});
  @override
  Widget build(BuildContext context) {
    return const DefaultTabController(
      length: 3,
      child: Column(children: [
        Padding(
          padding: EdgeInsets.fromLTRB(12, 12, 12, 0),
          child: Align(alignment: Alignment.centerLeft,
            child: Text('Settings', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600))),
        ),
        TabBar(
          labelColor: MpColors.red,
          unselectedLabelColor: MpColors.textDim,
          indicatorColor: MpColors.red,
          tabs: [Tab(text: 'Channels'), Tab(text: 'Risk Profiles'), Tab(text: 'Bot Settings')],
        ),
        Expanded(child: TabBarView(children: [
          _ChannelsTab(), _ProfilesTab(), _BotSettingsTab(),
        ])),
      ]),
    );
  }
}

// ─── Channels Tab ────────────────────────────────────────────────────

class _ChannelsTab extends StatefulWidget {
  const _ChannelsTab();
  @override
  State<_ChannelsTab> createState() => _ChannelsTabState();
}

class _ChannelsTabState extends State<_ChannelsTab> {
  late Future<List<Channel>> _f;
  @override
  void initState() { super.initState(); _f = mpApi.listChannels(); }
  void _reload() => setState(() => _f = mpApi.listChannels());

  Future<void> _edit({Channel? initial}) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => _ChannelDialog(initial: initial),
    );
    if (saved == true) _reload();
  }

  Future<void> _delete(Channel c) async {
    final ok = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
      title: Text('Delete channel "${c.displayName}"?'),
      actions: [
        TextButton(onPressed: () => dialogContext.pop(false), child: const Text('Cancel')),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: MpColors.danger),
          onPressed: () => dialogContext.pop(true),
          child: const Text('Delete'),
        ),
      ],
    ));
    if (ok == true) { await mpApi.deleteChannel(c.channelId); _reload(); }
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Align(alignment: Alignment.centerRight,
          child: ElevatedButton.icon(
            icon: const Icon(Icons.add, size: 16),
            label: const Text('Add channel'),
            onPressed: () => _edit(),
          ),
        ),
      ),
      Expanded(child: FutureBuilder<List<Channel>>(
        future: _f,
        builder: (ctx, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final cs = snap.data!;
          if (cs.isEmpty) return const Center(child: Text('No channels.'));
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            children: cs.map((c) => Card(child: ListTile(
              title: Text(c.displayName),
              subtitle: Text('${c.signalPrefix} · priority ${c.priority} · id ${c.channelId}',
                  style: kMono.copyWith(fontSize: 11, color: MpColors.textDim)),
              trailing: Wrap(spacing: 4, children: [
                Switch(
                  value: c.enabled,
                  onChanged: (v) async {
                    v ? await mpApi.enableChannel(c.channelId) : await mpApi.disableChannel(c.channelId);
                    _reload();
                  },
                ),
                IconButton(icon: const Icon(Icons.edit, size: 18), onPressed: () => _edit(initial: c)),
                IconButton(icon: const Icon(Icons.delete_outline, size: 18, color: MpColors.danger),
                    onPressed: () => _delete(c)),
              ]),
            ))).toList(),
          );
        },
      )),
    ]);
  }
}

class _ChannelDialog extends StatefulWidget {
  final Channel? initial;
  const _ChannelDialog({this.initial});
  @override
  State<_ChannelDialog> createState() => _ChannelDialogState();
}

class _ChannelDialogState extends State<_ChannelDialog> {
  late final _name = TextEditingController(text: widget.initial?.displayName ?? '');
  late final _prefix = TextEditingController(text: widget.initial?.signalPrefix ?? '');
  late final _id = TextEditingController(text: widget.initial?.channelId.toString() ?? '');
  late final _priority = TextEditingController(text: '${widget.initial?.priority ?? 10}');
  late String _entry = widget.initial?.entryLogicModule ?? 'billirichy.entry';
  late String _mgmt = widget.initial?.managementLogicModule ?? 'billirichy.management';
  late final _notes = TextEditingController(text: widget.initial?.notes ?? '');
  late bool _enabled = widget.initial?.enabled ?? true;
  bool _busy = false;

  bool get _isEdit => widget.initial != null;
  
  static const _entryModules = ['billirichy.entry', 'firepips.entry'];
  static const _managementModules = ['billirichy.management', 'firepips.management'];

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final c = Channel(
        channelId: int.tryParse(_id.text) ?? 0,
        displayName: _name.text,
        signalPrefix: _prefix.text,
        entryLogicModule: _entry,
        managementLogicModule: _mgmt,
        priority: int.tryParse(_priority.text) ?? 10,
        enabled: _enabled,
        notes: _notes.text.isEmpty ? null : _notes.text,
      );
      if (_isEdit) {
        await mpApi.updateChannel(widget.initial!.channelId, c);
      } else {
        await mpApi.createChannel(c);
      }
      if (mounted) context.pop(true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEdit ? 'Edit channel' : 'Add channel'),
      content: SizedBox(width: 480, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: _id, enabled: !_isEdit, keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Channel ID (Telegram)')),
        const SizedBox(height: 12),
        TextField(controller: _name, decoration: const InputDecoration(labelText: 'Display name')),
        const SizedBox(height: 12),
        TextField(controller: _prefix, decoration: const InputDecoration(labelText: 'Signal prefix')),
        const SizedBox(height: 12),
        TextField(controller: _priority, keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Priority')),
        const SizedBox(height: 16),
        const Align(alignment: Alignment.centerLeft,
          child: Text('Logic Modules', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: _entryModules.contains(_entry) ? _entry : null,
          decoration: const InputDecoration(labelText: 'Entry logic module', isDense: true),
          items: _entryModules.map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
          onChanged: (v) => setState(() => _entry = v ?? _entry),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _managementModules.contains(_mgmt) ? _mgmt : null,
          decoration: const InputDecoration(labelText: 'Management logic module', isDense: true),
          items: _managementModules.map((m) => DropdownMenuItem(value: m, child: Text(m))).toList(),
          onChanged: (v) => setState(() => _mgmt = v ?? _mgmt),
        ),
        const SizedBox(height: 16),
        TextField(controller: _notes, maxLines: 2, decoration: const InputDecoration(labelText: 'Notes')),
        const SizedBox(height: 12),
        Row(children: [
          Switch(value: _enabled, onChanged: (v) => setState(() => _enabled = v)),
          const Text('Enabled'),
        ]),
      ]))),
      actions: [
        TextButton(onPressed: () => context.pop(false), child: const Text('Cancel')),
        ElevatedButton(onPressed: _busy ? null : _save, child: Text(_busy ? 'Saving…' : (_isEdit ? 'Save' : 'Create'))),
      ],
    );
  }
}

// ─── Risk Profiles Tab ──────────────────────────────────────────────

class _ProfilesTab extends StatefulWidget {
  const _ProfilesTab();
  @override
  State<_ProfilesTab> createState() => _ProfilesTabState();
}

class _ProfilesTabState extends State<_ProfilesTab> {
  late Future<List<RiskProfile>> _f;
  @override
  void initState() { super.initState(); _f = mpApi.listProfiles(); }
  void _reload() => setState(() => _f = mpApi.listProfiles());

  Future<void> _edit({RiskProfile? initial}) async {
    final saved = await showDialog<bool>(context: context, builder: (_) => _ProfileDialog(initial: initial));
    if (saved == true) _reload();
  }

  Future<void> _setDefault(RiskProfile p) async {
    await mpApi.patchProfile(p.profileId, {'is_default': true});
    _reload();
  }

  Future<void> _delete(RiskProfile p) async {
    final ok = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
      title: Text('Delete profile "${p.profileName}"?'),
      actions: [
        TextButton(onPressed: () => dialogContext.pop(false), child: const Text('Cancel')),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: MpColors.danger),
          onPressed: () => dialogContext.pop(true),
          child: const Text('Delete'),
        ),
      ],
    ));
    if (ok == true) { await mpApi.deleteProfile(p.profileId); _reload(); }
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Align(alignment: Alignment.centerRight,
          child: ElevatedButton.icon(icon: const Icon(Icons.add, size: 16),
            label: const Text('Add profile'), onPressed: () => _edit()),
        ),
      ),
      Expanded(child: FutureBuilder<List<RiskProfile>>(
        future: _f,
        builder: (ctx, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final ps = snap.data!;
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            children: ps.map((p) => Card(child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Row(children: [
                    Text(p.profileName, style: const TextStyle(fontWeight: FontWeight.w600)),
                    if (p.isDefault) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(color: MpColors.warning.withOpacity(0.2), borderRadius: BorderRadius.circular(20)),
                        child: const Text('DEFAULT', style: TextStyle(color: MpColors.warning, fontSize: 9, fontWeight: FontWeight.w600)),
                      ),
                    ],
                  ])),
                  if (!p.isDefault) IconButton(
                    tooltip: 'Set default', icon: const Icon(Icons.star_outline, size: 18),
                    onPressed: () => _setDefault(p),
                  ),
                  IconButton(icon: const Icon(Icons.edit, size: 18), onPressed: () => _edit(initial: p)),
                  IconButton(icon: const Icon(Icons.delete_outline, size: 18, color: MpColors.danger),
                      onPressed: () => _delete(p)),
                ]),
                if (p.notes != null) Text(p.notes!, style: const TextStyle(fontSize: 11, color: MpColors.textDim)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  _stat('Per trade', '${p.maxRiskPerTradePct}%'),
                  _stat('Daily', '${p.dailyLossPct}%${p.dailyTrailing ? " trail" : ""}'),
                  _stat('Overall', '${p.overallLossPct}%${p.overallTrailing ? " trail" : ""}'),
                  _stat('Max trades', '${p.maxConcurrentTrades}'),
                  _stat('Commission', '\$${p.commissionPerLot}/lot'),
                  _stat('Safety', '${p.safetyBufferPct}%'),
                ]),
              ]),
            ))).toList(),
          );
        },
      )),
    ]);
  }

  Widget _stat(String k, String v) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(6)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(k.toUpperCase(), style: const TextStyle(fontSize: 9, color: MpColors.textDim, letterSpacing: 1)),
      Text(v, style: kMono.copyWith(fontSize: 11)),
    ]),
  );
}

class _ProfileDialog extends StatefulWidget {
  final RiskProfile? initial;
  const _ProfileDialog({this.initial});
  @override
  State<_ProfileDialog> createState() => _ProfileDialogState();
}

class _ProfileDialogState extends State<_ProfileDialog> {
  late final _name = TextEditingController(text: widget.initial?.profileName ?? '');
  late final _maxRisk = TextEditingController(text: '${widget.initial?.maxRiskPerTradePct ?? 0.5}');
  late final _daily = TextEditingController(text: '${widget.initial?.dailyLossPct ?? 4}');
  late final _overall = TextEditingController(text: '${widget.initial?.overallLossPct ?? 8}');
  late final _payout = TextEditingController(text: '${widget.initial?.payoutBufferPct ?? 1}');
  late final _maxTrades = TextEditingController(text: '${widget.initial?.maxConcurrentTrades ?? 5}');
  late final _commission = TextEditingController(text: '${widget.initial?.commissionPerLot ?? 7}');
  late final _safety = TextEditingController(text: '${widget.initial?.safetyBufferPct ?? 0.5}');
  late final _lock = TextEditingController(text: widget.initial?.profitLockPct?.toString() ?? '');
  late final _lockFloor = TextEditingController(text: widget.initial?.profitLockFloorPct?.toString() ?? '');
  late final _notes = TextEditingController(text: widget.initial?.notes ?? '');
  late bool _isDefault = widget.initial?.isDefault ?? false;
  late bool _dailyTrail = widget.initial?.dailyTrailing ?? true;
  late bool _overallTrail = widget.initial?.overallTrailing ?? true;
  late bool _overallFromClosed = widget.initial?.overallTrailFromClosedBalance ?? true;
  bool _busy = false;

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final body = {
        'profile_name': _name.text,
        'is_default': _isDefault,
        'max_risk_per_trade_pct': double.tryParse(_maxRisk.text) ?? 0,
        'daily_loss_pct': double.tryParse(_daily.text) ?? 0,
        'daily_trailing': _dailyTrail,
        'overall_loss_pct': double.tryParse(_overall.text) ?? 0,
        'overall_trailing': _overallTrail,
        'overall_trail_from_closed_balance': _overallFromClosed,
        'profit_lock_pct': _lock.text.isEmpty ? null : double.tryParse(_lock.text),
        'profit_lock_floor_pct': _lockFloor.text.isEmpty ? null : double.tryParse(_lockFloor.text),
        'payout_buffer_pct': double.tryParse(_payout.text) ?? 0,
        'max_concurrent_trades': int.tryParse(_maxTrades.text) ?? 5,
        'commission_per_lot': double.tryParse(_commission.text) ?? 0,
        'safety_buffer_pct': double.tryParse(_safety.text) ?? 0,
        'notes': _notes.text.isEmpty ? null : _notes.text,
      };
      if (widget.initial != null) {
        await mpApi.updateProfile(widget.initial!.profileId, body);
      } else {
        await mpApi.createProfile(body);
      }
      if (mounted) context.pop(true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _num(TextEditingController c, String label) => TextField(
    controller: c,
    keyboardType: const TextInputType.numberWithOptions(decimal: true),
    decoration: InputDecoration(labelText: label, isDense: true),
  );

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.initial == null ? 'Add risk profile' : 'Edit risk profile'),
      content: SizedBox(width: 520, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: _name, decoration: const InputDecoration(labelText: 'Profile name')),
        const SizedBox(height: 8),
        Row(children: [
          Switch(value: _isDefault, onChanged: (v) => setState(() => _isDefault = v)),
          const Text('Default profile'),
        ]),
        const SizedBox(height: 16),
        const Align(alignment: Alignment.centerLeft,
          child: Text('Risk Limits', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _num(_maxRisk, 'Max risk / trade %')),
          const SizedBox(width: 8),
          Expanded(child: _num(_daily, 'Daily loss %')),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Switch(value: _dailyTrail, onChanged: (v) => setState(() => _dailyTrail = v)),
          const Text('Daily trail'),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _num(_overall, 'Overall loss %')),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Switch(value: _overallTrail, onChanged: (v) => setState(() => _overallTrail = v)),
          const Text('Overall trail'),
          const SizedBox(width: 8),
          Switch(value: _overallFromClosed, onChanged: (v) => setState(() => _overallFromClosed = v)),
          const Flexible(child: Text('From closed bal.')),
        ]),
        const SizedBox(height: 16),
        const Align(alignment: Alignment.centerLeft,
          child: Text('Profit Protection', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _num(_lock, 'Profit lock %')),
          const SizedBox(width: 8),
          Expanded(child: _num(_lockFloor, 'Profit lock floor %')),
        ]),
        const SizedBox(height: 16),
        const Align(alignment: Alignment.centerLeft,
          child: Text('Trading Parameters', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _num(_payout, 'Payout buffer %')),
          const SizedBox(width: 8),
          Expanded(child: _num(_maxTrades, 'Max concurrent')),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Expanded(child: _num(_commission, 'Commission/lot')),
          const SizedBox(width: 8),
          Expanded(child: _num(_safety, 'Safety buffer %')),
        ]),
        const SizedBox(height: 12),
        TextField(controller: _notes, maxLines: 2, decoration: const InputDecoration(labelText: 'Notes')),
      ]))),
      actions: [
        TextButton(onPressed: () => context.pop(false), child: const Text('Cancel')),
        ElevatedButton(onPressed: _busy ? null : _save, child: Text(_busy ? 'Saving…' : 'Save')),
      ],
    );
  }
}

// ─── Bot Settings Tab ────────────────────────────────────────────────

class _BotSettingsTab extends StatelessWidget {
  const _BotSettingsTab();
  @override
  Widget build(BuildContext context) {
    return FutureBuilder<BotStatus>(
      future: mpApi.botStatus(),
      builder: (ctx, snap) {
        if (!snap.hasData) return const Center(child: CircularProgressIndicator());
        final b = snap.data!;
        return ListView(padding: const EdgeInsets.all(12), children: [
          Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Trading hours', style: TextStyle(fontWeight: FontWeight.w600)),
            SwitchListTile(contentPadding: EdgeInsets.zero,
              title: const Text('Weekend trading'), value: b.allowWeekendTrading, onChanged: null),
            SwitchListTile(contentPadding: EdgeInsets.zero,
              title: const Text('End-of-day trading'), value: b.allowEodTrading, onChanged: null),
            const Text('Configure on the Bot Control page or via your admin API.',
                style: TextStyle(fontSize: 11, color: MpColors.textDim)),
          ]))),
          const SizedBox(height: 12),
          Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('System info', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            _kv('Bot status', b.status),
            _kv('Dry run', b.dryRun ? 'yes' : 'no'),
            _kv('Active trades', '${b.totalActiveTrades}'),
            _kv('Active accounts', '${b.activeAccounts}'),
            _kv('App version', 'Mirror Pupil v5.1'),
          ]))),
        ]);
      },
    );
  }

  Widget _kv(String k, String v) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 2),
    child: Row(children: [
      Expanded(child: Text(k, style: const TextStyle(color: MpColors.textDim, fontSize: 12))),
      Text(v, style: kMono.copyWith(fontSize: 12)),
    ]),
  );
}