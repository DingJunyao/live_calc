import '../../../core/api/api_client.dart';
import '../models/proposal.dart';
import '../models/user_place.dart';

class ProfileRepository {
  final ApiClient _client;
  ProfileRepository({ApiClient? client}) : _client = client ?? ApiClient.instance;

  Future<List<Proposal>> getProposals({int page = 1, int pageSize = 50}) async {
    final response = await _client.dio.get('/proposals', queryParameters: {'page': page, 'page_size': pageSize});
    final list = response.data as List<dynamic>;
    return list.map((e) => Proposal.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<UserPlace>> getPlaces() async {
    final response = await _client.dio.get('/places');
    final list = response.data as List<dynamic>;
    return list.map((e) => UserPlace.fromJson(e as Map<String, dynamic>)).toList();
  }
}
