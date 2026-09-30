<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ChampFormulaire from '@/components/ChampFormulaire.vue'
import { Button } from '@/components/ui/button'
import { redirectionSure } from '@/auth/droits'
import { useSessionStore } from '@/stores/session'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()

const email = ref('')
const motDePasse = ref('')
const erreurEmail = ref<string | null>(null)
const erreurMotDePasse = ref<string | null>(null)
const erreurServeur = ref<string | null>(route.query.expiree ? 'Votre session a expiré. Reconnectez-vous.' : null)
const enCours = ref(false)
const aideOubliVisible = ref(false)

const champEmail = ref<InstanceType<typeof ChampFormulaire> | null>(null)
const champMotDePasse = ref<InstanceType<typeof ChampFormulaire> | null>(null)
const alerte = ref<HTMLElement | null>(null)

function valider(): boolean {
  erreurEmail.value = !email.value.trim()
    ? "Saisissez votre adresse e-mail."
    : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())
      ? null
      : "Format attendu : prenom.nom@globalretail.com"
  erreurMotDePasse.value = motDePasse.value ? null : 'Saisissez votre mot de passe.'
  if (erreurEmail.value) champEmail.value?.focus()
  else if (erreurMotDePasse.value) champMotDePasse.value?.focus()
  return !erreurEmail.value && !erreurMotDePasse.value
}

async function soumettre() {
  erreurServeur.value = null
  if (!valider()) return
  enCours.value = true
  const erreur = await session.connecter(email.value.trim(), motDePasse.value)
  enCours.value = false
  if (erreur) {
    erreurServeur.value = erreur
    motDePasse.value = ''
    await nextTick()
    alerte.value?.focus()
    return
  }
  await router.replace(redirectionSure(route.query.redirect))
}
</script>

<template>
  <main id="contenu" class="grid min-h-svh place-items-center bg-muted/60 px-4 py-10">
    <div class="w-full max-w-sm">
      <section
        aria-labelledby="titre-connexion"
        class="rounded-xl border bg-card px-6 py-8 shadow-sm sm:px-8"
      >
        <header class="mb-6 text-center">
          <h1 id="titre-connexion" class="flex items-center justify-center gap-2 text-2xl font-semibold text-primary">
            <span aria-hidden="true" class="inline-block size-3.5 rounded-[3px] bg-primary" />
            StockPredict
          </h1>
          <p class="mt-1 text-sm text-muted-foreground">Plateforme de prédiction des stocks</p>
        </header>

        <form novalidate class="grid gap-4" aria-describedby="mention-journal" @submit.prevent="soumettre">
          <ChampFormulaire
            id="email"
            ref="champEmail"
            v-model="email"
            label="Adresse e-mail"
            type="email"
            autocomplete="username"
            aide="Format : prenom.nom@globalretail.com"
            :erreur="erreurEmail"
            requis
          />
          <ChampFormulaire
            id="mot-de-passe"
            ref="champMotDePasse"
            v-model="motDePasse"
            label="Mot de passe"
            type="password"
            autocomplete="current-password"
            :erreur="erreurMotDePasse"
            requis
            revelable
          />

          <div
            v-if="erreurServeur"
            ref="alerte"
            role="alert"
            tabindex="-1"
            class="rounded-md border border-status-critical/30 bg-status-critical/5 px-3 py-2 text-sm text-status-critical outline-none"
          >
            {{ erreurServeur }}
          </div>

          <Button type="submit" class="h-10 w-full" :disabled="enCours">
            {{ enCours ? 'Connexion…' : 'Se connecter' }}
          </Button>
        </form>

        <div class="mt-4 text-center">
          <button
            type="button"
            class="text-sm text-primary underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
            :aria-expanded="aideOubliVisible"
            aria-controls="aide-oubli"
            @click="aideOubliVisible = !aideOubliVisible"
          >
            Mot de passe oublié ?
          </button>
          <p v-show="aideOubliVisible" id="aide-oubli" class="mt-2 text-sm text-muted-foreground">
            Contactez votre administrateur : il réinitialisera votre mot de passe.
          </p>
        </div>
      </section>

      <p id="mention-journal" class="mt-6 text-center text-xs text-muted-foreground">
        Accès réservé — toutes les connexions sont journalisées
      </p>
    </div>
  </main>
</template>
