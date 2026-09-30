<script setup lang="ts">
import {
  Bell,
  Boxes,
  Download,
  KeyRound,
  LayoutDashboard,
  LogOut,
  RefreshCw,
  ScrollText,
  TrendingUp,
  TriangleAlert,
  Users,
} from '@lucide/vue'
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LIBELLES_ROLES } from '@/auth/droits'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PAYS, usePaysStore } from '@/stores/pays'
import { useSessionStore } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const pays = usePaysStore()
const session = useSessionStore()

// Menu (D-16), filtré selon les rôles déclarés sur les routes (matrice RG-13)
const menu = [
  { to: '/', label: 'Tableau de bord', icon: LayoutDashboard },
  { to: '/stocks', label: 'Stocks', icon: Boxes },
  { to: '/previsions', label: 'Prévisions', icon: TrendingUp },
  { to: '/alertes', label: 'Alertes', icon: TriangleAlert },
  { to: '/synchronisation', label: 'Synchronisation', icon: RefreshCw },
  { to: '/exports', label: 'Exports', icon: Download },
  { to: '/utilisateurs', label: 'Utilisateurs', icon: Users },
  { to: '/journaux', label: 'Journaux', icon: ScrollText },
]

const navigation = computed(() =>
  menu.filter((item) => {
    const cible = router.resolve(item.to)
    return session.role !== null && (cible.meta.roles ?? []).includes(session.role)
  }),
)

const titre = computed(() => route.meta.title)
const nomAffiche = computed(() =>
  session.utilisateur ? `${session.utilisateur.prenom} ${session.utilisateur.nom.charAt(0)}.` : '',
)

async function seDeconnecter() {
  await session.deconnecter()
  await router.replace({ name: 'connexion' })
}
</script>

<template>
  <!-- Lien d'évitement (RGAA 12.7) -->
  <a
    href="#contenu"
    class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:shadow"
  >
    Aller au contenu principal
  </a>

  <div class="flex min-h-svh">
    <aside class="hidden w-60 shrink-0 flex-col bg-sidebar text-sidebar-foreground md:flex">
      <div class="px-5 py-5">
        <p class="text-lg font-semibold text-white">StockPredict</p>
        <p class="text-xs opacity-75">GLOBALRETAIL — Supply Chain</p>
      </div>
      <nav aria-label="Navigation principale" class="flex-1 px-3">
        <ul class="space-y-1">
          <li v-for="item in navigation" :key="item.to">
            <RouterLink
              :to="item.to"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm outline-none transition-colors hover:bg-sidebar-accent/60 focus-visible:ring-2 focus-visible:ring-sidebar-ring"
              exact-active-class="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
            >
              <component :is="item.icon" class="size-4" aria-hidden="true" />
              {{ item.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>
      <div v-if="session.utilisateur" class="border-t border-sidebar-border px-5 py-4 text-xs">
        <p class="font-medium text-white">{{ nomAffiche }}</p>
        <p class="opacity-75">{{ LIBELLES_ROLES[session.utilisateur.role] }}</p>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col bg-muted/40">
      <header class="flex items-center gap-3 border-b bg-background px-4 py-3 md:px-6">
        <h1 class="mr-auto truncate text-lg font-semibold">{{ titre }}</h1>

        <Select v-model="pays.code">
          <SelectTrigger class="w-40" aria-label="Pays affiché">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="p in PAYS" :key="p.code" :value="p.code">
              {{ p.code === 'TOUS' ? p.libelle : `${p.code} — ${p.libelle}` }}
            </SelectItem>
          </SelectContent>
        </Select>

        <Button variant="ghost" size="icon" aria-label="Alertes (bientôt disponible)" disabled>
          <Bell aria-hidden="true" />
        </Button>
        <Button as-child variant="ghost" size="icon">
          <RouterLink to="/mot-de-passe" aria-label="Changer mon mot de passe" title="Changer mon mot de passe">
            <KeyRound aria-hidden="true" />
          </RouterLink>
        </Button>
        <Button variant="ghost" size="icon" aria-label="Se déconnecter" title="Se déconnecter" @click="seDeconnecter">
          <LogOut aria-hidden="true" />
        </Button>
      </header>

      <!-- Navigation mobile : la sidebar est masquée sous md -->
      <nav aria-label="Navigation principale (mobile)" class="overflow-x-auto border-b bg-sidebar md:hidden">
        <ul class="flex gap-1 px-2 py-2">
          <li v-for="item in navigation" :key="item.to" class="shrink-0">
            <RouterLink
              :to="item.to"
              class="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm text-sidebar-foreground outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
              exact-active-class="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
            >
              <component :is="item.icon" class="size-4" aria-hidden="true" />
              {{ item.label }}
            </RouterLink>
          </li>
        </ul>
      </nav>

      <main id="contenu" tabindex="-1" class="flex-1 p-4 outline-none md:p-6">
        <slot />
      </main>
    </div>
  </div>
</template>
