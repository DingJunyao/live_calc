import '../../../core/api/api_client.dart';
import '../models/meal_recommendation.dart';

class HomeRepository {
  final ApiClient _client;

  HomeRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<DailyRecommendation> getTodayRecommendation() async {
    final response = await _client.dio.get('/meals/today');
    return DailyRecommendation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<DailyRecommendation> refreshToday() async {
    final response = await _client.dio.post('/meals/today/refresh');
    return DailyRecommendation.fromJson(response.data as Map<String, dynamic>);
  }
}
