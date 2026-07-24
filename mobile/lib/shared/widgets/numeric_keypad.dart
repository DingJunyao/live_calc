import 'package:flutter/material.dart';

/// Calculator-style numeric keypad for price/quantity input
class NumericKeypad extends StatelessWidget {
  final ValueChanged<String> onKeyTap;
  final VoidCallback onConfirm;

  const NumericKeypad({
    super.key,
    required this.onKeyTap,
    required this.onConfirm,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildRow(['7', '8', '9', '⌫']),
          _buildRow(['4', '5', '6', 'C']),
          _buildRow(['1', '2', '3', '✓']),
          _buildBottomRow(),
        ],
      ),
    );
  }

  Widget _buildRow(List<String> keys) {
    return Row(
      children: keys.map((key) => _KeyButton(
        label: key,
        isAction: key == '⌫' || key == 'C' || key == '✓',
        isConfirm: key == '✓',
        onTap: () => onKeyTap(key),
      )).toList(),
    );
  }

  Widget _buildBottomRow() {
    return Row(
      children: [
        Expanded(flex: 2, child: _KeyButton(label: '0', onTap: () => onKeyTap('0'))),
        _KeyButton(label: '.', onTap: () => onKeyTap('.')),
        Expanded(flex: 1, child: _KeyButton(
          label: '✓',
          isAction: true,
          isConfirm: true,
          onTap: onConfirm,
        )),
      ],
    );
  }
}

class _KeyButton extends StatelessWidget {
  final String label;
  final bool isAction;
  final bool isConfirm;
  final VoidCallback onTap;

  const _KeyButton({
    required this.label,
    required this.onTap,
    this.isAction = false,
    this.isConfirm = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bgColor = isConfirm
        ? theme.colorScheme.primary
        : isAction
            ? theme.colorScheme.surfaceContainerHigh
            : theme.colorScheme.surface;
    final fgColor = isConfirm
        ? theme.colorScheme.onPrimary
        : theme.colorScheme.onSurface;

    return Expanded(
      child: AspectRatio(
        aspectRatio: 1.3,
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Material(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
            child: InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: onTap,
              child: Center(
                child: Text(
                  label,
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w500,
                    color: fgColor,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
