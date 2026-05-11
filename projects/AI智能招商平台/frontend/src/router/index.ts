import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'Login', component: () => import('@/views/LoginView.vue'), meta: { requiresAuth: false } },
  {
    path: '/', component: () => import('@/views/LayoutView.vue'), redirect: '/dashboard', meta: { requiresAuth: true },
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/DashboardView.vue') },
      { path: 'brand', name: 'Brand', component: () => import('@/views/BrandView.vue') },
      { path: 'product', name: 'Product', component: () => import('@/views/ProductView.vue') },
      { path: 'qa', name: 'QA', component: () => import('@/views/QAView.vue') },
      { path: 'device', name: 'Device', component: () => import('@/views/DeviceView.vue') },
      { path: 'user', name: 'User', component: () => import('@/views/UserView.vue') },
      { path: 'settings', name: 'Settings', component: () => import('@/views/SettingsView.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth !== false && !authStore.token) next('/login')
  else next()
})

export default router
