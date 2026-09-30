"""Prévisions, alertes et instantanés de KPI."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import StatutAlerte, TypeAlerte, check_enum, enum_texte


class Prevision(Base):
    """Demande journalière prévue par couple produit × entrepôt (D-05), une ligne par date cible."""

    __tablename__ = "prevision"

    id_prevision: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    date_calcul: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_cible: Mapped[date]
    quantite_prevue: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    borne_basse: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # quantile 2,5 %
    borne_haute: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # quantile 97,5 %
    version_modele: Mapped[str] = mapped_column(String(80))  # RG-08
    fiabilite_reduite: Mapped[bool] = mapped_column(default=False)  # UC-02 2b
    id_produit: Mapped[int] = mapped_column(ForeignKey("produit.id_produit"))
    id_entrepot: Mapped[int] = mapped_column(ForeignKey("entrepot.id_entrepot"))

    __table_args__ = (
        CheckConstraint(
            "borne_basse <= quantite_prevue AND quantite_prevue <= borne_haute", name="ic"
        ),
        Index(
            "ix_prevision_couple_calcul", "id_produit", "id_entrepot", "date_calcul", "date_cible"
        ),
    )


class Alerte(Base):
    __tablename__ = "alerte"

    id_alerte: Mapped[int] = mapped_column(primary_key=True)
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    type_alerte: Mapped[TypeAlerte] = mapped_column(enum_texte(TypeAlerte, "type_alerte"))
    message: Mapped[str] = mapped_column(Text)
    statut_alerte: Mapped[StatutAlerte] = mapped_column(
        enum_texte(StatutAlerte, "statut_alerte"), default=StatutAlerte.OUVERTE
    )
    id_produit: Mapped[int] = mapped_column(ForeignKey("produit.id_produit"))
    id_entrepot: Mapped[int] = mapped_column(ForeignKey("entrepot.id_entrepot"))
    # D-01
    date_rupture_estimee: Mapped[date | None]
    quantite_recommandee: Mapped[int | None]
    date_commande_conseillee: Mapped[date | None]
    motif: Mapped[str | None] = mapped_column(Text)
    id_commande: Mapped[int | None] = mapped_column(ForeignKey("commande_fournisseur.id_commande"))
    id_utilisateur_traitement: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateur.id_utilisateur")
    )
    date_traitement: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        check_enum("type_alerte", TypeAlerte),
        check_enum("statut_alerte", StatutAlerte),
        # RG-10 : « ignorée » exige un motif
        CheckConstraint(
            "statut_alerte <> 'IGNOREE' OR (motif IS NOT NULL AND length(trim(motif)) > 0)",
            name="motif_si_ignoree",
        ),
        # D-01 : une seule alerte ouverte par couple × type
        Index(
            "uq_alerte_ouverte_couple_type",
            "id_produit",
            "id_entrepot",
            "type_alerte",
            unique=True,
            postgresql_where="statut_alerte = 'OUVERTE'",
        ),
        # Index partiel sur les alertes actives (§3.3)
        Index(
            "ix_alerte_ouvertes",
            "id_entrepot",
            "type_alerte",
            postgresql_where="statut_alerte = 'OUVERTE'",
        ),
    )


class KpiQuotidien(Base):
    """Instantané quotidien des KPI par entrepôt (D-07) : agrégeable par pays / groupe (RG-04)."""

    __tablename__ = "kpi_quotidien"

    date_kpi: Mapped[date] = mapped_column(primary_key=True)
    id_entrepot: Mapped[int] = mapped_column(ForeignKey("entrepot.id_entrepot"), primary_key=True)
    code_pays: Mapped[str] = mapped_column(CHAR(2), ForeignKey("pays.code_pays"))
    nb_couples: Mapped[int]
    nb_couples_disponibles: Mapped[int]  # stock > 0 → taux de disponibilité
    nb_sous_seuil: Mapped[int]
    nb_ruptures_prevues: Mapped[int]
    valeur_surstock_ht: Mapped[Decimal] = mapped_column(Numeric(14, 2))
