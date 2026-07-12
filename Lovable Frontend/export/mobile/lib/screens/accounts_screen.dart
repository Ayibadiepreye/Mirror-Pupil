import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../main.dart';
import '../models/models.dart';
import '../theme.dart';
import '../utils.dart' as utils;

enum _Status { all, active, paused, breached }

class AccountsScreen extends StatefulWidget {
  const AccountsScreen({super.key});
  @override
  State<AccountsScreen> createState() => _AccountsScreenState();
}

class _AccountsScreenState extends State<AccountsScreen> {
  late Future<List<Account>> _f;
  late Future<List<RiskProfile>> _profiles;
  String _search = '';
  _Status _status = _Status.all;

  @override
  void initState() {
    super.initState();
    _f = mpApi.listAccounts();
    _profiles = mpApi.listProfiles();
  }

  void _reload() => setState(() => _f = mpApi.listAccounts());

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

  Future<void> _delete(Account a) async {
    if (!await _confirm('Delete account?',
        desc: 'Remove ${a.displayName ?? a.accountKey} from Mirror Pupil. This cannot be undone.',
        destructive: true, confirm: 'Delete')) {
      return;
    }
    await mpApi.deleteAccount(a.accountKey);
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
        child: Row(children: [
          const Expanded(child: Text('Accounts',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600))),
          ElevatedButton.icon(
            icon: const Icon(Icons.add, size: 18),
            label: const Text('Add'),
            onPressed: () async {
              final added = await showDialog<bool>(
                context: context,
                builder: (_) => const AddAccountDialog(),
              );
              if (added == true) _reload();
            },
          ),
        ]),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(children: [
          Expanded(child: TextField(
            decoration: const InputDecoration(
              hintText: 'Search…', prefixIcon: Icon(Icons.search), isDense: true,
            ),
            onChanged: (v) => setState(() => _search = v),
          )),
          const SizedBox(width: 8),
          DropdownButton<_Status>(
            value: _status,
            onChanged: (v) => setState(() => _status = v ?? _Status.all),
            items: const [
              DropdownMenuItem(value: _Status.all, child: Text('All')),
              DropdownMenuItem(value: _Status.active, child: Text('Active')),
              DropdownMenuItem(value: _Status.paused, child: Text('Paused')),
              DropdownMenuItem(value: _Status.breached, child: Text('Breached')),
            ],
          ),
        ]),
      ),
      Expanded(
        child: FutureBuilder<List<Account>>(
          future: _f,
          builder: (ctx, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final s = _search.toLowerCase();
            final filtered = snap.data!.where((a) {
              if (_status == _Status.active && (a.paused || a.breached)) return false;
              if (_status == _Status.paused && !a.paused) return false;
              if (_status == _Status.breached && !a.breached) return false;
              if (s.isEmpty) return true;
              return a.tlEmail.toLowerCase().contains(s)
                  || (a.displayName ?? '').toLowerCase().contains(s)
                  || a.accountKey.toLowerCase().contains(s);
            }).toList();
            if (filtered.isEmpty) return const Center(child: Text('No accounts match.'));
            return RefreshIndicator(
              onRefresh: () async => _reload(),
              child: FutureBuilder<List<RiskProfile>>(
                future: _profiles,
                builder: (ctx, ps) {
                  final profiles = ps.data ?? const <RiskProfile>[];
                  return ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) => _AccountCard(
                      a: filtered[i],
                      profile: profiles.firstWhere(
                        (p) => p.profileId == filtered[i].riskProfileId,
                        orElse: () => RiskProfile(
                          profileId: 0, profileName: '—', isDefault: false,
                          maxRiskPerTradePct: 0, dailyLossPct: 0, dailyTrailing: false,
                          overallLossPct: 0, overallTrailing: false, overallTrailFromClosedBalance: false,
                          payoutBufferPct: 0, maxConcurrentTrades: 0,
                          commissionPerLot: 0, safetyBufferPct: 0,
                        ),
                      ),
                      onPauseResume: () async {
                        filtered[i].paused
                          ? await mpApi.resumeAccount(filtered[i].accountKey)
                          : await mpApi.pauseAccount(filtered[i].accountKey);
                        _reload();
                      },
                      onDelete: () => _delete(filtered[i]),
                      onEdit: () async {
                        final saved = await showDialog<bool>(
                          context: context,
                          builder: (_) => EditAccountDialog(account: filtered[i], profiles: profiles),
                        );
                        if (saved == true) _reload();
                      },
                    ),
                  );
                },
              ),
            );
          },
        ),
      ),
    ]);
  }
}

