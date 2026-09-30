"""Création des comptes par l'administrateur (D-30) et premier admin en ligne de commande (D-29)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.api.utilisateurs import generer_mot_de_passe_temporaire
from app.creer_admin import CreationImpossible, creer_admin
from app.db import SessionLocal, engine
from app.main import app
from app.models import Journal
from app.securite.mots_de_passe import probleme_politique

MOT_DE_PASSE = "Admin-Initial-2026"
CSRF = {"X-Requested-With": "StockPredict"}
NOUVEAU = {
    "prenom": "Sarah",
    "nom": "Lefèvre",
    "email": "Sarah.Lefevre@globalretail.example",
    "role": "ANALYSTE",
}


@pytest.fixture(autouse=True)
def base_vide():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE journal, utilisateur RESTART IDENTITY CASCADE"))


@pytest.fixture
def admin():
    with SessionLocal() as db:
        return creer_admin(
            db,
            prenom="Steven",
            nom="Laurent",
            email="steven.laurent@globalretail.example",
            mot_de_passe=MOT_DE_PASSE,
        )


@pytest.fixture
def client_admin(admin):
    with TestClient(app, headers=CSRF) as c:
        r = c.post("/api/auth/login", json={"email": admin.email, "mot_de_passe": MOT_DE_PASSE})
        assert r.status_code == 200
        yield c


# --- Premier administrateur (ligne de commande) ------------------------------------------------


def test_creer_admin_sur_base_vide(admin):
    assert admin.role == "ADMIN" and admin.actif and not admin.doit_changer_mdp
    with SessionLocal() as db:
        assert db.scalar(select(Journal.action)) == "ADMIN_CREE_EN_LIGNE_DE_COMMANDE"


@pytest.mark.parametrize(
    ("email", "mot_de_passe", "message"),
    [
        ("pas-un-email", MOT_DE_PASSE, "invalide"),
        ("x@globalretail.example", "court", "12 caractères"),
    ],
)
def test_creer_admin_refuse_les_saisies_invalides(email, mot_de_passe, message):
    with SessionLocal() as db, pytest.raises(CreationImpossible, match=message):
        creer_admin(db, prenom="A", nom="B", email=email, mot_de_passe=mot_de_passe)


def test_creer_admin_refuse_un_email_existant(admin):
    with SessionLocal() as db, pytest.raises(CreationImpossible, match="existe déjà"):
        creer_admin(db, prenom="A", nom="B", email=admin.email.upper(), mot_de_passe=MOT_DE_PASSE)


# --- Création de comptes par l'admin -----------------------------------------------------------


def test_admin_cree_un_compte_avec_mot_de_passe_temporaire(client_admin):
    r = client_admin.post("/api/utilisateurs", json=NOUVEAU)
    assert r.status_code == 201
    corps = r.json()
    assert corps["utilisateur"]["email"] == "sarah.lefevre@globalretail.example"
    assert corps["utilisateur"]["role"] == "ANALYSTE"
    assert corps["utilisateur"]["doit_changer_mdp"] is True
    temporaire = corps["mot_de_passe_temporaire"]
    assert probleme_politique(temporaire) is None

    # Le nouvel utilisateur se connecte avec le mot de passe temporaire puis doit le changer
    with TestClient(app, headers=CSRF) as sarah:
        r = sarah.post(
            "/api/auth/login", json={"email": NOUVEAU["email"], "mot_de_passe": temporaire}
        )
        assert r.status_code == 200 and r.json()["doit_changer_mdp"] is True
        assert sarah.get("/api/utilisateurs").status_code == 403


def test_le_mot_de_passe_temporaire_n_est_stocke_nulle_part_en_clair(client_admin):
    temporaire = client_admin.post("/api/utilisateurs", json=NOUVEAU).json()[
        "mot_de_passe_temporaire"
    ]
    with engine.connect() as conn:
        journal = conn.execute(text("SELECT * FROM journal")).all()
        comptes = conn.execute(text("SELECT * FROM utilisateur")).all()
    tout = " ".join(str(ligne) for ligne in [*journal, *comptes])
    assert temporaire not in tout


def test_creation_journalisee_au_nom_de_l_admin(client_admin, admin):
    client_admin.post("/api/utilisateurs", json=NOUVEAU)
    with SessionLocal() as db:
        entree = db.scalar(select(Journal).where(Journal.action == "UTILISATEUR_CREE"))
    assert entree.id_utilisateur == admin.id_utilisateur
    assert entree.details["role"] == "ANALYSTE"


def test_email_deja_utilise_409(client_admin):
    assert client_admin.post("/api/utilisateurs", json=NOUVEAU).status_code == 201
    doublon = {**NOUVEAU, "email": NOUVEAU["email"].upper()}
    assert client_admin.post("/api/utilisateurs", json=doublon).status_code == 409


def test_role_inconnu_refuse(client_admin):
    assert (
        client_admin.post("/api/utilisateurs", json={**NOUVEAU, "role": "SUPERADMIN"}).status_code
        == 422
    )


def test_liste_des_comptes(client_admin):
    client_admin.post("/api/utilisateurs", json=NOUVEAU)
    emails = [u["email"] for u in client_admin.get("/api/utilisateurs").json()]
    assert emails == ["steven.laurent@globalretail.example", "sarah.lefevre@globalretail.example"]


@pytest.mark.parametrize("role", ["RESPONSABLE", "ANALYSTE"])
def test_seul_l_admin_gere_les_comptes(client_admin, role):
    temporaire = client_admin.post("/api/utilisateurs", json={**NOUVEAU, "role": role}).json()[
        "mot_de_passe_temporaire"
    ]
    with TestClient(app, headers=CSRF) as autre:
        autre.post("/api/auth/login", json={"email": NOUVEAU["email"], "mot_de_passe": temporaire})
        autre.post(
            "/api/auth/mot-de-passe",
            json={"mot_de_passe_actuel": temporaire, "nouveau_mot_de_passe": "Nouveau-Secret-2026"},
        )
        assert autre.get("/api/utilisateurs").status_code == 403
        assert (
            autre.post(
                "/api/utilisateurs", json={**NOUVEAU, "email": "x@globalretail.example"}
            ).status_code
            == 403
        )


def test_sans_session_401():
    with TestClient(app, headers=CSRF) as anonyme:
        assert anonyme.get("/api/utilisateurs").status_code == 401


def test_mots_de_passe_temporaires_differents_et_conformes():
    lot = {generer_mot_de_passe_temporaire() for _ in range(50)}
    assert len(lot) == 50
    assert all(probleme_politique(m) is None and len(m) == 16 for m in lot)
