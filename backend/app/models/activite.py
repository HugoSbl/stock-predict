"""Données d'activité alimentées par les sources : ventes, stocks, commandes fournisseurs."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import StatutCommande, check_enum, enum_texte


class Stock(Base):
    """Stock courant d'un couple produit × entrepôt (association STOCKER) = dernier relevé WMS."""

    __tablename__ = "stock"

    id_produit: Mapped[int] = mapped_column(ForeignKey("produit.id_produit"), primary_key=True)
    id_entrepot: Mapped[int] = mapped_column(ForeignKey("entrepot.id_entrepot"), primary_key=True)
    quantite_stock: Mapped[int]
    date_maj: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("quantite_stock >= 0", name="quantite_stock"),
        Index("ix_stock_id_entrepot", "id_entrepot"),
    )


class StockQuotidien(Base):
    """Relevé de stock de fin de journée envoyé par le WMS (D-20).

    Sert à tracer l'historique des courbes de stock.
    """

    __tablename__ = "stock_quotidien"

    id_produit: Mapped[int] = mapped_column(ForeignKey("produit.id_produit"), primary_key=True)
    id_entrepot: Mapped[int] = mapped_column(ForeignKey("entrepot.id_entrepot"), primary_key=True)
    date_releve: Mapped[date] = mapped_column(ForeignKey("calendrier.date_jour"), primary_key=True)
    quantite_stock: Mapped[int]

    __table_args__ = (
        CheckConstraint("quantite_stock >= 0", name="quantite_stock"),
        Index("ix_stock_quotidien_date_releve", "date_releve"),
    )


class Vente(Base):
    """Ventes journalières agrégées par produit × entrepôt (D-19).

    Table partitionnée par mois sur date_vente (§3.3) : la clé primaire inclut donc date_vente.
    Les partitions sont créées par la fonction SQL creer_partitions_vente() (migration initiale).
    """

    __tablename__ = "vente"

    id_vente: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    date_vente: Mapped[date] = mapped_column(
        Date, ForeignKey("calendrier.date_jour"), primary_key=True
    )
    quantite_vendue: Mapped[int]
    prix_vente_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    id_produit: Mapped[int] = mapped_column(ForeignKey("produit.id_produit"))
    id_entrepot: Mapped[int] = mapped_column(ForeignKey("entrepot.id_entrepot"))

    __table_args__ = (
        # Doublon strict (RG-02) : une seule ligne par jour × produit × entrepôt
        UniqueConstraint("date_vente", "id_produit", "id_entrepot"),
        CheckConstraint("quantite_vendue >= 0", name="quantite_vendue"),
        CheckConstraint("prix_vente_ht >= 0", name="prix_vente_ht"),
        Index("ix_vente_produit_entrepot_date", "id_produit", "id_entrepot", "date_vente"),
        {"postgresql_partition_by": "RANGE (date_vente)"},
    )


class CommandeFournisseur(Base):
    __tablename__ = "commande_fournisseur"

    id_commande: Mapped[int] = mapped_column(primary_key=True)
    numero_commande: Mapped[str] = mapped_column(String(30), unique=True)  # D-19
    date_achat: Mapped[date]
    date_livraison_estimee: Mapped[date]
    date_livraison_reelle: Mapped[date | None]
    statut: Mapped[StatutCommande] = mapped_column(enum_texte(StatutCommande, "statut"))
    id_fournisseur: Mapped[int] = mapped_column(
        ForeignKey("fournisseur.id_fournisseur"), index=True
    )
    id_entrepot: Mapped[int] = mapped_column(ForeignKey("entrepot.id_entrepot"), index=True)

    __table_args__ = (
        check_enum("statut", StatutCommande),
        CheckConstraint("date_livraison_estimee >= date_achat", name="dates"),
        # Commandes en cours : utilisées par le stock projeté (D-06) et UC-04 3a
        Index(
            "ix_commande_fournisseur_en_cours",
            "id_entrepot",
            "date_livraison_estimee",
            postgresql_where="statut = 'EN_COURS'",
        ),
    )


class LigneCommande(Base):
    """Association COMPOSER : quantités commandées par produit."""

    __tablename__ = "ligne_commande"

    id_commande: Mapped[int] = mapped_column(
        ForeignKey("commande_fournisseur.id_commande", ondelete="CASCADE"), primary_key=True
    )
    id_produit: Mapped[int] = mapped_column(ForeignKey("produit.id_produit"), primary_key=True)
    quantite_commandee: Mapped[int]

    __table_args__ = (
        CheckConstraint("quantite_commandee > 0", name="quantite_commandee"),
        Index("ix_ligne_commande_id_produit", "id_produit"),
    )
