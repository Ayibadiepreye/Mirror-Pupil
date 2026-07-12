import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../auth/auth_service.dart';
import '../theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  bool _signup = false;

  Future<void> _go(Future<dynamic> Function() fn, String provider) async {
    setState(() => _busy = true);
    try {
      await fn();
      if (mounted) context.go('/');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$provider sign-in failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.6),
            radius: 1.2,
            colors: [Color(0x33B22222), MpColors.app],
            stops: [0, 0.8],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(children: [
                  // Logo with gradient and shadow
                  Container(
                    width: 56, height: 56,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(14),
                      gradient: const LinearGradient(
                        colors: [MpColors.crimson, MpColors.red],
                        begin: Alignment.topLeft, end: Alignment.bottomRight,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: MpColors.crimson.withValues(alpha: 0.4),
                          blurRadius: 16,
                          spreadRadius: 2,
                        ),
                      ],
                    ),
                    child: const Icon(Icons.shield_outlined, color: Colors.white, size: 28),
                  ),
                  const SizedBox(height: 14),
                  const Text('Mirror Pupil', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600)),
                  const Text('KNIGHTS OF THE BLOOD OATH',
                      style: TextStyle(fontSize: 10, letterSpacing: 3, color: MpColors.textDim)),
                  const SizedBox(height: 24),
                  // Card with backdrop blur effect
                  Container(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: MpColors.border),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.4),
                          blurRadius: 24,
                          spreadRadius: 4,
                        ),
                      ],
                    ),
                    child: Card(
                      margin: EdgeInsets.zero,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      child: Padding(
                        padding: const EdgeInsets.all(18),
                        child: Column(children: [
                          // Segmented button with gradient
                          Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.05),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Row(children: [
                              Expanded(child: _ModeButton(
                                label: 'Sign in',
                                selected: !_signup,
                                onTap: () => setState(() => _signup = false),
                              )),
                              Expanded(child: _ModeButton(
                                label: 'Sign up',
                                selected: _signup,
                                onTap: () => setState(() => _signup = true),
                              )),
                            ]),
                          ),
                          const SizedBox(height: 14),
                          // Google button with official logo
                          SizedBox(
                            width: double.infinity, height: 46,
                            child: ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.white,
                                foregroundColor: Colors.black87,
                                elevation: 0,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(8),
                                ),
                              ),
                              onPressed: _busy ? null : () => _go(auth.signInWithGoogle, 'Google'),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  _GoogleLogo(),
                                  const SizedBox(width: 10),
                                  const Text('Continue with Google',
                                    style: TextStyle(fontWeight: FontWeight.w500)),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          const Row(children: [
                            Expanded(child: Divider()),
                            Padding(
                              padding: EdgeInsets.symmetric(horizontal: 10),
                              child: Text('OR', style: TextStyle(fontSize: 10, color: MpColors.textDim))),
                            Expanded(child: Divider()),
                          ]),
                          const SizedBox(height: 8),
                          TextField(
                            controller: _email,
                            keyboardType: TextInputType.emailAddress,
                            decoration: const InputDecoration(labelText: 'Email'),
                          ),
                          const SizedBox(height: 10),
                          TextField(
                            controller: _password,
                            obscureText: true,
                            decoration: const InputDecoration(labelText: 'Password'),
                          ),
                          const SizedBox(height: 14),
                          // Submit button with gradient
                          SizedBox(
                            width: double.infinity, height: 46,
                            child: Container(
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [MpColors.crimson, MpColors.red],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.transparent,
                                  shadowColor: Colors.transparent,
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                ),
                                onPressed: _busy ? null : () =>
                                    _go(() => auth.signInWithPassword(_email.text.trim(), _password.text), 'Email'),
                                child: Text(_signup ? 'Create account' : 'Sign in',
                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          const Text(
                            'By continuing you agree to your firm\'s trading policy and risk profile.',
                            style: TextStyle(fontSize: 11, color: MpColors.textDim),
                            textAlign: TextAlign.center,
                          ),
                        ]),
                      ),
                    ),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ModeButton extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _ModeButton({required this.label, required this.selected, required this.onTap});
  
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          gradient: selected 
            ? const LinearGradient(
                colors: [MpColors.crimson, MpColors.red],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: selected ? Colors.white : MpColors.textDim,
          ),
        ),
      ),
    );
  }
}

class _GoogleLogo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 18,
      height: 18,
      child: CustomPaint(
        painter: _GoogleLogoPainter(),
      ),
    );
  }
}

class _GoogleLogoPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    
    // Blue
    paint.color = const Color(0xFF4285F4);
    canvas.drawPath(
      Path()
        ..moveTo(17.64, 9.2)
        ..cubicTo(17.64, 8.56, 17.58, 7.95, 17.47, 7.36)
        ..lineTo(9, 7.36)
        ..lineTo(9, 10.85)
        ..lineTo(13.84, 10.85)
        ..cubicTo(13.64, 11.87, 13.04, 12.74, 12.04, 13.27)
        ..lineTo(12.04, 15.53)
        ..lineTo(14.95, 15.53)
        ..cubicTo(16.65, 13.96, 17.64, 11.65, 17.64, 9.2)
        ..close(),
      paint,
    );
    
    // Green
    paint.color = const Color(0xFF34A853);
    canvas.drawPath(
      Path()
        ..moveTo(9, 18)
        ..cubicTo(11.43, 18, 13.47, 17.2, 14.96, 15.82)
        ..lineTo(12.05, 13.56)
        ..cubicTo(11.24, 14.1, 10.21, 14.42, 9, 14.42)
        ..cubicTo(6.66, 14.42, 4.68, 12.84, 3.97, 10.72)
        ..lineTo(0.96, 10.72)
        ..lineTo(0.96, 13.05)
        ..cubicTo(2.44, 15.98, 5.48, 18, 9, 18)
        ..close(),
      paint,
    );
    
    // Yellow
    paint.color = const Color(0xFFFBBC05);
    canvas.drawPath(
      Path()
        ..moveTo(3.97, 10.72)
        ..cubicTo(3.78, 10.18, 3.68, 9.6, 3.68, 9)
        ..cubicTo(3.68, 8.4, 3.78, 7.82, 3.97, 7.28)
        ..lineTo(3.97, 4.95)
        ..lineTo(0.96, 4.95)
        ..cubicTo(0.35, 6.17, 0, 7.54, 0, 9)
        ..cubicTo(0, 10.46, 0.35, 11.83, 0.96, 13.05)
        ..lineTo(3.97, 10.72)
        ..close(),
      paint,
    );
    
    // Red
    paint.color = const Color(0xFFEA4335);
    canvas.drawPath(
      Path()
        ..moveTo(9, 3.58)
        ..cubicTo(10.32, 3.58, 11.5, 4.03, 12.44, 4.93)
        ..lineTo(15.02, 2.35)
        ..cubicTo(13.46, 0.89, 11.43, 0, 9, 0)
        ..cubicTo(5.48, 0, 2.44, 2.02, 0.96, 4.95)
        ..lineTo(3.97, 7.28)
        ..cubicTo(4.68, 5.16, 6.66, 3.58, 9, 3.58)
        ..close(),
      paint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
