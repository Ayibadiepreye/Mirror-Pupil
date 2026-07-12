// Mirror Pupil — WebSocket service with auto-reconnect (exponential backoff, max 5).
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'api_client.dart';

enum WsStatus { connecting, connected, disconnected }

class WsService {
  WebSocketChannel? _ch;
  StreamSubscription? _sub;
  int _attempts = 0;
  bool _stopped = false;

  final _statusCtrl = StreamController<WsStatus>.broadcast();
  final _messageCtrl = StreamController<Map<String, dynamic>>.broadcast();

  Stream<WsStatus> get status$ => _statusCtrl.stream;
  Stream<Map<String, dynamic>> get message$ => _messageCtrl.stream;

  void connect() {
    // Skip WebSocket connection in mock mode
    if (MpConfig.useMock) {
      _statusCtrl.add(WsStatus.disconnected);
      _stopped = true; // Prevent reconnection attempts
      return;
    }
    if (_stopped) return;
    _statusCtrl.add(WsStatus.connecting);
    final uri = Uri.parse('${MpConfig.wsBaseUrl}/ws/updates');
    try {
      _ch = WebSocketChannel.connect(uri);
    } catch (_) {
      _scheduleReconnect();
      return;
    }
    _statusCtrl.add(WsStatus.connected);
    _attempts = 0;
    _sub = _ch!.stream.listen(
      (data) {
        try {
          final msg = jsonDecode(data.toString()) as Map<String, dynamic>;
          _messageCtrl.add(msg);
        } catch (_) {}
      },
      onDone: _scheduleReconnect,
      onError: (_) => _scheduleReconnect(),
      cancelOnError: true,
    );
  }

  void _scheduleReconnect() {
    _statusCtrl.add(WsStatus.disconnected);
    if (_stopped || _attempts >= 5) return;
    final wait = Duration(seconds: 1 << _attempts);
    _attempts++;
    Future.delayed(wait, connect);
  }

  Future<void> dispose() async {
    _stopped = true;
    await _sub?.cancel();
    await _ch?.sink.close();
    await _statusCtrl.close();
    await _messageCtrl.close();
  }
}