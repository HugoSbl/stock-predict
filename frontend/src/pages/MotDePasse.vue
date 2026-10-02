<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import ChampFormulaire from '@/components/ChampFormulaire.vue'
import { Button } from '@/components/ui/button'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const router = useRouter()

const force = computed(() => session.utilisateur?.doit_changer_mdp ?? false)
const actuel = ref('')
const nouveau = ref('')
const confirmation = ref('')
const erreurs = ref<{ actuel?: string; nouveau?: string; confirmation?: string }>({})
const erreurServeur = ref<string | null>(null)
const enCours = ref(false)

const AIDE = 'Au moins 12 caractères, mélangeant lettres et chiffres ou symboles.'

async function soumettre() {
  erreurServeur.value = null
  erreurs.value = {
    actuel: actuel.value ? undefined : 'Saisissez votre mot de passe actuel.',
    nouveau: nouveau.value.length >= 12 ? undefined : 'Au moins 12 caractères.',
    confirmation: confirmation.value === nouveau.value ? undefined : 'Les deux saisies ne correspondent pas.',
  }
  if (Object.values(erreurs.value).some(Boolean)) return
  enCours.value = true
  const erreur = await session.changerMotDePasse(actuel.value, nouveau.value)
  enCours.value = false
  if (erreur) {
    erreurServeur.value = erreur
    return
  }
  await router.replace('/')
}

async function seDeconnecter() {
  await session.deconnecter()
  await router.replace({ name: 'connexion' })
}
</script>

<template>
  <main id="contenu" class="grid min-h-svh place-items-center bg-muted/60 px-4 py-10">
    <section aria-labelledby="titre-mdp" class="w-full max-w-sm rounded-xl border bg-card px-6 py-8 shadow-sm sm:px-8">
      <h1 id="titre-mdp" class="text-xl font-semibold">Changer mon mot de passe</h1>
      <p v-if="force" class="mt-2 text-sm text-muted-foreground">
        Votre mot de passe a été réinitialisé par un administrateur : choisissez-en un nouveau pour continuer.
      </p>

      <form novalidate class="mt-6 grid gap-4" @submit.prevent="soumettre">
        <ChampFormulaire id="mdp-actuel" v-model="actuel" label="Mot de passe actuel" type="password"
          autocomplete="current-password" :erreur="erreurs.actuel" requis revelable />
        <ChampFormulaire id="mdp-nouveau" v-model="nouveau" label="Nouveau mot de passe" type="password"
          autocomplete="new-password" :aide="AIDE" :erreur="erreurs.nouveau" requis revelable />
        <ChampFormulaire id="mdp-confirmation" v-model="confirmation" label="Confirmation du nouveau mot de passe"
          type="password" autocomplete="new-password" :erreur="erreurs.confirmation" requis revelable />

        <div v-if="erreurServeur" role="alert" class="rounded-md border border-status-critical/30 bg-status-critical/5 px-3 py-2 text-sm text-status-critical">
          {{ erreurServeur }}
        </div>

        <Button type="submit" class="h-10" :disabled="enCours">
          {{ enCours ? 'Enregistrement…' : 'Enregistrer' }}
        </Button>
        <Button v-if="force" type="button" variant="ghost" @click="seDeconnecter">Se déconnecter</Button>
        <Button v-else type="button" variant="ghost" @click="router.back()">Annuler</Button>
      </form>
    </section>
  </main>
</template>
