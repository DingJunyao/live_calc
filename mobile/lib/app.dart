import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/providers/auth_provider.dart';

class LiveCalcApp extends ConsumerStatefulWidget {
  const LiveCalcApp({super.key});

  @override
  ConsumerState<LiveCalcApp> createState() => _LiveCalcAppState();
}

class _LiveCalcAppState extends ConsumerState<LiveCalcApp> {

  @override
  void initState() {
    super.initState();
    _initAuth();
  }

  Future<void> _initAuth() async {
    await ref.read(authProvider.notifier).checkAuth();

  }

  @override
  Widget build(BuildContext context) {
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

