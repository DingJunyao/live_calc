import 'dart:ui' show PointerDeviceKind;
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
// 内部类 RenderLineChart 的 getResponseAtLocation 是公开 API，用于绕过 fl_chart
// 1.2.0 的手势竞技场缺陷（见 _onPointerGlobal 注释）。选择编译期类型安全（升级
// 时编译报错而非运行期崩溃）；fl_chart 升级时需复核此依赖。
// ignore: implementation_imports
import 'package:fl_chart/src/chart/line_chart/line_chart_renderer.dart';
import '../repositories/recipe_repository.dart';
import '../utils/ingredient_colors.dart';

/// 趋势筛选天数映射：周/月/季/年/全部（对齐 web 常量）
const costHistoryDays = <String, int>{
  'week': 7, 'month': 30, 'quarter': 90, 'year': 365, 'all': 3650,
};

/// 堆叠面积图单条序列
class StackedSeries {
  final String name;
  final Color color;
  final List<FlSpot> spots;
  const StackedSeries(
      {required this.name, required this.color, required this.spots});
}

/// 从成本历史构建堆叠序列：每食材一条线，y 按「本食材成本 + 前面所有食材成本」累加
/// （对齐 web echarts stack:'total'）。无 breakdown 时返回空列表。
List<StackedSeries> buildStackedSeries(List<CostHistoryPoint> points) {
  if (points.isEmpty) return const [];
  final hasBreakdown = points.any((p) => p.breakdown.isNotEmpty);
  if (!hasBreakdown) return const [];

  // 收集所有食材（按首次出现顺序）
  final ingOrder = <int, String>{};
  for (final p in points) {
    for (final b in p.breakdown) {
      ingOrder.putIfAbsent(b.ingredientId ?? 0, () => b.ingredientName);
    }
  }

  // 堆叠 = 每天内按序列顺序累加（echarts stack:'total' 语义）：
  // 第 j 条线的 y = 第 j 条及之前所有食材当日成本之和。
  // 「天」是外层循环，累加器每进入新的一天都从 0 重新开始。
  // 匹配 key 时用 (ingredientId ?? 0) 对齐收集 pass（null id 归 key 0），
  // fold 求和保证同天重复 id 的明细都计入，缺失时 where 为空自然得 0。
  final keys = ingOrder.keys.toList();
  final spotsByKey = {for (final k in keys) k: <FlSpot>[]};
  for (var i = 0; i < points.length; i++) {
    final day = points[i];
    var acc = 0.0;
    for (var j = 0; j < keys.length; j++) {
      final key = keys[j];
      final cost = day.breakdown
          .where((b) => (b.ingredientId ?? 0) == key)
          .fold<double>(0, (s, b) => s + b.cost);
      acc += cost;
      spotsByKey[key]!.add(FlSpot(i.toDouble(), acc));
    }
  }
  return [
    for (var j = 0; j < keys.length; j++)
      StackedSeries(
        name: ingOrder[keys[j]]!,
        color: getIngredientColor(keys[j] == 0 ? null : keys[j]),
        spots: spotsByKey[keys[j]]!,
      ),
  ];
}

/// 构建 tooltip 明细项：日期 + 每食材「名: ¥成本」+「合计: ¥x」。
/// fl_chart 传入的 touchedSpots 按到触点距离排序（非序列顺序），
/// 必须先按 barIndex（序列顺序）重排，再逆推每食材本日成本 = 累加值差值。
/// fl_chart 对每条线独立按「到触点像素距离」取最近 spot（x 相同但 y 不同，
/// 相邻天像素宽过小、线间 y 差大时，远线会取到 i±1 天）——逆推必须统一到
/// 触点这一天（dayIndex = touchedSpots.first.x，fl_chart painter 已按距离
/// 升序返回），用各线该天堆叠值差值，否则混日会出现负数成本、Σ明细≠合计。
/// 注意不能用 barIndex 重排后的 sorted.first 做锚点：那是底部线（barIndex=0）
/// 的最近点，可能与触点天错位（日期显示触点天、明细却是邻天）。
/// 调用约束：touchedSpots 必须来自本图 lineBarsData（barIndex 恒 <
/// series.length、spot.bar.spots 与序列同长同引用），此处不做代码守卫——
/// 守卫会破坏 1:1 契约（条数必须与 spots 一致，fl_chart painter 校验
/// tooltipItems.length == showingSpots.length，不一致直接 throw）。
/// 日期行并入第一条、合计行并入最后一条的 children（TextSpan 渲染时
/// text 与 children 相连，文本各放一份不重复）。
List<LineTooltipItem> buildStackedTooltipItems(
    List<StackedSeries> series, List<LineBarSpot> touchedSpots, String date) {
  if (touchedSpots.isEmpty) return [];
  // 锚点须先取（touchedSpots 未重排时 first 即距触点最近线 = 触点天）
  final dayIndex = touchedSpots.first.x.toInt();
  final sorted = [...touchedSpots]
    ..sort((a, b) => a.barIndex.compareTo(b.barIndex));
  const plain = TextStyle(color: Colors.white);
  const bold = TextStyle(fontWeight: FontWeight.bold, color: Colors.white);
  final items = <LineTooltipItem>[];
  var prev = 0.0;
  for (final spot in sorted) {
    final stackedY = spot.bar.spots[dayIndex].y;
    final line =
        '${series[spot.barIndex].name}: ¥${(stackedY - prev).toStringAsFixed(2)}';
    items.add(LineTooltipItem(line, plain));
    prev = stackedY;
  }
  // 日期行并入第一条
  items[0] = LineTooltipItem('$date\n', bold,
      children: [TextSpan(text: items[0].text, style: plain)]);
  // 合计行并入最后一条（触点天堆叠总值）
  items.last = LineTooltipItem(items.last.text, items.last.textStyle, children: [
    ...(items.last.children ?? const []),
    TextSpan(
        text: '\n合计: ¥${sorted.last.bar.spots[dayIndex].y.toStringAsFixed(2)}',
        style: bold),
  ]);
  return items;
}

