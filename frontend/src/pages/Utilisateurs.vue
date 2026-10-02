<script setup lang="ts">
/**
 * Gestion des comptes (ADMIN) : création avec rôle et mot de passe temporaire (D-30).
 * Modification de rôle, désactivation et réinitialisation : lot 7.
 */
import { Check, Copy } from '@lucide/vue'
import { computed, nextTick, onMounted, ref } from 'vue'
import { api, messageErreur } from '@/api/client'
import type { components } from '@/api/schema'
import { LIBELLES_ROLES, type Role, TOUS_LES_ROLES } from '@/auth/droits'
import ChampFormulaire from '@/components/ChampFormulaire.vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'

type Compte = components['schemas']['UtilisateurAdminOut']

const comptes = ref<Compte[]>([])
const erreurChargement = ref<string | null>(null)

const prenom = ref('')
const nom = ref('')
const email = ref('')
const role = ref<Role | ''>('')
const erreurs = ref<{ prenom?: string; nom?: string; email?: string; role?: string }>({})
const erreurServeur = ref<string | null>(null)
const enCours = ref(false)

const cree = ref<{ compte: Compte; temporaire: string } | null>(null)
const copie = ref(false)
const zoneResultat = ref<HTMLElement | null>(null)

const dateFr = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
const trie = computed(() => comptes.value)

async function charger() {
  const { data, error } = await api.GET('/api/utilisateurs')
  if (data) comptes.value = data
  else erreurChargement.value = messageErreur(error, 'Impossible de charger les comptes.')
}

async function creer() {
  erreurServeur.value = null
  cree.value = null
  erreurs.value = {
    prenom: prenom.value.trim() ? undefined : 'Saisissez le prénom.',
    nom: nom.value.trim() ? undefined : 'Saisissez le nom.',
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()) ? undefined : 'Saisissez une adresse e-mail valide.',
    role: role.value ? undefined : 'Choisissez un rôle.',
  }
  if (Object.values(erreurs.value).some(Boolean)) return
  enCours.value = true
  const { data, error } = await api.POST('/api/utilisateurs', {
    body: { prenom: prenom.value.trim(), nom: nom.value.trim(), email: email.value.trim(), role: role.value as Role },
  })
  enCours.value = false
  if (!data) {
    erreurServeur.value = messageErreur(error, 'Création impossible.')
    return
  }
  cree.value = { compte: data.utilisateur, temporaire: data.mot_de_passe_temporaire }
  prenom.value = nom.value = email.value = ''
  role.value = ''
  copie.value = false
  await charger()
  await nextTick()
  zoneResultat.value?.focus()
}

async function copier() {
  if (!cree.value) return
  await navigator.clipboard.writeText(cree.value.temporaire)
  copie.value = true
}

onMounted(charger)
</script>

<template>
  <div class="grid max-w-5xl gap-6">
    <Card>
      <CardHeader>
        <CardTitle>Créer un compte</CardTitle>
        <CardDescription>
          Un mot de passe temporaire est généré : transmettez-le à la personne, elle devra le changer à sa première connexion.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form novalidate class="grid gap-4 sm:grid-cols-2" @submit.prevent="creer">
          <ChampFormulaire id="prenom" v-model="prenom" label="Prénom" autocomplete="off" :erreur="erreurs.prenom" requis />
          <ChampFormulaire id="nom" v-model="nom" label="Nom" autocomplete="off" :erreur="erreurs.nom" requis />
          <ChampFormulaire id="email-compte" v-model="email" label="Adresse e-mail" type="email" autocomplete="off"
            :erreur="erreurs.email" requis />
          <div class="grid content-start gap-1.5">
            <Label for="role" class="text-sm font-medium">Rôle<span aria-hidden="true" class="text-status-critical"> *</span></Label>
            <select
              id="role"
              v-model="role"
              required
              aria-required="true"
              :aria-invalid="erreurs.role ? true : undefined"
              :aria-describedby="erreurs.role ? 'role-erreur' : 'role-aide'"
              class="h-10 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive"
            >
              <option value="" disabled>Choisir un rôle…</option>
              <option v-for="r in TOUS_LES_ROLES" :key="r" :value="r">{{ LIBELLES_ROLES[r] }}</option>
            </select>
            <p v-if="erreurs.role" id="role-erreur" class="text-sm text-status-critical">{{ erreurs.role }}</p>
            <p v-else id="role-aide" class="text-xs text-muted-foreground">Détermine les droits (matrice RG-13).</p>
          </div>

          <div v-if="erreurServeur" role="alert" class="rounded-md border border-status-critical/30 bg-status-critical/5 px-3 py-2 text-sm text-status-critical sm:col-span-2">
            {{ erreurServeur }}
          </div>
          <div class="sm:col-span-2">
            <Button type="submit" :disabled="enCours">{{ enCours ? 'Création…' : 'Créer le compte' }}</Button>
          </div>
        </form>

        <div
          v-if="cree"
          ref="zoneResultat"
          role="status"
          tabindex="-1"
          class="mt-6 rounded-lg border border-status-ok/40 bg-status-ok/5 p-4 outline-none"
        >
          <p class="text-sm font-medium">
            Compte créé pour {{ cree.compte.prenom }} {{ cree.compte.nom }} ({{ LIBELLES_ROLES[cree.compte.role] }}).
          </p>
          <p class="mt-2 text-sm">Mot de passe temporaire :</p>
          <div class="mt-1 flex flex-wrap items-center gap-2">
            <code class="rounded bg-background px-2 py-1 font-mono text-base">{{ cree.temporaire }}</code>
            <Button type="button" variant="outline" size="sm" @click="copier">
              <component :is="copie ? Check : Copy" aria-hidden="true" />
              {{ copie ? 'Copié' : 'Copier' }}
            </Button>
          </div>
          <p class="mt-2 text-xs text-muted-foreground">Il ne sera plus affiché : transmettez-le maintenant par un canal sûr.</p>
        </div>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>Comptes</CardTitle>
      </CardHeader>
      <CardContent class="overflow-x-auto">
        <p v-if="erreurChargement" role="alert" class="text-sm text-status-critical">{{ erreurChargement }}</p>
        <table v-else class="w-full text-left text-sm">
          <caption class="sr-only">Comptes utilisateurs de la plateforme</caption>
          <thead class="border-b text-xs text-muted-foreground">
            <tr>
              <th scope="col" class="py-2 pr-4 font-medium">Nom</th>
              <th scope="col" class="py-2 pr-4 font-medium">Adresse e-mail</th>
              <th scope="col" class="py-2 pr-4 font-medium">Rôle</th>
              <th scope="col" class="py-2 pr-4 font-medium">Statut</th>
              <th scope="col" class="py-2 font-medium">Dernière connexion</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in trie" :key="c.id_utilisateur" class="border-b last:border-0">
              <th scope="row" class="py-2 pr-4 font-medium">{{ c.prenom }} {{ c.nom }}</th>
              <td class="py-2 pr-4">{{ c.email }}</td>
              <td class="py-2 pr-4">{{ LIBELLES_ROLES[c.role] }}</td>
              <td class="py-2 pr-4">
                <span v-if="!c.actif" class="text-muted-foreground">Désactivé</span>
                <span v-else-if="c.doit_changer_mdp" class="text-status-warning">Première connexion en attente</span>
                <span v-else class="text-status-ok">Actif</span>
              </td>
              <td class="py-2">{{ c.derniere_connexion ? dateFr.format(new Date(c.derniere_connexion)) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  </div>
</template>
