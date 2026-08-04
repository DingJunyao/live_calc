import 'package:flutter/material.dart';
import '../repositories/recipe_repository.dart';

/// 成本趋势图表：min/max 区间带 + avg 折线 + 触摸 tooltip + 区间筛选。
/// 与 Web 端 PriceTrendChart 体验一致（无第三方图表库依赖）。
class CostTrendChart extends StatefulWidget {
  final List<CostHistoryPoint> points;
  final bool loading;
  final String unit;
  final Color color;
  final ValueChanged<int>? onRangeChange;

  const CostTrendChart({
    super.key,
    required this.points,
    this.loading = false,
    this.unit = '元',
    this.color = const Color(0xFFFF9800),
    this.onRangeChange,
  });

  @override
  State<CostTrendChart> createState() => _CostTrendChartState();
}

enum _Range { week, month, quarter }

class _CostTrendChartState extends State<CostTrendChart> {
  _Range _selected = _Range.month;
  int? _touchIndex;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.show_chart, color: widget.color, size: 20),
            const SizedBox(width: 8),
            Text('成本趋势',
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const Spacer(),
            _buildRangeToggle(theme),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(height: 200, child: _buildBody(theme)),
      ],
    );
  }

  Widget _buildRangeToggle(ThemeData theme) {
    const labels = {'week': '周', 'month': '月', 'quarter': '季'};
    return SegmentedButton<_Range>(
      style: const ButtonStyle(
        visualDensity: VisualDensity.compact,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      segments: _Range.values
          .map((r) => ButtonSegment(value: r, label: Text(labels[r.name]!)))
          .toList(),
      selected: {_selected},
      onSelectionChanged: (s) {
        setState(() => _selected = s.first);
        final days = switch (_selected) {
          _Range.week => 7,
          _Range.month => 30,
          _Range.quarter => 90,
        };
        widget.onRangeChange?.call(days);
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
            Icon(Icons.show_chart, size: 48, color: theme.colorScheme.outline),
            const SizedBox(height: 8),
            Text('暂无成本历史数据',
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.outline)),
          ],
        ),
      );
    }
    return _Chart(
      points: widget.points,
      color: widget.color,
      touchIndex: _touchIndex,
      onTouch: (i) => setState(() => _touchIndex = i),
    );
  }
}

class _Chart extends StatelessWidget {
  final List<CostHistoryPoint> points;
  final Color color;
  final int? touchIndex;
  final ValueChanged<int?> onTouch;

  const _Chart({
    required this.points,
    required this.color,
    required this.touchIndex,
    required this.onTouch,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onPanDown: (d) => _handleTouch(d.localPosition, constraints.biggest),
          onPanUpdate: (d) =>
              _handleTouch(d.localPosition, constraints.biggest),
          onPanEnd: (_) => onTouch(null),
          child: Stack(
            children: [
              CustomPaint(
                size: Size.infinite,
                painter: _TrendPainter(
                  points: points,
                  color: color,
                  touchIndex: touchIndex,
                  gridColor: Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
              if (touchIndex != null && touchIndex! < points.length)
                Positioned(
                  left: 0,
                  right: 0,
                  top: 0,
                  child: _Tooltip(
                      points: points, index: touchIndex!, color: color),
                ),
            ],
          ),
        );
      },
    );
  }

  void _handleTouch(Offset local, Size size) {
    if (points.length < 2) return;
    const plotLeft = 44.0;
    final plotW = size.width - plotLeft - 8;
    final dx = plotW / (points.length - 1);
    final rel = (local.dx - plotLeft) / dx;
    final idx = rel.round().clamp(0, points.length - 1);
    onTouch(idx);
  }
}

class _Tooltip extends StatelessWidget {
  final List<CostHistoryPoint> points;
  final int index;
  final Color color;
  const _Tooltip(
      {required this.points, required this.index, required this.color});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final p = points[index];
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: theme.colorScheme.inverseSurface,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(p.date,
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.onInverseSurface)),
            const SizedBox(height: 2),
            Text('均价 ¥${p.avgCost.toStringAsFixed(2)}',
                style: theme.textTheme.labelMedium?.copyWith(
                    color: theme.colorScheme.onInverseSurface,
                    fontWeight: FontWeight.bold)),
            Text(
                '区间 ¥${p.minCost.toStringAsFixed(2)} ~ ¥${p.maxCost.toStringAsFixed(2)}',
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.onInverseSurface)),
          ],
        ),
      ),
    );
  }
}

class _TrendPainter extends CustomPainter {
  final List<CostHistoryPoint> points;
  final Color color;
  final int? touchIndex;
  final Color gridColor;

