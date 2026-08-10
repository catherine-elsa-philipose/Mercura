import '../../../core/network/api_client.dart';
import '../domain/customer.dart';

class CustomerService {
  final ApiClient _client;
  CustomerService(this._client);

  Future<List<Customer>> getCustomers(int businessId) async {
    final response = await _client.dio.get('/businesses/$businessId/customers');
    final List data = response.data['items'] ?? response.data;
    return data.map((e) => Customer.fromJson(e)).toList();
  }

  Future<Customer> createCustomer(int businessId, Map<String, dynamic> data) async {
    final response = await _client.dio.post('/businesses/$businessId/customers', data: data);
    return Customer.fromJson(response.data);
  }

  Future<Customer> updateCustomer(int businessId, int customerId, Map<String, dynamic> data) async {
    final response = await _client.dio.patch('/businesses/$businessId/customers/$customerId', data: data);
    return Customer.fromJson(response.data);
  }

  Future<Customer> deactivateCustomer(int businessId, int customerId) async {
    final response = await _client.dio.patch('/businesses/$businessId/customers/$customerId/deactivate');
    return Customer.fromJson(response.data);
  }

  Future<Customer> reactivateCustomer(int businessId, int customerId) async {
    final response = await _client.dio.patch('/businesses/$businessId/customers/$customerId/reactivate');
    return Customer.fromJson(response.data);
  }
}
