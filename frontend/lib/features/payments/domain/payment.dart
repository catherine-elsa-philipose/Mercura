class Payment {
  final int id;
  final int invoiceId;
  final double amount;
  final String paymentMethod;
  final String status;

  Payment({
    required this.id,
    required this.invoiceId,
    required this.amount,
    required this.paymentMethod,
    required this.status,
  });

  factory Payment.fromJson(Map<String, dynamic> json) {
    return Payment(
      id: json['id'],
      invoiceId: json['invoice_id'] ?? 0,
      amount: double.parse((json['amount'] ?? 0).toString()),
      paymentMethod: json['payment_method'] is String
          ? json['payment_method']
          : (json['payment_method']?['value'] ?? json['payment_method'].toString()),
      status: json['status']?.toString() ?? 'completed',
    );
  }
}
