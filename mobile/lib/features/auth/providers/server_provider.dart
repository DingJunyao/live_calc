import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/api/api_client.dart';

class ServerConfigNotifier extends StateNotifier<String?> {
  ServerConfigNotifier() : super(null);
  static const _key = 'server_base_url';

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final url = prefs.getString(_key);
    if (url != null) ApiClient.instance.updateBaseUrl(url);
    state = url;
  }

  Future<void> setUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, url);
    ApiClient.instance.updateBaseUrl(url);
    state = url;
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
    state = null;
  }
}

final serverConfigProvider =
    StateNotifierProvider<ServerConfigNotifier, String?>((ref) {
  return ServerConfigNotifier();
});
