 import 'package:flutter/material.dart';
 import 'package:flutter_riverpod/flutter_riverpod.dart';
 import '../providers/recipe_provider.dart';
 import '../../../shared/widgets/loading_indicator.dart';
 import '../../../shared/widgets/error_display.dart';
 
 class RecipeAnalysisScreen extends ConsumerWidget {
   final int id;
   const RecipeAnalysisScreen({super.key, required this.id});
 
   @override
   Widget build(BuildContext context, WidgetRef ref) {
     final theme = Theme.of(context);
     final asyncDetail = ref.watch(recipeDetailProvider(id));
 
     return asyncDetail.when(
       loading: () => const Scaffold(
         appBar: AppBar(title: Text('菜谱分析')),
         body: LoadingIndicator(message: '加载分析...'),
       ),
       error: (e, _) => Scaffold(
         appBar: AppBar(title: const Text('菜谱分析')),
         body: ErrorDisplay(message: e.toString(), onRetry: () => ref.invalidate(recipeDetailProvider(id))),
       ),
       data: (detail) {
         final totalCost = detail.totalCost ?? 0;
         final maxCost = detail.ingredients
             .map((i) => i.estimatedCost ?? 0)
             .reduce((a, b) => a > b ? a : b);
 
         return Scaffold(
           appBar: AppBar(title: Text('${detail.name} - 分析')),
           body: SingleChildScrollView(
             padding: const EdgeInsets.all(16),
             child: Column(
               crossAxisAlignment: CrossAxisAlignment.start,
               children: [
                 // Cost breakdown
                 Text('成本分布', style: theme.textTheme.titleMedium),
                 const SizedBox(height: 16),
                 if (detail.ingredients.isEmpty)
                   Text('暂无食材数据', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.outline))
                 else
                   ...detail.ingredients.map((ing) {
                     final cost = ing.estimatedCost ?? 0;
                     final pct = totalCost > 0 ? (cost / totalCost * 100) : 0.0;
                     final barWidth = maxCost > 0 ? (cost / maxCost) : 0.0;
 
                     return Padding(
                       padding: const EdgeInsets.only(bottom: 12),
                       child: Column(
                         crossAxisAlignment: CrossAxisAlignment.start,
                         children: [
                           Row(
                             mainAxisAlignment: MainAxisAlignment.spaceBetween,
                             children: [
                               Expanded(child: Text(ing.name, style: theme.textTheme.bodyMedium)),
                               Text('¥${cost.toStringAsFixed(2)}', style: theme.textTheme.bodyMedium?.copyWith(
                                 fontWeight: FontWeight.bold,
                               )),
                               Text('${pct.toStringAsFixed(1)}%', style: theme.textTheme.labelSmall?.copyWith(
                                 color: theme.colorScheme.outline,
                               )),
                             ],
                           ),
                           const SizedBox(height: 4),
                           ClipRRect(
                             borderRadius: BorderRadius.circular(4),
                             child: LinearProgressIndicator(
                               value: barWidth,
                               minHeight: 8,
                               backgroundColor: theme.colorScheme.surfaceContainerHighest,
                             ),
                           ),
                         ],
                       ),
                     );
                   }),
 
                 const SizedBox(height: 16),
                 Container(
                   padding: const EdgeInsets.all(12),
                   decoration: BoxDecoration(
                     color: theme.colorScheme.primaryContainer,
                     borderRadius: BorderRadius.circular(8),
                   ),
                   child: Row(
                     mainAxisAlignment: MainAxisAlignment.spaceBetween,
                     children: [
                       Text('总成本', style: theme.textTheme.titleMedium),
                       Text('¥${totalCost.toStringAsFixed(2)}',
                         style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                     ],
                   ),
                 ),
 
                 const SizedBox(height: 32),
 
                 // Nutrition section (placeholder - real data needs API)
                 Text('营养信息', style: theme.textTheme.titleMedium),
                 const SizedBox(height: 12),
                 Container(
                   padding: const EdgeInsets.all(16),
                   decoration: BoxDecoration(
                     color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                     borderRadius: BorderRadius.circular(12),
                   ),
                   child: Row(
                     mainAxisAlignment: MainAxisAlignment.spaceAround,
                     children: [
                       _NutritionItem(label: '蛋白质', value: '--', unit: 'g', icon: Icons.fitness_center),
                       _NutritionItem(label: '碳水', value: '--', unit: 'g', icon: Icons.grain),
                       _NutritionItem(label: '脂肪', value: '--', unit: 'g', icon: Icons.oil_barrel),
                       _NutritionItem(label: '热量', value: '--', unit: 'kcal', icon: Icons.local_fire_department),
                     ],
                   ),
                 ),
                 const SizedBox(height: 8),
                 Text('营养数据需要 USDA 匹配后显示',
                   style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.outline)),
               ],
             ),
           ),
         );
       },
     );
   }
 }
 
 class _NutritionItem extends StatelessWidget {
   final String label;
   final String value;
   final String unit;
   final IconData icon;
 
   const _NutritionItem({required this.label, required this.value, required this.unit, required this.icon});
 
   @override
   Widget build(BuildContext context) {
     final theme = Theme.of(context);
     return Column(
       mainAxisSize: MainAxisSize.min,
       children: [
         Icon(icon, color: theme.colorScheme.primary, size: 24),
         const SizedBox(height: 4),
         Text('$value$unit', style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
         Text(label, style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.outline)),
       ],
     );
   }
 }