  _TrendPainter({
    required this.points,
    required this.color,
    required this.touchIndex,
    required this.gridColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    const plotLeft = 44.0;
    const plotTop = 8.0;
    final plotRight = size.width - 8;
    final plotBottom = size.height - 24;
    final plotW = plotRight - plotLeft;
    final plotH = plotBottom - plotTop;

    double minV = double.infinity;
    double maxV = double.negativeInfinity;
    for (final p in points) {
      if (p.minCost < minV) minV = p.minCost;
      if (p.maxCost > maxV) maxV = p.maxCost;
    }
    if (maxV == minV) {
      maxV += 1;
      minV -= 1;
    }
    final pad = (maxV - minV) * 0.08;
    minV -= pad;
    maxV += pad;
    final yScale = plotH / (maxV - minV);

    double xAt(int i) => plotLeft + (plotW / (points.length - 1)) * i;
    double yAt(double v) => plotBottom - (v - minV) * yScale;

    final gridPaint = Paint()
      ..color = gridColor
      ..strokeWidth = 0.5;
    for (var i = 0; i <= 4; i++) {
      final v = minV + (maxV - minV) * i / 4;
      final y = yAt(v);
      canvas.drawLine(Offset(plotLeft, y), Offset(plotRight, y), gridPaint);
      _text(canvas, '¥${v.toStringAsFixed(0)}', Offset(2, y - 7), gridColor, 9);
    }

    // min/max 区间带
    final bandPath = Path();
    for (var i = 0; i < points.length; i++) {
      final x = xAt(i);
      final y = yAt(points[i].maxCost);
      if (i == 0) {
        bandPath.moveTo(x, y);
      } else {
        bandPath.lineTo(x, y);
      }
    }
    for (var i = points.length - 1; i >= 0; i--) {
      bandPath.lineTo(xAt(i), yAt(points[i].minCost));
    }
    bandPath.close();
    canvas.drawPath(
      bandPath,
      Paint()
        ..color = color.withValues(alpha: 0.15)
        ..style = PaintingStyle.fill,
    );

    // min/max 虚线
    final dashPaint = Paint()
      ..color = color.withValues(alpha: 0.5)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    _drawDashed(canvas, _pathOf(points, xAt, (p) => p.minCost, yAt), dashPaint);
    _drawDashed(canvas, _pathOf(points, xAt, (p) => p.maxCost, yAt), dashPaint);

    // 均价折线
    final linePaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..isAntiAlias = true;
    canvas.drawPath(_pathOf(points, xAt, (p) => p.avgCost, yAt), linePaint);

    // 触摸十字线 + 高亮点
    if (touchIndex != null && touchIndex! >= 0 && touchIndex! < points.length) {
      final x = xAt(touchIndex!);
      canvas.drawLine(
        Offset(x, plotTop),
        Offset(x, plotBottom),
        Paint()
          ..color = gridColor.withValues(alpha: 0.8)
          ..strokeWidth = 1,
      );
      canvas.drawCircle(
        Offset(x, yAt(points[touchIndex!].avgCost)),
        4,
        Paint()..color = color,
      );
    }

    // X 轴日期（首/中/尾）
    final idxList = [0, (points.length / 2).floor(), points.length - 1];
    for (final i in idxList) {
      final date = points[i].date;
      final label = date.length >= 5 ? date.substring(5) : date;
      _text(canvas, label, Offset(xAt(i) - 12, plotBottom + 6), gridColor, 9);
    }
  }

  Path _pathOf(List<CostHistoryPoint> pts, double Function(int) xAt,
      double Function(CostHistoryPoint) sel, double Function(double) yAt) {
    final path = Path();
    for (var i = 0; i < pts.length; i++) {
      final x = xAt(i);
      final y = yAt(sel(pts[i]));
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    return path;
  }

  void _drawDashed(Canvas canvas, Path path, Paint paint) {
    for (final metric in path.computeMetrics()) {
      double dist = 0;
      while (dist < metric.length) {
        final next = dist + 4;
        canvas.drawPath(metric.extractPath(dist, next), paint);
        dist += 7;
      }
    }
  }

  void _text(Canvas canvas, String s, Offset pos, Color color, double size) {
    final tp = TextPainter(
      text: TextSpan(text: s, style: TextStyle(color: color, fontSize: size)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, pos);
  }

  @override
  bool shouldRepaint(covariant _TrendPainter old) =>
      old.points != points ||
      old.touchIndex != touchIndex ||
      old.color != color;
}
