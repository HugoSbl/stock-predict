# Règles de gestion

Reprises du dossier de conception (§2.5). Les précisions entre crochets renvoient à `docs/decisions.md`.

| ID | Règle |
|---|---|
| RG-01 | Tout import ne conserve que les colonnes mappées au schéma cible ; les autres sont ignorées et comptabilisées dans le compte rendu. |
| RG-02 | Une ligne importée est rejetée si : type invalide, quantité négative, référence produit ou entrepôt inconnue, doublon strict. Les lignes rejetées sont stockées et exportables [D-03]. |
| RG-03 | Un import est atomique : en cas d'erreur bloquante, aucune ligne n'est conservée (rollback). |
| RG-04 | Chaque entrepôt est rattaché à un et un seul pays ; tout indicateur est agrégeable par entrepôt, par pays ou par groupe de pays. |
| RG-05 | Le taux de TVA appliqué à la valorisation est celui du référentiel PAYS ; les règles douanières relèvent d'API externes (hors POC) [D-08]. |
| RG-06 | Une prévision porte sur un couple produit × entrepôt et un horizon parmi 7, 30, 60 ou 90 jours ; elle comporte toujours un intervalle de confiance à 95 % [D-05]. |
| RG-07 | Les prévisions intègrent les facteurs saisonniers (jour de semaine, mois, périodes promotionnelles et fêtes calendaires). |
| RG-08 | Toute prévision est traçable : date de calcul et version du modèle sont conservées. |
| RG-09 | Alerte SOUS_SEUIL quand le stock passe sous le seuil d'alerte du produit ; RUPTURE_PREVUE quand la borne basse du stock projeté atteint zéro dans les 7 jours ; SURSTOCK selon [D-07]. |
| RG-10 | Une alerte ne peut être fermée que par un changement de statut explicite (« traitée » ou « ignorée » avec motif), par un utilisateur habilité. |
| RG-11 | Le seuil d'alerte d'un produit est un entier ≥ 0, modifiable uniquement par RESPONSABLE ou ADMIN. |
| RG-12 | Mots de passe stockés exclusivement en hash renforcé (bcrypt/argon2) ; jamais transmis ni journalisés en clair. |
| RG-13 | Trois rôles (RESPONSABLE, ANALYSTE, ADMIN) ; toute action est refusée par défaut si le rôle ne l'autorise pas explicitement. |
| RG-14 | Toute action significative (connexion, import, export, alerte émise ou traitée, administration) est journalisée : horodatage, utilisateur ou système, IP, détails. |
| RG-15 | Cinq échecs de connexion consécutifs verrouillent le compte 15 minutes ; l'événement est journalisé. |

## Matrice des droits (RG-13)

| Action | RESPONSABLE | ANALYSTE | ADMIN |
|---|:-:|:-:|:-:|
| Tableau de bord, stocks, prévisions, bascule pays | ✅ | ✅ | ✅ |
| Traiter / ignorer une alerte | ✅ | ❌ | ✅ |
| Modifier un seuil d'alerte | ✅ | ❌ | ✅ |
| Recalculer la prévision d'un couple produit × entrepôt [D-09] | ✅ | ✅ | ✅ |
| Consulter l'écran Synchronisation, exporter les rejets | ✅ | ✅ | ✅ |
| Forcer la chaîne complète (synchro + ML + alertes) | ❌ | ❌ | ✅ |
| Exports CSV / Excel | ✅ | ✅ | ✅ |
| Gérer utilisateurs, consulter les journaux | ❌ | ❌ | ✅ |
