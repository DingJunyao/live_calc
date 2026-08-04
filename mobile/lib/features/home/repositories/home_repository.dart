/// Home repository: calls backend api to fetch today's meal recommendations.
library;

import '../../../core/api/api_client.dart';
import '../models/meal_recommendation.dart';

class HomeRepository {
  final ApiClient _client;

  HomeRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<DailyRecommendation> getTodayRecommendation() async {
    final response = await _client.dio.get('/meals/recommendations');
    return DailyRecommendation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<DailyRecommendation> triggerGenerate() async {
    final response = await _client.dio.post('/meals/recommendations/generate');
    return DailyRecommendation.fromJson(response.data as Map<String, dynamic>);
  }
}
