<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PAYS, usePaysStore } from '@/stores/pays'

type Etat = 'chargement' | 'ok' | 'degrade' | 'injoignable'

const pays = usePaysStore()
const etat = ref<Etat>('chargement')
const version = ref<string>()

const libelles: Record<Etat, string> = {
  chargement: 'Vérification…',
  ok: 'API et base de données opérationnelles',
  degrade: 'API joignable, base de données indisponible',
  injoignable: 'API injoignable',
}

onMounted(async () => {
  try {
    const { data, error } = await api.GET('/api/health')
    const corps = data ?? error
    version.value = corps?.version
    etat.value = corps?.status === 'ok' ? 'ok' : 'degrade'
  } catch {
    etat.value = 'injoignable'
  }
})
</script>

<template>
  <div class="grid max-w-3xl gap-4">
    <Card>
      <CardHeader>
        <CardTitle>État de la plateforme</CardTitle>
        <CardDescription>Socle technique (lot 0). Les indicateurs arrivent avec le lot 6.</CardDescription>
      </CardHeader>
      <CardContent class="flex flex-wrap items-center gap-3" role="status" aria-live="polite">
        <Badge
          :class="{
            'bg-status-ok text-white': etat === 'ok',
            'bg-status-warning text-white': etat === 'degrade',
            'bg-status-critical text-white': etat === 'injoignable',
          }"
          :variant="etat === 'chargement' ? 'secondary' : 'default'"
        >
          {{ etat === 'ok' ? 'OK' : etat === 'chargement' ? '…' : etat === 'degrade' ? 'Dégradé' : 'Erreur' }}
        </Badge>
        <span class="text-sm">{{ libelles[etat] }}</span>
        <span v-if="version" class="text-xs text-muted-foreground">v{{ version }}</span>
      </CardContent>
    </Card>

    <Card>
      <CardHeader>
        <CardTitle>Contexte pays</CardTitle>
        <CardDescription>Sélection conservée pendant la session (UC-05).</CardDescription>
      </CardHeader>
      <CardContent class="text-sm">
        Pays affiché : <strong>{{ PAYS.find((p) => p.code === pays.code)?.libelle }}</strong>
      </CardContent>
    </Card>
  </div>
</template>
