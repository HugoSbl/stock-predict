"""Sources API, exécutions de synchronisation et lignes rejetées (UC-03, RG-01 à RG-03)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import (
    Declencheur,
    MotifRejet,
    StatutSynchro,
    TypeDonneesSource,
    check_enum,
    enum_texte,
)


class SourceApi(Base):
    """Configuration d'un connecteur (D-04).

    Le secret n'est jamais en base : seulement le nom de la variable d'environnement.
    """

    __tablename__ = "source_api"

    id_source: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True)
    url: Mapped[str] = mapped_column(String(500))
    type_donnees: Mapped[TypeDonneesSource] = mapped_column(
        enum_texte(TypeDonneesSource, "type_donnees")
    )
    # { "colonne_source": "colonne_cible", ... } — les colonnes absentes sont ignorées (RG-01)
    mapping_colonnes: Mapped[dict[str, str]] = mapped_column(JSONB)
    frequence_cron: Mapped[str] = mapped_column(String(50))
    actif: Mapped[bool] = mapped_column(default=True)
    nom_variable_secret: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (check_enum("type_donnees", TypeDonneesSource),)


class Synchronisation(Base):
    __tablename__ = "synchronisation"

    id_synchro: Mapped[int] = mapped_column(primary_key=True)
    date_debut: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    date_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    id_source: Mapped[int] = mapped_column(ForeignKey("source_api.id_source"))  # D-04
    declencheur: Mapped[Declencheur] = mapped_column(enum_texte(Declencheur, "declencheur"))
    lignes_integrees: Mapped[int] = mapped_column(default=0)
    lignes_rejetees: Mapped[int] = mapped_column(default=0)
    colonnes_ignorees: Mapped[list[str] | None] = mapped_column(JSONB)  # RG-01 : compte rendu
    tentatives: Mapped[int] = mapped_column(default=0)
    statut: Mapped[StatutSynchro] = mapped_column(enum_texte(StatutSynchro, "statut"))
    message_erreur: Mapped[str | None] = mapped_column(Text)
    # Utilisateur à l'origine d'un forçage manuel ; NULL si ordonnanceur
    id_utilisateur: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id_utilisateur"))

    __table_args__ = (
        check_enum("declencheur", Declencheur),
        check_enum("statut", StatutSynchro),
        Index("ix_synchronisation_source_debut", "id_source", "date_debut"),
    )


class LigneRejetee(Base):
    """Ligne source rejetée (D-03), exportable.

    Écrite hors de la transaction d'import : elle survit au rollback (RG-03).
    """

    __tablename__ = "ligne_rejetee"

    id_rejet: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id_synchro: Mapped[int] = mapped_column(
        ForeignKey("synchronisation.id_synchro", ondelete="CASCADE"), index=True
    )
    numero_ligne: Mapped[int]
    donnees: Mapped[dict[str, Any]] = mapped_column(JSONB)
    motif: Mapped[MotifRejet] = mapped_column(enum_texte(MotifRejet, "motif"))

    __table_args__ = (check_enum("motif", MotifRejet),)
