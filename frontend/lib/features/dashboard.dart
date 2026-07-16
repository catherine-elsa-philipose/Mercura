import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.auto_awesome),
            onPressed: () => context.push('/assistant'),
            tooltip: 'AI Business Assistant',
          )
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.dashboard, size: 80, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              'Welcome to Mercura',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            const Text('Dashboard UI is under development.'),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: () => context.push('/assistant'),
              icon: const Icon(Icons.chat),
              label: const Text('Chat with AI Assistant'),
            )
          ],
        ),
      ),
    );
  }
}
