import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../auth/providers/auth_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final authState = ref.watch(authProvider);
    final user = authState.user;

    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // User info card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(children: [
                CircleAvatar(
                  radius: 32,
                  child: Text(user?.username.isNotEmpty == true ? user!.username[0].toUpperCase() : '?'),
                ),
                const SizedBox(width: 16),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(user?.username ?? 'User', style: theme.textTheme.titleLarge),
                  Text(user?.email ?? '', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.outline)),
                ])),
              ]),
            ),
          ),
          const SizedBox(height: 24),

          // Settings section
          Text('Settings', style: theme.textTheme.titleSmall?.copyWith(color: theme.colorScheme.outline)),
          const SizedBox(height: 8),
          Card(child: Column(children: [
            ListTile(leading: const Icon(Icons.scale), title: const Text('Unit Preferences'), onTap: () {}),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.restaurant), title: const Text('Nutrition Goals'), onTap: () {}),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.attach_money), title: const Text('Budget Settings'), onTap: () {}),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.dns), title: const Text('Server Address'), onTap: () => context.push('/server-config')),
          ])),
          const SizedBox(height: 24),

          // My data section
          Text('My Data', style: theme.textTheme.titleSmall?.copyWith(color: theme.colorScheme.outline)),
          const SizedBox(height: 8),
          Card(child: Column(children: [
            ListTile(leading: const Icon(Icons.rate_review_outlined), title: const Text('My Proposals'), onTap: () => context.push('/profile/proposals')),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.place_outlined), title: const Text('My Places'), onTap: () => context.push('/profile/places')),
          ])),
          const SizedBox(height: 32),

          // Logout
          SafeArea(
            child: OutlinedButton.icon(
              onPressed: () async {
                await ref.read(authProvider.notifier).logout();
                if (context.mounted) context.go('/login');
              },
              icon: const Icon(Icons.logout),
              label: const Text('Logout'),
              style: OutlinedButton.styleFrom(foregroundColor: theme.colorScheme.error),
            ),
          ),
        ],
      ),
    );
  }
}
