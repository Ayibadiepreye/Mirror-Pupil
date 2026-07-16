import 'dart:math' as math;
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'firebase_options.dart';
import 'theme.dart';
import 'api/api_client.dart';
import 'api/ws_service.dart';
import 'auth/auth_service.dart';
import 'services/fcm_service.dart';
import 'screens/login_screen.dart';
import 'screens/pending_approval_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/accounts_screen.dart';
import 'screens/trades_screen.dart';
import 'screens/history_screen.dart';
import 'screens/notifications_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/bot_control_screen.dart';

/// Globals. Swap for Riverpod/Provider/BLoC in production.
late MpApi mpApi;
late WsService mpWs;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  mpApi = MpApi();
  mpWs = WsService()..connect();
  await auth.load();
  
  // Initialize push notifications (only if user is logged in)
  if (auth.current != null) {
    await fcmService.initialize();
  }
  
  runApp(const MpApp());
}

final _router = GoRouter(
  refreshListenable: _AuthListenable(),
  redirect: (ctx, state) {
    final loggedIn = auth.current != null;
    final atLogin = state.matchedLocation == '/login';
    final atPending = state.matchedLocation == '/pending-approval';
    
    if (!loggedIn && !atLogin && !atPending) return '/login';
    if (loggedIn && atLogin) return '/';
    return null;
  },
  routes: [
    GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    GoRoute(path: '/pending-approval', builder: (_, __) => const PendingApprovalScreen()),
    ShellRoute(
      builder: (ctx, state, child) =>
          RootShell(currentLocation: state.uri.path, child: child),
      routes: [
        GoRoute(path: '/', builder: (_, __) => const DashboardScreen()),
        GoRoute(path: '/accounts', builder: (_, __) => const AccountsScreen()),
        GoRoute(path: '/trades', builder: (_, __) => const ActiveTradesScreen()),
        GoRoute(path: '/history', builder: (_, __) => const HistoryScreen()),
        GoRoute(path: '/notifications', builder: (_, __) => const NotificationsScreen()),
        GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
        GoRoute(path: '/bot-control', builder: (_, __) => const BotControlScreen()),
      ],
    ),
  ],
);

class _AuthListenable extends ChangeNotifier {
  _AuthListenable() {
    auth.changes.listen((_) => notifyListeners());
  }
}

class MpApp extends StatelessWidget {
  const MpApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp.router(
        title: 'Mirror Pupil',
        debugShowCheckedModeBanner: false,
        theme: mpTheme(),
        routerConfig: _router,
      );
}

class RootShell extends StatefulWidget {
  final Widget child;
  final String currentLocation;
  const RootShell({super.key, required this.child, required this.currentLocation});

  @override
  State<RootShell> createState() => _RootShellState();
}

/// Tabs mirror the web sidebar (6 items). The bell in the AppBar handles
/// notifications, just like the web header.
const List<(String, String, IconData)> _tabs = [
  ('/',            'Dashboard', Icons.dashboard_outlined),
  ('/accounts',    'Accounts',  Icons.people_outline),
  ('/trades',      'Active',    Icons.trending_up),
  ('/history',     'History',   Icons.history),
  ('/bot-control', 'Bot',       Icons.smart_toy_outlined),
  ('/settings',    'Settings',  Icons.settings_outlined),
];

class _RootShellState extends State<RootShell> {
  bool _open = false;
  int _unreadCount = 0;
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    _loadUnreadCount();
    // Poll for unread count every 30 seconds
    _pollTimer = Timer.periodic(const Duration(seconds: 30), (_) => _loadUnreadCount());
    
