class Invoice {
  final int id;
  final String invoiceNumber;
  final int customerId;
  final double subtotal;
  final double taxTotal;
  final double totalAmount;
  final String status;
  final String? issueDate;

  Invoice({
    required this.id,
    required this.invoiceNumber,
    required this.customerId,
    required this.subtotal,
    required this.taxTotal,
    required this.totalAmount,
    required this.status,
    this.issueDate,
  });

  factory Invoice.fromJson(Map<String, dynamic> json) {
    return Invoice(
      id: json['id'],
      invoiceNumber: json['invoice_number'] ?? '',
      customerId: json['customer_id'] ?? 0,
      subtotal: double.parse((json['subtotal'] ?? 0).toString()),
      taxTotal: double.parse((json['tax'] ?? json['tax_total'] ?? 0).toString()),
      totalAmount: double.parse((json['total'] ?? json['total_amount'] ?? 0).toString()),
      status: (json['status'] is String) ? json['status'] : (json['status']?['value'] ?? json['status'].toString()),
      issueDate: json['invoice_date']?.toString() ?? json['issue_date']?.toString(),
    );
  }
}
