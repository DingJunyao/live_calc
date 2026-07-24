import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/recipe_provider.dart';
import '../../../shared/widgets/loading_indicator.dart';
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
              onSubmitted: (v) => ref.read(recipeListProvider.notifier).loadRecipes(search: v),
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
      child: GridView.builder(
        padding: const EdgeInsets.all(12),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          childAspectRatio: 0.8,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
        ),
        itemCount: state.recipes.length,
        itemBuilder: (ctx, i) {
          final r = state.recipes[i];
          return Card(
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: () => context.push('/recipes/${r.id}'),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Image placeholder or icon
                  Expanded(
                    child: Container(
                      width: double.infinity,
                      color: theme.colorScheme.primaryContainer.withValues(alpha: 0.3),
                      child: r.imageUrl != null
                          ? Image.network(r.imageUrl!, fit: BoxFit.cover, width: double.infinity)
                          : Icon(Icons.restaurant, size: 48, color: theme.colorScheme.primary.withValues(alpha: 0.5)),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(r.name, style: theme.textTheme.titleSmall, maxLines: 1, overflow: TextOverflow.ellipsis),
                        const SizedBox(height: 4),
                        if (r.estimatedCost != null)
                          Text('¥${r.estimatedCost!.toStringAsFixed(1)}',
                            style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.primary)),
                        Text('${r.ingredientCount} 种食材',
                            style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.outline)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}