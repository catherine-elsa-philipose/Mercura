import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/providers.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activeBusinessNameAsync = ref.watch(activeBusinessNameProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings & Configuration'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Business Information',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    activeBusinessNameAsync.when(
                      data: (name) => ListTile(
                        leading: const Icon(Icons.business),
                        title: const Text('Business Name'),
                        subtitle: Text(
                          name,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                      loading: () => const ListTile(
                        leading: SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        title: Text('Loading Business Name...'),
                      ),
                      error: (err, stack) => const ListTile(
                        leading: Icon(Icons.business),
                        title: Text('Business Name'),
                        subtitle: Text('My Business'),
                      ),
                    ),
                    const Divider(),
                    const ListTile(
                      leading: Icon(Icons.security, color: Colors.green),
                      title: Text('Authentication Status'),
                      subtitle: Text('Secure JWT Session Active'),
                    ),
                    const Divider(),
                    const ListTile(
                      leading: Icon(Icons.cloud_done, color: Colors.blue),
                      title: Text('Backend Connection'),
                      subtitle: Text('Connected to Mercura API Service'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'System Actions',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.refresh, color: Colors.blue),
                    title: const Text('Reload Workspace'),
                    onTap: () {
                      ref.invalidate(activeBusinessProvider);
                      ref.invalidate(activeBusinessIdProvider);
                      ref.invalidate(activeBusinessNameProvider);
                      ref.invalidate(dashboardSummaryProvider);
                      ref.invalidate(customersProvider);
                      ref.invalidate(productsProvider);
                      ref.invalidate(invoicesProvider);
                      ref.invalidate(paymentsProvider);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Workspace refreshed.')),
                      );
                    },
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.logout, color: Colors.red),
                    title: const Text('Logout', style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                    onTap: () async {
                      await ref.read(tokenStorageProvider).deleteToken();
                      if (context.mounted) {
                        context.go('/login');
                      }
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
