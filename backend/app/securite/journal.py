"""Journal d'audit (RG-14) : horodatage, utilisateur ou système, IP, détails."""

import ipaddress
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Journal

# Aucun secret ne doit atteindre le journal (RG-12), même par erreur d'un appelant
CLES_INTERDITES = ("mot_de_passe", "mdp", "password", "jeton", "token", "secret")


def adresse_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    candidate = None
    if settings.faire_confiance_au_proxy:
        transfert = request.headers.get("x-forwarded-for")
        if transfert:
            candidate = transfert.split(",")[0].strip()
    if candidate is None and request.client:
        candidate = request.client.host
    try:
        return str(ipaddress.ip_address(candidate)) if candidate else None
    except ValueError:
        return None


def _nettoyer(details: dict[str, Any] | None) -> dict[str, Any] | None:
    if details is None:
        return None
    return {
        cle: "***" if any(mot in cle.lower() for mot in CLES_INTERDITES) else valeur
        for cle, valeur in details.items()
    }


def journaliser(
    db: Session,
    action: str,
    *,
    request: Request | None = None,
    id_utilisateur: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Ajoute une entrée au journal dans la transaction courante (l'appelant commite).

    id_utilisateur None = action du système (ordonnanceur, seed…).
    """
    db.add(
        Journal(
            action=action,
            adresse_ip=adresse_ip(request),
            details=_nettoyer(details),
            id_utilisateur=id_utilisateur,
        )
    )
