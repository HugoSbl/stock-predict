"""Authentification (UC-01) : connexion, déconnexion, session, changement de mot de passe."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Utilisateur
from app.models.enums import Role
from app.securite import mots_de_passe
from app.securite.dependances import UtilisateurCourant, utilisateur_courant
from app.securite.horloge import maintenant
from app.securite.jetons import NOM_COOKIE, creer_jeton
from app.securite.journal import journaliser

router = APIRouter(prefix="/auth", tags=["authentification"])

IDENTIFIANTS_INCORRECTS = "Identifiants incorrects"
COMPTE_VERROUILLE = (
    "Compte temporairement verrouillé suite à plusieurs échecs. Réessayez plus tard."
)

Db = Annotated[Session, Depends(get_db)]


class ConnexionIn(BaseModel):
    email: EmailStr
    mot_de_passe: str = Field(min_length=1, max_length=256)


class ChangementMotDePasseIn(BaseModel):
    mot_de_passe_actuel: str = Field(min_length=1, max_length=256)
    nouveau_mot_de_passe: str = Field(min_length=1, max_length=256)


class UtilisateurOut(BaseModel):
    id_utilisateur: int
    nom: str
    prenom: str
    email: str
    role: Role
    doit_changer_mdp: bool

    model_config = {"from_attributes": True}


def _motif_echec(utilisateur: Utilisateur | None) -> str:
    """Motif interne, journalisé uniquement : la réponse HTTP reste générique (A07)."""
    if utilisateur is None:
        return "compte_inconnu"
    return "compte_inactif" if not utilisateur.actif else "mot_de_passe_invalide"


def _poser_cookie(response: Response, id_utilisateur: int) -> None:
    response.set_cookie(
        NOM_COOKIE,
        creer_jeton(id_utilisateur),
        max_age=settings.session_duree_heures * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/api",
    )


@router.post(
    "/login",
    response_model=UtilisateurOut,
    responses={
        401: {"description": "Identifiants incorrects"},
        423: {"description": "Compte verrouillé"},
    },
)
def connexion(donnees: ConnexionIn, request: Request, response: Response, db: Db) -> Utilisateur:
    email = donnees.email.lower()
    utilisateur = db.scalar(select(Utilisateur).where(func.lower(Utilisateur.email) == email))
    instant = maintenant()

    # Compte verrouillé (RG-15) : le mot de passe n'est même pas vérifié
    if utilisateur and utilisateur.verrouille_jusqu_a and utilisateur.verrouille_jusqu_a > instant:
        journaliser(
            db,
            "CONNEXION_REFUSEE_VERROUILLAGE",
            request=request,
            id_utilisateur=utilisateur.id_utilisateur,
        )
        db.commit()
        raise HTTPException(status.HTTP_423_LOCKED, COMPTE_VERROUILLE)

    mot_de_passe_ok = mots_de_passe.verifier(
        utilisateur.mdp_hash if utilisateur else None, donnees.mot_de_passe
    )
    if utilisateur is None or not utilisateur.actif or not mot_de_passe_ok:
        details = {"email": email, "motif": _motif_echec(utilisateur)}
        if utilisateur is not None:
            utilisateur.nb_echecs_connexion += 1
            details["echecs_consecutifs"] = utilisateur.nb_echecs_connexion
            if utilisateur.nb_echecs_connexion >= settings.echecs_avant_verrouillage:
                utilisateur.verrouille_jusqu_a = instant + timedelta(
                    minutes=settings.duree_verrouillage_minutes
                )
                utilisateur.nb_echecs_connexion = 0
                journaliser(
                    db,
                    "COMPTE_VERROUILLE",
                    request=request,
                    id_utilisateur=utilisateur.id_utilisateur,
                    details={"jusqu_a": utilisateur.verrouille_jusqu_a.isoformat()},
                )
        journaliser(
            db,
            "CONNEXION_ECHEC",
            request=request,
            id_utilisateur=utilisateur.id_utilisateur if utilisateur else None,
            details=details,
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, IDENTIFIANTS_INCORRECTS)

    utilisateur.nb_echecs_connexion = 0
    utilisateur.verrouille_jusqu_a = None
    utilisateur.derniere_connexion = instant
    if mots_de_passe.doit_etre_rehache(utilisateur.mdp_hash):
        utilisateur.mdp_hash = mots_de_passe.hacher(donnees.mot_de_passe)
    journaliser(db, "CONNEXION", request=request, id_utilisateur=utilisateur.id_utilisateur)
    db.commit()
    _poser_cookie(response, utilisateur.id_utilisateur)
    return utilisateur


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def deconnexion(request: Request, response: Response, db: Db) -> None:
    """Toujours accessible : efface le cookie ; journalise si une session valide existait."""
    try:
        utilisateur = utilisateur_courant(db, request.cookies.get(NOM_COOKIE))
        journaliser(db, "DECONNEXION", request=request, id_utilisateur=utilisateur.id_utilisateur)
        db.commit()
    except HTTPException:
        pass
    response.delete_cookie(
        NOM_COOKIE, path="/api", httponly=True, samesite="strict", secure=settings.cookie_secure
    )


@router.get("/me", response_model=UtilisateurOut)
def moi(utilisateur: UtilisateurCourant) -> Utilisateur:
    return utilisateur


@router.post(
    "/mot-de-passe",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={400: {"description": "Mot de passe actuel incorrect ou politique non respectée"}},
)
def changer_mot_de_passe(
    donnees: ChangementMotDePasseIn, utilisateur: UtilisateurCourant, request: Request, db: Db
) -> None:
    if not mots_de_passe.verifier(utilisateur.mdp_hash, donnees.mot_de_passe_actuel):
        journaliser(
            db, "MOT_DE_PASSE_ECHEC", request=request, id_utilisateur=utilisateur.id_utilisateur
        )
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    if probleme := mots_de_passe.probleme_politique(donnees.nouveau_mot_de_passe):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, probleme)
    if donnees.nouveau_mot_de_passe == donnees.mot_de_passe_actuel:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Le nouveau mot de passe doit être différent"
        )
    utilisateur.mdp_hash = mots_de_passe.hacher(donnees.nouveau_mot_de_passe)
    utilisateur.doit_changer_mdp = False
    journaliser(
        db, "MOT_DE_PASSE_MODIFIE", request=request, id_utilisateur=utilisateur.id_utilisateur
    )
    db.commit()
