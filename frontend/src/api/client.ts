import createClient, { type Middleware } from 'openapi-fetch'
import type { paths } from './schema'

/**
 * Client typé de l'API StockPredict, généré depuis l'OpenAPI FastAPI (`npm run gen:api`).
 * Ne jamais écrire les types d'API à la main.
 */
export const api = createClient<paths>({
  baseUrl: '',
  credentials: 'same-origin',
  // Anti-CSRF (D-12) : toute requête mutante doit porter cet en-tête
  headers: { 'X-Requested-With': 'StockPredict' },
})

let surSessionExpiree: (() => void) | null = null

/** Appelé par le store de session : réaction à une session expirée pendant la navigation. */
export function quandSessionExpiree(callback: () => void) {
  surSessionExpiree = callback
}

const detectionSessionExpiree: Middleware = {
  onResponse({ request, response }) {
    const url = new URL(request.url, window.location.origin)
    if (response.status === 401 && !url.pathname.startsWith('/api/auth/')) surSessionExpiree?.()
  },
}
api.use(detectionSessionExpiree)

/** Message d'erreur lisible depuis une réponse d'erreur FastAPI. */
export function messageErreur(erreur: unknown, parDefaut = 'Une erreur est survenue.'): string {
  const detail = (erreur as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Saisie invalide.'
  return parDefaut
}
