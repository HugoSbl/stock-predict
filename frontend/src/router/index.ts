import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { redirectionSure, type Role, TOUS_LES_ROLES } from '@/auth/droits'
import AccesRefuse from '@/pages/AccesRefuse.vue'
import Connexion from '@/pages/Connexion.vue'
import EnConstruction from '@/pages/EnConstruction.vue'
import MotDePasse from '@/pages/MotDePasse.vue'
import TableauDeBord from '@/pages/TableauDeBord.vue'
import Utilisateurs from '@/pages/Utilisateurs.vue'
import { surveillerExpiration, useSessionStore } from '@/stores/session'

declare module 'vue-router' {
  interface RouteMeta {
    title: string
    /** Lot qui livre cet écran (docs/lots.md) — utilisé par la page « en construction ». */
    lot?: number
    /** Rôles autorisés (matrice docs/regles-de-gestion.md). Absent = refusé (sauf page publique). */
    roles?: Role[]
    /** Accessible sans être connecté. */
    public?: boolean
    /** Page affichée sans le menu et l'en-tête. */
    pleinEcran?: boolean
  }
}

const ADMIN: Role[] = ['ADMIN']

// Menu et libellés : D-16 ; droits : matrice RG-13 (le serveur revérifie toujours)
export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'tableau-de-bord', component: TableauDeBord, meta: { title: 'Tableau de bord', lot: 6, roles: TOUS_LES_ROLES } },
  { path: '/stocks', name: 'stocks', component: EnConstruction, meta: { title: 'Stocks', lot: 6, roles: TOUS_LES_ROLES } },
  { path: '/previsions', name: 'previsions', component: EnConstruction, meta: { title: 'Prévisions', lot: 6, roles: TOUS_LES_ROLES } },
  { path: '/alertes', name: 'alertes', component: EnConstruction, meta: { title: 'Alertes', lot: 5, roles: TOUS_LES_ROLES } },
  { path: '/synchronisation', name: 'synchronisation', component: EnConstruction, meta: { title: 'Synchronisation', lot: 3, roles: TOUS_LES_ROLES } },
  { path: '/exports', name: 'exports', component: EnConstruction, meta: { title: 'Exports', lot: 7, roles: TOUS_LES_ROLES } },
  { path: '/utilisateurs', name: 'utilisateurs', component: Utilisateurs, meta: { title: 'Utilisateurs', roles: ADMIN } },
  { path: '/journaux', name: 'journaux', component: EnConstruction, meta: { title: 'Journaux', lot: 7, roles: ADMIN } },
  { path: '/connexion', name: 'connexion', component: Connexion, meta: { title: 'Connexion', public: true, pleinEcran: true } },
  { path: '/mot-de-passe', name: 'mot-de-passe', component: MotDePasse, meta: { title: 'Changer mon mot de passe', roles: TOUS_LES_ROLES, pleinEcran: true } },
  { path: '/acces-refuse', name: 'acces-refuse', component: AccesRefuse, meta: { title: 'Accès refusé', roles: TOUS_LES_ROLES } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes: [...routes, { path: '/:pathMatch(.*)*', redirect: '/' }],
})

router.beforeEach(async (to) => {
  const session = useSessionStore()
  if (!session.chargee) await session.charger()
  const utilisateur = session.utilisateur

  if (to.meta.public) {
    return utilisateur && to.name === 'connexion' ? redirectionSure(to.query.redirect) : true
  }
  if (!utilisateur) {
    return { name: 'connexion', query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
  }
  if (utilisateur.doit_changer_mdp && to.name !== 'mot-de-passe') return { name: 'mot-de-passe' }
  if (!to.meta.roles?.includes(utilisateur.role)) return { name: 'acces-refuse' }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title} — StockPredict`
})

surveillerExpiration(() => {
  const courant = router.currentRoute.value
  if (!courant.meta.public) {
    router.push({ name: 'connexion', query: { redirect: courant.fullPath, expiree: '1' } })
  }
})
