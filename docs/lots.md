# Découpage en lots

Chaque lot = une issue GitHub (label `lot-<n>`) = une branche = une PR. Le détail et les critères d'acceptation sont **dans l'issue** (`gh issue view <n>`).
Un lot est **vertical** : base + API + écran quand c'est pertinent, et démontrable sur `main` à la fin.

```
           ┌──────────► 2. Auth & rôles ─────────────────────────┐
0. Socle ──┤                                                     ├──► 6. Écrans consultation ──► 7. Exports & admin ──► 8. Finitions
           └──► 1. Données ──► 3. Ingestion ──► 4. ML ──► 5. Alertes ─┘
```

| Lot | Titre | Dépend de | Profil |
|---|---|---|---|
| 0 | Socle technique (monorepo, Docker, squelettes, tunnel) | — | 1 personne, avant tout le reste |
| 1 | Schéma BDD + générateur de données + sources simulées | 0 | data |
| 2 | Authentification, rôles, journal | 0 | back (+ écran connexion) |
| 3 | Ingestion par connecteurs + écran Synchronisation | 1, 2 | back + front |
| 4 | Prévisions ML | 1 (données en base via 3 ou seed direct) | data |
| 5 | Génération et traitement des alertes | 4 | back + front |
| 6 | Tableau de bord, Stocks, Prévisions, bascule pays | 2, 4 (peut démarrer sur 1 avec données seed) | front |
| 7 | Exports CSV/Excel, gestion utilisateurs, journaux | 2 | back + front |
| 8 | Chaîne CRON, sécurité, RGAA, tests, doc | tout | tous |

**Parallélisme possible** après le lot 0 : 1 et 2 en parallèle ; puis 3, 4 (sur données seed) et 6 (sur données seed) en parallèle.