class _AccountCard extends StatelessWidget {
  final Account a;
  final RiskProfile profile;
  final VoidCallback onPauseResume, onDelete, onEdit;
  const _AccountCard({required this.a, required this.profile,
      required this.onPauseResume, required this.onDelete, required this.onEdit});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [MpColors.crimson.withValues(alpha: 0.08), MpColors.base],
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(a.displayName ?? a.tlEmail,
                style: const TextStyle(fontWeight: FontWeight.w600))),
            if (a.profitCapFrozen)
              const _Pill('CAP FROZEN', color: MpColors.danger)
            else if (a.breached)
              const _Pill('BREACHED', color: MpColors.danger)
            else if (a.paused)
              const _Pill('PAUSED', color: MpColors.warning)
            else if (a.profitCapEnabled)
              const _Pill('CAP ACTIVE', color: MpColors.primary)
            else
              const _Pill('ACTIVE', color: MpColors.success),
          ]),
          Text(a.accountKey, style: kMono.copyWith(fontSize: 11, color: MpColors.textDim)),
          Text(a.tlServer, style: const TextStyle(fontSize: 11, color: MpColors.textDim)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: _kv('Balance', utils.formatCurrency(a.currentBalance))),
            Expanded(child: _kv('Daily P&L', utils.formatCurrency(a.dailyPnl),
                color: a.dailyPnl >= 0 ? MpColors.success : MpColors.danger)),
            Expanded(child: _kv('Profile', profile.profileName)),
          ]),
          const SizedBox(height: 12),
          _progressBar('Daily Drawdown', a.dailyDrawdownPct, a.dailyLossLimitPct),
          const SizedBox(height: 8),
          _progressBar('Max Drawdown', a.overallDrawdownPct, a.overallLossLimitPct),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: _kv('Consistency', a.consistencyScore != null ? '${a.consistencyScore!.toStringAsFixed(1)}%' : 'N/A',
                color: _getConsistencyColor(a.consistencyScore))),
            Expanded(child: _kv('Profitable Days', '${a.profitableDaysCount} / ${a.requiredProfitableDays}')),
          ]),
          
          if (a.profitCapEnabled) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: a.profitCapFrozen ? MpColors.danger.withValues(alpha: 0.1) : MpColors.primary.withValues(alpha: 0.1),
                border: Border.all(color: a.profitCapFrozen ? MpColors.danger : MpColors.primary),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(children: [
                Icon(a.profitCapFrozen ? Icons.lock : Icons.security, 
                  size: 16, 
                  color: a.profitCapFrozen ? MpColors.danger : MpColors.primary),
                const SizedBox(width: 8),
                Expanded(child: Text(
                  a.profitCapFrozen 
                    ? 'Profit Cap FROZEN' 
                    : 'Profit Cap: ${a.profitCapType == "percentage" ? "${a.profitCapValue}%" : "\$${a.profitCapValue}"}',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: a.profitCapFrozen ? MpColors.danger : MpColors.primary,
                  ),
                )),
              ]),
            ),
          ],
          
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            OutlinedButton.icon(
              icon: Icon(a.paused ? Icons.play_arrow : Icons.pause, size: 16),
              label: Text(a.paused ? 'Resume' : 'Pause'),
              onPressed: onPauseResume,
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.edit_outlined, size: 16),
              label: const Text('Edit'),
              onPressed: onEdit,
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.delete_outline, size: 16, color: MpColors.danger),
              label: const Text('Delete', style: TextStyle(color: MpColors.danger)),
              onPressed: onDelete,
            ),
          ]),
        ]),
      ),
    );
  }

  Widget _kv(String k, String v, {Color? color}) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(k.toUpperCase(), style: const TextStyle(fontSize: 9, color: MpColors.textDim, letterSpacing: 1)),
      Text(v, style: kMono.copyWith(fontWeight: FontWeight.w600, color: color)),
    ],
  );

  Widget _progressBar(String label, double current, double limit) {
    final ratio = limit > 0 ? (current / limit) : 0.0;
    final color = ratio > 0.9 ? MpColors.danger : ratio > 0.7 ? MpColors.warning : MpColors.success;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text(label, style: const TextStyle(fontSize: 10, color: MpColors.textDim)),
        Text('${current.toStringAsFixed(2)}% / ${limit.toStringAsFixed(0)}%',
            style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w600)),
      ]),
      const SizedBox(height: 4),
      ClipRRect(
        borderRadius: BorderRadius.circular(2),
        child: LinearProgressIndicator(
          value: ratio.clamp(0.0, 1.0),
          backgroundColor: MpColors.border,
          valueColor: AlwaysStoppedAnimation(color),
          minHeight: 6,
        ),
      ),
    ]);
  }

  Color _getConsistencyColor(double? score) {
    if (score == null) return MpColors.textDim;
    if (score >= 20) return MpColors.danger;
    if (score >= 18) return MpColors.warning;
    return MpColors.success;
  }
}

