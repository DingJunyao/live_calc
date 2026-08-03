import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/providers/auth_provider.dart';
import 'features/auth/providers/server_provider.dart';

/// Thin [ChangeNotifier] wrapper so [GoRouter.refreshListenable] can be nudged
/// from outside (notifyListeners is otherwise protected).
class _RouterRefreshNotifier extends ChangeNotifier {
  void refresh() => notifyListeners();
}

class LiveCalcApp extends ConsumerStatefulWidget {
  const LiveCalcApp({super.key});

  @override
  ConsumerState<LiveCalcApp> createState() => _LiveCalcAppState();
}

class _LiveCalcAppState extends ConsumerState<LiveCalcApp> {
  final _refreshNotifier = _RouterRefreshNotifier();
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    // Create the router exactly once; auth/server changes are wired through
    // refreshListenable so the redirect re-evaluates without rebuilding the
    // whole router each frame.
    _router = createAppRouter(ref, _refreshNotifier);
    _bootstrap();
  }

  @override
  void dispose() {
    _refreshNotifier.dispose();
    super.dispose();
  }

  Future<void> _bootstrap() async {
    // Restore the server address first (the auth check needs the base URL),
    // then restore the session / auto-login from saved credentials.
    await ref.read(serverConfigProvider.notifier).load();
    await ref.read(authProvider.notifier).checkAuth();
  }

  @override
  Widget build(BuildContext context) {
    // Whenever auth or server state changes, nudge the router so its redirect
    // runs again with the fresh values.
    ref.listen(authProvider, (_, __) => _refreshNotifier.refresh());
    ref.listen(serverConfigProvider, (_, __) => _refreshNotifier.refresh());
    return MaterialApp.router(
      title: '生计 - 生活成本计算器',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}
