<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

// Titre réel (h2 par défaut, le h1 étant le titre de page dans l'en-tête) : structure de titres RGAA 9.1
const props = withDefaults(
  defineProps<{
    class?: HTMLAttributes['class']
    as?: 'h2' | 'h3' | 'h4' | 'div'
  }>(),
  { class: undefined, as: 'h2' },
)
</script>

<template>
  <component
    :is="props.as"
    data-slot="card-title"
    :class="cn('text-base leading-snug font-medium group-data-[size=sm]/card:text-sm cn-font-heading', props.class)"
  >
    <slot />
  </component>
</template>
