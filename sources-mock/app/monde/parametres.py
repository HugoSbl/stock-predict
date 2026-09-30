"""Paramètres du monde simulé. Modifier GRAINE ou DATE_DEBUT change toutes les données."""

from datetime import date

GRAINE = 20260930
DATE_DEBUT = date(2024, 10, 1)  # début de l'historique
DATE_FIN_REFERENTIELS = date(2030, 12, 31)  # calendrier et promotions générés jusque-là (fixe)
HORIZON_CALENDRIER_JOURS = 120  # calendrier exporté jusqu'à aujourd'hui + horizon (prévisions 90 j)

NB_PRODUITS = 300
TAUX_LIGNES_INVALIDES = 0.05  # API sources uniquement (RG-02) ; l'export seed est propre
