import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('./views/Dashboard.vue')
  },
  {
    path: '/stocks',
    name: 'StockList',
    component: () => import('./views/StockList.vue')
  },
  {
    path: '/stock/:code',
    name: 'StockDetail',
    component: () => import('./views/StockDetail.vue')
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: () => import('./views/Backtest.vue')
  },
  {
    path: '/indicators',
    name: 'Indicators',
    component: () => import('./views/Indicators.vue')
  },
  {
    path: '/indicators-detail',
    name: 'IndicatorsDetail',
    component: () => import('./views/IndicatorsDetail.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
