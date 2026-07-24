import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'app.dart';
import 'core/services/connectivity_service.dart';
import 'core/services/offline_sync_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final connectivity = ConnectivityService();
  await connectivity.initialize();

  final syncService = OfflineSyncService();
  syncService.start(connectivity.onConnectivityChanged);

  runApp(
    const ProviderScope(
      child: LiveCalcApp(),
    ),
  );
}
