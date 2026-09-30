#!/usr/bin/env node
// Expose le front (et donc /api via le proxy Vite) sur une URL publique (D-17).
//   npm run share                 → tunnel Cloudflare éphémère, sans compte (URL change à chaque lancement)
//   SHARE_TUNNEL=tailscale npm run share → Tailscale Funnel, URL stable (nécessite `tailscale up`)
import { spawn, spawnSync } from 'node:child_process'

const PORT = 5173
const mode = process.env.SHARE_TUNNEL ?? 'cloudflare'

async function frontDisponible() {
  try {
    await fetch(`http://localhost:${PORT}`, { signal: AbortSignal.timeout(2000) })
    return true
  } catch {
    return false
  }
}

function binaireDisponible(nom) {
  return spawnSync('which', [nom]).status === 0
}

function annoncer(url) {
  const ligne = '─'.repeat(url.length + 4)
  console.log(`\n┌${ligne}┐\n│  ${url}  │\n└${ligne}┘`)
  console.log('Lien à partager avec l’équipe. Ctrl+C pour couper le tunnel.\n')
}

if (!(await frontDisponible())) {
  console.error(`Rien n'écoute sur http://localhost:${PORT} — lance d'abord \`npm run dev\`.`)
  process.exit(1)
}

if (mode === 'tailscale') {
  if (!binaireDisponible('tailscale')) {
    console.error('tailscale introuvable : `brew install tailscale` puis `tailscale up`.')
    process.exit(1)
  }
  spawn('tailscale', ['funnel', String(PORT)], { stdio: 'inherit' })
} else {
  if (!binaireDisponible('cloudflared')) {
    console.error('cloudflared introuvable : `brew install cloudflared` (macOS) ou https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/')
    process.exit(1)
  }
  const tunnel = spawn('cloudflared', ['tunnel', '--no-autoupdate', '--url', `http://localhost:${PORT}`])
  let annonce = false
  const lire = (chunk) => {
    const url = chunk.toString().match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/)?.[0]
    if (url && !annonce) {
      annonce = true
      annoncer(url)
    }
    if (process.env.DEBUG) process.stderr.write(chunk)
  }
  tunnel.stdout.on('data', lire)
  tunnel.stderr.on('data', lire)
  tunnel.on('exit', (code) => process.exit(code ?? 0))
  process.on('SIGINT', () => tunnel.kill('SIGINT'))
}
