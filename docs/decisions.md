# Journal des décisions (ADR)

Complète et corrige le dossier de conception là où il est muet ou incohérent. **Prioritaire sur le PDF.**
Format : une entrée par décision, jamais réécrite — une décision remplacée est marquée « Remplacée par D-xx ».

---

## D-01 — Table ALERTE complétée
Le MLD ne permet pas UC-04 ni RG-10. Colonnes ajoutées à `alerte` :
`date_rupture_estimee DATE NULL`, `quantite_recommandee INT NULL`, `date_commande_conseillee DATE NULL`,
`motif TEXT NULL` (obligatoire si statut IGNOREE), `id_commande FK NULL` (lien UC-04 3a),
`id_utilisateur_traitement FK NULL`, `date_traitement TIMESTAMPTZ NULL`.
Types : `SOUS_SEUIL | RUPTURE_PREVUE | SURSTOCK`. Statuts : `OUVERTE | TRAITEE | IGNOREE`.
Une seule alerte OUVERTE par (produit, entrepôt, type) : une regénération met à jour l'existante (index unique partiel).

## D-02 — Verrouillage de compte (RG-15)
Colonnes ajoutées à `utilisateur` : `nb_echecs_connexion INT DEFAULT 0`, `verrouille_jusqu_a TIMESTAMPTZ NULL`, `derniere_connexion TIMESTAMPTZ NULL`.
Remise à zéro du compteur à chaque connexion réussie.

## D-03 — Lignes rejetées exportables (RG-02)
Nouvelle table `ligne_rejetee (id_rejet, #id_synchro, numero_ligne, donnees JSONB, motif)`.
Motifs normalisés : `TYPE_INVALIDE | QUANTITE_NEGATIVE | PRODUIT_INCONNU | ENTREPOT_INCONNU | DOUBLON`.
Les rejets sont insérés dans une transaction séparée de l'import (ils doivent survivre à un rollback RG-03).

## D-04 — Configuration des sources (§5.3 « motif de connecteurs »)
Nouvelle table `source_api (id_source, nom, url, type_donnees, mapping_colonnes JSONB, frequence_cron, actif, nom_variable_secret)`.
Le secret n'est jamais en base : `nom_variable_secret` désigne une variable d'environnement.
`synchronisation.source_api` devient `#id_source`.
Appels sortants limités aux URL de `source_api` (liste blanche, OWASP A10).

## D-05 — Granularité des prévisions
Le modèle prédit la **demande journalière** (ventes). Une ligne `prevision` par (produit, entrepôt, date_calcul, **date_cible**) :
`quantite_prevue`, `borne_basse`, `borne_haute` (IC 95 % : quantiles 2,5 % / 97,5 %), `version_modele`.
On calcule toujours 90 jours ; les horizons 7 / 30 / 60 / 90 sont des filtres d'affichage. `horizon_jours` est remplacé par `date_cible`.
Seul le dernier calcul par couple est affiché ; les anciens sont conservés (RG-08).

## D-06 — Stock projeté et recommandation (calculés à la lecture, non stockés)
- `stock_projete(j) = stock_actuel − Σ demande_prevue(≤ j) + Σ livraisons attendues(≤ j)`
  (livraisons = lignes de commandes non livrées, à `date_livraison_estimee`).