class _Pill extends StatelessWidget {
  final String text;
  final Color color;
  const _Pill(this.text, {required this.color});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(
      color: color.withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(20),
    ),
    child: Text(text, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600)),
  );
}

// ─── Add Account Dialog (Discover + Manual) ──────────────────────────

class AddAccountDialog extends StatefulWidget {
  const AddAccountDialog({super.key});
  @override
  State<AddAccountDialog> createState() => _AddAccountDialogState();
}

class _AddAccountDialogState extends State<AddAccountDialog> with SingleTickerProviderStateMixin {
  late final TabController _tc = TabController(length: 2, vsync: this);
  final _discover = {'email': '', 'password': '', 'server': '', 'prop_firm': ''};
  List<Map<String, dynamic>> _discovered = [];
  bool _busy = false;

  final _manual = {
    'tl_email': '', 'tl_password': '', 'tl_prop_firm': '',
    'tl_server': '', 'tl_account_id': '', 'display_name': '',
  };

  Future<void> _runDiscover() async {
    setState(() => _busy = true);
    try {
      final r = await mpApi.discoverAccounts(_discover);
      setState(() => _discovered = r);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Found ${r.length} account(s)')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Discover failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addDiscovered(Map<String, dynamic> a) async {
    try {
      await mpApi.createAccount({
        'credential_key': _discover['email'],
        'tl_email': _discover['email'],
        'tl_password': _discover['password'],
        'tl_prop_firm': _discover['prop_firm'],
        'tl_server': _discover['server'],
        'tl_account_id': a['id'],
        'display_name': a['number'],
        'initial_balance': a['balance'],
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Account added')));
        // Remove the added account from discovered list
        setState(() {
          _discovered.removeWhere((acc) => acc['id'] == a['id']);
        });
        // Close dialog if no more accounts to add
        if (_discovered.isEmpty) {
          context.pop(true);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to add: $e')));
      }
    }
  }

  Future<void> _addManual() async {
    setState(() => _busy = true);
    try {
      await mpApi.createAccount({
        'credential_key': _manual['tl_email'],
        'tl_email': _manual['tl_email'],
        'tl_password': _manual['tl_password'],
        'tl_prop_firm': _manual['tl_prop_firm'],
        'tl_server': _manual['tl_server'],
        'tl_account_id': _manual['tl_account_id'],
        'display_name': (_manual['display_name']?.isEmpty ?? true) ? _manual['tl_account_id'] : _manual['display_name'],
        'initial_balance': 0.0, // User will need to sync or manually set this later
      });
      if (mounted) context.pop(true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520, maxHeight: 600),
        child: Padding(padding: const EdgeInsets.all(16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Text('Add account', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            const Text('Discover from TradeLocker or enter details manually.',
                style: TextStyle(color: MpColors.textDim, fontSize: 12)),
            const SizedBox(height: 12),
            TabBar(controller: _tc, labelColor: MpColors.red, indicatorColor: MpColors.red,
              tabs: const [Tab(text: 'Discover'), Tab(text: 'Manual')]),
            Flexible(child: TabBarView(controller: _tc, children: [
              SingleChildScrollView(padding: const EdgeInsets.symmetric(vertical: 12),
                child: Column(children: [
                  _field('Email', (v) => _discover['email'] = v),
                  _field('Password', (v) => _discover['password'] = v, obscure: true),
                  _dropdown('Server', _discover['server'], ['live', 'demo'], (v) => setState(() => _discover['server'] = v ?? 'live')),
                  _field('Broker / Prop firm', (v) => _discover['prop_firm'] = v),
                  const SizedBox(height: 8),
                  SizedBox(width: double.infinity, child: ElevatedButton(
                    onPressed: _busy ? null : _runDiscover,
                    child: Text(_busy ? 'Discovering…' : 'Discover accounts'),
                  )),
                  if (_discovered.isNotEmpty) const SizedBox(height: 12),
                  ..._discovered.map((a) => Card(child: ListTile(
                    dense: true,
                    title: Text('Account ${a['number']}'),
                    subtitle: Text('\$${(a['balance'] as num).toStringAsFixed(2)}', style: kMono.copyWith(fontSize: 11)),
                    trailing: OutlinedButton(onPressed: () => _addDiscovered(a), child: const Text('Add')),
                  ))),
                ]),
              ),
              SingleChildScrollView(padding: const EdgeInsets.symmetric(vertical: 12),
                child: Column(children: [
                  _field('Email', (v) => _manual['tl_email'] = v),
                  _field('Password', (v) => _manual['tl_password'] = v, obscure: true),
                  _field('Broker / Prop firm', (v) => _manual['tl_prop_firm'] = v),
                  _dropdown('Server', _manual['tl_server'], ['live', 'demo'], (v) => setState(() => _manual['tl_server'] = v ?? 'live')),
                  _field('Account ID', (v) => _manual['tl_account_id'] = v),
                  _field('Display name', (v) => _manual['display_name'] = v),
                  const SizedBox(height: 8),
                  SizedBox(width: double.infinity, child: ElevatedButton(
                    onPressed: _busy ? null : _addManual,
                    child: Text(_busy ? 'Adding…' : 'Add account'),
                  )),
                ]),
              ),
            ])),
            Row(mainAxisAlignment: MainAxisAlignment.end, children: [
              TextButton(onPressed: () => context.pop(), child: const Text('Close')),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _field(String label, ValueChanged<String> onChanged, {bool obscure = false}) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: TextField(
      obscureText: obscure,
      decoration: InputDecoration(labelText: label, isDense: true),
      onChanged: onChanged,
    ),
  );

  Widget _dropdown(String label, String? value, List<String> items, ValueChanged<String?> onChanged) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: DropdownButtonFormField<String>(
      decoration: InputDecoration(labelText: label, isDense: true),
      initialValue: value == null || value.isEmpty ? null : value,
      items: items.map((v) => DropdownMenuItem(
        value: v,
        child: Text(v.substring(0, 1).toUpperCase() + v.substring(1)),
      )).toList(),
      onChanged: onChanged,
    ),
  );
}

// ─── Edit Account Dialog ────────────────────────────────────────────

class EditAccountDialog extends StatefulWidget {
  final Account account;
  final List<RiskProfile> profiles;
  const EditAccountDialog({super.key, required this.account, required this.profiles});
  @override
  State<EditAccountDialog> createState() => _EditAccountDialogState();
}

class _EditAccountDialogState extends State<EditAccountDialog> {
  late String _displayName = widget.account.displayName ?? '';
  late double? _lot = widget.account.lotSizeOverride;
  late int? _maxTrades = widget.account.maxConcurrentTradesOverride;
  late int? _profileId = widget.account.riskProfileId;
  late bool _profitCapEnabled = widget.account.profitCapEnabled;
  late String _profitCapType = widget.account.profitCapType ?? 'dollar';
  late double _profitCapValue = widget.account.profitCapValue ?? 0.0;
  late double _profitCapBuffer = widget.account.profitCapBufferPct;
  bool _busy = false;
  bool _busyProfitCap = false;
  bool _busyUnfreeze = false;

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      await mpApi.updateAccount(widget.account.accountKey, {
        'display_name': _displayName,
        'lot_size_override': _lot,
        'max_concurrent_trades_override': _maxTrades,
        'risk_profile_id': _profileId,
      });
      if (mounted) context.pop(true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
  
  Future<void> _saveProfitCap() async {
    // Validation
    if (_profitCapEnabled) {
      if (_profitCapValue <= 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Cap value must be greater than 0'))
        );
        return;
      }
      if (_profitCapBuffer < 0 || _profitCapBuffer > 100) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Buffer must be between 0 and 100'))
        );
        return;
      }
    }
    
    setState(() => _busyProfitCap = true);
    try {
      await mpApi.updateProfitCap(widget.account.accountKey, {
        'enabled': _profitCapEnabled,
        'cap_type': _profitCapType,
        'cap_value': _profitCapValue,
        'buffer_pct': _profitCapBuffer,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profit cap updated successfully'))
        );
        context.pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Profit cap update failed: $e'), backgroundColor: MpColors.danger)
        );
      }
    } finally {
      if (mounted) setState(() => _busyProfitCap = false);
    }
  }
  
  Future<void> _unfreezeAccount() async {
    setState(() => _busyUnfreeze = true);
    try {
      await mpApi.unfreezeProfitCap(widget.account.accountKey);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Account unfrozen successfully'))
        );
        context.pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Unfreeze failed: $e'), backgroundColor: MpColors.danger)
        );
      }
    } finally {
      if (mounted) setState(() => _busyUnfreeze = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit account'),
      content: SizedBox(width: 400, child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(widget.account.accountKey, style: kMono.copyWith(fontSize: 11, color: MpColors.textDim)),
        const SizedBox(height: 8),
        TextField(
          decoration: const InputDecoration(labelText: 'Display name'),
          controller: TextEditingController(text: _displayName),
          onChanged: (v) => _displayName = v,
        ),
        const SizedBox(height: 8),
        TextField(
          decoration: const InputDecoration(labelText: 'Lot size override'),
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          controller: TextEditingController(text: _lot?.toString() ?? ''),
          onChanged: (v) => _lot = v.isEmpty ? null : double.tryParse(v),
        ),
        const SizedBox(height: 8),
        TextField(
          decoration: const InputDecoration(labelText: 'Max concurrent trades'),
          keyboardType: TextInputType.number,
          controller: TextEditingController(text: _maxTrades?.toString() ?? ''),
          onChanged: (v) => _maxTrades = v.isEmpty ? null : int.tryParse(v),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<int?>(
          decoration: const InputDecoration(labelText: 'Risk profile'),
          initialValue: _profileId,
          isExpanded: true,
          items: [
            const DropdownMenuItem<int?>(value: null, child: Text('— None —')),
            ...widget.profiles.map((p) => DropdownMenuItem<int?>(
              value: p.profileId,
              child: Text('${p.profileName}${p.isDefault ? " (default)" : ""}', 
                overflow: TextOverflow.ellipsis, maxLines: 1),
            )),
          ],
          onChanged: (v) => setState(() => _profileId = v),
        ),
        
        const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 8),
        
        // ─── Profit Cap Section ───
        Row(children: [
          const Text('Profit Cap', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(width: 8),
          if (widget.account.profitCapFrozen)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: MpColors.danger,
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text('FROZEN', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
            ),
        ]),
        const SizedBox(height: 8),
        
        if (widget.account.profitCapFrozen) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: MpColors.danger.withOpacity(0.1),
              border: Border.all(color: MpColors.danger),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(children: [
              const Text(
                '⚠️ Account frozen due to profit cap breach',
                style: TextStyle(fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              const Text(
                'All trades have been closed. Unfreeze to resume trading.',
                style: TextStyle(fontSize: 12),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              ElevatedButton(
                onPressed: _busyUnfreeze ? null : _unfreezeAccount,
                style: ElevatedButton.styleFrom(backgroundColor: MpColors.success),
                child: Text(_busyUnfreeze ? 'Unfreezing…' : 'Unfreeze Account'),
              ),
            ]),
          ),
          const SizedBox(height: 12),
        ],
        
        SwitchListTile(
          title: const Text('Enable Profit Cap'),
          value: _profitCapEnabled,
          onChanged: (v) => setState(() => _profitCapEnabled = v),
          contentPadding: EdgeInsets.zero,
        ),
        
        if (_profitCapEnabled) ...[
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            decoration: const InputDecoration(labelText: 'Cap Type'),
            initialValue: _profitCapType,
            isExpanded: true,
            items: const [
              DropdownMenuItem(value: 'dollar', child: Text('Dollar Amount')),
              DropdownMenuItem(value: 'percentage', child: Text('Percentage')),
            ],
            onChanged: (v) => setState(() => _profitCapType = v ?? 'dollar'),
          ),
          const SizedBox(height: 8),
          TextField(
            decoration: InputDecoration(
              labelText: 'Cap Value',
              suffixText: _profitCapType == 'percentage' ? '%' : '\$',
              helperText: _profitCapType == 'percentage' 
                ? 'e.g., 5 = 5% profit cap'
                : 'e.g., 250 = \$250 profit cap',
            ),
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            controller: TextEditingController(text: _profitCapValue.toString()),
            onChanged: (v) => _profitCapValue = double.tryParse(v) ?? 0.0,
          ),
          const SizedBox(height: 8),
          TextField(
            decoration: const InputDecoration(
              labelText: 'Safety Buffer (%)',
              suffixText: '%',
              helperText: 'Triggers before exact cap (default: 2%)',
            ),
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            controller: TextEditingController(text: _profitCapBuffer.toString()),
            onChanged: (v) => _profitCapBuffer = double.tryParse(v) ?? 2.0,
          ),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _busyProfitCap ? null : _saveProfitCap,
            style: ElevatedButton.styleFrom(backgroundColor: MpColors.primary),
            child: Text(_busyProfitCap ? 'Saving Profit Cap…' : 'Save Profit Cap'),
          ),
        ],
      ]))),
      actions: [
        TextButton(onPressed: () => context.pop(false), child: const Text('Cancel')),
        ElevatedButton(onPressed: _busy ? null : _save, child: Text(_busy ? 'Saving…' : 'Save')),
      ],
    );
  }
}