import 'package:flutter/material.dart';

class AppTheme {
  static const Color _primaryColor = Color(0xFF558B2F);
  static const Color _secondaryColor = Color(0xFF547C8C);
 static const Color _errorColor = Color(0xFFBA1A1A);

  /// 中文字体回退链：按平台优先级，确保 CJK 字形使用设备原生高质量字体，
  /// 而非 Flutter 默认 Roboto 的位图兜底。Latin 仍用默认 Roboto。
  static const _cjkFontFallback = [
    'Noto Sans CJK SC',   // Android / Linux
    'Source Han Sans SC', // 别名
    'Source Han Sans CN',
    'PingFang SC',        // iOS / macOS
    'Microsoft YaHei',    // Windows
    '微软雅黑',
    'sans-serif',
  ];

 static ThemeData get lightTheme {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: _primaryColor,
      secondary: _secondaryColor,
      error: _errorColor,
      brightness: Brightness.light,
    );
    return _buildTheme(colorScheme);
  }

  static ThemeData get darkTheme {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: _primaryColor,
      secondary: _secondaryColor,
      error: _errorColor,
      brightness: Brightness.dark,
    );
    return _buildTheme(colorScheme);
  }

 static ThemeData _buildTheme(ColorScheme colorScheme) {
   final base = ThemeData(
     useMaterial3: true,
      colorScheme: colorScheme,
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: colorScheme.surface,
        foregroundColor: colorScheme.onSurface,
      ),
      navigationBarTheme: NavigationBarThemeData(
        elevation: 0,
        backgroundColor: colorScheme.surface,
        indicatorColor: colorScheme.primaryContainer,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
       border: OutlineInputBorder(
         borderRadius: BorderRadius.circular(12),
       ),
     ),
   );
   // 全局应用中文字体回退，保证中文渲染清晰、行高一致
   return base.copyWith(
     textTheme: base.textTheme.apply(fontFamilyFallback: _cjkFontFallback),
     primaryTextTheme:
         base.primaryTextTheme.apply(fontFamilyFallback: _cjkFontFallback),
   );
 }
}

