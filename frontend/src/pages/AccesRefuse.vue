<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
</script>

<template>
  <Card class="max-w-xl">
    <CardHeader>
      <CardTitle>Accès refusé</CardTitle>
      <CardDescription>Votre rôle ne permet pas d'accéder à cette page.</CardDescription>
    </CardHeader>
    <CardContent>
      <RouterLink to="/" class="text-sm text-primary underline underline-offset-4">Retour au tableau de bord</RouterLink>
    </CardContent>
  </Card>
</template>
