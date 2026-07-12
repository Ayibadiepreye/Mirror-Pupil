import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../main.dart';
import '../models/models.dart' as models;
import '../theme.dart';
import '../utils.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});
  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<List<models.Notification>> _f;
  bool _unreadOnly = false;
  final Set<int> _expanded = {};

  @override
  void initState() { super.initState(); _f = mpApi.listNotifications(limit: 200); }

  void _reload() => setState(() {
    _f = mpApi.listNotifications(unreadOnly: _unreadOnly, limit: 200);
  });

  IconData _icon(String c) {
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

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Row(children: [
          IconButton(
            icon: const Icon(Icons.close),
            tooltip: 'Close',
            onPressed: () {
              if (Navigator.of(context).canPop()) {
                Navigator.of(context).pop();
              } else {
                context.go('/');
              }
            },
          ),
          const SizedBox(width: 4),
          const Expanded(child: Text('Notifications',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 18))),
          Row(children: [
            const Text('Unread', style: TextStyle(fontSize: 11)),
            Switch(value: _unreadOnly, onChanged: (v) { setState(() => _unreadOnly = v); _reload(); }),
          ]),
          ElevatedButton.icon(
            icon: const Icon(Icons.done_all, size: 16),
            label: const Text('All read'),
            style: ElevatedButton.styleFrom(backgroundColor: MpColors.crimson),
            onPressed: () async {
              final n = await mpApi.markAllNotificationsRead();
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Marked $n as read')));
              }
              _reload();
            },
          ),
        ]),
      ),
      Expanded(child: FutureBuilder<List<models.Notification>>(
        future: _f,
        builder: (ctx, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final items = snap.data!;
          final criticals = items.where((n) => n.severity == 'CRITICAL' && !n.read).toList();
          if (items.isEmpty) return const Center(child: Text('No notifications.'));
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                if (criticals.isNotEmpty)
                  Card(
                    color: MpColors.danger.withOpacity(0.12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                      side: const BorderSide(color: MpColors.danger),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        const Row(children: [
                          Icon(Icons.warning_amber, color: MpColors.danger),
                          SizedBox(width: 6),
                          Text('Critical alerts', style: TextStyle(fontWeight: FontWeight.w600)),
                        ]),
                        const SizedBox(height: 6),
                        ...criticals.map((n) => Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Row(children: [
                            Expanded(child: RichText(text: TextSpan(children: [
                              TextSpan(text: n.title, style: const TextStyle(color: MpColors.text, fontWeight: FontWeight.w600)),
                              const TextSpan(text: ' — ', style: TextStyle(color: MpColors.textDim)),
                              TextSpan(text: n.message, style: const TextStyle(color: MpColors.textDim)),
                            ]))),
                            TextButton(
                              onPressed: () async { await mpApi.markNotificationRead(n.notificationId); _reload(); },
                              child: const Text('Dismiss', style: TextStyle(fontSize: 11)),
                            ),
                          ]),
                        )),
                      ]),
                    ),
                  ),
                ...items.map((n) {
                  final open = _expanded.contains(n.notificationId);
                  return Card(
                    margin: const EdgeInsets.only(bottom: 6),
                    child: Container(
                      decoration: BoxDecoration(border: Border(left: BorderSide(color: _sevColor(n.severity), width: 4))),
                      padding: const EdgeInsets.all(10),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Icon(_icon(n.category), color: _sevColor(n.severity), size: 18),
                        const SizedBox(width: 8),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            if (!n.read) Container(
                              width: 6, height: 6, margin: const EdgeInsets.only(right: 6),
                              decoration: const BoxDecoration(color: MpColors.red, shape: BoxShape.circle),
                            ),
                            Expanded(child: Text(n.title, style: const TextStyle(fontWeight: FontWeight.w600))),
                            Text(formatTimeAgo(n.createdAt), style: const TextStyle(fontSize: 11, color: MpColors.textDim)),
                          ]),
                          const SizedBox(height: 2),
                          Text(n.message, style: const TextStyle(fontSize: 12)),
                          const SizedBox(height: 6),
                          Wrap(spacing: 6, runSpacing: 4, children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(color: _sevColor(n.severity).withOpacity(0.15), borderRadius: BorderRadius.circular(20)),
                              child: Text(n.severity, style: TextStyle(color: _sevColor(n.severity), fontSize: 9, fontWeight: FontWeight.w600)),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(20)),
                              child: Text(n.category, style: const TextStyle(fontSize: 9, color: MpColors.textDim)),
                            ),
                            if (n.accountKey != null)
                              Text(shortenKey(n.accountKey!), style: kMono.copyWith(fontSize: 10, color: MpColors.textDim)),
                            if (n.metadata.isNotEmpty)
                              GestureDetector(
                                onTap: () => setState(() => open ? _expanded.remove(n.notificationId) : _expanded.add(n.notificationId)),
                                child: Row(mainAxisSize: MainAxisSize.min, children: [
                                  Icon(open ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down, size: 14, color: MpColors.textDim),
                                  const Text('metadata', style: TextStyle(fontSize: 10, color: MpColors.textDim)),
                                ]),
                              ),
                          ]),
                          if (open && n.metadata.isNotEmpty) Container(
                            margin: const EdgeInsets.only(top: 6),
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(color: Colors.black.withOpacity(0.3), borderRadius: BorderRadius.circular(6)),
                            child: Text(n.metadata.toString(), style: kMono.copyWith(fontSize: 11)),
                          ),
                        ])),
                        Column(children: [
                          if (!n.read)
                            IconButton(
                              tooltip: 'Mark read',
                              icon: const Icon(Icons.mark_email_read_outlined, size: 18),
                              onPressed: () async { await mpApi.markNotificationRead(n.notificationId); _reload(); },
                            ),
                          IconButton(
                            tooltip: 'Delete',
                            icon: const Icon(Icons.delete_outline, size: 18, color: MpColors.danger),
                            onPressed: () async {
                              final ok = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(
                                title: const Text('Delete notification?'),
                                content: Text(n.title),
                                actions: [
                                  TextButton(onPressed: () => dialogContext.pop(false), child: const Text('Cancel')),
                                  ElevatedButton(
                                    style: ElevatedButton.styleFrom(backgroundColor: MpColors.danger),
                                    onPressed: () => dialogContext.pop(true),
                                    child: const Text('Delete'),
                                  ),
                                ],
                              ));
                              if (ok == true) { await mpApi.deleteNotification(n.notificationId); _reload(); }
                            },
                          ),
                        ]),
                      ]),
                    ),
                  );
                }),
              ],
            ),
          );
        },
      )),
    ]);
  }
}