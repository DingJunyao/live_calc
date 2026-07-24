import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
 import 'core/router/app_router.dart';
 import 'core/theme/app_theme.dart';

class LiveCalcApp extends ConsumerWidget {
  const LiveCalcApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
     final router = createAppRouter(ref);
     return MaterialApp.router(
       title: '生记',
       theme: AppTheme.lightTheme,
       darkTheme: AppTheme.darkTheme,
       routerConfig: router,
       debugShowCheckedModeBanner: false,
     );
  }
}
