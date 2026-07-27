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

    Widget recArea;
    if (state.loading) {
      recArea = const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: LoadingIndicator(message: '\u52a0\u8f7d\u4e2d...'),
      );
    } else if (state.generating) {
      recArea = const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: LoadingIndicator(message: '\u6b63\u5728\u751f\u6210\u4eca\u65e5\u63a8\u8350\uff0cAI \u6b63\u5728\u4e3a\u4f60\u642d\u914d\u98df\u8c31\u2026'),
      );
    } else if (state.error != null) {
      recArea = Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: ErrorDisplay(
          message: state.error!,
          onRetry: () => ref.read(homeProvider.notifier).loadToday(),
        ),
      );
    } else if (state.recommendation != null && state.recommendation!.meals.isNotEmpty) {
      recArea = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ...state.recommendation!.meals.map((meal) => Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: MealCard(
              meal: meal,
              onTap: meal.recipeId != null
                  ? () => context.push('/recipes/' + meal.recipeId.toString())
                  : null,
            ),
          )),
        ],
      );
    } else {
      recArea = const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(
          child: Text('\u6682\u65e0\u63a8\u8350\uff0c\u70b9\u51fb\u5237\u65b0\u6309\u94ae\u751f\u6210\u4eca\u65e5\u63a8\u8350'),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('\u751f\u8ba1'),
        leading: Builder(
          builder: (ctx) => IconButton(
            icon: const Icon(Icons.menu),
            onPressed: () => Scaffold.of(ctx).openDrawer(),
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: state.generating
                ? null
                : () => ref.read(homeProvider.notifier).refresh(),
            tooltip: '\u6362\u4e00\u6362',
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
                    Text('\u4eca\u65e5\u63a8\u8350', style: theme.textTheme.titleLarge),
                  ],
                ),
              ),
              recArea,
              const SizedBox(height: 24),
              const QuickEntryGrid(),
            ],
          ),
        ),
      ),
    );
  }
}
