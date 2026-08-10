import '../../../core/network/api_client.dart';
import '../domain/product.dart';

class ProductService {
  final ApiClient _client;
  ProductService(this._client);

  Future<List<Product>> getProducts(int businessId) async {
    final response = await _client.dio.get('/businesses/$businessId/products');
    final List data = response.data['items'] ?? response.data;
    return data.map((e) => Product.fromJson(e)).toList();
  }

  Future<Product> createProduct(int businessId, Map<String, dynamic> data) async {
    final response = await _client.dio.post('/businesses/$businessId/products', data: data);
    return Product.fromJson(response.data);
  }

  Future<Product> updateProduct(int businessId, int productId, Map<String, dynamic> data) async {
    final response = await _client.dio.patch('/businesses/$businessId/products/$productId', data: data);
    return Product.fromJson(response.data);
  }

  Future<Product> deactivateProduct(int businessId, int productId) async {
    final response = await _client.dio.patch('/businesses/$businessId/products/$productId/deactivate');
    return Product.fromJson(response.data);
  }

  Future<Product> reactivateProduct(int businessId, int productId) async {
    final response = await _client.dio.patch('/businesses/$businessId/products/$productId/reactivate');
    return Product.fromJson(response.data);
  }

  Future<void> adjustStock(int businessId, int productId, int quantity, String reason) async {
    final String type = quantity >= 0 ? "IN" : "OUT";
    await _client.dio.post('/businesses/$businessId/products/$productId/stock', data: {
      'adjustment_type': type,
      'quantity': quantity,
      'reason': reason,
    });
  }
}