    // Listen to WebSocket notifications
    mpWs.onNotification.listen((_) {
      _loadUnreadCount();
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadUnreadCount() async {
    try {
      final count = await mpApi.unreadCount();
      if (mounted) setState(() => _unreadCount = count);
    } catch (e) {
      // Silently fail - don't disrupt UI
    }
  }

  @override
  void didUpdateWidget(covariant RootShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.currentLocation != widget.currentLocation && _open) {
      setState(() => _open = false);
    }
    // Reload unread count when navigating away from notifications
    if (oldWidget.currentLocation.startsWith('/notifications') && 
        !widget.currentLocation.startsWith('/notifications')) {
      _loadUnreadCount();
    }
  }

  @override
  Widget build(BuildContext context) {
    final loc = widget.currentLocation;
    final onNotifs = loc.startsWith('/notifications');
    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          // Mirror Pupil logo
          SvgPicture.asset('assets/logo.svg', width: 24, height: 24),
          const SizedBox(width: 8),
          const Text('Mirror Pupil',
              style: TextStyle(fontWeight: FontWeight.w600)),
        ]),
        actions: [
          Stack(
            clipBehavior: Clip.none,
            children: [
              IconButton(
                icon: Icon(onNotifs ? Icons.notifications_active : Icons.notifications_none,
                    color: onNotifs ? MpColors.red : null),
                tooltip: onNotifs ? 'Close notifications' : 'Open notifications',
                onPressed: () => context.go(onNotifs ? '/' : '/notifications'),
              ),
              if (_unreadCount > 0)
                Positioned(
                  right: 8,
                  top: 8,
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: const BoxDecoration(
                      color: MpColors.red,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 16,
                    ),
                    child: Text(
                      _unreadCount > 99 ? '99+' : '$_unreadCount',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: () async {
              await auth.signOut();
              if (mounted) context.go('/login');
            },
          ),
        ],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(1),
          child: Divider(height: 1, color: MpColors.border),
        ),
      ),
      body: Stack(children: [
        // Main content
        Positioned.fill(child: widget.child),
        
        // Navigation FAB and buttons
        Positioned(
          right: 16, bottom: 16,
          child: IgnorePointer(
            ignoring: false,
            child: SizedBox(
              width: 400, height: 400,
              child: Stack(
                clipBehavior: Clip.none,
                alignment: Alignment.bottomRight,
                children: [
                  // Backdrop overlay when menu is open (only covers the button area)
                  if (_open)
                    Positioned.fill(
                      child: GestureDetector(
                        onTap: () => setState(() => _open = false),
                        child: Container(color: Colors.transparent),
                      ),
                    ),
                  
                  // Navigation buttons (positioned radially)
                  for (int i = 0; i < _tabs.length; i++) _buildRadialItem(i, loc),
                  
                  // FAB toggle button (bottom right corner)
                  Positioned(
                    right: 0, bottom: 0,
                    child: FloatingActionButton(
                      backgroundColor: MpColors.red,
                      foregroundColor: Colors.white,
                      elevation: 8,
                      onPressed: () {
                        setState(() => _open = !_open);
                      },
                      child: AnimatedRotation(
                        turns: _open ? 0.125 : 0,
                        duration: const Duration(milliseconds: 200),
                        child: const Icon(Icons.add),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ]),
    );
  }

  Widget _buildRadialItem(int i, String loc) {
    // Don't render buttons when menu is closed
    if (!_open) return const SizedBox.shrink();
    
    // Roomy quarter-arc with extra sweep so each button has its own space.
    const radius = 150.0;
    const startDeg = 175.0;
    const endDeg = 280.0;
    final step = _tabs.length > 1 ? (endDeg - startDeg) / (_tabs.length - 1) : 0.0;
    final angle = (startDeg + step * i) * math.pi / 180;
    final dx = math.cos(angle) * radius;
    final dy = math.sin(angle) * radius;
    final t = _tabs[i];
    final active = t.$1 == '/' ? loc == '/' : loc.startsWith(t.$1);
    
    // Position relative to bottom-right corner (where FAB is)
    // dx is negative (left), dy is negative (up)
    return Positioned(
      right: 28 - dx - 24, // 28 = half FAB width, 24 = half button width
      bottom: 28 - dy - 24, // 28 = half FAB height, 24 = half button height
      child: Material(
        color: active ? MpColors.red : MpColors.base,
        elevation: 8,
        shape: CircleBorder(
          side: BorderSide(color: active ? MpColors.red : MpColors.border, width: 2),
        ),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: () {
            setState(() => _open = false); 
            context.go(t.$1); 
          },
          child: Container(
            width: 56, 
            height: 56,
            alignment: Alignment.center,
            child: Icon(t.$3, size: 24,
                color: active ? Colors.white : MpColors.text),
          ),
        ),
      ),
    );
  }
}