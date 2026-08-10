import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers.dart';
import '../domain/invoice.dart';
import '../../products/domain/product.dart';

class InvoicesScreen extends ConsumerStatefulWidget {
  const InvoicesScreen({super.key});

  @override
  ConsumerState<InvoicesScreen> createState() => _InvoicesScreenState();
}

class _InvoicesScreenState extends ConsumerState<InvoicesScreen> {
  void _showAddInvoiceDialog(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return const CreateInvoiceDialog();
      },
    );
  }

  Future<void> _cancelInvoice(Invoice invoice) async {
    try {
      final businessId = await ref.read(activeBusinessIdProvider.future);
      await ref.read(invoiceServiceProvider).cancelInvoice(businessId, invoice.id);
      ref.invalidate(invoicesProvider);
      ref.invalidate(dashboardSummaryProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Invoice ${invoice.invoiceNumber} cancelled.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncData = ref.watch(invoicesProvider);
    final customersAsync = ref.watch(customersProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Invoices'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
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
                  Icon(Icons.receipt_long_outlined, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text('No invoices found.', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () => _showAddInvoiceDialog(context),
                    icon: const Icon(Icons.add),
                    label: const Text('Create Your First Invoice'),
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
              final invoice = items[index];
              final customerName = customersAsync.maybeWhen(
                data: (customers) {
                  final list = customers.where((c) => c.id == invoice.customerId).toList();
                  return list.isNotEmpty ? list.first.name : 'Unknown Customer';
                },
                orElse: () => 'Loading...',
              );

              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.tertiaryContainer,
                  child: Icon(Icons.receipt, color: Theme.of(context).colorScheme.onTertiaryContainer),
                ),
                title: Text(invoice.invoiceNumber, style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text('Customer: $customerName • Status: ${invoice.status.toUpperCase()}'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '₹${invoice.totalAmount.toStringAsFixed(2)}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    PopupMenuButton<String>(
                      onSelected: (val) {
                        if (val == 'cancel') {
                          _cancelInvoice(invoice);
                        }
                      },
                      itemBuilder: (context) => [
                        if (invoice.status.toLowerCase() != 'cancelled')
                          const PopupMenuItem(
                            value: 'cancel',
                            child: Row(
                              children: [
                                Icon(Icons.cancel_outlined, size: 20, color: Colors.red),
                                SizedBox(width: 8),
                                Text('Cancel Invoice', style: TextStyle(color: Colors.red)),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Error loading invoices: $err')),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddInvoiceDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }
}

class CreateInvoiceDialog extends ConsumerStatefulWidget {
  const CreateInvoiceDialog({super.key});

  @override
  ConsumerState<CreateInvoiceDialog> createState() => _CreateInvoiceDialogState();
}

class _CreateInvoiceDialogState extends ConsumerState<CreateInvoiceDialog> {
  int? _selectedCustomerId;
  final List<Map<String, dynamic>> _lineItems = [];
  double _taxRate = 0.0;
  double _discountAmount = 0.0;
  DateTime _invoiceDate = DateTime.now();
  DateTime _dueDate = DateTime.now().add(const Duration(days: 30));

  int? _tempProductId;
  final _quantityController = TextEditingController(text: '1');
  final _priceController = TextEditingController();
  final _taxController = TextEditingController(text: '0');
  final _discountController = TextEditingController(text: '0');
  final _notesController = TextEditingController();

  double get subtotal {
    return _lineItems.fold(0.0, (sum, item) {
      final q = item['quantity'] as int;
      final p = item['price'] as double;
      return sum + (q * p);
    });
  }

  double get taxTotal {
    return subtotal * (_taxRate / 100.0);
  }

  double get totalAmount {
    final val = subtotal + taxTotal - _discountAmount;
    return val < 0.0 ? 0.0 : val;
  }

  @override
  void dispose() {
    _quantityController.dispose();
    _priceController.dispose();
    _taxController.dispose();
    _discountController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _selectDate(BuildContext context, bool isInvoiceDate) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: isInvoiceDate ? _invoiceDate : _dueDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2101),
    );
    if (picked != null) {
      setState(() {
        if (isInvoiceDate) {
          _invoiceDate = picked;
          if (_dueDate.isBefore(_invoiceDate)) {
            _dueDate = _invoiceDate.add(const Duration(days: 30));
          }
        } else {
          _dueDate = picked;
        }
      });
    }
  }

  Widget _buildCalculationRow(String label, String value, {bool isNegative = false, bool isBold = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
            color: isNegative ? Colors.red : null,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
            color: isNegative ? Colors.red : null,
          ),
        ),
      ],
    );
  }

  Future<void> _submitInvoice() async {
    if (_selectedCustomerId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select a customer.')),
      );
      return;
    }
    if (_lineItems.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please add at least one line item.')),
      );
      return;
    }

    final scaffoldMessenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);

    try {
      final businessId = await ref.read(activeBusinessIdProvider.future);
      final itemsData = _lineItems.map((item) {
        final prod = item['product'] as Product;
        final qty = item['quantity'] as int;
        final price = item['price'] as double;
        return {
          'product_id': prod.id,
          'quantity': qty,
          'unit_price': price,
        };
      }).toList();

      final payload = {
        'customer_id': _selectedCustomerId,
        'tax': taxTotal,
        'discount': _discountAmount,
        'notes': _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
        'invoice_date': '${_invoiceDate.year}-${_invoiceDate.month.toString().padLeft(2, '0')}-${_invoiceDate.day.toString().padLeft(2, '0')}',
        'due_date': '${_dueDate.year}-${_dueDate.month.toString().padLeft(2, '0')}-${_dueDate.day.toString().padLeft(2, '0')}',
        'items': itemsData,
      };

      await ref.read(invoiceServiceProvider).createInvoice(businessId, payload);
      ref.invalidate(invoicesProvider);
      ref.invalidate(dashboardSummaryProvider);
      navigator.pop();
      scaffoldMessenger.showSnackBar(
        const SnackBar(content: Text('Invoice created successfully.')),
      );
    } catch (e) {
      scaffoldMessenger.showSnackBar(
        SnackBar(content: Text('Error creating invoice: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final customersAsync = ref.watch(customersProvider);
    final productsAsync = ref.watch(productsProvider);

    return AlertDialog(
      title: const Text('Create New Invoice'),
      content: customersAsync.when(
        data: (customers) => productsAsync.when(
          data: (products) {
            final activeCustomers = customers.where((c) => c.isActive).toList();
            final activeProducts = products.where((p) => p.isActive).toList();

            if (activeCustomers.isEmpty) {
              return const Text('Please add at least one active customer first.');
            }

            return ConstrainedBox(
              constraints: const BoxConstraints(
                maxWidth: 650,
              ),
              child: SizedBox(
                width: MediaQuery.of(context).size.width * 0.8,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      DropdownButtonFormField<int>(
                        initialValue: _selectedCustomerId,
                        decoration: const InputDecoration(
                          labelText: 'Select Customer *',
                          prefixIcon: Icon(Icons.person),
                        ),
                        items: activeCustomers.map((c) {
                          return DropdownMenuItem<int>(
                            value: c.id,
                            child: Text(c.name),
                          );
                        }).toList(),
                        onChanged: (val) {
                          setState(() {
                            _selectedCustomerId = val;
                          });
                        },
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _selectDate(context, true),
                              icon: const Icon(Icons.calendar_today),
                              label: Text(
                                'Issue Date: ${_invoiceDate.year}-${_invoiceDate.month.toString().padLeft(2, '0')}-${_invoiceDate.day.toString().padLeft(2, '0')}',
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _selectDate(context, false),
                              icon: const Icon(Icons.calendar_today),
                              label: Text(
                                'Due Date: ${_dueDate.year}-${_dueDate.month.toString().padLeft(2, '0')}-${_dueDate.day.toString().padLeft(2, '0')}',
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const Divider(),
                      Text(
                        'Line Items',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Expanded(
                            flex: 3,
                            child: DropdownButtonFormField<int>(
                              initialValue: _tempProductId,
                              decoration: const InputDecoration(
                                labelText: 'Product',
                                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              ),
                              items: activeProducts.map((p) {
                                return DropdownMenuItem<int>(
                                  value: p.id,
                                  child: Text('${p.name} (₹${p.sellingPrice.toStringAsFixed(2)})'),
                                );
                              }).toList(),
                              onChanged: (val) {
                                setState(() {
                                  _tempProductId = val;
                                  if (val != null) {
                                    final prod = activeProducts.firstWhere((p) => p.id == val);
                                    _priceController.text = prod.sellingPrice.toString();
                                  }
                                });
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            flex: 1,
                            child: TextField(
                              controller: _quantityController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Qty',
                                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            flex: 2,
                            child: TextField(
                              controller: _priceController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Price (₹)',
                                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton.filled(
                            onPressed: () {
                              if (_tempProductId == null) return;
                              final prod = activeProducts.firstWhere((p) => p.id == _tempProductId);
                              final qty = int.tryParse(_quantityController.text) ?? 1;
                              final price = double.tryParse(_priceController.text) ?? prod.sellingPrice;

                              if (qty <= 0) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(content: Text('Quantity must be greater than 0.')),
                                );
                                return;
                              }

                              setState(() {
                                final existingIndex = _lineItems.indexWhere((item) => (item['product'] as Product).id == prod.id);
                                if (existingIndex >= 0) {
                                  final currentQty = (_lineItems[existingIndex]['quantity'] as int);
                                  _lineItems[existingIndex]['quantity'] = currentQty + qty;
                                } else {
                                  _lineItems.add({
                                    'product': prod,
                                    'quantity': qty,
                                    'price': price,
                                  });
                                }
                                _tempProductId = null;
                                _quantityController.text = '1';
                                _priceController.clear();
                              });
                            },
                            icon: const Icon(Icons.add),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      if (_lineItems.isEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12.0),
                          child: Center(
                            child: Text(
                              'No items added yet.',
                              style: TextStyle(color: Colors.grey[500], fontStyle: FontStyle.italic),
                            ),
                          ),
                        )
                      else
                        Card(
                          color: Theme.of(context).colorScheme.surface.withAlpha(76),
                          child: ListView.builder(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: _lineItems.length,
                            itemBuilder: (context, index) {
                              final item = _lineItems[index];
                              final prod = item['product'] as Product;
                              final qty = item['quantity'] as int;
                              final price = item['price'] as double;
                              final total = qty * price;

                              return ListTile(
                                title: Text(prod.name),
                                subtitle: Text('$qty x ₹${price.toStringAsFixed(2)}'),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      '₹${total.toStringAsFixed(2)}',
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    IconButton(
                                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                                      onPressed: () {
                                        setState(() {
                                          _lineItems.removeAt(index);
                                        });
                                      },
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                        ),
                      const Divider(),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: _taxController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Tax Rate (%)',
                                prefixIcon: Icon(Icons.percent),
                              ),
                              onChanged: (val) {
                                setState(() {
                                  _taxRate = double.tryParse(val) ?? 0.0;
                                });
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: _discountController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Discount (₹)',
                                prefixIcon: Icon(Icons.discount),
                              ),
                              onChanged: (val) {
                                setState(() {
                                  _discountAmount = double.tryParse(val) ?? 0.0;
                                });
                              },
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _notesController,
                        decoration: const InputDecoration(
                          labelText: 'Notes / Remarks',
                          prefixIcon: Icon(Icons.note),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.primaryContainer.withAlpha(51),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Column(
                          children: [
                            _buildCalculationRow(
                              'Subtotal',
                              '₹${subtotal.toStringAsFixed(2)}',
                            ),
                            const SizedBox(height: 4),
                            _buildCalculationRow(
                              'Tax Total ($_taxRate%)',
                              '₹${taxTotal.toStringAsFixed(2)}',
                            ),
                            const SizedBox(height: 4),
                            _buildCalculationRow(
                              'Discount',
                              '-₹${_discountAmount.toStringAsFixed(2)}',
                              isNegative: true,
                            ),
                            const Divider(),
                            _buildCalculationRow(
                              'Total Amount',
                              '₹${totalAmount.toStringAsFixed(2)}',
                              isBold: true,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, stack) => Text('Error loading products: $err'),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Text('Error loading customers: $err'),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _submitInvoice,
          child: const Text('Create Invoice'),
        ),
      ],
    );
  }
}
