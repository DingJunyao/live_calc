import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';
import 'features/auth/providers/auth_provider.dart';
import 'features/auth/repositories/auth_repository.dart';
import 'core/services/connectivity_service.dart';
import 'core/services/offline_sync_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final connectivity = ConnectivityService();
  await connectivity.initialize();

  final syncService = OfflineSyncService();
  syncService.start(connectivity.onConnectivityChanged);

    // Check if user is already logged in
  final authNotifier = AuthNotifier(AuthRepository());
  await authNotifier.checkAuth();

  runApp(
    const ProviderScope(
      child: LiveCalcApp(),
    ),
  );
}


