"""Salissage déterministe des données exposées par les API (RG-01, RG-02).

Environ 5 % des lignes sont corrompues (type invalide, quantité négative, produit ou entrepôt
inconnu, doublon strict) et chaque ligne porte des colonnes que le schéma cible ne connaît pas.
Le choix des lignes dépend uniquement de (source, jour, rang) : même réponse à chaque appel.
"""

import hashlib
from collections.abc import Callable
from typing import Any

from app.monde.parametres import GRAINE, TAUX_LIGNES_INVALIDES

Ligne = dict[str, Any]


def _alea(*cles: object) -> float:
    empreinte = hashlib.blake2b(":".join(map(str, (GRAINE, *cles))).encode(), digest_size=8)
    return int.from_bytes(empreinte.digest(), "big") / 2**64


def _quantite_negative(champ: str) -> Callable[[Ligne], Ligne]:
    return lambda ligne: {**ligne, champ: -abs(int(ligne[champ])) - 1}


def _type_invalide(champ: str) -> Callable[[Ligne], Ligne]:
    return lambda ligne: {**ligne, champ: "N/A"}


def _produit_inconnu(ligne: Ligne) -> Ligne:
    return {**ligne, "sku": "REF-0000"}


def _entrepot_inconnu(ligne: Ligne) -> Ligne:
    return {**ligne, "warehouse_code": "XX-INC"}


def corruptions(champ_quantite: str) -> list[Callable[[Ligne], Ligne] | None]:
    """Types de corruption ; None = doublon strict (la ligne est émise deux fois)."""
    return [
        _quantite_negative(champ_quantite),
        _type_invalide(champ_quantite),
        _produit_inconnu,
        _entrepot_inconnu,
        None,
    ]


def salir(
    lignes: list[Ligne],
    source: str,
    cle_jour: str,
    champ_quantite: str,
    taux: float = TAUX_LIGNES_INVALIDES,
) -> list[Ligne]:
    types = corruptions(champ_quantite)
    resultat: list[Ligne] = []
    for rang, ligne in enumerate(lignes):
        if _alea(source, cle_jour, rang, "salir") >= taux:
            resultat.append(ligne)
            continue
        corruption = types[int(_alea(source, cle_jour, rang, "type") * len(types))]
        if corruption is None:
            resultat.extend([ligne, dict(ligne)])
        else:
            resultat.append(corruption(ligne))
    return resultat
