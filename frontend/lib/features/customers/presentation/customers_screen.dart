import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/providers.dart';
import '../domain/customer.dart';

class CustomersScreen extends ConsumerStatefulWidget {
  const CustomersScreen({super.key});

  @override
  ConsumerState<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends ConsumerState<CustomersScreen> {
  void _showAddOrEditCustomerDialog(BuildContext context, {Customer? customer}) {
    final nameController = TextEditingController(text: customer?.name ?? '');
    final phoneController = TextEditingController(text: customer?.phone ?? '');
    final emailController = TextEditingController(text: customer?.email ?? '');

    showDialog(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(customer == null ? 'Add Customer' : 'Edit Customer'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(labelText: 'Name', prefixIcon: Icon(Icons.person)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: phoneController,
                  decoration: const InputDecoration(labelText: 'Phone', prefixIcon: Icon(Icons.phone)),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: emailController,
                  decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.email)),
                ),
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
                    'phone': phoneController.text.trim().isEmpty ? null : phoneController.text.trim(),
                    'email': emailController.text.trim().isEmpty ? null : emailController.text.trim(),
                  };
                  if (customer == null) {
                    await ref.read(customerServiceProvider).createCustomer(businessId, data);
                  } else {
                    await ref.read(customerServiceProvider).updateCustomer(businessId, customer.id, data);
                  }
                  ref.invalidate(customersProvider);
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

  Future<void> _deactivateCustomer(Customer customer) async {
    try {
      final businessId = await ref.read(activeBusinessIdProvider.future);
      await ref.read(customerServiceProvider).deactivateCustomer(businessId, customer.id);
      ref.invalidate(customersProvider);
      ref.invalidate(dashboardSummaryProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${customer.name} deactivated.')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<void> _reactivateCustomer(Customer customer) async {
    try {
      final businessId = await ref.read(activeBusinessIdProvider.future);
      await ref.read(customerServiceProvider).reactivateCustomer(businessId, customer.id);
      ref.invalidate(customersProvider);
      ref.invalidate(dashboardSummaryProvider);
      ref.invalidate(activeBusinessProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${customer.name} reactivated.')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncData = ref.watch(customersProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Customers'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(customersProvider),
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
                  Icon(Icons.people_outline, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text('No customers found.', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () => _showAddOrEditCustomerDialog(context),
                    icon: const Icon(Icons.add),
                    label: const Text('Add Your First Customer'),
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
              final customer = items[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                  child: Text(
                    customer.name.isNotEmpty ? customer.name[0].toUpperCase() : 'C',
                    style: TextStyle(color: Theme.of(context).colorScheme.onPrimaryContainer, fontWeight: FontWeight.bold),
                  ),
                ),
                title: Text(customer.name, style: TextStyle(fontWeight: FontWeight.w600, color: customer.isActive ? null : Colors.grey)),
                subtitle: Text(customer.email ?? customer.phone ?? 'No contact details'),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Chip(
                      avatar: Icon(
                        customer.isActive ? Icons.check_circle : Icons.cancel,
                        size: 16,
                        color: customer.isActive ? Colors.green : Colors.red,
                      ),
                      label: Text(customer.isActive ? 'Active' : 'Inactive'),
                    ),
                    PopupMenuButton<String>(
                      onSelected: (val) {
                        if (val == 'edit' || val == 'view') {
                          _showAddOrEditCustomerDialog(context, customer: customer);
                        } else if (val == 'deactivate') {
                          _deactivateCustomer(customer);
                        } else if (val == 'reactivate') {
                          _reactivateCustomer(customer);
                        }
                      },
                      itemBuilder: (context) => [
                        if (customer.isActive)
                          const PopupMenuItem(value: 'edit', child: Row(children: [Icon(Icons.edit, size: 20), SizedBox(width: 8), Text('Edit')])),
                        if (customer.isActive)
                          const PopupMenuItem(value: 'deactivate', child: Row(children: [Icon(Icons.block, size: 20, color: Colors.red), SizedBox(width: 8), Text('Deactivate', style: TextStyle(color: Colors.red))])),
                        if (!customer.isActive)
                          const PopupMenuItem(value: 'reactivate', child: Row(children: [Icon(Icons.check_circle_outline, size: 20, color: Colors.green), SizedBox(width: 8), Text('Reactivate', style: TextStyle(color: Colors.green))])),
                        if (!customer.isActive)
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
        error: (err, stack) => Center(child: Text('Error loading customers: $err')),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddOrEditCustomerDialog(context),
        child: const Icon(Icons.add),
      ),
    );
  }
}
