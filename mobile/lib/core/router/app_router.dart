import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/home/screens/home_screen.dart';
import '../../features/prices/screens/price_list_screen.dart';
import '../../features/prices/screens/quick_fill_screen.dart';
import '../../features/recipes/screens/recipe_list_screen.dart';
import '../../features/recipes/screens/recipe_detail_screen.dart';
import '../../features/recipes/screens/recipe_analysis_screen.dart';
import '../../features/ingredients/screens/ingredient_list_screen.dart';
import '../../features/ingredients/screens/ingredient_detail_screen.dart';
import '../../features/products/screens/product_list_screen.dart';
import '../../features/products/screens/product_detail_screen.dart';
import '../../features/merchants/screens/merchant_list_screen.dart';
import '../../features/merchants/screens/merchant_detail_screen.dart';
import '../../features/merchants/screens/merchant_map_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/profile/screens/my_proposals_screen.dart';
import '../../features/profile/screens/my_places_screen.dart';
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
            path: '/recipes/:id',
            name: 'recipe-detail',
            builder: (_, state) => RecipeDetailScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/recipes/:id/analysis',
            name: 'recipe-analysis',
            builder: (_, state) => RecipeAnalysisScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/ingredients',
            name: RouteNames.ingredients,
            builder: (_, __) => const IngredientListScreen(),
          ),
          GoRoute(
            path: '/ingredients/:id',
            name: 'ingredient-detail',
            builder: (_, state) => IngredientDetailScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/products',
            name: RouteNames.products,
            builder: (_, __) => const ProductListScreen(),
          ),
          GoRoute(
            path: '/products/:id',
            name: 'product-detail',
            builder: (_, state) => ProductDetailScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/merchants',
            name: RouteNames.merchants,
            builder: (_, __) => const MerchantListScreen(),
          ),
          GoRoute(
            path: '/merchants/:id',
            name: 'merchant-detail',
            builder: (_, state) => MerchantDetailScreen(
              id: int.parse(state.pathParameters['id']!),
            ),
          ),
          GoRoute(
            path: '/profile',
            name: RouteNames.profile,
            builder: (_, __) => const ProfileScreen(),
          ),
          GoRoute(
            path: '/profile/proposals',
            name: RouteNames.myProposals,
            builder: (_, __) => const MyProposalsScreen(),
          ),
          GoRoute(
            path: '/profile/places',
            name: RouteNames.myPlaces,
            builder: (_, __) => const MyPlacesScreen(),
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
            child: Text('\u751f\u8bb0', style: Theme.of(context).textTheme.titleLarge),
          ),
          const NavigationDrawerDestination(icon: Icon(Icons.search), label: Text('\u641c\u7d22')),
          const Divider(),
          const NavigationDrawerDestination(icon: Icon(Icons.science_outlined), label: Text('\u539f\u6599\u7ba1\u7406')),
          const NavigationDrawerDestination(icon: Icon(Icons.inventory_2_outlined), label: Text('\u5546\u54c1\u7ba1\u7406')),
          const NavigationDrawerDestination(icon: Icon(Icons.store_outlined), label: Text('\u5546\u5bb6\u7ba1\u7406')),
          const NavigationDrawerDestination(icon: Icon(Icons.map_outlined), label: Text('\u5546\u5bb6\u5730\u56fe')),
          const NavigationDrawerDestination(icon: Icon(Icons.bar_chart_outlined), label: Text('\u62a5\u8868')),
          const NavigationDrawerDestination(icon: Icon(Icons.settings_outlined), label: Text('\u8bbe\u7f6e')),
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
                NavigationRailDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: Text('\u9996\u9875')),
                NavigationRailDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: Text('\u8bb0\u4ef7')),
                NavigationRailDestination(icon: Icon(Icons.restaurant_outlined), selectedIcon: Icon(Icons.restaurant), label: Text('\u83dc\u8c31')),
                NavigationRailDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: Text('\u6211\u7684')),
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
                NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: '\u9996\u9875'),
                NavigationDestination(icon: Icon(Icons.receipt_long_outlined), selectedIcon: Icon(Icons.receipt_long), label: '\u8bb0\u4ef7'),
                NavigationDestination(icon: Icon(Icons.restaurant_outlined), selectedIcon: Icon(Icons.restaurant), label: '\u83dc\u8c31'),
                NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: '\u6211\u7684'),
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


