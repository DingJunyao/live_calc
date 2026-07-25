import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/providers/auth_provider.dart';

class LiveCalcApp extends ConsumerWidget {
  const LiveCalcApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Check auth on first build
    ref.read(authProvider.notifier).checkAuth();

    final router = createAppRouter(ref);
    return MaterialApp.router(
      title: '生计 - 生活成本计算器',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
