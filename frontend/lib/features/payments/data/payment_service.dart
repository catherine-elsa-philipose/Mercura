import '../../../core/network/api_client.dart';
import '../domain/payment.dart';

class PaymentService {
  final ApiClient _client;
  PaymentService(this._client);

  Future<List<Payment>> getPayments(int businessId) async {
    final response = await _client.dio.get('/businesses/$businessId/payments');
    final List data = response.data['items'] ?? response.data;
    return data.map((e) => Payment.fromJson(e)).toList();
  }

  Future<Payment> createPayment(int businessId, int invoiceId, Map<String, dynamic> data) async {
    final response = await _client.dio.post('/businesses/$businessId/invoices/$invoiceId/payments', data: data);
    return Payment.fromJson(response.data);
  }

  Future<List<Payment>> getInvoicePayments(int businessId, int invoiceId) async {
    final response = await _client.dio.get('/businesses/$businessId/invoices/$invoiceId/payments');
    final List data = response.data is List ? response.data : (response.data['items'] ?? response.data);
    return data.map((e) => Payment.fromJson(e)).toList();
  }
}
