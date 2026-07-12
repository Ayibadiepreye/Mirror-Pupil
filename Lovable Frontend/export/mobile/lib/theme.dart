// Mirror Pupil — Knights of the Blood Oath theme for Flutter.
import 'package:flutter/material.dart';

class MpColors {
  static const base = Color(0xFF16161A);
  static const app = Color(0xFF1E1E24);
  static const crimson = Color(0xFFB22222);
  static const red = Color(0xFFE74C3C);
  static const primary = Color(0xFFE74C3C); // Alias for red
  static const text = Color(0xFFE0E0E0);
  static const textDim = Color(0xFFA0A0A0);
  static const border = Color(0xFF2A2A30);
  static const success = Color(0xFF10B981);
  static const danger = Color(0xFFEF4444);
  static const warning = Color(0xFFF59E0B);
  static const info = Color(0xFF3B82F6);
}

ThemeData mpTheme() {
  const scheme = ColorScheme.dark(
    primary: MpColors.red,
    secondary: MpColors.crimson,
    surface: MpColors.base,
    error: MpColors.danger,
    onPrimary: Colors.white,
    onSecondary: Colors.white,
    onSurface: MpColors.text,
    onError: Colors.white,
  );

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: scheme,
    scaffoldBackgroundColor: MpColors.app,
    fontFamily: 'Inter',
    appBarTheme: const AppBarTheme(
      backgroundColor: MpColors.base,
      foregroundColor: MpColors.text,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: MpColors.base,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: MpColors.border),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: MpColors.app,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: MpColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: MpColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: MpColors.red),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: MpColors.red,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    ),
    dividerTheme: const DividerThemeData(color: MpColors.border),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: MpColors.base,
      selectedItemColor: MpColors.red,
      unselectedItemColor: MpColors.textDim,
      type: BottomNavigationBarType.fixed,
    ),
  );
}

const TextStyle kMono = TextStyle(fontFamily: 'JetBrainsMono', fontFeatures: [FontFeature.tabularFigures()]);