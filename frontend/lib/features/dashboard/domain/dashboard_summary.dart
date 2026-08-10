
class DashboardSummary {
  final int totalCustomers;
  final int totalProducts;
  final int lowStockProducts;
  final int totalInvoices;
  final double monthlyRevenue;
  final double outstandingBalance;

  DashboardSummary({
    required this.totalCustomers,
    required this.totalProducts,
    required this.lowStockProducts,
    required this.totalInvoices,
    required this.monthlyRevenue,
    required this.outstandingBalance,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      totalCustomers: json['total_customers'] ?? 0,
      totalProducts: json['total_products'] ?? 0,
      lowStockProducts: json['low_stock_products'] ?? 0,
      totalInvoices: json['total_invoices'] ?? 0,
      monthlyRevenue: double.parse((json['monthly_revenue'] ?? 0).toString()),
      outstandingBalance: double.parse((json['outstanding_balance'] ?? 0).toString()),
    );
  }
}
