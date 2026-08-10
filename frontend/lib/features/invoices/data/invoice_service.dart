import '../../../core/network/api_client.dart';
import '../domain/invoice.dart';

class InvoiceService {
  final ApiClient _client;
  InvoiceService(this._client);

  Future<List<Invoice>> getInvoices(int businessId) async {
    final response = await _client.dio.get('/businesses/$businessId/invoices');
    final List data = response.data['items'] ?? response.data;
    return data.map((e) => Invoice.fromJson(e)).toList();
  }

  Future<Invoice> createInvoice(int businessId, Map<String, dynamic> data) async {
    final response = await _client.dio.post('/businesses/$businessId/invoices', data: data);
    return Invoice.fromJson(response.data);
  }

  Future<Invoice> cancelInvoice(int businessId, int invoiceId) async {
    final response = await _client.dio.patch('/businesses/$businessId/invoices/$invoiceId/cancel');
    return Invoice.fromJson(response.data);
  }
}
