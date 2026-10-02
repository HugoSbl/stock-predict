"""Gestion des comptes par l'administrateur (UC « Gérer les utilisateurs et les droits », D-30).

Les comptes sont créés par l'ADMIN (UC-01 : « compte actif créé par l'administrateur ») avec un
mot de passe temporaire, affiché une seule fois, à changer à la première connexion (D-10).
"""

import secrets
import string
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Utilisateur
from app.models.enums import Role
from app.securite.dependances import exiger_role
from app.securite.journal import journaliser
from app.securite.mots_de_passe import hacher, probleme_politique

router = APIRouter(prefix="/utilisateurs", tags=["utilisateurs"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[Utilisateur, Depends(exiger_role(Role.ADMIN))]


class UtilisateurAdminOut(BaseModel):
    id_utilisateur: int
    nom: str
    prenom: str
    email: str
    role: Role
    actif: bool
    doit_changer_mdp: bool
    derniere_connexion: datetime | None

    model_config = {"from_attributes": True}


class CreationUtilisateurIn(BaseModel):
    prenom: str = Field(min_length=1, max_length=100)
    nom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: Role


class CreationUtilisateurOut(BaseModel):
    utilisateur: UtilisateurAdminOut
    mot_de_passe_temporaire: str = Field(
        description="Affiché une seule fois pour être transmis ; jamais stocké en clair."
    )


def generer_mot_de_passe_temporaire() -> str:
    """16 caractères aléatoires (module secrets), conformes à la politique (D-27)."""
    alphabet = string.ascii_letters + string.digits + "-_!?"
    while True:
        candidat = "".join(secrets.choice(alphabet) for _ in range(16))
        if not probleme_politique(candidat) and any(c.isdigit() for c in candidat):
            return candidat


@router.get("", response_model=list[UtilisateurAdminOut])
def lister(_: Admin, db: Db) -> list[Utilisateur]:
    return list(db.scalars(select(Utilisateur).order_by(Utilisateur.nom, Utilisateur.prenom)))


@router.post(
    "",
    response_model=CreationUtilisateurOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Adresse e-mail déjà utilisée"}},
)
def creer(donnees: CreationUtilisateurIn, admin: Admin, request: Request, db: Db) -> dict:
    email = donnees.email.lower()
    if db.scalar(select(Utilisateur.id_utilisateur).where(func.lower(Utilisateur.email) == email)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Un compte existe déjà avec cette adresse e-mail"
        )
    temporaire = generer_mot_de_passe_temporaire()
    utilisateur = Utilisateur(
        prenom=donnees.prenom.strip(),
        nom=donnees.nom.strip(),
        email=email,
        role=donnees.role,
        mdp_hash=hacher(temporaire),
        actif=True,
        nb_echecs_connexion=0,
        doit_changer_mdp=True,
    )
    db.add(utilisateur)
    db.flush()
    journaliser(
        db,
        "UTILISATEUR_CREE",
        request=request,
        id_utilisateur=admin.id_utilisateur,
        details={"id_cree": utilisateur.id_utilisateur, "email": email, "role": donnees.role.value},
    )
    db.commit()
    return {"utilisateur": utilisateur, "mot_de_passe_temporaire": temporaire}
