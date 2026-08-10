
class Customer {
  final int id;
  final int businessId;
  final String name;
  final String? phone;
  final String? email;
  final bool isActive;

  Customer({
    required this.id,
    required this.businessId,
    required this.name,
    this.phone,
    this.email,
    required this.isActive,
  });

  factory Customer.fromJson(Map<String, dynamic> json) {
    return Customer(
      id: json['id'],
      businessId: json['business_id'],
      name: json['name'],
      phone: json['phone'],
      email: json['email'],
      isActive: json['is_active'],
    );
  }
}
