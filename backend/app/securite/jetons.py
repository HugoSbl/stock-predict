"""Jeton de session (JWT signé HS256), transporté dans un cookie httpOnly (D-12)."""

from datetime import timedelta

import jwt

from app.config import settings
from app.securite.horloge import maintenant

NOM_COOKIE = "stockpredict_session"
ALGORITHME = "HS256"


def creer_jeton(id_utilisateur: int) -> str:
    emis = maintenant()
    charge = {
        "sub": str(id_utilisateur),
        "iat": emis,
        "exp": emis + timedelta(hours=settings.session_duree_heures),
    }
    return jwt.encode(charge, settings.jwt_secret, algorithm=ALGORITHME)


def lire_jeton(jeton: str) -> int | None:
    """Identifiant de l'utilisateur, ou None si le jeton est invalide ou expiré.

    L'expiration est comparée à `maintenant()` (même horloge que l'émission) plutôt qu'à
    l'horloge interne de PyJWT.
    """
    try:
        charge = jwt.decode(
            jeton,
            settings.jwt_secret,
            algorithms=[ALGORITHME],
            options={"require": ["sub", "exp", "iat"], "verify_exp": False},
        )
        if charge["exp"] <= maintenant().timestamp():
            return None
        return int(charge["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
