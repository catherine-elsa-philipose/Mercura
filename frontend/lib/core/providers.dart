import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'network/api_client.dart';
import 'storage/local_storage.dart';
import '../features/auth/data/auth_service.dart';
import 'routing/router.dart';
import 'network/interceptors.dart';

import '../features/customers/data/customer_service.dart';
import '../features/customers/domain/customer.dart';
import '../features/products/data/product_service.dart';
import '../features/products/domain/product.dart';
import '../features/invoices/data/invoice_service.dart';
import '../features/invoices/domain/invoice.dart';
import '../features/payments/data/payment_service.dart';
import '../features/payments/domain/payment.dart';
import '../features/dashboard/data/dashboard_service.dart';
import '../features/dashboard/domain/dashboard_summary.dart';

final tokenStorageProvider = Provider((ref) => TokenStorage());

final dioProvider = Provider((ref) {
  final dio = Dio();
  return dio;
});

final apiClientProvider = Provider((ref) {
  final dio = ref.watch(dioProvider);
  final client = ApiClient(dio);

  final tokenStorage = ref.watch(tokenStorageProvider);
  final router = ref.watch(routerProvider);

  client.addInterceptor(AuthInterceptor(tokenStorage, router));

  return client;
});

final authServiceProvider = Provider((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final tokenStorage = ref.watch(tokenStorageProvider);
  return AuthService(apiClient, tokenStorage);
});

// Active Business Providers
final activeBusinessProvider = FutureProvider<Map<String, dynamic>?>((ref) async {
  final apiClient = ref.watch(apiClientProvider);
  try {
    final response = await apiClient.dio.get('/businesses');
    if (response.data is List && (response.data as List).isNotEmpty) {
      return Map<String, dynamic>.from(response.data[0]);
    }
  } catch (_) {
    // Fail silently in production
  }
  return null;
});

final activeBusinessIdProvider = FutureProvider<int>((ref) async {
  final activeBiz = await ref.watch(activeBusinessProvider.future);
  if (activeBiz != null) {
    final id = activeBiz['id'];
    if (id is int) return id;
    if (id != null) return int.parse(id.toString());
  }
  return 1;
});

final activeBusinessNameProvider = FutureProvider<String>((ref) async {
  final activeBiz = await ref.watch(activeBusinessProvider.future);
  if (activeBiz != null && activeBiz['name'] != null) {
    return activeBiz['name'].toString();
  }
  return "My Business";
});

// Services
final customerServiceProvider = Provider((ref) => CustomerService(ref.watch(apiClientProvider)));
final productServiceProvider = Provider((ref) => ProductService(ref.watch(apiClientProvider)));
final invoiceServiceProvider = Provider((ref) => InvoiceService(ref.watch(apiClientProvider)));
final paymentServiceProvider = Provider((ref) => PaymentService(ref.watch(apiClientProvider)));
final dashboardServiceProvider = Provider((ref) => DashboardService(ref.watch(apiClientProvider)));

// State Providers (Async)
final customersProvider = FutureProvider<List<Customer>>((ref) async {
  final businessId = await ref.watch(activeBusinessIdProvider.future);
  return ref.watch(customerServiceProvider).getCustomers(businessId);
});

final productsProvider = FutureProvider<List<Product>>((ref) async {
  final businessId = await ref.watch(activeBusinessIdProvider.future);
  return ref.watch(productServiceProvider).getProducts(businessId);
});

final invoicesProvider = FutureProvider<List<Invoice>>((ref) async {
  final businessId = await ref.watch(activeBusinessIdProvider.future);
  return ref.watch(invoiceServiceProvider).getInvoices(businessId);
});

final paymentsProvider = FutureProvider<List<Payment>>((ref) async {
  final businessId = await ref.watch(activeBusinessIdProvider.future);
  return ref.watch(paymentServiceProvider).getPayments(businessId);
});

final dashboardSummaryProvider = FutureProvider<DashboardSummary>((ref) async {
  final businessId = await ref.watch(activeBusinessIdProvider.future);
  return ref.watch(dashboardServiceProvider).getSummary(businessId);
});
