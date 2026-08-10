import '../../../core/network/api_client.dart';
import '../domain/dashboard_summary.dart';

class DashboardService {
  final ApiClient _client;
  DashboardService(this._client);

  Future<DashboardSummary> getSummary(int businessId) async {
    final response = await _client.dio.get('/businesses/$businessId/dashboard/summary');
    return DashboardSummary.fromJson(response.data);
  }
}
