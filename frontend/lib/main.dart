import 'package:flutter/material.dart';

void main() {
  runApp(const MercuraApp());
}

class MercuraApp extends StatelessWidget {
  const MercuraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mercura Platform',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blueGrey,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const MercuraStarterScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class MercuraStarterScreen extends StatelessWidget {
  const MercuraStarterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mercura Platform'),
        centerTitle: true,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.business,
              size: 80,
              color: Colors.blueGrey,
            ),
            const SizedBox(height: 24),
            Text(
              'Mercura Project Foundation Ready',
              style: Theme.of(context).textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            Text(
              'Phase 1: Lightweight Project Foundation\n'
              'Backend: FastAPI | Frontend: Flutter Web',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[700],
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
