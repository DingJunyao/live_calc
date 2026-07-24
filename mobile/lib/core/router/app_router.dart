import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:live_calc/features/home/screens/home_screen.dart';
import 'package:live_calc/features/prices/screens/price_list_screen.dart';
import 'package:live_calc/features/recipes/screens/recipe_list_screen.dart';
import 'package:live_calc/features/profile/screens/profile_screen.dart';
import 'package:go_router/go_router.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

// 认证守卫用 ChangeNotifier + Riverpod
class AuthGuard extends ChangeNotifier {
  bool _isLoggedIn = false;
  bool _hasServerConfig = false;

  bool get isLoggedIn => _isLoggedIn;
  bool get hasServerConfig => _hasServerConfig;

  void setLoggedIn(bool value) {
    _isLoggedIn = value;
    notifyListeners();
  }

  void setServerConfigured(bool value) {
    _hasServerConfig = value;
    notifyListeners();
  }
}

final authGuardProvider = ChangeNotifierProvider<AuthGuard>((ref) {
  return AuthGuard();
});

// 路由构建函数
GoRouter createAppRouter(WidgetRef ref) {
  final authGuard = ref.watch(authGuardProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/home',
    redirect: (context, state) {
      final isLoggedIn = authGuard.isLoggedIn;
      final location = state.matchedLocation;
      final isAuthRoute = location == '/login' || location == '/register' || location == '/server-config';

      if (!isLoggedIn && !isAuthRoute) return '/server-config';
      if (isLoggedIn && isAuthRoute) return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/server-config',
        name: 'server-config',
        builder: (_, __) => const Scaffold(body: Center(child: Text('服务器配置 - 待实现'))),
      ),
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (_, __) => const Scaffold(body: Center(child: Text('登录 - 待实现'))),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        builder: (_, __) => const Scaffold(body: Center(child: Text('注册 - 待实现'))),
      ),
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (_, __, child) => ScaffoldWithNavBar(child: child),
        routes: [
          GoRoute(
            path: '/home',
            name: 'home',
            builder: (_, __) => const HomeScreen(),
          ),
          GoRoute(
            path: '/prices',
            name: 'prices',
            builder: (_, __) => const PriceListScreen(),
          ),
          GoRoute(
            path: '/recipes',
            name: 'recipes',
            builder: (_, __) => const RecipeListScreen(),
          ),
          GoRoute(
            path: '/profile',
            name: 'profile',
            builder: (_, __) => const ProfileScreen(),
          ),
        ],
      ),
    ],
  );
}

/// 底部 Tab + Drawer 的 Scaffold
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
          // 平板/大屏用 NavigationRail
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
