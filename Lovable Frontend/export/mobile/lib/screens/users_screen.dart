import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../main.dart';
import '../models/models.dart';
import '../theme.dart';

class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});
  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  late Future<List<User>> _pendingF;
  late Future<List<User>> _allF;
  bool _showPendingOnly = true;

  @override
  void initState() {
    super.initState();
    _pendingF = mpApi.pendingUsers();
    _allF = mpApi.allUsers();
  }

  void _reload() => setState(() {
    _pendingF = mpApi.pendingUsers();
    _allF = mpApi.allUsers();
  });

  Future<void> _approve(User u) async {
    final ok = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
      title: const Text('Approve user?'),
      content: Text('${u.email}\nThis will grant them access to the system.'),
      actions: [
        TextButton(onPressed: () => dialogContext.pop(false), child: const Text('Cancel')),
        ElevatedButton(
          onPressed: () => dialogContext.pop(true),
          child: const Text('Approve'),
        ),
      ],
    ));
    if (ok != true) return;

    try {
      final r = await mpApi.approveUser(u.userId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(r['message'] ?? 'User approved')));
      }
      _reload();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to approve user: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      const Padding(
        padding: EdgeInsets.fromLTRB(12, 12, 12, 4),
        child: Align(alignment: Alignment.centerLeft,
          child: Text('User Management', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600))),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(children: [
          ChoiceChip(
            label: const Text('Pending Approval'),
            selected: _showPendingOnly,
            onSelected: (v) => setState(() => _showPendingOnly = v),
          ),
          const SizedBox(width: 8),
          ChoiceChip(
            label: const Text('All Users'),
            selected: !_showPendingOnly,
            onSelected: (v) => setState(() => _showPendingOnly = !v),
          ),
        ]),
      ),
      Expanded(
        child: RefreshIndicator(
          onRefresh: () async => _reload(),
          child: _showPendingOnly
              ? FutureBuilder<List<User>>(
                  future: _pendingF,
                  builder: (ctx, snap) {
                    if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                    final list = snap.data!;
                    if (list.isEmpty) return const Center(child: Text('No pending users.'));
                    return ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: list.length,
                      itemBuilder: (_, i) => _UserCard(
                        u: list[i],
                        onApprove: () => _approve(list[i]),
                      ),
                    );
                  },
                )
              : FutureBuilder<List<User>>(
                  future: _allF,
                  builder: (ctx, snap) {
                    if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                    final list = snap.data!;
                    if (list.isEmpty) return const Center(child: Text('No users.'));
                    return ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: list.length,
                      itemBuilder: (_, i) => _UserCard(u: list[i], onApprove: null),
                    );
                  },
                ),
        ),
      ),
    ]);
  }
}

class _UserCard extends StatelessWidget {
  final User u;
  final VoidCallback? onApprove;
  const _UserCard({required this.u, this.onApprove});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(u.email, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                if (u.displayName != null) ...[
                  const SizedBox(height: 2),
                  Text(u.displayName!, style: const TextStyle(fontSize: 12, color: MpColors.textDim)),
                ],
              ]),
            ),
            if (u.isSuperAdmin) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: MpColors.crimson.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                child: const Text('ADMIN', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600)),
              ),
            ],
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: u.isApproved 
                    ? MpColors.success.withValues(alpha: 0.2) 
                    : Colors.orange.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                u.isApproved ? 'APPROVED' : 'PENDING',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: u.isApproved ? MpColors.success : Colors.orange,
                ),
              ),
            ),
          ]),
          const SizedBox(height: 8),
          Text('Registered ${formatTimeAgo(u.createdAt)}', 
              style: const TextStyle(fontSize: 11, color: MpColors.textDim)),
          if (onApprove != null) ...[
            const SizedBox(height: 10),
            ElevatedButton.icon(
              icon: const Icon(Icons.check_circle, size: 16),
              label: const Text('Approve'),
              onPressed: onApprove,
            ),
          ],
        ]),
      ),
    );
  }
}
