"""Modèle de demande : intensité moyenne attendue par jour × couple produit-entrepôt.

intensité = base(couple) × saison(catégorie) × jour de semaine(pays) × fériés(pays)
            × Noël / Pâques(catégorie) × vacances(pays, catégorie) × promotion(produit) × tendance
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from dateutil.easter import easter

from app.monde.catalogue import CATEGORIES, PRODUITS_MAQUETTES, Entrepot, Produit
from app.monde.promotions import Promotion

# Profil hebdomadaire des magasins servis (lundi … dimanche). Dimanche fermé en Allemagne.
PROFIL_SEMAINE = {
    "FR": np.array([0.85, 0.85, 0.95, 0.95, 1.20, 1.45, 0.45]),
    "DE": np.array([0.95, 0.95, 1.00, 1.05, 1.35, 1.55, 0.00]),
}
EFFET_FERIE = {"FR": 0.30, "DE": 0.00}  # magasins partiellement ouverts en France
EFFET_VEILLE_FERIE = 1.30
UPLIFT_PAR_POINT_DE_REMISE = 0.03  # 25 % de remise → ×1,75
CREUX_APRES_PROMO = 0.85  # 7 jours après la fin
CROISSANCE_ANNUELLE = 0.03


def popularite_base(
    rng: np.random.Generator, produits: list[Produit], entrepots: list[Entrepot]
) -> np.ndarray:
    """Ventes moyennes journalières de chaque couple (ordre : produit puis entrepôt)."""
    pop = np.clip(rng.lognormal(mean=np.log(12), sigma=0.8, size=len(produits)), 0.5, 300)
    # Les produits des maquettes (en tête du catalogue) sont des best-sellers
    nb_vedettes = len(PRODUITS_MAQUETTES)
    pop[:nb_vedettes] = rng.uniform(60, 150, size=nb_vedettes)
    affinite = {
        pays: rng.lognormal(0, 0.3, size=len(produits)) for pays in ("FR", "DE")
    }  # préférences nationales
    base = np.empty((len(produits), len(entrepots)))
    for j, e in enumerate(entrepots):
        base[:, j] = pop * e.taille * affinite[e.code_pays]
    return base.reshape(-1)


def facteur_saison(jours: pd.DatetimeIndex, produits: list[Produit]) -> np.ndarray:
    """Matrice (jours × produits) des effets saisonniers annuels + Noël + Pâques."""
    doy = jours.dayofyear.to_numpy()[:, None]
    cat = np.array([p.id_categorie - 1 for p in produits])
    amplitude = np.array([c.amplitude_saison for c in CATEGORIES])[cat]
    pic = np.array([c.jour_pic for c in CATEGORIES])[cat]
    saison = 1 + amplitude * np.cos(2 * np.pi * (doy - pic) / 365.25)

    noel = np.array([c.effet_noel for c in CATEGORIES])[cat]
    paques = np.array([c.effet_paques for c in CATEGORIES])[cat]
    mois, jour = jours.month.to_numpy(), jours.day.to_numpy()
    en_noel = ((mois == 12) & (jour >= 15) & (jour <= 24))[:, None]
    dates_paques = {a: easter(a) for a in set(jours.year)}
    en_paques = np.array(
        [dates_paques[d.year] - timedelta(days=7) <= d.date() < dates_paques[d.year] for d in jours]
    )[:, None]
    return saison * np.where(en_noel, noel, 1.0) * np.where(en_paques, paques, 1.0)


def facteur_promotion(
    jours: pd.DatetimeIndex, promotions: list[Promotion], nb_produits: int
) -> tuple[np.ndarray, np.ndarray]:
    """(effet multiplicatif, taux de remise en %) par jour × produit."""
    debut = jours[0].date()
    n = len(jours)
    effet = np.ones((n, nb_produits))
    remise = np.zeros((n, nb_produits))
    for promo in promotions:
        i0 = (promo.date_debut - debut).days
        i1 = (promo.date_fin - debut).days + 1
        if i1 <= 0 or i0 >= n:
            continue
        cols = np.array(promo.id_produits) - 1
        a, b = max(i0, 0), min(i1, n)
        effet[a:b, cols] = 1 + UPLIFT_PAR_POINT_DE_REMISE * promo.taux_remise
        remise[a:b, cols] = promo.taux_remise
        c, d = max(i1, 0), min(i1 + 7, n)
        if c < d:
            effet[c:d, cols] = np.minimum(effet[c:d, cols], CREUX_APRES_PROMO)
    return effet, remise


def intensite_demande(
    jours: pd.DatetimeIndex,
    calendrier: pd.DataFrame,
    produits: list[Produit],
    entrepots: list[Entrepot],
    base: np.ndarray,
    effet_promo: np.ndarray,
    debut_historique: date,
) -> np.ndarray:
    """Matrice (jours × couples) de la demande moyenne attendue."""
    nb_p, nb_e = len(produits), len(entrepots)
    cal = calendrier.set_index("date_jour").loc[[d.date() for d in jours]]
    saison = facteur_saison(jours, produits)  # jours × produits
    cat = np.array([p.id_categorie - 1 for p in produits])
    effet_vacances = np.array([c.effet_vacances for c in CATEGORIES])[cat]
    dow = jours.dayofweek.to_numpy()
    annees = (jours - pd.Timestamp(debut_historique)).days.to_numpy() / 365.25
    tendance = (1 + CROISSANCE_ANNUELLE * annees)[:, None]

    intensite = np.empty((len(jours), nb_p, nb_e))
    for pays in ("FR", "DE"):
        ferie = cal[f"ferie_{pays.lower()}"].to_numpy()
        veille = np.roll(ferie, -1) & ~ferie & (dow != 6)
        vacances = cal[f"vacances_{pays.lower()}"].to_numpy()[:, None]
        jour_pays = PROFIL_SEMAINE[pays][dow]
        jour_pays = np.where(ferie, jour_pays * EFFET_FERIE[pays], jour_pays)
        jour_pays = np.where(veille, jour_pays * EFFET_VEILLE_FERIE, jour_pays)
        commun = saison * effet_promo * tendance * jour_pays[:, None]
        commun = commun * np.where(vacances, effet_vacances, 1.0)
        for j, e in enumerate(entrepots):
            if e.code_pays == pays:
                intensite[:, :, j] = commun
    return intensite.reshape(len(jours), nb_p * nb_e) * base[None, :]
