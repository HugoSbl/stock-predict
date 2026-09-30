"""Hachage des mots de passe (RG-12) : argon2id, jamais stockés ni journalisés en clair."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hacheur = PasswordHasher()  # argon2id, paramètres recommandés par la bibliothèque

# Hash factice : vérifié quand l'e-mail est inconnu, pour que le temps de réponse ne révèle pas
# l'existence d'un compte.
_HASH_FACTICE = _hacheur.hash("mot-de-passe-factice-pour-temps-constant")

LONGUEUR_MINIMALE = 12


def hacher(mot_de_passe: str) -> str:
    return _hacheur.hash(mot_de_passe)


def verifier(hash_stocke: str | None, mot_de_passe: str) -> bool:
    try:
        return (
            _hacheur.verify(hash_stocke or _HASH_FACTICE, mot_de_passe) and hash_stocke is not None
        )
    except (VerificationError, InvalidHashError):
        return False


def doit_etre_rehache(hash_stocke: str) -> bool:
    return _hacheur.check_needs_rehash(hash_stocke)


def probleme_politique(mot_de_passe: str) -> str | None:
    """Politique minimale (D-27) : longueur, et mélange de lettres et de chiffres ou symboles."""
    if len(mot_de_passe) < LONGUEUR_MINIMALE:
        return f"Le mot de passe doit contenir au moins {LONGUEUR_MINIMALE} caractères."
    if mot_de_passe.isalpha() or mot_de_passe.isdigit():
        return "Le mot de passe doit mélanger lettres et chiffres ou symboles."
    return None
