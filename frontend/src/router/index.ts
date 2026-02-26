import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/dashboard/Dashboard.vue').then(m => m.default)
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/Login.vue').then(m => m.default)
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/Register.vue').then(m => m.default)
  },
  {
    path: '/products',
    name: 'products',
    component: () => import('@/views/products/ProductList.vue').then(m => m.default)
  },
  {
    path: '/recipes',
    name: 'recipes',
    component: () => import('@/views/recipes/RecipeList.vue').then(m => m.default)
  },
  {
    path: '/locations',
    name: 'locations',
    component: () => import('@/views/locations/LocationMap.vue').then(m => m.default)
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/views/reports/ReportOverview.vue').then(m => m.default)
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/admin/AdminPanel.vue').then(m => m.default)
  },
  {
    path: '/admin/users',
    name: 'userManagement',
    component: () => import('@/views/admin/UserManagement.vue').then(m => m.default)
  },
  {
    path: '/admin/invite-codes',
    name: 'inviteCodeManagement',
    component: () => import('@/views/admin/InviteCodeManager.vue').then(m => m.default)
  },
  {
    path: '/admin/recipe-import',
    name: 'recipeImport',
    component: () => import('@/views/admin/RecipeImport.vue').then(m => m.default)
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  // 检查是否已登录
  if (!userStore.isLoggedIn) {
    // 尝试从本地存储初始化用户信息
    const isValid = await userStore.initializeUserFromStorage();

    if (!isValid && to.name !== 'login' && to.name !== 'register') {
      // 如果令牌无效且不在登录/注册页面，跳转到登录页
      next({ name: 'login' })
      return
    }
  }

  // 如果用户已登录，但访问的是登录或注册页面，重定向到首页
  if ((to.name === 'login' || to.name === 'register') && userStore.isLoggedIn) {
    next({ name: 'dashboard' })
    return
  }

  next()
})

export default router
