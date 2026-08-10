import 'package:flutter/material.dart';

const seedColor = Color(0xFF6200EE);

const lightColorScheme = ColorScheme.light(
  primary: seedColor,
  onPrimary: Colors.white,
  secondary: Color(0xFF03DAC6),
  onSecondary: Colors.black,
  error: Color(0xFFB00020),
  onError: Colors.white,
  surface: Color(0xFFF6F8FA),
  onSurface: Colors.black,
);

const darkColorScheme = ColorScheme.dark(
  primary: Color(0xFFBB86FC),
  onPrimary: Colors.black,
  secondary: Color(0xFF03DAC6),
  onSecondary: Colors.black,
  error: Color(0xFFCF6679),
  onError: Colors.black,
  surface: Color(0xFF121212),
  onSurface: Colors.white,
);
