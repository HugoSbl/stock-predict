<script setup lang="ts">
/**
 * Champ de formulaire accessible (RGAA 11) : label explicite, aide et erreur reliées au champ par
 * aria-describedby, aria-invalid en cas d'erreur. Option « révélable » pour les mots de passe.
 */
import { computed, ref } from 'vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const props = withDefaults(
  defineProps<{
    id: string
    label: string
    type?: string
    autocomplete?: string
    aide?: string
    erreur?: string | null
    requis?: boolean
    revelable?: boolean
  }>(),
  { type: 'text', autocomplete: 'off', aide: undefined, erreur: null, requis: false, revelable: false },
)
const valeur = defineModel<string>({ default: '' })

const visible = ref(false)
const typeEffectif = computed(() => (props.revelable && visible.value ? 'text' : props.type))
const idAide = computed(() => `${props.id}-aide`)
const idErreur = computed(() => `${props.id}-erreur`)
const decritPar = computed(
  () => [props.aide ? idAide.value : null, props.erreur ? idErreur.value : null].filter(Boolean).join(' ') || undefined,
)

const champ = ref<InstanceType<typeof Input> | null>(null)
defineExpose({ focus: () => (champ.value?.$el as HTMLInputElement | undefined)?.focus() })
</script>

<template>
  <!-- content-start : pas d'étirement vertical quand la cellule voisine de la grille est plus haute -->
  <div class="grid content-start gap-1.5">
    <Label :for="id" class="text-sm font-medium">
      {{ label }}<span v-if="requis" aria-hidden="true" class="text-status-critical"> *</span>
    </Label>
    <div class="relative">
      <Input
        :id="id"
        ref="champ"
        v-model="valeur"
        :type="typeEffectif"
        :autocomplete="autocomplete"
        :required="requis"
        :aria-required="requis || undefined"
        :aria-invalid="erreur ? true : undefined"
        :aria-describedby="decritPar"
        :class="['h-10', revelable ? 'pr-20' : '']"
      />
      <button
        v-if="revelable"
        type="button"
        class="absolute inset-y-1 right-1 rounded-md px-2 text-xs font-medium text-primary outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        :aria-pressed="visible"
        :aria-label="visible ? `Masquer le ${label.toLowerCase()}` : `Afficher le ${label.toLowerCase()}`"
        @click="visible = !visible"
      >
        {{ visible ? 'masquer' : 'voir' }}
      </button>
    </div>
    <p v-if="aide" :id="idAide" class="text-xs text-muted-foreground">{{ aide }}</p>
    <p v-if="erreur" :id="idErreur" class="text-sm text-status-critical">{{ erreur }}</p>
  </div>
</template>
