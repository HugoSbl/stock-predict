"""Création d'un compte administrateur en ligne de commande (D-29).

    npm run creer-admin            (ou : python -m app.creer_admin)

Sert à créer le tout premier ADMIN d'une base vide, ou à rétablir un accès administrateur perdu.
Le mot de passe est saisi sans écho et n'apparaît ni dans le code, ni dans .env, ni dans le journal.
"""

import getpass
import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Utilisateur
from app.models.enums import Role
from app.securite.journal import journaliser
from app.securite.mots_de_passe import hacher, probleme_politique


class CreationImpossible(Exception):
    pass


def creer_admin(
    db: Session, *, prenom: str, nom: str, email: str, mot_de_passe: str
) -> Utilisateur:
    email = email.strip().lower()
    if "@" not in email:
        raise CreationImpossible("Adresse e-mail invalide.")
    if probleme := probleme_politique(mot_de_passe):
        raise CreationImpossible(probleme)
    if db.scalar(select(Utilisateur.id_utilisateur).where(func.lower(Utilisateur.email) == email)):
        raise CreationImpossible(f"Un compte existe déjà pour {email}.")
    admin = Utilisateur(
        prenom=prenom.strip(),
        nom=nom.strip(),
        email=email,
        role=Role.ADMIN,
        mdp_hash=hacher(mot_de_passe),
        actif=True,
        nb_echecs_connexion=0,
        doit_changer_mdp=False,
    )
    db.add(admin)
    db.flush()
    journaliser(
        db,
        "ADMIN_CREE_EN_LIGNE_DE_COMMANDE",
        details={"id_cree": admin.id_utilisateur, "email": email},
    )
    db.commit()
    return admin


def _demander(question: str) -> str:
    while not (reponse := input(question).strip()):
        pass
    return reponse


def main() -> None:
    print("Création d'un compte administrateur StockPredict")
    prenom = _demander("Prénom : ")
    nom = _demander("Nom : ")
    email = _demander("Adresse e-mail : ")
    mot_de_passe = getpass.getpass(
        "Mot de passe (12 caractères min., lettres + chiffres/symboles) : "
    )
    if getpass.getpass("Confirmation : ") != mot_de_passe:
        sys.exit("Les deux saisies ne correspondent pas.")
    try:
        with SessionLocal() as db:
            admin = creer_admin(db, prenom=prenom, nom=nom, email=email, mot_de_passe=mot_de_passe)
    except CreationImpossible as erreur:
        sys.exit(f"Échec : {erreur}")
    print(f"Compte administrateur créé : {admin.email}")


if __name__ == "__main__":
    main()
