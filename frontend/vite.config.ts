import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// En Docker, l'API est joignable via le nom de service "backend" ; en local via localhost.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // Domaines des tunnels de démo (D-17) : cloudflared (quick tunnel) et Tailscale Funnel
    allowedHosts: ['.trycloudflare.com', '.ts.net'],
    // Un seul port exposé : le front relaie /api vers FastAPI
    proxy: { '/api': { target: apiTarget, changeOrigin: true } },
    // Les événements fichiers ne traversent pas toujours les bind mounts Docker
    watch: process.env.VITE_USE_POLLING ? { usePolling: true, interval: 300 } : undefined,
  },
})
