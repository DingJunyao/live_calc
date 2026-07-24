import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/home_provider.dart';
import '../widgets/meal_card.dart';
import '../widgets/quick_entry_grid.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../../../shared/widgets/error_display.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(homeProvider.notifier).loadToday());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(homeProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('生记'),
        leading: Builder(
          builder: (ctx) => IconButton(
            icon: const Icon(Icons.menu),
            onPressed: () => Scaffold.of(ctx).openDrawer(),
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(homeProvider.notifier).refresh(),
            tooltip: '换一换',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(homeProvider.notifier).refresh(),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.only(bottom: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: Row(
                  children: [
                    Icon(Icons.today, color: theme.colorScheme.primary),
                    const SizedBox(width: 8),
                    Text('今日推荐', style: theme.textTheme.titleLarge),
                  ],
                ),
              ),
              if (state.loading)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 48),
                  child: LoadingIndicator(message: '加载推荐中...'),
                )
              else if (state.error != null)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 24),
                  child: ErrorDisplay(
                    message: state.error!,
                    onRetry: () => ref.read(homeProvider.notifier).loadToday(),
                  ),
                )
              else if (state.recommendation != null)
                ...state.recommendation!.meals.map((meal) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  child: MealCard(
                    meal: meal,
                    onTap: meal.recipeId != null
                        ? () => context.push('/recipes/' + meal.recipeId.toString())
                        : null,
                  ),
                )),
              const SizedBox(height: 24),
              const QuickEntryGrid(),
            ],
          ),
        ),
      ),
    );
  }
}