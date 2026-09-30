---
name: lot
description: Démarrer ou reprendre un lot StockPredict à partir de son issue GitHub. Utiliser quand l'utilisateur tape "/lot <n>", "on attaque le lot <n>", "reprends le lot <n>".
---

# Démarrer un lot

Argument : numéro de lot (ex. `3`).

1. **Synchroniser** : `git fetch && git checkout main && git pull`.
2. **Lire l'issue** : `gh issue list --label lot-<n> --state all` puis `gh issue view <numéro> --comments`. Lire aussi `docs/decisions.md` et `docs/regles-de-gestion.md` (sections citées par l'issue).
3. **Vérifier les dépendances** listées dans l'issue : si un lot prérequis n'est pas fusionné, le dire et proposer de travailler sur des données seed / des mocks plutôt que de bloquer.
4. **Branche** : si une branche `lot-<n>-*` existe déjà (locale ou distante), la reprendre ; sinon `git checkout -b lot-<n>-<slug>`. S'assigner l'issue (`gh issue edit <numéro> --add-assignee @me`).
5. **Plan** : proposer un plan court (fichiers, étapes, comment on vérifiera) et le faire valider avant de coder.
6. **Implémenter** par petites étapes, commits fréquents, en respectant `CLAUDE.md`.
7. **Vérifier** chaque critère d'acceptation de l'issue (tests + démonstration réelle dans l'app). Ne pas déclarer terminé sans preuve.
8. **Décisions** : tout arbitrage nouveau → entrée `D-xx` dans `docs/decisions.md` dans la même branche.
9. **PR** : `gh pr create` avec `Closes #<numéro>`, la liste des critères cochés et comment tester.
10. **Après fusion** : vérifier que l'issue est fermée (`gh issue view <numéro> --json state`) ; sinon `gh issue close <numéro> -c "Livré par #<PR>."` (le lien automatique ne s'est pas déclenché sur les PR #10 et #11).
