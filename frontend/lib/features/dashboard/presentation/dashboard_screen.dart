import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/providers.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSummary = ref.watch(dashboardSummaryProvider);
    final activeBusinessNameAsync = ref.watch(activeBusinessNameProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            activeBusinessNameAsync.when(
              data: (name) => Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
              loading: () => const Text('Loading...', style: TextStyle(fontWeight: FontWeight.bold)),
              error: (err, stack) => const Text('Mercura Dashboard', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
            const Text('Business Overview', style: TextStyle(fontSize: 12, fontWeight: FontWeight.normal)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(dashboardSummaryProvider);
              ref.invalidate(activeBusinessProvider);
            },
            tooltip: 'Refresh Dashboard',
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await ref.read(tokenStorageProvider).deleteToken();
              if (context.mounted) context.go('/login');
            },
            tooltip: 'Logout',
          ),
        ],
      ),
      body: asyncSummary.when(
        data: (summary) {
          final isWide = MediaQuery.of(context).size.width > 900;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header banner
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Theme.of(context).colorScheme.primary,
                        Theme.of(context).colorScheme.tertiary,
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      activeBusinessNameAsync.when(
                        data: (name) => Text(
                          'Welcome back, $name!',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        loading: () => Text(
                          'Welcome back!',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        error: (err, stack) => Text(
                          'Welcome to Mercura',
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Here's today's business overview.",
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.white70,
                            ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                Text(
                  'Key Metrics',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 16),

                GridView.count(
                  crossAxisCount: isWide ? 3 : 2,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    _buildStatCard(
                      context,
                      title: 'Total Customers',
                      value: summary.totalCustomers.toString(),
                      icon: Icons.people,
                      color: Colors.blue,
                      onTap: () => context.go('/customers'),
                    ),
                    _buildStatCard(
                      context,
                      title: 'Total Products',
                      value: summary.totalProducts.toString(),
                      icon: Icons.inventory_2,
                      color: Colors.teal,
                      onTap: () => context.go('/products'),
                    ),
                    _buildStatCard(
                      context,
                      title: 'Low Stock Alerts',
                      value: summary.lowStockProducts.toString(),
                      icon: Icons.warning_amber_rounded,
                      color: summary.lowStockProducts > 0 ? Colors.orange : Colors.grey,
                      onTap: () => context.go('/products'),
                    ),
                    _buildStatCard(
                      context,
                      title: 'Total Invoices',
                      value: summary.totalInvoices.toString(),
                      icon: Icons.receipt_long,
                      color: Colors.purple,
                      onTap: () => context.go('/invoices'),
                    ),
                    _buildStatCard(
                      context,
                      title: 'Monthly Revenue',
                      value: '₹${summary.monthlyRevenue.toStringAsFixed(2)}',
                      icon: Icons.attach_money,
                      color: Colors.green,
                      onTap: () => context.go('/payments'),
                    ),
                    _buildStatCard(
                      context,
                      title: 'Outstanding Balance',
                      value: '₹${summary.outstandingBalance.toStringAsFixed(2)}',
                      icon: Icons.money_off,
                      color: summary.outstandingBalance > 0 ? Colors.red : Colors.grey,
                      onTap: () => context.go('/invoices'),
                    ),
                  ],
                ),
                const SizedBox(height: 32),

                // Quick Action & AI Assistant Row
                Card(
                  elevation: 1,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.auto_awesome, color: Theme.of(context).colorScheme.primary),
                            const SizedBox(width: 8),
                            Text(
                              'AI Business Assistant',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Get instant answers about your products, revenue trends, low stock warnings, or financial metrics using natural language.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: [
                            FilledButton.icon(
                              onPressed: () => context.go('/assistant'),
                              icon: const Icon(Icons.chat_bubble_outline),
                              label: const Text('Open AI Assistant'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => context.go('/customers'),
                              icon: const Icon(Icons.person_add_outlined),
                              label: const Text('Manage Customers'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => context.go('/products'),
                              icon: const Icon(Icons.add_shopping_cart),
                              label: const Text('Manage Inventory'),
                            ),
                            OutlinedButton.icon(
                              onPressed: () => context.go('/invoices'),
                              icon: const Icon(Icons.receipt),
                              label: const Text('Manage Invoices'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 48, color: Colors.red),
                const SizedBox(height: 16),
                Text('Failed to load dashboard data: $err', textAlign: TextAlign.center),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => ref.invalidate(dashboardSummaryProvider),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatCard(
    BuildContext context, {
    required String title,
    required String value,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Card(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircleAvatar(
                radius: 24,
                backgroundColor: color.withAlpha(25),
                child: Icon(icon, size: 28, color: color),
              ),
              const SizedBox(height: 12),
              Text(
                title,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Colors.grey[700]),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
