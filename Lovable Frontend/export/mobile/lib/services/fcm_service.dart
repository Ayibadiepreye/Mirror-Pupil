// Mirror Pupil — Firebase Cloud Messaging Service
// Handles push notifications for mobile devices
import 'package:firebase_messaging/firebase_messaging.dart';
import '../main.dart';

/// Background message handler (must be top-level function)
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  print('Handling background message: ${message.messageId}');
  if (message.data.isNotEmpty) {
    print('Background message data: ${message.data}');
  }
}

class FcmService {
  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  
  /// Initialize FCM and register token with backend
  Future<void> initialize() async {
    try {
      // Request notification permissions (iOS)
      final settings = await _fcm.requestPermission(
        alert: true,
        announcement: false,
        badge: true,
        carPlay: false,
        criticalAlert: false,
        provisional: false,
        sound: true,
      );
      
      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        print('User denied notification permissions');
        return;
      }
      
      // Get FCM token
      final token = await _fcm.getToken();
      if (token != null) {
        print('FCM Token: $token');
        await _registerTokenWithBackend(token);
      }
      
      // Listen for token refresh
      _fcm.onTokenRefresh.listen(_registerTokenWithBackend);
      
      // Set up message handlers
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);
      FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);
      FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
      
      // Check if app was opened from a notification
      final initialMessage = await _fcm.getInitialMessage();
      if (initialMessage != null) {
        _handleNotificationTap(initialMessage);
      }
    } catch (e) {
      print('FCM initialization failed: $e');
      print('Push notifications will not be available');
      // App continues without FCM - not critical
    }
  }
  
  Future<void> _registerTokenWithBackend(String token) async {
    try {
      await mpApi.registerFcmToken(token);
      print('FCM token registered with backend');
    } catch (e) {
      print('Failed to register FCM token: $e');
    }
  }
  
  void _handleForegroundMessage(RemoteMessage message) {
    print('Foreground message: ${message.messageId}');
    // Firebase automatically displays notifications
  }
  
  void _handleNotificationTap(RemoteMessage message) {
    print('Notification tapped: ${message.messageId}');
    final notificationId = message.data['notification_id'];
    if (notificationId != null) {
      print('Navigate to notification: $notificationId');
    }
  }
  
  /// Get current FCM token
  Future<String?> getToken() async {
    return await _fcm.getToken();
  }
  
  /// Delete FCM token (sign out)
  Future<void> deleteToken() async {
    await _fcm.deleteToken();
    print('FCM token deleted');
  }
}

final fcmService = FcmService();
