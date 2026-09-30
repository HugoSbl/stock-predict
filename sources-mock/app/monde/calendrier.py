"""Dimension calendrier (RG-07) : jours fériés FR/DE (lib holidays) et vacances scolaires.

Les vacances sont une approximation nationale (union des zones FR / des Länder DE) : suffisant pour
un effet saisonnier, pas pour un usage calendaire exact.
"""

from datetime import date, timedelta

import holidays
import pandas as pd
from dateutil.easter import easter


def _periodes_vacances_fr(annee: int) -> list[tuple[date, date]]:
    return [
        (date(annee, 1, 1), date(annee, 1, 4)),  # fin des vacances de Noël
        (date(annee, 2, 15), date(annee, 3, 2)),  # hiver
        (date(annee, 4, 12), date(annee, 4, 27)),  # printemps
        (date(annee, 7, 5), date(annee, 8, 31)),  # été
        (date(annee, 10, 18), date(annee, 11, 2)),  # Toussaint
        (date(annee, 12, 20), date(annee, 12, 31)),  # Noël
    ]


def _periodes_vacances_de(annee: int) -> list[tuple[date, date]]:
    paques = easter(annee)
    return [
        (date(annee, 1, 1), date(annee, 1, 5)),  # Weihnachtsferien (fin)
        (paques - timedelta(days=7), paques + timedelta(days=7)),  # Osterferien
        (date(annee, 7, 15), date(annee, 8, 25)),  # Sommerferien
        (date(annee, 10, 13), date(annee, 10, 24)),  # Herbstferien
        (date(annee, 12, 22), date(annee, 12, 31)),  # Weihnachtsferien (début)
    ]


def _jours(periodes: list[tuple[date, date]]) -> set[date]:
    jours: set[date] = set()
    for debut, fin in periodes:
        jours.update(debut + timedelta(days=i) for i in range((fin - debut).days + 1))
    return jours


def generer_calendrier(debut: date, fin: date) -> pd.DataFrame:
    annees = range(debut.year, fin.year + 1)
    feries_fr = holidays.country_holidays("FR", years=annees)
    feries_de = holidays.country_holidays("DE", years=annees)
    vacances_fr = _jours([p for a in annees for p in _periodes_vacances_fr(a)])
    vacances_de = _jours([p for a in annees for p in _periodes_vacances_de(a)])

    dates = pd.date_range(debut, fin, freq="D")
    iso = dates.isocalendar()
    jours = [d.date() for d in dates]
    return pd.DataFrame(
        {
            "date_jour": jours,
            "jour_semaine": iso["day"].to_numpy(),
            "numero_semaine": iso["week"].to_numpy(),
            "mois": dates.month,
            "annee": dates.year,
            "ferie_fr": [j in feries_fr for j in jours],
            "ferie_de": [j in feries_de for j in jours],
            "vacances_fr": [j in vacances_fr for j in jours],
            "vacances_de": [j in vacances_de for j in jours],
        }
    )
