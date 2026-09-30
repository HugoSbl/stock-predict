"""Comptes de démonstration : un par rôle, personnages des parcours du dossier (§2.4).

    python -m app.comptes_demo

Mot de passe commun lu dans DEMO_MOT_DE_PASSE (.env) : jamais de secret dans le code.
Idempotent : crée ou réinitialise les comptes (mot de passe, rôle, déverrouillage).
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Utilisateur
from app.models.enums import Role
from app.securite.journal import journaliser
from app.securite.mots_de_passe import hacher, probleme_politique

COMPTES = [
    ("Bernard", "Paul", "paul.bernard@globalretail.example", Role.RESPONSABLE),
    ("Lefèvre", "Sarah", "sarah.lefevre@globalretail.example", Role.ANALYSTE),
    ("Laurent", "Steven", "steven.laurent@globalretail.example", Role.ADMIN),
]


def creer_comptes_demo(db: Session, mot_de_passe: str) -> list[str]:
    if probleme := probleme_politique(mot_de_passe):
        raise ValueError(f"DEMO_MOT_DE_PASSE invalide : {probleme}")
    hash_ = hacher(mot_de_passe)
    emails = []
    for nom, prenom, email, role in COMPTES:
        compte = db.scalar(select(Utilisateur).where(Utilisateur.email == email))
        if compte is None:
            compte = Utilisateur(nom=nom, prenom=prenom, email=email)
            db.add(compte)
        compte.role = role
        compte.mdp_hash = hash_
        compte.actif = True
        compte.nb_echecs_connexion = 0
        compte.verrouille_jusqu_a = None
        compte.doit_changer_mdp = False
        emails.append(email)
    journaliser(db, "COMPTES_DEMO_INITIALISES", details={"comptes": emails})
    db.commit()
    return emails


def main() -> None:
    if not settings.demo_mot_de_passe:
        print("DEMO_MOT_DE_PASSE absent : comptes de démonstration non créés.", file=sys.stderr)
        sys.exit(1)
    with SessionLocal() as db:
        for email in creer_comptes_demo(db, settings.demo_mot_de_passe):
            print(f"  compte prêt : {email}")


if __name__ == "__main__":
    main()
