class Product {
  final int id;
  final String name;
  final String sku;
  final double costPrice;
  final double sellingPrice;
  final int currentStock;
  final String? category;
  final bool isActive;

  Product({
    required this.id,
    required this.name,
    required this.sku,
    required this.costPrice,
    required this.sellingPrice,
    required this.currentStock,
    this.category,
    required this.isActive,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'],
      name: json['name'],
      sku: json['sku'],
      costPrice: double.parse(json['cost_price'].toString()),
      sellingPrice: double.parse(json['selling_price'].toString()),
      currentStock: json['current_stock'],
      category: json['category'],
      isActive: json['is_active'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'sku': sku,
      'cost_price': costPrice,
      'selling_price': sellingPrice,
      'current_stock': currentStock,
      'category': category,
      'is_active': isActive,
    };
  }
}
