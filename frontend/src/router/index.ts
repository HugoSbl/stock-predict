import { createRouter, createWebHistory } from 'vue-router'
import EnConstruction from '@/pages/EnConstruction.vue'
import TableauDeBord from '@/pages/TableauDeBord.vue'

declare module 'vue-router' {
  interface RouteMeta {
    title: string
    /** Lot qui livre cet écran (docs/lots.md) — utilisé par la page « en construction ». */
    lot?: number
  }
}

// Menu et libellés : D-16
export const routes = [
  { path: '/', name: 'tableau-de-bord', component: TableauDeBord, meta: { title: 'Tableau de bord', lot: 6 } },
  { path: '/stocks', name: 'stocks', component: EnConstruction, meta: { title: 'Stocks', lot: 6 } },
  { path: '/previsions', name: 'previsions', component: EnConstruction, meta: { title: 'Prévisions', lot: 6 } },
  { path: '/alertes', name: 'alertes', component: EnConstruction, meta: { title: 'Alertes', lot: 5 } },
  { path: '/synchronisation', name: 'synchronisation', component: EnConstruction, meta: { title: 'Synchronisation', lot: 3 } },
  { path: '/exports', name: 'exports', component: EnConstruction, meta: { title: 'Exports', lot: 7 } },
  { path: '/utilisateurs', name: 'utilisateurs', component: EnConstruction, meta: { title: 'Utilisateurs', lot: 7 } },
  { path: '/journaux', name: 'journaux', component: EnConstruction, meta: { title: 'Journaux', lot: 7 } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: [...routes, { path: '/:pathMatch(.*)*', redirect: '/' }],
})

router.afterEach((to) => {
  document.title = `${to.meta.title} — StockPredict`
})
