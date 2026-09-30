"""Utilisateurs et journal d'audit (RG-12 à RG-15)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import Role, check_enum, enum_texte


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id_utilisateur: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    mdp_hash: Mapped[str] = mapped_column(String(255))  # RG-12 : jamais en clair
    role: Mapped[Role] = mapped_column(enum_texte(Role, "role"))
    actif: Mapped[bool] = mapped_column(default=True)
    # D-02
    nb_echecs_connexion: Mapped[int] = mapped_column(default=0)
    verrouille_jusqu_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # D-10
    doit_changer_mdp: Mapped[bool] = mapped_column(default=False)

    __table_args__ = (check_enum("role", Role),)


class Journal(Base):
    """Journal d'audit (RG-14). id_utilisateur NULL = action système (ordonnanceur)."""

    __tablename__ = "journal"

    id_log: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    date_action: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    action: Mapped[str] = mapped_column(String(60))
    adresse_ip: Mapped[str | None] = mapped_column(INET)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    id_utilisateur: Mapped[int | None] = mapped_column(ForeignKey("utilisateur.id_utilisateur"))

    __table_args__ = (
        Index("ix_journal_date_action", "date_action"),
        Index("ix_journal_action_date", "action", "date_action"),
        Index("ix_journal_id_utilisateur", "id_utilisateur"),
        Index("ix_journal_details", "details", postgresql_using="gin"),  # §3.3
    )
