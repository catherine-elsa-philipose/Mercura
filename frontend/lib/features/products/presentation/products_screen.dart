import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers.dart';
import '../domain/product.dart';

class ProductsScreen extends ConsumerStatefulWidget {
  const ProductsScreen({super.key});

  @override
  ConsumerState<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends ConsumerState<ProductsScreen> {
  void _showAddOrEditProductDialog(BuildContext context, {Product? product}) {
    final nameController = TextEditingController(text: product?.name ?? '');
    final skuController = TextEditingController(text: product?.sku ?? '');
    final costPriceController = TextEditingController(text: product?.costPrice.toString() ?? '');
    final sellingPriceController = TextEditingController(text: product?.sellingPrice.toString() ?? '');
    final stockController = TextEditingController(text: product?.currentStock.toString() ?? '');
    final categoryController = TextEditingController(text: product?.category ?? '');

    showDialog(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(product == null ? 'Add Product' : 'Edit Product'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: 'Product Name', prefixIcon: Icon(Icons.shopping_bag)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: skuController,
                  decoration: const InputDecoration(labelText: 'SKU', prefixIcon: Icon(Icons.qr_code)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: categoryController,
                  decoration: const InputDecoration(labelText: 'Category', prefixIcon: Icon(Icons.category)),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: costPriceController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Cost Price'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: sellingPriceController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Selling Price'),
                      ),
                    ),
                  ],
                ),
                if (product == null) ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: stockController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Initial Stock', prefixIcon: Icon(Icons.warehouse)),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                try {
                  final businessId = await ref.read(activeBusinessIdProvider.future);
                  final data = {
                    'name': nameController.text.trim(),
                    'sku': skuController.text.trim().isEmpty ? 'SKU-${DateTime.now().millisecondsSinceEpoch}' : skuController.text.trim(),
                    'cost_price': double.tryParse(costPriceController.text) ?? 0.0,
                    'selling_price': double.tryParse(sellingPriceController.text) ?? 0.0,
                    if (product == null) 'current_stock': int.tryParse(stockController.text) ?? 0,
                    'category': categoryController.text.trim().isEmpty ? null : categoryController.text.trim(),
                  };
                  if (product == null) {
                    await ref.read(productServiceProvider).createProduct(businessId, data);
                  } else {
                    await ref.read(productServiceProvider).updateProduct(businessId, product.id, data);
                  }
                  ref.invalidate(productsProvider);
                  ref.invalidate(dashboardSummaryProvider);
                  if (dialogContext.mounted) Navigator.pop(dialogContext);
                } catch (e) {
                  if (dialogContext.mounted) {
                    ScaffoldMessenger.of(dialogContext).showSnackBar(SnackBar(content: Text('Error: $e')));
                  }
                }
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
  }

  void _showAdjustStockDialog(BuildContext context, Product product) {
    final qtyController = TextEditingController();
    final reasonController = TextEditingController(text: 'Manual adjustment');

    showDialog(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text('Adjust Stock: ${product.name}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Current Stock: ${product.currentStock} units'),
              const SizedBox(height: 12),
              TextField(
                controller: qtyController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Quantity Change (+/-)', hintText: 'e.g. 10 or -5'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonController,
                decoration: const InputDecoration(labelText: 'Reason'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                try {
                  final qty = int.tryParse(qtyController.text);
                  if (qty == null) {
                    if (dialogContext.mounted) {
                      ScaffoldMessenger.of(dialogContext).showSnackBar(const SnackBar(content: Text('Enter a valid numeric quantity')));
                    }
                    return;
                  }
                  final businessId = await ref.read(activeBusinessIdProvider.future);
                  await ref.read(productServiceProvider).adjustStock(businessId, product.id, qty, reasonController.text.trim());
                  ref.invalidate(productsProvider);
                  ref.invalidate(dashboardSummaryProvider);
                  if (dialogContext.mounted) Navigator.pop(dialogContext);
                } catch (e) {
                  if (dialogContext.mounted) {
                    ScaffoldMessenger.of(dialogContext).showSnackBar(SnackBar(content: Text('Error: $e')));
                  }
                }
              },
              child: const Text('Adjust'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _deactivateProduct(Product product) async {
    try {
      final businessId = await ref.read(activeBusinessIdProvider.future);
      await ref.read(productServiceProvider).deactivateProduct(businessId, product.id);
      ref.invalidate(productsProvider);
      ref.invalidate(dashboardSummaryProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${product.name} deactivated.')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<void> _reactivateProduct(Product product) async {
    try {
      final businessId = await ref.read(activeBusinessIdProvider.future);
      await ref.read(productServiceProvider).reactivateProduct(businessId, product.id);
      ref.invalidate(productsProvider);
      ref.invalidate(dashboardSummaryProvider);
      ref.invalidate(activeBusinessProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${product.name} reactivated.')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncData = ref.watch(productsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Products & Inventory'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(productsProvider),
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
                  Icon(Icons.inventory_2_outlined, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text('No products found.', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () => _showAddOrEditProductDialog(context),
                    icon: const Icon(Icons.add),
                    label: const Text('Add Your First Product'),
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
              final product = items[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.secondaryContainer,
                  child: Icon(Icons.inventory_2, color: Theme.of(context).colorScheme.onSecondaryContainer),
                ),
                title: Text(product.name, style: TextStyle(fontWeight: FontWeight.w600, color: product.isActive ? null : Colors.grey)),
                subtitle: Text('SKU: ${product.sku} | Stock: ${product.currentStock} units'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Chip(
                      avatar: Icon(
                        product.isActive ? Icons.check_circle : Icons.cancel,
                        size: 16,
                        color: product.isActive ? Colors.green : Colors.red,
                      ),
                      label: Text(product.isActive ? 'Active' : 'Inactive'),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '₹${product.sellingPrice.toStringAsFixed(2)}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: Colors.teal[700]),
                    ),
                    PopupMenuButton<String>(
                      onSelected: (val) {
                        if (val == 'edit' || val == 'view') {
                          _showAddOrEditProductDialog(context, product: product);
                        } else if (val == 'adjust') {
                          _showAdjustStockDialog(context, product);
                        } else if (val == 'deactivate') {
                          _deactivateProduct(product);
                        } else if (val == 'reactivate') {
                          _reactivateProduct(product);
                        }
                      },
                      itemBuilder: (context) => [
                        if (product.isActive)
                          const PopupMenuItem(value: 'edit', child: Row(children: [Icon(Icons.edit, size: 20), SizedBox(width: 8), Text('Edit')])),
                        if (product.isActive)
                          const PopupMenuItem(value: 'adjust', child: Row(children: [Icon(Icons.tune, size: 20), SizedBox(width: 8), Text('Adjust Stock')])),
                        if (product.isActive)
                          const PopupMenuItem(value: 'deactivate', child: Row(children: [Icon(Icons.block, size: 20, color: Colors.red), SizedBox(width: 8), Text('Deactivate', style: TextStyle(color: Colors.red))])),
                        if (!product.isActive)
                          const PopupMenuItem(value: 'reactivate', child: Row(children: [Icon(Icons.check_circle_outline, size: 20, color: Colors.green), SizedBox(width: 8), Text('Reactivate', style: TextStyle(color: Colors.green))])),
                        if (!product.isActive)
                          const PopupMenuItem(value: 'view', child: Row(children: [Icon(Icons.visibility, size: 20), SizedBox(width: 8), Text('View')])),
                      ],
                    ),
                  ],
                ),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Error loading products: $err')),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddOrEditProductDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }
}