/// 成本趋势堆叠面积图：周/月/季/年/全部筛选 + 食材标签点击高亮；
/// 无 breakdown 数据时回退 avg/min/max 折线+区间（对齐 web CostTrendAnalysis）。
class CostTrendStackedChart extends StatefulWidget {
  final List<CostHistoryPoint> points;
  final bool loading;
  final ValueChanged<String>? onFilterChange;
  const CostTrendStackedChart({
    super.key,
    required this.points,
    this.loading = false,
    this.onFilterChange,
  });

  @override
  State<CostTrendStackedChart> createState() => _CostTrendStackedChartState();
}

class _CostTrendStackedChartState extends State<CostTrendStackedChart> {
  String _filter = 'quarter';
  int? _highlightIndex;
  // 自定义 touch 处理下的 tooltip 展示状态（驱动画布绘制 tooltip）
  List<ShowingTooltipIndicators> _tooltipSpots = [];
  // 挂到 LineChart.chartRendererKey，用于在 pointer 层直接拿到 RenderLineChart
  // 计算命中 spot（绕过 fl_chart 手势竞技场缺陷，见 _onPointerGlobal 注释）
  final GlobalKey _chartKey = GlobalKey();

  @override
  void didUpdateWidget(CostTrendStackedChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.points != widget.points) {
      _highlightIndex = null;
      // 数据变化后旧 tooltip 的位置/成本已失效，一并清空
      _tooltipSpots = [];
    }
  }

  // 应用命中结果：命中序列即设置（点击后 tooltip 保留，对齐 web 点击即显；
  // 内置实现移动端 FlTapUpEvent 会清空 → 用户反馈「点击没有提示」的放大器），
  // 点空白/手势取消才清空。
  void _applySpots(List<LineBarSpot>? spots) {
    if (spots == null || spots.isEmpty) {
      if (_tooltipSpots.isNotEmpty) {
        setState(() => _tooltipSpots = []);
      }
      return;
    }
    // 与内置实现一致：y 降序，最顶部序列排前（tooltip 定位于最高点）
    final sorted = [...spots]..sort((a, b) => b.y.compareTo(a.y));
    setState(() {
      _tooltipSpots = [ShowingTooltipIndicators(sorted)];
    });
  }

  // pointer 层直接响应（down/move/up/hover）：fl_chart 1.2.0 的手势竞技场有缺陷
  // —— RenderBaseChart.handleEvent 先注册 longPressGestureRecognizer，而指针抬起时
  // GestureArenaManager.sweep 盲取第一个存活成员（longPress.acceptGesture 为空实现，
  // flutter 源码注释自认「may happen from a sweep」），tap 永远被 reject →
  // onTapDown/onTapUp 不触发 → 快速点击（<100ms）无 tooltip。这里绕开竞技场，
  // 用 RenderLineChart 公开的 getResponseAtLocation 计算命中，任何点击都出 tooltip。
  void _onPointerGlobal(Offset globalPosition) {
    final box = _chartKey.currentContext?.findRenderObject();
    if (box is! RenderLineChart) return;
    final local = box.globalToLocal(globalPosition);
    _applySpots(box.getResponseAtLocation(local).lineBarSpots);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.show_chart, color: theme.colorScheme.tertiary, size: 20),
              const SizedBox(width: 8),
              Text('成本趋势',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const Spacer(),
              // DropdownButton 宽度自适应，窄屏 + 系统字体缩放下不会像 5 段切换器撑爆标题行
              _buildFilterToggle(theme),
            ]),
            const SizedBox(height: 12),
            // 图表区外包 Listener 自处理 pointer 事件（绕过 fl_chart 竞技场缺陷，
            // 让快速点击也出 tooltip，见 _onPointerGlobal 注释）
            // MouseRegion 包一层处理鼠标移出图表区清空 tooltip（Listener 无
            // onPointerExit；onPointerHover 仅桌面悬停触发，天然 mouse 门槛）
            MouseRegion(
              onExit: (_) => _applySpots(null),
              child: Listener(
                behavior: HitTestBehavior.translucent,
                onPointerDown: (e) => _onPointerGlobal(e.position),
                // 触屏拖滚视图时 move 不追（避免滑动时满屏 tooltip 闪烁）
                onPointerMove: (e) {
                  if (e.kind == PointerDeviceKind.mouse) {
                    _onPointerGlobal(e.position);
                  }
                },
                onPointerUp: (e) => _onPointerGlobal(e.position),
                onPointerHover: (e) => _onPointerGlobal(e.position),
                child: SizedBox(height: 200, child: _buildBody(theme)),
              ),
            ),
            if (widget.points.any((p) => p.breakdown.isNotEmpty)) ...[
              const SizedBox(height: 12),
              _buildIngredientTags(theme),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFilterToggle(ThemeData theme) {
    const labels = {'week': '周', 'month': '月', 'quarter': '季', 'year': '年', 'all': '全部'};
    return DropdownButton<String>(
      key: const Key('filter_dropdown'),
      value: _filter,
      isDense: true,
      underline: const SizedBox.shrink(),
      style: theme.textTheme.bodyMedium,
      items: labels.keys
          .map((k) => DropdownMenuItem(value: k, child: Text(labels[k]!)))
          .toList(),
      onChanged: (v) {
        if (v == null) return;
        setState(() => _filter = v);
        widget.onFilterChange?.call(v);
      },
    );
  }

  Widget _buildBody(ThemeData theme) {
    if (widget.loading && widget.points.isEmpty) {
      return const Center(child: CircularProgressIndicator(strokeWidth: 2));
    }
    if (widget.points.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.show_chart, size: 40, color: theme.colorScheme.outline),
            const SizedBox(height: 8),
            Text('暂无成本趋势数据',
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.outline)),
          ],
        ),
      );
    }
    final series = buildStackedSeries(widget.points);
    if (series.isEmpty) return _buildFallbackLineChart(theme);
    return _buildStackedChart(theme, series);
  }

  Widget _buildStackedChart(ThemeData theme, List<StackedSeries> series) {
    final isHighlighted = _highlightIndex != null;
    final lineBars = series.asMap().entries.map((e) {
      final i = e.key;
      final s = e.value;
      final highlight = _highlightIndex == i;
      final dimmed = isHighlighted && !highlight;
      return LineChartBarData(
        spots: s.spots,
        color: s.color,
        barWidth: highlight ? 2.5 : 1.5,
        isCurved: true,
        curveSmoothness: 0.35,
        dotData: const FlDotData(show: false),
        belowBarData: BarAreaData(
          show: true,
          color: s.color.withValues(alpha: dimmed ? 0.05 : 0.30),
        ),
      );
    }).toList();

    return LineChart(
      // 挂到 RenderLineChart，供 _onPointerGlobal 计算命中 spot
      chartRendererKey: _chartKey,
      LineChartData(
        // 自定义 touch 处理下的 tooltip 状态（内置 handleBuiltInTouches 在
        // 移动端 tap-up 清空 tooltip，导致「点击没有提示」）
        showingTooltipIndicators: _tooltipSpots,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: 1,
          getDrawingHorizontalLine: (v) => FlLine(
              color: theme.colorScheme.outlineVariant, strokeWidth: 0.5),
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              getTitlesWidget: (v, meta) => Text('¥${v.toInt()}',
                  style: TextStyle(fontSize: 9, color: theme.colorScheme.outline)),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 1,
              getTitlesWidget: (v, meta) {
                final i = v.toInt();
                if (i < 0 || i >= widget.points.length) {
                  return const SizedBox.shrink();
                }
                final idxList = {0, widget.points.length ~/ 2, widget.points.length - 1};
                if (!idxList.contains(i)) return const SizedBox.shrink();
                final date = widget.points[i].date;
                final label = date.length >= 5 ? date.substring(5) : date;
                return Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(label,
                      style: TextStyle(fontSize: 9, color: theme.colorScheme.outline)),
                );
              },
            ),
          ),
          topTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          // 默认阈值 10px 会过滤掉距触点较远的序列，导致 tooltip 缺失中间/顶部线、
          // 差值逆推与合计全错。堆叠图各序列同 x 不同 y，必须全量命中。
          touchSpotThreshold: double.infinity,
          // 关闭内置/自定义 touch 回调（不设 touchCallback → handleEvent 提前返回，
          // recognizers 不启动 → 无 FlTapCancel 等事件来清空 tooltip）。
          // 点击/悬停全部由外层 Listener 处理（见 _onPointerGlobal 注释）。
          handleBuiltInTouches: false,
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) => buildStackedTooltipItems(
                series,
                touchedSpots,
                widget.points[touchedSpots.first.x.toInt()].date),
          ),
        ),
        lineBarsData: lineBars,
      ),
    );
  }

  // 回退：avg/min/max 折线+区间（对齐 web 无 breakdown 时的回退图）
  Widget _buildFallbackLineChart(ThemeData theme) {
    final points = widget.points;
    final avg = LineChartBarData(
      spots: [
        for (var i = 0; i < points.length; i++)
          FlSpot(i.toDouble(), points[i].avgCost)
      ],
      color: const Color(0xFFFF9800),
      barWidth: 2,
      isCurved: true,
      dotData: const FlDotData(show: false),
      belowBarData: BarAreaData(
        show: true,
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            const Color(0xFFFF9800).withValues(alpha: 0.25),
            const Color(0xFFFF9800).withValues(alpha: 0.02),
          ],
        ),
      ),
    );
    return LineChart(
      // 挂到 RenderLineChart，供 _onPointerGlobal 计算命中 spot
      chartRendererKey: _chartKey,
      LineChartData(
        // 同主图：自定义 touch 处理下的 tooltip 状态
        showingTooltipIndicators: _tooltipSpots,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (v) =>
              FlLine(color: theme.colorScheme.outlineVariant, strokeWidth: 0.5),
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 44,
              getTitlesWidget: (v, meta) => Text('¥${v.toInt()}',
                  style: TextStyle(fontSize: 9, color: theme.colorScheme.outline)),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: 1,
              getTitlesWidget: (v, meta) {
                final i = v.toInt();
                if (i < 0 || i >= points.length) return const SizedBox.shrink();
                if (!{0, points.length ~/ 2, points.length - 1}.contains(i)) {
                  return const SizedBox.shrink();
                }
                final date = points[i].date;
                final label = date.length >= 5 ? date.substring(5) : date;
                return Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(label,
                      style: TextStyle(fontSize: 9, color: theme.colorScheme.outline)),
                );
              },
            ),
          ),
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
        ),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          // 同主图：默认 10px 阈值会过滤掉距触点较远的线（单线图尤其容易落空），
          // 必须全量命中；关闭 touch 回调，点击/悬停全部由外层 Listener 处理
          touchSpotThreshold: double.infinity,
          handleBuiltInTouches: false,
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (touchedSpots) {
              final idx = touchedSpots.first.x.toInt();
              final date = points[idx].date;
              // 同主图契约：返回条数必须与 touchedSpots 一致（painter 校验不一致
              // throw）。单线图仅命中 1 个 spot → 日期放 text，均价/区间行并入
              // children，渲染效果与原三条 item 一致。
              const plain = TextStyle(color: Colors.white);
              const bold =
                  TextStyle(fontWeight: FontWeight.bold, color: Colors.white);
              return [
                LineTooltipItem('$date\n', bold, children: [
                  TextSpan(
                      text: '均价: ¥${points[idx].avgCost.toStringAsFixed(2)}\n',
                      style: plain),
                  TextSpan(
                      text: '区间: ¥${points[idx].minCost.toStringAsFixed(2)} ~ '
                          '¥${points[idx].maxCost.toStringAsFixed(2)}',
                      style: plain),
                ]),
              ];
            },
          ),
        ),
        lineBarsData: [avg],
      ),
    );
  }

  // 食材标签（点击高亮/取消，对齐 web toggleIngredientHighlight）
  Widget _buildIngredientTags(ThemeData theme) {
    final series = buildStackedSeries(widget.points);
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: series.asMap().entries.map((e) {
        final i = e.key;
        final s = e.value;
        final selected = _highlightIndex == i;
        return ActionChip(
          avatar: Icon(Icons.circle, size: 12, color: s.color),
          label: Text(s.name,
              style: TextStyle(fontWeight: selected ? FontWeight.bold : null)),
          visualDensity: VisualDensity.compact,
          side: BorderSide(
              color: selected ? s.color : theme.colorScheme.outlineVariant),
          onPressed: () => setState(() {
            _highlightIndex = selected ? null : i;
          }),
        );
      }).toList(),
    );
  }
}
