"""Énumérations métier.

Stockées en VARCHAR + CHECK : plus simple à faire évoluer qu'un ENUM PostgreSQL.
"""

from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum


class Role(StrEnum):
    RESPONSABLE = "RESPONSABLE"
    ANALYSTE = "ANALYSTE"
    ADMIN = "ADMIN"


class StatutCommande(StrEnum):
    EN_COURS = "EN_COURS"
    LIVREE = "LIVREE"
    ANNULEE = "ANNULEE"


class TypeAlerte(StrEnum):
    SOUS_SEUIL = "SOUS_SEUIL"
    RUPTURE_PREVUE = "RUPTURE_PREVUE"
    SURSTOCK = "SURSTOCK"


class StatutAlerte(StrEnum):
    OUVERTE = "OUVERTE"
    TRAITEE = "TRAITEE"
    IGNOREE = "IGNOREE"


class TypeDonneesSource(StrEnum):
    VENTES = "VENTES"
    STOCKS = "STOCKS"
    COMMANDES = "COMMANDES"


class Declencheur(StrEnum):
    CRON = "CRON"
    MANUEL = "MANUEL"


class StatutSynchro(StrEnum):
    EN_COURS = "EN_COURS"
    SUCCES = "SUCCES"
    ECHEC_API = "ECHEC_API"
    ECHEC = "ECHEC"


class MotifRejet(StrEnum):
    TYPE_INVALIDE = "TYPE_INVALIDE"
    QUANTITE_NEGATIVE = "QUANTITE_NEGATIVE"
    PRODUIT_INCONNU = "PRODUIT_INCONNU"
    ENTREPOT_INCONNU = "ENTREPOT_INCONNU"
    DOUBLON = "DOUBLON"


def enum_texte(enum_cls: type[StrEnum], nom: str) -> Enum:
    """Type VARCHAR portant l'énumération côté Python (sans contrainte : voir check_enum)."""
    return Enum(
        enum_cls,
        name=nom,
        native_enum=False,
        create_constraint=False,
        length=max(len(v) for v in enum_cls),
        values_callable=lambda e: [m.value for m in e],
    )


def check_enum(colonne: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    """Contrainte CHECK unique et nommée (ck_<table>_<colonne>) limitant la colonne aux valeurs."""
    valeurs = ", ".join(f"'{m.value}'" for m in enum_cls)
    return CheckConstraint(f"{colonne} IN ({valeurs})", name=colonne)
