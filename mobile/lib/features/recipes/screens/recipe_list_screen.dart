import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/recipe_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
import '../models/recipe_summary.dart';
import '../../../shared/widgets/error_display.dart';
import '../../../shared/widgets/empty_state.dart';

class RecipeListScreen extends ConsumerStatefulWidget {
  const RecipeListScreen({super.key});

  @override
  ConsumerState<RecipeListScreen> createState() => _RecipeListScreenState();
}

class _RecipeListScreenState extends ConsumerState<RecipeListScreen> {
  final _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(recipeListProvider.notifier).loadRecipes());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = ref.watch(recipeListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('菜谱'),
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: '搜索菜谱...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          ref.read(recipeListProvider.notifier).loadRecipes();
                        },
                      )
                    : null,
              ),
              onSubmitted: (v) =>
                  ref.read(recipeListProvider.notifier).loadRecipes(search: v),
            ),
          ),

          // Content
          Expanded(
            child: _buildContent(theme, state),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(ThemeData theme, RecipeListState state) {
    if (state.loading && state.recipes.isEmpty) {
      return const LoadingIndicator(message: '加载菜谱...');
    }
    if (state.error != null && state.recipes.isEmpty) {
      return ErrorDisplay(
        message: state.error!,
        onRetry: () => ref.read(recipeListProvider.notifier).loadRecipes(),
      );
    }
    if (state.recipes.isEmpty) {
      return const EmptyState(
        icon: Icons.restaurant,
        title: '暂无菜谱',
        subtitle: '在 Web 端创建菜谱后即可查看',
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(recipeListProvider.notifier).loadRecipes(),
      // 用 Wrap + 固定宽度卡片：高度由内容决定，彻底消除单元格固定高度导致的溢出
      child: LayoutBuilder(
        builder: (context, constraints) {
          const padding = 12.0;
          const spacing = 12.0;
          final cardWidth = (constraints.maxWidth - padding * 2 - spacing) / 2;
          return SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(padding),
            child: Wrap(
              spacing: spacing,
              runSpacing: spacing,
              children: state.recipes.map((r) {
                return SizedBox(
                  width: cardWidth,
                  child: Card(
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: () => context.push('/recipes/${r.id}'),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          AspectRatio(
                            aspectRatio: 4 / 3,
                            child: Container(
                              width: double.infinity,
                              color: theme.colorScheme.primaryContainer
                                  .withValues(alpha: 0.3),
                              child: r.imageUrl != null
                                  ? Image.network(r.imageUrl!,
                                      fit: BoxFit.cover, width: double.infinity)
                                  : Icon(Icons.restaurant,
                                      size: 48,
                                      color: theme.colorScheme.primary
                                          .withValues(alpha: 0.5)),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.all(8),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(r.name,
                                    style: theme.textTheme.titleSmall,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis),
                                const SizedBox(height: 4),
                                _buildPriceCalories(
                                    theme, r, state.loadingCosts),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          );
        },
      ), // 关闭 LayoutBuilder
    ); // 关闭 RefreshIndicator
  }

  Widget _buildPriceCalories(ThemeData theme, RecipeSummary r, bool loading) {
    final servings = r.servings > 0 ? r.servings : 1;
    final hasCost = r.estimatedCost != null;
    final hasCal = r.calories != null;
    // 价格/热量懒加载中：显示占位，避免跳变
    if (!hasCost && !hasCal) {
      return Text(
        loading ? '--' : '${r.servings} 人份',
        style: theme.textTheme.labelSmall
            ?.copyWith(color: theme.colorScheme.outline),
      );
    }
    final children = <Widget>[];
    if (hasCost) {
      children.add(
        Text(
          '¥${r.estimatedCost!.toStringAsFixed(2)}/$servings人份',
          style: theme.textTheme.labelMedium?.copyWith(
            color: theme.colorScheme.primary,
            fontWeight: FontWeight.bold,
          ),
        ),
      );
    }
    if (hasCost && hasCal) {
      children.add(Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: Text('·',
            style: theme.textTheme.labelSmall
                ?.copyWith(color: theme.colorScheme.outline)),
      ));
    }
    if (hasCal) {
      final perServing = (r.calories! / servings).round();
      children.add(
        Text(
          '$perServing kcal/份',
          style: theme.textTheme.labelSmall
              ?.copyWith(color: theme.colorScheme.outline),
        ),
      );
    }
    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      children: children,
    );
  }
}
