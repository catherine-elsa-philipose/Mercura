import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers.dart';

class PaymentsScreen extends ConsumerStatefulWidget {
  const PaymentsScreen({super.key});

  @override
  ConsumerState<PaymentsScreen> createState() => _PaymentsScreenState();
}

class _PaymentsScreenState extends ConsumerState<PaymentsScreen> {
  void _showRecordPaymentDialog(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return const RecordPaymentDialog();
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final asyncData = ref.watch(paymentsProvider);
    final invoicesAsync = ref.watch(invoicesProvider);
    final customersAsync = ref.watch(customersProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payments'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(paymentsProvider);
              ref.invalidate(invoicesProvider);
              ref.invalidate(customersProvider);
            },
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: asyncData.when(
        data: (items) {
          if (items.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.payment_outlined, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text('No payments recorded yet.', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () => _showRecordPaymentDialog(context),
                    icon: const Icon(Icons.add),
                    label: const Text('Record Payment'),
                  ),
                ],
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            separatorBuilder: (context, index) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final payment = items[index];

              final invoiceNum = invoicesAsync.maybeWhen(
                data: (invoices) {
                  final list = invoices.where((i) => i.id == payment.invoiceId).toList();
                  return list.isNotEmpty ? list.first.invoiceNumber : 'Inv #${payment.invoiceId}';
                },
                orElse: () => 'Inv #${payment.invoiceId}',
              );

              final customerName = invoicesAsync.maybeWhen(
                data: (invoices) {
                  final list = invoices.where((i) => i.id == payment.invoiceId).toList();
                  if (list.isNotEmpty) {
                    final customerId = list.first.customerId;
                    return customersAsync.maybeWhen(
                      data: (customers) {
                        final cList = customers.where((c) => c.id == customerId).toList();
                        return cList.isNotEmpty ? cList.first.name : 'Unknown Customer';
                      },
                      orElse: () => 'Loading...',
                    );
                  }
                  return 'Unknown Customer';
                },
                orElse: () => 'Loading...',
              );

              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Colors.teal[500]!.withAlpha(25),
                  child: Icon(Icons.attach_money, color: Colors.teal[800]),
                ),
                title: Text(
                  '₹${payment.amount.toStringAsFixed(2)}',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                subtitle: Text('$invoiceNum • Customer: $customerName • Method: ${payment.paymentMethod}'),
                trailing: Chip(
                  avatar: const Icon(Icons.check_circle, size: 16, color: Colors.green),
                  label: Text(payment.status.toUpperCase()),
                ),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Error loading payments: $err')),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showRecordPaymentDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }
}

class RecordPaymentDialog extends ConsumerStatefulWidget {
  const RecordPaymentDialog({super.key});

  @override
  ConsumerState<RecordPaymentDialog> createState() => _RecordPaymentDialogState();
}

class _RecordPaymentDialogState extends ConsumerState<RecordPaymentDialog> {
  int? _selectedInvoiceId;
  String _customerName = '';
  double _outstandingAmount = 0.0;
  bool _isLoadingInvoiceDetails = false;

  final _amountController = TextEditingController();
  String _selectedMethod = 'CASH';

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final invoicesAsync = ref.watch(invoicesProvider);

    return StatefulBuilder(
      builder: (context, setDialogState) {
        return AlertDialog(
          title: const Text('Record Payment'),
          content: invoicesAsync.when(
            data: (invoices) {
              final unpaidInvoices = invoices
                  .where((i) => i.status.toLowerCase() != 'paid' && i.status.toLowerCase() != 'cancelled')
                  .toList();
              if (unpaidInvoices.isEmpty) {
                return const Text('No unpaid invoices available to record payments.');
              }
              return SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    DropdownButtonFormField<int>(
                      initialValue: _selectedInvoiceId,
                      decoration: const InputDecoration(
                        labelText: 'Select Invoice',
                        prefixIcon: Icon(Icons.receipt),
                      ),
                      items: unpaidInvoices.map((i) {
                        return DropdownMenuItem<int>(
                          value: i.id,
                          child: Text('Invoice #${i.invoiceNumber} (₹${i.totalAmount.toStringAsFixed(2)})'),
                        );
                      }).toList(),
                      onChanged: (val) async {
                        if (val == null) return;
                        final scaffoldMessenger = ScaffoldMessenger.of(context);
                        setDialogState(() {
                          _selectedInvoiceId = val;
                          _isLoadingInvoiceDetails = true;
                          _customerName = '';
                          _outstandingAmount = 0.0;
                        });

                        try {
                          final businessId = await ref.read(activeBusinessIdProvider.future);
                          final invoice = unpaidInvoices.firstWhere((i) => i.id == val);

                          final customers = ref.read(customersProvider).value ?? [];
                          final cust = customers.where((c) => c.id == invoice.customerId).toList();
                          final customerName = cust.isNotEmpty ? cust.first.name : 'Unknown Customer';

                          final invoicePayments =
                              await ref.read(paymentServiceProvider).getInvoicePayments(businessId, val);
                          final totalPaid = invoicePayments.fold(0.0, (sum, p) => sum + p.amount);
                          final outstanding = invoice.totalAmount - totalPaid;

                          setDialogState(() {
                            _customerName = customerName;
                            _outstandingAmount = outstanding < 0.0 ? 0.0 : outstanding;
                            _amountController.text = _outstandingAmount.toStringAsFixed(2);
                            _isLoadingInvoiceDetails = false;
                          });
                        } catch (e) {
                          setDialogState(() {
                            _isLoadingInvoiceDetails = false;
                          });
                          scaffoldMessenger.showSnackBar(
                            SnackBar(content: Text('Error loading invoice details: $e')),
                          );
                        }
                      },
                    ),
                    const SizedBox(height: 16),
                    if (_isLoadingInvoiceDetails)
                      const Center(
                        child: Padding(
                          padding: EdgeInsets.all(8.0),
                          child: CircularProgressIndicator(),
                        ),
                      )
                    else if (_selectedInvoiceId != null) ...[
                      Text('Customer Name: ', style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                      Text(
                        _customerName,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      const SizedBox(height: 12),
                      Text('Outstanding Balance: ', style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                      Text(
                        '₹${_outstandingAmount.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 18,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _amountController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        decoration: const InputDecoration(
                          labelText: 'Payment Amount (₹) *',
                          prefixIcon: Icon(Icons.currency_rupee),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    DropdownButtonFormField<String>(
                      initialValue: _selectedMethod,
                      decoration: const InputDecoration(labelText: 'Payment Method'),
                      items: const [
                        DropdownMenuItem(value: 'CASH', child: Text('Cash')),
                        DropdownMenuItem(value: 'CREDIT_CARD', child: Text('Credit Card')),
                        DropdownMenuItem(value: 'BANK_TRANSFER', child: Text('Bank Transfer')),
                        DropdownMenuItem(value: 'UPI', child: Text('UPI')),
                        DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                      ],
                      onChanged: (val) {
                        if (val != null) {
                          setDialogState(() {
                            _selectedMethod = val;
                          });
                        }
                      },
                    ),
                  ],
                ),
              );
            },
            loading: () => const SizedBox(height: 100, child: Center(child: CircularProgressIndicator())),
            error: (err, stack) => Text('Error loading invoices: $err'),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: _selectedInvoiceId == null || _isLoadingInvoiceDetails
                  ? null
                  : () async {
                      final scaffoldMessenger = ScaffoldMessenger.of(context);
                      final navigator = Navigator.of(context);
                      try {
                        final amount = double.tryParse(_amountController.text);
                        if (amount == null || amount <= 0) {
                          scaffoldMessenger.showSnackBar(
                            const SnackBar(content: Text('Please enter a valid amount greater than 0.')),
                          );
                          return;
                        }
                        if (amount > _outstandingAmount + 0.01) {
                          scaffoldMessenger.showSnackBar(
                            SnackBar(
                              content: Text(
                                'Payment amount exceeds outstanding balance of ₹${_outstandingAmount.toStringAsFixed(2)}.',
                              ),
                            ),
                          );
                          return;
                        }

                        final businessId = await ref.read(activeBusinessIdProvider.future);
                        await ref.read(paymentServiceProvider).createPayment(businessId, _selectedInvoiceId!, {
                          'amount': amount,
                          'payment_method': _selectedMethod,
                        });

                        ref.invalidate(paymentsProvider);
                        ref.invalidate(invoicesProvider);
                        ref.invalidate(dashboardSummaryProvider);

                        navigator.pop();
                        scaffoldMessenger.showSnackBar(
                          const SnackBar(content: Text('Payment recorded successfully.')),
                        );
                      } catch (e) {
                        scaffoldMessenger.showSnackBar(
                          SnackBar(content: Text('Error recording payment: $e')),
                        );
                      }
                    },
              child: const Text('Record'),
            ),
          ],
        );
      },
    );
  }
}
