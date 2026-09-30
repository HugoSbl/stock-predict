"""Configuration par variables d'environnement, relue à chaque requête (modifiable en test)."""

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Paris")


def cle_api() -> str:
    return os.environ.get("MOCK_API_KEY", "dev-mock-key")


def date_reference() -> date:
    """« Aujourd'hui » du monde simulé. MOCK_DATE_REFERENCE=AAAA-MM-JJ pour figer la date."""
    valeur = os.environ.get("MOCK_DATE_REFERENCE")
    return date.fromisoformat(valeur) if valeur else datetime.now(FUSEAU).date()


def delai_timeout_secondes() -> float:
    return float(os.environ.get("MOCK_TIMEOUT_SECONDES", "45"))


def pannes_permanentes() -> dict[str, str]:
    """MOCK_PANNES="purchase-orders=timeout,sales=500" → {"purchase-orders": "timeout", ...}."""
    brut = os.environ.get("MOCK_PANNES", "")
    return dict(p.split("=", 1) for p in brut.replace(" ", "").split(",") if "=" in p)
