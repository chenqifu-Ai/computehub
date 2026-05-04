import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../layouts/Layout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '数据看板' }
      },
      {
        path: 'stations',
        name: 'Stations',
        component: () => import('../views/Stations.vue'),
        meta: { title: '充电站管理' }
      },
      {
        path: 'piles',
        name: 'Piles',
        component: () => import('../views/Piles.vue'),
        meta: { title: '充电桩管理' }
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('../views/Orders.vue'),
        meta: { title: '订单管理' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router