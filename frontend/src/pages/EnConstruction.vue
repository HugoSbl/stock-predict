<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const route = useRoute()
// Issue GitHub du lot n = #(n + 1)
const issue = computed(() =>
  route.meta.lot === undefined
    ? null
    : `https://github.com/HugoSbl/stock-predict/issues/${route.meta.lot + 1}`,
)
</script>

<template>
  <Card class="max-w-xl">
    <CardHeader>
      <CardTitle>Écran en construction</CardTitle>
      <CardDescription>« {{ route.meta.title }} » sera livré par le lot {{ route.meta.lot }}.</CardDescription>
    </CardHeader>
    <CardContent v-if="issue">
      <a :href="issue" class="text-sm text-primary underline underline-offset-4" target="_blank" rel="noopener">
        Voir l'issue du lot {{ route.meta.lot }}
      </a>
    </CardContent>
  </Card>
</template>
