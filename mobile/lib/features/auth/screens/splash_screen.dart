import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../../../shared/widgets/loading_indicator.dart';

/// Shown while the app restores its session (saved token / auto-login) so the
/// user never bounces through the server-config or login screens during start.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: SizedBox(
                width: 80,
                height: 80,
                child: SvgPicture.asset('assets/images/logo.svg'),
              ),
            ),
            const SizedBox(height: 16),
            Text('生计',
                style: theme.textTheme.headlineMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 32),
            const LoadingIndicator(message: '登录中…'),
          ],
        ),
      ),
    );
  }
}
