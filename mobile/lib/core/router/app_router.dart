import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/home/screens/home_screen.dart';
import '../../features/prices/screens/price_list_screen.dart';
import '../../features/prices/screens/quick_fill_screen.dart';
import '../../features/recipes/screens/recipe_list_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/auth/providers/auth_provider.dart';
import '../../features/auth/screens/server_config_screen.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/register_screen.dart';
import 'route_names.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

GoRouter createAppRouter(WidgetRef ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/home',
    redirect: (context, state) {
      final isLoggedIn = authState.status == AuthStatus.authenticated;
      final location = state.matchedLocation;
      final isAuthRoute = location == '/login' || location == '/register' || location == '/server-config';

      if (!isLoggedIn && !isAuthRoute) return '/server-config';
      if (isLoggedIn && isAuthRoute) return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/server-config',
        name: RouteNames.serverConfig,
        builder: (_, __) => const ServerConfigScreen(),
      ),
      GoRoute(
        path: '/login',
        name: RouteNames.login,
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        name: RouteNames.register,
        builder: (_, __) => const RegisterScreen(),
      ),
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (_, __, child) => ScaffoldWithNavBar(child: child),
        routes: [
          GoRoute(
            path: '/home',
            name: RouteNames.home,
            builder: (_, __) => const HomeScreen(),
          ),
          GoRoute(
            path: '/prices',
            name: RouteNames.prices,
            builder: (_, __) => const PriceListScreen(),
          ),
          GoRoute(
            path: '/prices/quick-fill',
            name: 'quick-fill',
            builder: (_, __) => const QuickFillScreen(),
          ),
          GoRoute(
            path: '/recipes',
            name: RouteNames.recipes,
            builder: (_, __) => const RecipeListScreen(),
          ),
          GoRoute(
            path: '/profile',
            name: RouteNames.profile,
            builder: (_, __) => const ProfileScreen(),
          ),
        ],
      ),
    ],
  );
}

class ScaffoldWithNavBar extends ConsumerStatefulWidget {
  final Widget child;
  const ScaffoldWithNavBar({super.key, required this.child});

  @override
  ConsumerState<ScaffoldWithNavBar> createState() => _ScaffoldWithNavBarState();
}

class _ScaffoldWithNavBarState extends ConsumerState<ScaffoldWithNavBar> {
  int _selectedIndex = 0;
  static const _tabRoutes = ['/home', '/prices', '/recipes', '/profile'];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final tabIndex = _tabRoutes.indexOf(location);
    if (tabIndex >= 0 && tabIndex != _selectedIndex) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() => _selectedIndex = tabIndex);
      });
    }

    return Scaffold(
      drawer: NavigationDrawer(
        onDestinationSelected: (i) {
          Navigator.of(context).pop();
        },
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
            child: Text('生记', style: Theme.of(context).textTheme.titleLarge),
          ),
          const NavigationDrawerDestination(icon: Icon(Icons.search), label: Text('搜索')),
          const Divider(),
          const NavigationDrawerDestination(icon: Icon(Icons.science_outlined), label: Text('原料管理')),
          const NavigationDrawerDestination(icon: Icon(Icons.inventory_2_outlined), label: Text('商品管理')),
          const NavigationDrawerDestination(icon: Icon(Icons.store_outlined), label: Text('商家管理')),
          const NavigationDrawerDestination(icon: Icon(Icons.map_outlined), label: Text('商家地图')),
          const NavigationDrawerDestination(icon: Icon(Icons.bar_chart_outlined), label: Text('报表')),
          const NavigationDrawerDestination(icon: Icon(Icons.settings_outlined), label: Text('设置')),
        ],
      ),
      body: Row(
        children: [
          if (MediaQuery.of(context).size.width >= 600)
            NavigationRail(
              selectedIndex: _selectedIndex,
              onDestinationSelected: (i) => _onTabSelected(context, i),
              labelType: NavigationRailLabelType.all,
              destinations: const [
                NavigationRailDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: Text('首页')),
                NavigationRailDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: Text('记价')),
                NavigationRailDestination(icon: Icon(Icons.restaurant_outlined), selectedIcon: Icon(Icons.restaurant), label: Text('菜谱')),
                NavigationRailDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: Text('我的')),
              ],
            ),
          Expanded(child: widget.child),
        ],
      ),
      bottomNavigationBar: MediaQuery.of(context).size.width < 600
          ? NavigationBar(
              selectedIndex: _selectedIndex,
              onDestinationSelected: (i) => _onTabSelected(context, i),
              destinations: const [
                NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: '首页'),
                NavigationDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: '记价'),
                NavigationDestination(icon: Icon(Icons.restaurant_outlined), selectedIcon: Icon(Icons.restaurant), label: '菜谱'),
                NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: '我的'),
              ],
            )
          : null,
    );
  }

  void _onTabSelected(BuildContext context, int index) {
    setState(() => _selectedIndex = index);
    context.go(_tabRoutes[index]);
  }
}
