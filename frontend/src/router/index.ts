// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const SITE_NAME = '生计 - 生活成本计算器'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { requiresAuth: false, title: '登录' },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/auth/Register.vue'),
      meta: { requiresAuth: false, title: '注册' },
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
          meta: { title: '价格记录' },
        },
        {
          path: 'prices/quick-fill',
          name: 'quick-fill',
          component: () => import('@/views/prices/QuickFillView.vue'),
          meta: { title: '快速填写' },
        },
        {
          path: 'recipes',
          name: 'recipes',
          component: () => import('@/views/recipes/RecipesView.vue'),
          meta: { title: '菜谱管理' },
        },
        {
          path: 'recipes/:id',
          name: 'recipe-detail',
          component: () => import('@/views/recipes/RecipeDetail.vue'),
          meta: { detailType: '菜谱' },
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
          meta: { title: '商品管理' },
        },
        {
          path: 'data/products/:id',
          name: 'product-detail',
          component: () => import('@/views/products/ProductDetail.vue'),
          meta: { detailType: '商品' },
        },
        {
          path: 'data/ingredients',
          name: 'ingredients',
          component: () => import('@/views/data/IngredientsView.vue'),
          meta: { title: '原料管理' },
        },
        {
          path: 'data/ingredients/:id',
          name: 'ingredient-detail',
          component: () => import('@/views/ingredients/IngredientDetail.vue'),
          meta: { detailType: '原料' },
        },
        {
          path: 'data/merchants',
          name: 'merchants',
          component: () => import('@/views/data/MerchantsView.vue'),
          meta: { title: '商家管理' },
        },
        {
          path: 'data/merchants/:id',
          name: 'merchant-detail',
          component: () => import('@/views/merchants/MerchantDetail.vue'),
          meta: { detailType: '商家' },
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/profile/ProfileView.vue'),
          meta: { title: '个人中心' },
        },
        {
          path: 'admin',
          name: 'admin',
          meta: { adminOnly: true, title: '后台管理' },
          component: () => import('@/views/admin/AdminDashboard.vue'),
        },
        {
          path: 'admin/invite-codes',
          name: 'admin-invite-codes',
          meta: { adminOnly: true, title: '邀请码管理' },
          component: () => import('@/views/admin/InviteCodesView.vue'),
        },
        {
          path: 'admin/units',
          name: 'admin-units',
          meta: { adminOnly: true, title: '单位管理' },
          component: () => import('@/views/admin/UnitsView.vue'),
        },
        {
          path: 'admin/map-settings',
          name: 'admin-map-settings',
          meta: { adminOnly: true, title: '地图配置' },
          component: () => import('@/views/admin/MapSettingsView.vue'),
        },
        {
          path: 'admin/recipe-import',
          name: 'admin-recipe-import',
          meta: { adminOnly: true, title: '菜谱导入' },
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

// 路由切换后自动设置页面标题
router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  if (title) {
    document.title = `${title} - ${SITE_NAME}`
  }
})

export default router
