import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/profile_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';
import '../../../shared/widgets/empty_state.dart';

class MyPlacesScreen extends ConsumerStatefulWidget {
  const MyPlacesScreen({super.key});

  @override
  ConsumerState<MyPlacesScreen> createState() => _MyPlacesScreenState();
}

class _MyPlacesScreenState extends ConsumerState<MyPlacesScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(placeListProvider.notifier).load());
  }

  IconData _kindIcon(String? kind) {
    switch (kind) {
      case 'home':
        return Icons.home;
      case 'company':
        return Icons.business;
      default:
        return Icons.place;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(placeListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('My Places')),
      body: state.loading && state.items.isEmpty
          ? const LoadingIndicator()
          : state.error != null && state.items.isEmpty
              ? ErrorDisplay(message: state.error!, onRetry: () => ref.read(placeListProvider.notifier).load())
              : state.items.isEmpty
                  ? const EmptyState(
                      icon: Icons.place_outlined,
                      title: 'No Places',
                      subtitle: 'Saved locations will appear here')
                  : RefreshIndicator(
                      onRefresh: () => ref.read(placeListProvider.notifier).load(),
                      child: ListView.separated(
                        padding: const EdgeInsets.all(12),
                        itemCount: state.items.length,
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (ctx, i) {
                          final place = state.items[i];
                          return ListTile(
                            leading: Icon(_kindIcon(place.kind)),
                            title: Text(place.name),
                            subtitle: Text(place.address ?? '', style: theme.textTheme.bodySmall),
                          );
                        },
                      ),
                    ),
    );
  }
}
