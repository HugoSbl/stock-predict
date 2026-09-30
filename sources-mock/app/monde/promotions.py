"""Promotions : campagnes planifiées à l'avance (connues aussi pour les dates futures, RG-07)."""

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

THEMES = [
    "Prix choc",
    "Semaine du goût",
    "Spécial famille",
    "Opération fraîcheur",
    "Les incontournables",
    "Fête des saveurs",
    "Bons plans",
    "Temps forts",
]
MOIS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
TAUX_REMISE = np.array([10, 15, 20, 25, 30, 40])


@dataclass(frozen=True)
class Promotion:
    id_promotion: int
    libelle: str
    date_debut: date
    date_fin: date
    taux_remise: float
    id_produits: tuple[int, ...]


def generer_promotions(
    rng: np.random.Generator, debut: date, fin: date, nb_produits: int
) -> list[Promotion]:
    """Une campagne tous les 10 à 18 jours, de 7 à 14 jours, sur 8 à 20 produits."""
    promotions = []
    jour = debut + timedelta(days=int(rng.integers(3, 10)))
    while jour <= fin:
        duree = int(rng.integers(7, 15))
        nb = int(rng.integers(8, 21))
        produits = tuple(sorted(int(p) + 1 for p in rng.choice(nb_produits, nb, replace=False)))
        theme = THEMES[int(rng.integers(len(THEMES)))]
        promotions.append(
            Promotion(
                id_promotion=len(promotions) + 1,
                libelle=f"{theme} — {MOIS[jour.month - 1]} {jour.year}",
                date_debut=jour,
                date_fin=jour + timedelta(days=duree - 1),
                taux_remise=float(rng.choice(TAUX_REMISE)),
                id_produits=produits,
            )
        )
        jour += timedelta(days=int(rng.integers(10, 19)))
    return promotions
