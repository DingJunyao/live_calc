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
      ],
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth !== false)

  if (requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if ((to.name === 'login' || to.name === 'register') && userStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
