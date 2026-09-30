import createClient from 'openapi-fetch'
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
