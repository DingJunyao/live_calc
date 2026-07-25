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
      appBar: AppBar(title: const Text('个人中心')),
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
                  Text(user?.username ?? '用户', style: theme.textTheme.titleLarge),
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
            ListTile(leading: const Icon(Icons.scale), title: const Text('单位偏好'), onTap: () {}),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.restaurant), title: const Text('营养目标'), onTap: () {}),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.attach_money), title: const Text('预算设置'), onTap: () {}),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.dns), title: const Text('服务器地址'), onTap: () => context.push('/server-config')),
          ])),
          const SizedBox(height: 24),

          // My data section
          Text('My Data', style: theme.textTheme.titleSmall?.copyWith(color: theme.colorScheme.outline)),
          const SizedBox(height: 8),
          Card(child: Column(children: [
            ListTile(leading: const Icon(Icons.rate_review_outlined), title: const Text('我的提议'), onTap: () => context.push('/profile/proposals')),
            const Divider(height: 1),
            ListTile(leading: const Icon(Icons.place_outlined), title: const Text('我的地点'), onTap: () => context.push('/profile/places')),
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
              label: const Text('退出登录'),
              style: OutlinedButton.styleFrom(foregroundColor: theme.colorScheme.error),
            ),
          ),
        ],
      ),
    );
  }
}

