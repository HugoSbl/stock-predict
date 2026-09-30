# StockPredict

POC de plateforme de prédiction des stocks par Machine Learning (GLOBALRETAIL — Supply Chain).

- Dossier de conception : [`docs/conception/`](docs/conception/)
- Décisions d'architecture : [`docs/decisions.md`](docs/decisions.md)
- Lots de travail : [`docs/lots.md`](docs/lots.md) et les [issues](../../issues)

## Travailler sur le projet avec Claude Code

1. `git clone` puis ouvrir Claude Code à la racine : il charge automatiquement `CLAUDE.md`.
2. `gh auth login` (Claude lit les issues via `gh`).
3. Taper `/lot <n>` pour démarrer le lot `n`.

## Démarrage

```bash
cp .env.example .env
npm run dev          # http://localhost:5173
npm run share        # lien public à envoyer à l'équipe
```

Toutes les commandes : section **Commandes** de [`CLAUDE.md`](CLAUDE.md).
