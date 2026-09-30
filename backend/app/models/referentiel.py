"""Référentiels : pays, catégories, fournisseurs, entrepôts, produits, calendrier, promotions."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Table,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Pays(Base):
    __tablename__ = "pays"

    code_pays: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    nom_pays: Mapped[str] = mapped_column(String(100))
    taux_tva: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # en %, ex. 20.00
    devise: Mapped[str] = mapped_column(CHAR(3))

    __table_args__ = (CheckConstraint("taux_tva >= 0 AND taux_tva < 100", name="taux_tva"),)


class Categorie(Base):
    __tablename__ = "categorie"

    id_categorie: Mapped[int] = mapped_column(primary_key=True)
    libelle_categorie: Mapped[str] = mapped_column(String(100), unique=True)


class Fournisseur(Base):
    __tablename__ = "fournisseur"

    id_fournisseur: Mapped[int] = mapped_column(primary_key=True)
    code_fournisseur: Mapped[str] = mapped_column(String(20), unique=True)  # D-19
    nom_fournisseur: Mapped[str] = mapped_column(String(150))
    pays_fournisseur: Mapped[str] = mapped_column(String(100))
    delai_moyen_jours: Mapped[int] = mapped_column(SmallInteger)

    __table_args__ = (CheckConstraint("delai_moyen_jours > 0", name="delai_moyen_jours"),)


class Entrepot(Base):
    __tablename__ = "entrepot"

    id_entrepot: Mapped[int] = mapped_column(primary_key=True)
    code_entrepot: Mapped[str] = mapped_column(String(20), unique=True)  # D-19
    nom_entrepot: Mapped[str] = mapped_column(String(100))
    ville: Mapped[str] = mapped_column(String(100))
    capacite_max: Mapped[int]
    code_pays: Mapped[str] = mapped_column(ForeignKey("pays.code_pays"), index=True)  # RG-04

    __table_args__ = (CheckConstraint("capacite_max > 0", name="capacite_max"),)


class Produit(Base):
    __tablename__ = "produit"

    id_produit: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(20), unique=True)
    libelle: Mapped[str] = mapped_column(String(200))
    prix_unitaire_ht: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    seuil_alerte: Mapped[int]
    id_categorie: Mapped[int] = mapped_column(ForeignKey("categorie.id_categorie"), index=True)
    id_fournisseur_habituel: Mapped[int | None] = mapped_column(  # D-22
        ForeignKey("fournisseur.id_fournisseur"), index=True
    )

    __table_args__ = (
        CheckConstraint("seuil_alerte >= 0", name="seuil_alerte"),  # RG-11
        CheckConstraint("prix_unitaire_ht >= 0", name="prix_unitaire_ht"),
    )


class Calendrier(Base):
    """Dimension temps (RG-07) : connue aussi pour les dates futures."""

    __tablename__ = "calendrier"

    date_jour: Mapped[date] = mapped_column(Date, primary_key=True)
    jour_semaine: Mapped[int] = mapped_column(SmallInteger)  # 1 = lundi … 7 = dimanche (ISO)
    numero_semaine: Mapped[int] = mapped_column(SmallInteger)
    mois: Mapped[int] = mapped_column(SmallInteger)
    annee: Mapped[int] = mapped_column(SmallInteger)  # D-21
    ferie_fr: Mapped[bool]
    ferie_de: Mapped[bool]
    vacances_fr: Mapped[bool]  # D-21 : vacances distinctes par pays
    vacances_de: Mapped[bool]

    __table_args__ = (
        CheckConstraint("jour_semaine BETWEEN 1 AND 7", name="jour_semaine"),
        CheckConstraint("mois BETWEEN 1 AND 12", name="mois"),
    )


produit_promotion = Table(
    "produit_promotion",
    Base.metadata,
    Column(
        "id_promotion", ForeignKey("promotion.id_promotion", ondelete="CASCADE"), primary_key=True
    ),
    Column("id_produit", ForeignKey("produit.id_produit", ondelete="CASCADE"), primary_key=True),
)


class Promotion(Base):
    __tablename__ = "promotion"

    id_promotion: Mapped[int] = mapped_column(primary_key=True)
    libelle: Mapped[str] = mapped_column(String(200))
    date_debut: Mapped[date]
    date_fin: Mapped[date]
    taux_remise: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # en %, ex. 25.00

    __table_args__ = (
        CheckConstraint("date_fin >= date_debut", name="dates"),
        CheckConstraint("taux_remise > 0 AND taux_remise < 100", name="taux_remise"),
    )
