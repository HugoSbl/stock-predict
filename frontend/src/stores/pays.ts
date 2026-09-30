import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type CodePays = 'FR' | 'DE' | 'TOUS'

export const PAYS: { code: CodePays; libelle: string }[] = [
  { code: 'FR', libelle: 'France' },
  { code: 'DE', libelle: 'Allemagne' },
  { code: 'TOUS', libelle: 'Tous pays' },
]

const CLE = 'stockpredict.pays'

function lireSession(): CodePays {
  try {
    const valeur = sessionStorage.getItem(CLE)
    if (PAYS.some((p) => p.code === valeur)) return valeur as CodePays
  } catch {
    // stockage indisponible (navigation privée…) : valeur par défaut
  }
  return 'FR'
}

/** Contexte pays global (UC-05) : filtre toutes les vues, persiste pendant la session. */
export const usePaysStore = defineStore('pays', () => {
  const code = ref<CodePays>(lireSession())
  watch(code, (valeur) => {
    try {
      sessionStorage.setItem(CLE, valeur)
    } catch {
      // ignoré
    }
  })
  return { code }
})
