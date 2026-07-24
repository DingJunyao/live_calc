import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';

class LiveCalcApp extends ConsumerWidget {
  const LiveCalcApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: '生记',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      home: const Scaffold(
        body: Center(child: Text('生记 - 初始化中...')),
      ),
    );
  }
}
