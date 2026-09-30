import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, messageErreur, quandSessionExpiree } from '@/api/client'
import type { Utilisateur } from '@/auth/droits'

/** Session de l'utilisateur connecté. Le cookie (httpOnly) n'est jamais lisible en JavaScript. */
export const useSessionStore = defineStore('session', () => {
  const utilisateur = ref<Utilisateur | null>(null)
  const chargee = ref(false)

  const role = computed(() => utilisateur.value?.role ?? null)

  async function charger() {
    const { data } = await api.GET('/api/auth/me')
    utilisateur.value = data ?? null
    chargee.value = true
  }

  /** Renvoie null si la connexion réussit, sinon le message à afficher. */
  async function connecter(email: string, motDePasse: string): Promise<string | null> {
    const { data, error, response } = await api.POST('/api/auth/login', {
      body: { email, mot_de_passe: motDePasse },
    })
    if (data) {
      utilisateur.value = data
      return null
    }
    if (response.status === 422) return 'Identifiants incorrects'
    return messageErreur(error, 'Connexion impossible. Réessayez.')
  }

  async function deconnecter() {
    await api.POST('/api/auth/logout')
    utilisateur.value = null
  }

  async function changerMotDePasse(actuel: string, nouveau: string): Promise<string | null> {
    const { error, response } = await api.POST('/api/auth/mot-de-passe', {
      body: { mot_de_passe_actuel: actuel, nouveau_mot_de_passe: nouveau },
    })
    if (response.ok) {
      await charger()
      return null
    }
    return messageErreur(error)
  }

  return { utilisateur, chargee, role, charger, connecter, deconnecter, changerMotDePasse }
})

/** Branché au démarrage : une session expirée renvoie vers l'écran de connexion. */
export function surveillerExpiration(rediriger: () => void) {
  quandSessionExpiree(() => {
    useSessionStore().utilisateur = null
    rediriger()
  })
}
