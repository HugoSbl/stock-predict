# StockPredict — POC

Plateforme de prédiction des stocks (GLOBALRETAIL, Supply Chain). POC sur 2 pays pilotes : France et Allemagne.
Équipe de 5, chacun travaille avec son propre Claude : **ce fichier et `docs/` sont la source de vérité commune**.

## Sources de vérité (à lire avant de coder)

- Règles de gestion RG-01 → RG-15 : @docs/regles-de-gestion.md
- Décisions d'architecture et arbitrages (complètent le dossier) : @docs/decisions.md
- Découpage en lots et dépendances : @docs/lots.md
- Dossier de conception complet : `docs/conception/Dossier_conception_StockPredict_v2.pdf`
- Schéma physique : modèles SQLAlchemy `backend/app/models/` + migrations Alembic (issus du MLD §3.2 + décisions, cf. D-11)

En cas de conflit : `docs/decisions.md` > dossier PDF. Toute nouvelle décision structurante = nouvelle entrée `D-xx` dans `docs/decisions.md`, dans la même PR.

## Stack

| Couche | Choix |
|---|---|
| Back | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, uv, ruff, pytest |
| ML | pandas, scikit-learn (HistGradientBoosting, régression quantile) |
| Front | Vue 3 + Vite + TypeScript, shadcn-vue, TanStack Table, Chart.js |
| BDD | PostgreSQL 16 (Docker) |
| Sources simulées | `sources-mock/` : fausses API ERP Ventes / WMS Stocks / Portail Fournisseurs + générateur de données |
| Orchestration | Docker Compose (pas de Kubernetes au POC) |

## Structure

```
backend/        API FastAPI (auth, ingestion, ML, alertes, KPI)
frontend/       SPA Vue 3
sources-mock/   API sources simulées + générateur de données synthétiques
scripts/        outillage dev (tunnel de partage)
docs/           règles, décisions, lots, dossier de conception
```

## Conventions

- Nommage **en français** (métier et code applicatif), conforme au MLD (tables/colonnes : `produit`, `entrepot`, `quantite_stock`…), sans accents dans les identifiants. Les termes techniques standard restent en anglais (`router`, `get_db`, `health`…). Textes UI en français.
- Front ↔ back : uniquement via l'API REST `/api/...`. Le client TS est généré depuis l'OpenAPI FastAPI (`npm run gen:api`) — ne jamais écrire les types d'API à la main.
- Chaque endpoint vérifie le rôle côté serveur, refus par défaut (RG-13). Toute action significative écrit dans `journal` (RG-14).
- SQL toujours paramétré (ORM). Aucun secret dans le repo (`.env`, voir `.env.example`).
- Accessibilité RGAA : statut jamais porté par la seule couleur, graphiques doublés d'un tableau, labels explicites.

## Workflow Git

- Un lot = une issue GitHub = une branche `lot-<n>-<slug>` = une PR qui contient `Closes #<issue>`.
- Démarrer un lot : commande `/lot <n>` (voir `.claude/skills/lot/`).
- `main` doit toujours démarrer (`docker compose up`) : c'est la version montrée en direct à l'équipe.
- Petits commits, messages conventionnels (`feat:`, `fix:`, `docs:`…).

## Commandes

Pré-requis : Docker Desktop, Node 22, `uv` (`brew install uv`), `cloudflared` pour partager (`brew install cloudflared`).

| Commande (racine) | Effet |
|---|---|
| `cp .env.example .env` | Une seule fois après le clone |
| `npm run dev` | Démarre db + backend + sources-mock + frontend (hot reload partout) |
| `npm run share` | URL publique vers le front (proxy `/api` inclus) pour faire tester l'équipe |
| `npm run gen:api` | Régénère `frontend/src/api/schema.d.ts` depuis l'OpenAPI (backend démarré). **À lancer et commiter après tout changement d'API.** |
| `npm test` | Tests backend + sources-mock (dans les conteneurs) + type-check front |
| `npm run lint` | ruff check + format --check |
| `npm run migration -- "message"` | Génère une migration Alembic (autogenerate) |
| `npm run migrate` | Applique les migrations (fait aussi au démarrage du backend) |

URLs locales : app http://localhost:5173 · Swagger http://localhost:5173/api/docs · sources-mock http://localhost:8100/docs · Postgres localhost:5432.

Ajout d'une dépendance : `cd backend && uv add <pkg>` (ou `npm i` dans `frontend/`), puis `docker compose up --build -d` pour reconstruire l'image.
Tests Python hors Docker : `cd backend && uv run pytest` (nécessite la base de `npm run dev`).
