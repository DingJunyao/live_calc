import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
