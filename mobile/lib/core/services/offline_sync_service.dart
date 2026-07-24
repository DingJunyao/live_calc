import 'dart:async';
import 'package:dio/dio.dart';
import '../api/api_client.dart';
import '../database/app_database.dart';

class OfflineSyncService {
  final AppDatabase _db;
  final Dio _dio;
  StreamSubscription<bool>? _subscription;

  OfflineSyncService({AppDatabase? db, Dio? dio})
      : _db = db ?? AppDatabase(),
        _dio = dio ?? ApiClient.instance.dio;

  void start(Stream<bool> connectivityStream) {
    _subscription = connectivityStream.listen((online) {
      if (online) sync();
    });
    sync();
  }

  Future<void> sync() async {
    final pending = await _db.getPendingItems();
    for (final item in pending) {
      try {
        if (item.method == 'POST') {
          await _dio.post(item.endpoint, data: item.payload);
        } else if (item.method == 'PUT') {
          await _dio.put(item.endpoint, data: item.payload);
        } else if (item.method == 'DELETE') {
          await _dio.delete(item.endpoint);
        }
        await _db.markSynced(item.id);
      } catch (_) {
        // Will retry on next connectivity change
      }
    }
    await _db.deleteSynced();
  }

  Future<void> enqueue(String endpoint, String method, String payload) async {
    await _db.enqueue(OfflineQueueCompanion(
      endpoint: Value(endpoint),
      method: Value(method),
      payload: Value(payload),
      createdAt: Value(DateTime.now()),
    ));
  }

  void stop() {
    _subscription?.cancel();
  }
}
