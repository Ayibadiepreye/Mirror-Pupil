// Mirror Pupil — Firebase Authentication Service
// Handles Google Sign-In and Email/Password authentication with Firebase
import 'dart:async';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_client.dart';

class MpSession {
  final String token;
  final String email;
  final String displayName;
  final String provider; // 'google' | 'password'
  
  MpSession({
    required this.token,
    required this.email,
    required this.displayName,
    required this.provider,
  });

  Map<String, dynamic> toJson() => {
    'token': token,
    'email': email,
    'displayName': displayName,
    'provider': provider,
  };
  
  static MpSession fromJson(Map<String, dynamic> j) => MpSession(
    token: j['token'] ?? '',
    email: j['email'] ?? '',
    displayName: j['displayName'] ?? '',
    provider: j['provider'] ?? 'password',
  );
}

class AuthService {
  static const _key = 'mp.session.v1';
  final _ctrl = StreamController<MpSession?>.broadcast();
  final _auth = FirebaseAuth.instance;
  final _googleSignIn = GoogleSignIn();
  MpSession? _current;

  Stream<MpSession?> get changes => _ctrl.stream;
  MpSession? get current => _current;

  Future<void> load() async {
    // In mock mode, create a fake session to bypass authentication
    if (MpConfig.useMock) {
      _current = MpSession(
        token: 'mock-token',
        email: 'mock@example.com',
        displayName: 'Mock User',
        provider: 'mock',
      );
      _ctrl.add(_current);
      return;
    }
    
    final p = await SharedPreferences.getInstance();
    final raw = p.getString(_key);
    if (raw != null && raw.isNotEmpty) {
      final parts = raw.split('|');
      if (parts.length == 4) {
        _current = MpSession(
          token: parts[0],
          email: parts[1],
          displayName: parts[2],
          provider: parts[3],
        );
      }
    }
    
    // Check if Firebase user still valid
    final user = _auth.currentUser;
    if (user != null) {
      try {
        final token = await user.getIdToken();
        if (token != null) {
          _current = MpSession(
            token: token,
            email: user.email ?? '',
            displayName: user.displayName ?? user.email?.split('@').first ?? 'User',
            provider: user.providerData.first.providerId.contains('google') ? 'google' : 'password',
          );
          await _save(_current!);
        }
      } catch (_) {
        // Token refresh failed, clear session
        await signOut();
      }
    }
    
    _ctrl.add(_current);
  }

  Future<void> _save(MpSession s) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_key, '${s.token}|${s.email}|${s.displayName}|${s.provider}');
    _current = s;
    _ctrl.add(s);
  }

  Future<void> signOut() async {
    try {
      await _auth.signOut();
      await _googleSignIn.signOut();
    } catch (_) {}
    
    final p = await SharedPreferences.getInstance();
    await p.remove(_key);
    _current = null;
    _ctrl.add(null);
  }

  /// Sign in with email and password using Firebase Authentication
  Future<MpSession> signInWithPassword(String email, String password) async {
    if (email.isEmpty || password.isEmpty) {
      throw Exception('Email and password required');
    }
    
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
      
      final user = credential.user;
      if (user == null) throw Exception('Authentication failed');
      
      final token = await user.getIdToken();
      if (token == null) throw Exception('Failed to get auth token');
      
      final session = MpSession(
        token: token,
        email: user.email ?? email,
        displayName: user.displayName ?? email.split('@').first,
        provider: 'password',
      );
      
      await _save(session);
      return session;
    } on FirebaseAuthException catch (e) {
      throw Exception(_getFirebaseErrorMessage(e.code));
    }
  }

  /// Sign in with Google using Firebase Authentication
  Future<MpSession> signInWithGoogle() async {
    try {
      // Trigger Google Sign-In flow
      final googleUser = await _googleSignIn.signIn();
      if (googleUser == null) throw Exception('Google sign-in cancelled');
      
      // Get authentication details
      final googleAuth = await googleUser.authentication;
      
      // Create Firebase credential
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );
      
      // Sign in to Firebase
      final userCredential = await _auth.signInWithCredential(credential);
      final user = userCredential.user;
      if (user == null) throw Exception('Authentication failed');
      
      final token = await user.getIdToken();
      if (token == null) throw Exception('Failed to get auth token');
      
      final session = MpSession(
        token: token,
        email: user.email ?? '',
        displayName: user.displayName ?? user.email?.split('@').first ?? 'User',
        provider: 'google',
      );
      
      await _save(session);
      return session;
    } on FirebaseAuthException catch (e) {
      throw Exception(_getFirebaseErrorMessage(e.code));
    } catch (e) {
      throw Exception('Google sign-in failed: $e');
    }
  }

  /// Refresh the current auth token
  Future<void> refreshToken() async {
    final user = _auth.currentUser;
    if (user == null) {
      await signOut();
      return;
    }
    
    try {
      final token = await user.getIdToken(true); // Force refresh
      if (token != null && _current != null) {
        _current = MpSession(
          token: token,
          email: _current!.email,
          displayName: _current!.displayName,
          provider: _current!.provider,
        );
        await _save(_current!);
      }
    } catch (_) {
      await signOut();
    }
  }

  String _getFirebaseErrorMessage(String code) {
    switch (code) {
      case 'user-not-found':
        return 'No user found with this email';
      case 'wrong-password':
        return 'Incorrect password';
      case 'invalid-email':
        return 'Invalid email address';
      case 'user-disabled':
        return 'This account has been disabled';
      case 'too-many-requests':
        return 'Too many failed attempts. Try again later';
      case 'operation-not-allowed':
        return 'This sign-in method is not enabled';
      case 'email-already-in-use':
        return 'This email is already registered';
      case 'weak-password':
        return 'Password is too weak';
      default:
        return 'Authentication failed: $code';
    }
  }
}

final auth = AuthService();
