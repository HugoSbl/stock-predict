import type { components } from '@/api/schema'

export type Role = components['schemas']['Role']
export type Utilisateur = components['schemas']['UtilisateurOut']

export const TOUS_LES_ROLES: Role[] = ['RESPONSABLE', 'ANALYSTE', 'ADMIN']

export const LIBELLES_ROLES: Record<Role, string> = {
  RESPONSABLE: 'Responsable logistique',
  ANALYSTE: 'Data analyst',
  ADMIN: 'Administrateur',
}

/** Chemin de redirection après connexion : uniquement interne (pas de redirection ouverte). */
export function redirectionSure(valeur: unknown): string {
  return typeof valeur === 'string' && valeur.startsWith('/') && !valeur.startsWith('//')
    ? valeur
    : '/'
}
