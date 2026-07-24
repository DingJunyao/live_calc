import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import 'tables.dart';

part 'app_database.g.dart';

@DriftDatabase(tables: [OfflineQueue])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 1;

  Future<int> enqueue(OfflineQueueCompanion entry) {
    return into(offlineQueue).insert(entry);
  }

  Future<List<OfflineQueueData>> getPendingItems() {
    return (select(offlineQueue)..where((t) => t.synced.equals(false))).get();
  }

  Future<void> markSynced(int id) {
    return (update(offlineQueue)..where((t) => t.id.equals(id))).write(
      const OfflineQueueCompanion(synced: Value(true)),
    );
  }

  Future<void> deleteSynced() {
    return (delete(offlineQueue)..where((t) => t.synced.equals(true))).go();
  }
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'livecalc.db'));
    return NativeDatabase(file);
  });
}