- Borne basse du stock projeté = même formule avec la **borne haute** de la demande (scénario pessimiste).
- `date_rupture_estimee` = premier jour où la borne basse ≤ 0.
- `quantite_recommandee = demande_prevue(délai fournisseur + 14 j de couverture) + seuil_alerte − stock_projete(délai)`, arrondie à la dizaine supérieure, ≥ 0.
- `date_commande_conseillee = date_rupture_estimee − delai_moyen_jours` du fournisseur habituel (min. aujourd'hui).

## D-07 — KPI et alerte SURSTOCK
- **Produits sous seuil** : nb de couples produit × entrepôt avec `quantite_stock < seuil_alerte`.
- **Ruptures prévues sous 7 j** : nb de couples avec alerte RUPTURE_PREVUE ouverte.
- **Taux de disponibilité** : % des couples produit × entrepôt avec `quantite_stock > 0`.
- **Valeur de surstock** : Σ max(0, stock − demande prévue sur 60 j) × `prix_unitaire_ht`.
- **Alerte SURSTOCK** : couverture (stock / demande prévue moyenne journalière) > 90 jours.
- Tendances « vs semaine passée » : calculées sur un instantané quotidien des KPI (table `kpi_quotidien`, alimentée en fin de chaîne nocturne).

## D-08 — Montants et TVA (UC-05)
Montants stockés HT. Vue pays : affichage TTC avec le taux de `pays` + mention « TTC (TVA FR 20 %) ».
Vue « Tous pays » : affichage **HT** (taux hétérogènes), mention explicite. Devise EUR pour les deux pays pilotes.

## D-09 — Bouton « Recalculer » (UC-02 2a / maquette 4)
Deux actions distinctes :
- Recalculer la prévision d'**un** couple produit × entrepôt (sans resynchroniser) : RESPONSABLE, ANALYSTE, ADMIN.
- Forcer la **chaîne complète** (synchro → ML → alertes) : ADMIN uniquement (UC-03).
Les deux sont journalisées.

## D-10 — « Mot de passe oublié »
Pas d'envoi d'e-mail au POC. Le lien affiche « Contactez votre administrateur ». L'ADMIN réinitialise le mot de passe depuis l'écran Utilisateurs (mot de passe temporaire, changement forcé à la connexion suivante : colonne `doit_changer_mdp BOOLEAN`).

## D-11 — Back-end : FastAPI
FastAPI retenu (pas DRF) : async, OpenAPI natif pour générer le client TS, léger. SQLAlchemy 2 + Alembic.
La migration initiale exécute `db/mpd_stockpredict.sql` ; les amendements (D-01 à D-10) sont des migrations suivantes.

## D-12 — Session : JWT en cookie httpOnly
JWT (8 h) dans un cookie `httpOnly; Secure; SameSite=Strict` — jamais en localStorage (XSS).
Anti-CSRF : toute requête mutante doit porter l'en-tête `X-Requested-With: StockPredict` (rejetée sinon).

## D-13 — Modèle ML
Un **modèle global** (pas un modèle par couple) : `HistGradientBoostingRegressor`, 3 fits (quantiles 0,025 / 0,5 / 0,975).
Features : jour de semaine, mois, semaine, férié du pays de l'entrepôt, vacances scolaires, promo active + taux de remise, lags (7, 14, 28 j), moyennes glissantes, identifiants produit / catégorie / entrepôt encodés.
Prévision récursive sur 90 j. `version_modele` = `hgb-<date>-<hash court des hyperparamètres>`.
Historique < 60 jours pour un couple → prévision faite mais flag « fiabilité réduite » (UC-02 2b).
Évaluation : MAE et couverture réelle de l'IC sur les 28 derniers jours, loggées à chaque entraînement.

## D-14 — Données : sources simulées et générateur
Aucune API source réelle n'existe → service `sources-mock` (FastAPI) exposant :
`GET /api/v1/sales`, `GET /api/v1/stock-levels`, `GET /api/v1/purchase-orders` (noms repris de la maquette 5).
Un paramètre de panne simulée (`?fail=timeout|auth|500`, ou variable d'env) permet de démontrer UC-03 2a.
Le générateur produit ~5 % de lignes invalides (RG-02) et quelques colonnes non mappées (RG-01).
Jeu de référence : 2 ans d'historique ; FR = Lyon-Sud, Paris-Nord, Lille-Est ; DE = Berlin-Ouest, Munich-Est, Hambourg-Nord ; ~300 produits / 8 catégories ; saisonnalité hebdo + annuelle, pics de fêtes, effet promo, fériés FR/DE via la lib `holidays`. Volume ≈ 1,3 M lignes de ventes (paramétrable). Seed fixe → données reproductibles pour toute l'équipe.

## D-15 — Chaîne nocturne
Conteneur `worker` avec cron : 02:00 synchro (toutes sources actives) → recalcul ML → génération alertes → instantané KPI.
Même code appelé par le forçage ADMIN. Insertions massives via `COPY` dans une table de staging puis validation/insert en SQL.
Retry : 3 tentatives, backoff 5 s / 15 s / 45 s, timeout 30 s (UC-03 2a).

## D-16 — Libellés et navigation
Menu : Tableau de bord, Stocks, Prévisions, Alertes, Synchronisation, Exports, Utilisateurs (ADMIN), Journaux (ADMIN).
« Import données » (maquettes 2-4) est renommé « Synchronisation » (cohérent avec la maquette 5 et l'absence d'import manuel).
Les entrées non autorisées pour le rôle sont masquées (et refusées côté serveur).

## D-17 — Dev en direct
Vite fait proxy de `/api` vers FastAPI → un seul port (5173) à exposer via tunnel (`npm run share`).
