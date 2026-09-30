"""Modèles SQLAlchemy (tables du MLD + amendements docs/decisions.md).

Chaque module de modèles doit être importé ici pour qu'Alembic les détecte (autogenerate).
"""

from app.models.activite import (
    CommandeFournisseur,
    LigneCommande,
    Stock,
    StockQuotidien,
    Vente,
)
from app.models.pilotage import Alerte, KpiQuotidien, Prevision
from app.models.referentiel import (
    Calendrier,
    Categorie,
    Entrepot,
    Fournisseur,
    Pays,
    Produit,
    Promotion,
    produit_promotion,
)
from app.models.securite import Journal, Utilisateur
from app.models.synchro import LigneRejetee, SourceApi, Synchronisation

__all__ = [
    "Alerte",
    "Calendrier",
    "Categorie",
    "CommandeFournisseur",
    "Entrepot",
    "Fournisseur",
    "Journal",
    "KpiQuotidien",
    "LigneCommande",
    "LigneRejetee",
    "Pays",
    "Prevision",
    "Produit",
    "Promotion",
    "SourceApi",
    "Stock",
    "StockQuotidien",
    "Synchronisation",
    "Utilisateur",
    "Vente",
    "produit_promotion",
]
