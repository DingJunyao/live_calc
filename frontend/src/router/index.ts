// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/auth/Register.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/prices',
        },
        {
          path: 'prices',
          name: 'prices',
          component: () => import('@/views/prices/PricesView.vue'),
        },
        {
          path: 'recipes',
          name: 'recipes',
          component: () => import('@/views/recipes/RecipesView.vue'),
        },
        {
          path: 'recipes/:id',
          name: 'recipe-detail',
          component: () => import('@/views/recipes/RecipeDetail.vue'),
        },
        {
          path: 'data',
          name: 'data',
          redirect: '/data/products',
        },
        {
          path: 'data/products',
          name: 'products',
          component: () => import('@/views/data/ProductsView.vue'),
        },
        {
          path: 'data/products/:id',
          name: 'product-detail',
          component: () => import('@/views/products/ProductDetail.vue'),
        },
        {
          path: 'data/ingredients',
          name: 'ingredients',
          component: () => import('@/views/data/IngredientsView.vue'),
        },
        {
          path: 'data/ingredients/:id',
          name: 'ingredient-detail',
          component: () => import('@/views/ingredients/IngredientDetail.vue'),
        },
        {
          path: 'data/merchants',
          name: 'merchants',
          component: () => import('@/views/data/MerchantsView.vue'),
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/profile/ProfileView.vue'),
        },
        {
          path: 'admin',
          name: 'admin',
          meta: { adminOnly: true },
          component: () => import('@/views/admin/AdminDashboard.vue'),
        },
        {
          path: 'admin/invite-codes',
          name: 'admin-invite-codes',
          meta: { adminOnly: true },
          component: () => import('@/views/admin/InviteCodesView.vue'),
        },
        {
          path: 'admin/units',
          name: 'admin-units',
          meta: { adminOnly: true },
          component: () => import('@/views/admin/UnitsView.vue'),
        },
        {
          path: 'admin/map-settings',
          name: 'admin-map-settings',
          meta: { adminOnly: true },
          component: () => import('@/views/admin/MapSettingsView.vue'),
        },
        {
          path: 'admin/recipe-import',
          name: 'admin-recipe-import',
          meta: { adminOnly: true },
          component: () => import('@/views/admin/RecipeImportView.vue'),
        },
      ],
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth !== false)
  const adminOnly = to.matched.some((record) => record.meta.adminOnly === true)

  if (requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (adminOnly && !userStore.user?.is_admin) {
    // 非管理员访问管理页面，重定向到首页
    next('/')
  } else if ((to.name === 'login' || to.name === 'register') && userStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
