"""Authentification et contrôle d'accès par rôle, vérifiés côté serveur à chaque requête (RG-13).

- `utilisateur_courant` : session valide (cookie) et compte actif, sinon 401.
- `exiger_role(...)` : refus par défaut ; seuls les rôles listés passent (403 sinon). Refuse aussi
  tant que le changement de mot de passe imposé (D-10) n'est pas fait.
Le rôle est relu en base à chaque requête : un changement de rôle ou une désactivation s'applique
immédiatement, sans attendre l'expiration du jeton.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Utilisateur
from app.models.enums import Role
from app.securite.jetons import NOM_COOKIE, lire_jeton

NON_AUTHENTIFIE = "Authentification requise"
CHANGEMENT_MDP_REQUIS = "Changement de mot de passe requis"
ACCES_REFUSE = "Accès refusé"


def utilisateur_courant(
    db: Annotated[Session, Depends(get_db)],
    session: Annotated[str | None, Cookie(alias=NOM_COOKIE)] = None,
) -> Utilisateur:
    id_utilisateur = lire_jeton(session) if session else None
    utilisateur = db.get(Utilisateur, id_utilisateur) if id_utilisateur else None
    if utilisateur is None or not utilisateur.actif:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, NON_AUTHENTIFIE)
    return utilisateur


UtilisateurCourant = Annotated[Utilisateur, Depends(utilisateur_courant)]


def exiger_role(*roles: Role) -> Callable[..., Utilisateur]:
    """Dépendance `Depends(exiger_role(Role.ADMIN))`. Sans rôle listé, personne ne passe."""
    autorises = frozenset(roles)

    def verifier(utilisateur: UtilisateurCourant) -> Utilisateur:
        if utilisateur.doit_changer_mdp:
            raise HTTPException(status.HTTP_403_FORBIDDEN, CHANGEMENT_MDP_REQUIS)
        if utilisateur.role not in autorises:
            raise HTTPException(status.HTTP_403_FORBIDDEN, ACCES_REFUSE)
        return utilisateur

    verifier.roles_autorises = autorises  # lu par le test « refus par défaut »
    return verifier


TOUS_LES_ROLES = (Role.RESPONSABLE, Role.ANALYSTE, Role.ADMIN)
