"""Authentification (UC-01, RG-12 à RG-15, D-10, D-12)."""

import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.api import auth as module_auth
from app.db import SessionLocal, engine
from app.main import app
from app.models import Journal, Utilisateur
from app.models.enums import Role
from app.securite import jetons
from app.securite.jetons import NOM_COOKIE
from app.securite.mots_de_passe import hacher

MOT_DE_PASSE = "Lait-UHT-4512-demo"
EMAIL = "paul.bernard@globalretail.example"
CSRF = {"X-Requested-With": "StockPredict"}


@pytest.fixture(autouse=True)
def comptes():
    with SessionLocal() as db:
        db.add_all(
            [
                Utilisateur(
                    nom="Bernard",
                    prenom="Paul",
                    email=EMAIL,
                    mdp_hash=hacher(MOT_DE_PASSE),
                    role=Role.RESPONSABLE,
                    actif=True,
                    nb_echecs_connexion=0,
                    doit_changer_mdp=False,
                ),
                Utilisateur(
                    nom="Ancien",
                    prenom="Compte",
                    email="ancien@globalretail.example",
                    mdp_hash=hacher(MOT_DE_PASSE),
                    role=Role.ANALYSTE,
                    actif=False,
                    nb_echecs_connexion=0,
                    doit_changer_mdp=False,
                ),
            ]
        )
        db.commit()
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE journal, utilisateur RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    with TestClient(app, headers=CSRF, client=("198.51.100.20", 50000)) as c:
        yield c


@pytest.fixture
def horloge(monkeypatch):
    """Heure contrôlable, partagée par la connexion et l'émission des jetons."""
    etat = {"maintenant": datetime.now(UTC)}
    monkeypatch.setattr(module_auth, "maintenant", lambda: etat["maintenant"])
    monkeypatch.setattr(jetons, "maintenant", lambda: etat["maintenant"])
    return etat


def connexion(client, email=EMAIL, mot_de_passe=MOT_DE_PASSE):
    return client.post("/api/auth/login", json={"email": email, "mot_de_passe": mot_de_passe})


def actions_journal() -> list[str]:
    with SessionLocal() as db:
        return list(db.scalars(select(Journal.action).order_by(Journal.id_log)))


def compte(email=EMAIL) -> Utilisateur:
    with SessionLocal() as db:
        return db.scalar(select(Utilisateur).where(Utilisateur.email == email))


# --- Connexion --------------------------------------------------------------------------------


def test_connexion_reussie_pose_un_cookie_httponly_strict(client):
    r = connexion(client)
    assert r.status_code == 200
    assert r.json()["role"] == "RESPONSABLE"
    cookie = r.headers["set-cookie"]
    assert f"{NOM_COOKIE}=" in cookie
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Max-Age=28800" in cookie
    assert "mdp_hash" not in r.text


def test_session_permet_d_acceder_a_me(client):
    connexion(client)
    assert client.get("/api/auth/me").json()["email"] == EMAIL


def test_email_insensible_a_la_casse(client):
    assert connexion(client, email=EMAIL.upper()).status_code == 200


@pytest.mark.parametrize(
    ("email", "mot_de_passe"),
    [
        (EMAIL, "mauvais-mot-de-passe"),
        ("inconnu@globalretail.example", MOT_DE_PASSE),
        ("ancien@globalretail.example", MOT_DE_PASSE),  # compte désactivé
    ],
)
def test_echec_de_connexion_message_generique(client, email, mot_de_passe):
    r = connexion(client, email, mot_de_passe)
    assert r.status_code == 401
    assert r.json() == {"detail": "Identifiants incorrects"}
    assert "set-cookie" not in r.headers


def test_cookie_absent_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_jeton_falsifie_401(client):
    client.cookies.set(NOM_COOKIE, "abc.def.ghi", path="/api")
    assert client.get("/api/auth/me").status_code == 401


def test_session_expire_apres_8_heures(client, horloge):
    connexion(client)
    horloge["maintenant"] += timedelta(hours=8, minutes=1)
    jeton = client.cookies.get(NOM_COOKIE)
    assert jetons.lire_jeton(jeton) is None


def test_compte_desactive_pendant_la_session_perd_l_acces(client):
    connexion(client)
    with engine.begin() as conn:
        conn.execute(text("UPDATE utilisateur SET actif = false WHERE email = :e"), {"e": EMAIL})
    assert client.get("/api/auth/me").status_code == 401


def test_deconnexion_efface_le_cookie_et_journalise(client):
    connexion(client)
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert actions_journal()[-1] == "DECONNEXION"


# --- Verrouillage (RG-15) ---------------------------------------------------------------------


def test_verrouillage_au_cinquieme_echec(client, horloge):
    for _ in range(4):
        assert connexion(client, mot_de_passe="faux").status_code == 401
    assert compte().verrouille_jusqu_a is None
    assert connexion(client, mot_de_passe="faux").status_code == 401  # 5e échec : verrouille
    assert compte().verrouille_jusqu_a is not None
    # Même le bon mot de passe est refusé pendant le verrouillage
    r = connexion(client)
    assert r.status_code == 423
    assert "verrouillé" in r.json()["detail"]


def test_deverrouillage_apres_15_minutes(client, horloge):
    for _ in range(5):
        connexion(client, mot_de_passe="faux")
    horloge["maintenant"] += timedelta(minutes=14)
    assert connexion(client).status_code == 423
    horloge["maintenant"] += timedelta(minutes=2)
    assert connexion(client).status_code == 200
    assert compte().nb_echecs_connexion == 0


def test_une_connexion_reussie_remet_le_compteur_a_zero(client):
    for _ in range(4):
        connexion(client, mot_de_passe="faux")
    connexion(client)
    for _ in range(4):
        connexion(client, mot_de_passe="faux")
    assert compte().verrouille_jusqu_a is None


# --- Journal (RG-14) --------------------------------------------------------------------------


def test_connexions_echecs_et_verrouillage_sont_journalises(client):
    connexion(client)
    for _ in range(5):
        connexion(client, mot_de_passe="faux")
    connexion(client)
    actions = actions_journal()
    assert actions[0] == "CONNEXION"
    assert actions.count("CONNEXION_ECHEC") == 5
    assert "COMPTE_VERROUILLE" in actions
    assert actions[-1] == "CONNEXION_REFUSEE_VERROUILLAGE"


def test_journal_contient_utilisateur_ip_et_motif(client):
    connexion(client, mot_de_passe="faux")
    with SessionLocal() as db:
        entree = db.scalar(select(Journal).where(Journal.action == "CONNEXION_ECHEC"))
    assert entree.id_utilisateur == compte().id_utilisateur
    assert str(entree.adresse_ip) == "198.51.100.20"
    assert entree.details["motif"] == "mot_de_passe_invalide"
    assert entree.details["echecs_consecutifs"] == 1


def test_ip_reelle_lue_derriere_le_proxy(client):
    client.post(
        "/api/auth/login",
        json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE},
        headers={**CSRF, "X-Forwarded-For": "203.0.113.7, 10.0.0.1"},
    )
    with SessionLocal() as db:
        ip = db.scalar(select(Journal.adresse_ip).where(Journal.action == "CONNEXION"))
    assert str(ip) == "203.0.113.7"


def test_aucun_mot_de_passe_en_clair_ni_en_base_ni_dans_les_logs(client, caplog):
    caplog.set_level(logging.DEBUG)
    secret_tente = "Tentative-Secrete-987"  # noqa: S105
    connexion(client, mot_de_passe=secret_tente)
    connexion(client)
    client.post(
        "/api/auth/mot-de-passe",
        json={"mot_de_passe_actuel": MOT_DE_PASSE, "nouveau_mot_de_passe": "Nouveau-Secret-2026"},
    )
    with engine.connect() as conn:
        tout = " ".join(
            str(ligne)
            for table in ("journal", "utilisateur")
            for ligne in conn.execute(text(f"SELECT * FROM {table}"))  # noqa: S608
        )
    for secret in (secret_tente, MOT_DE_PASSE, "Nouveau-Secret-2026"):
        assert secret not in tout
        assert secret not in caplog.text
    assert "$argon2id$" in tout  # RG-12 : hash renforcé


# --- Changement de mot de passe (D-10) --------------------------------------------------------


def test_changement_de_mot_de_passe(client):
    connexion(client)
    r = client.post(
        "/api/auth/mot-de-passe",
        json={"mot_de_passe_actuel": MOT_DE_PASSE, "nouveau_mot_de_passe": "Nouveau-Secret-2026"},
    )
    assert r.status_code == 204
    client.post("/api/auth/logout")
    assert connexion(client).status_code == 401
    assert connexion(client, mot_de_passe="Nouveau-Secret-2026").status_code == 200


@pytest.mark.parametrize(
    ("actuel", "nouveau", "message"),
    [
        ("faux", "Nouveau-Secret-2026", "actuel incorrect"),
        (MOT_DE_PASSE, "court1", "12 caractères"),
        (MOT_DE_PASSE, "seulementdeslettres", "mélanger"),
        (MOT_DE_PASSE, MOT_DE_PASSE, "différent"),
    ],
)
def test_changement_de_mot_de_passe_refuse(client, actuel, nouveau, message):
    connexion(client)
    r = client.post(
        "/api/auth/mot-de-passe",
        json={"mot_de_passe_actuel": actuel, "nouveau_mot_de_passe": nouveau},
    )
    assert r.status_code == 400
    assert message in r.json()["detail"]


# --- CSRF (D-12) ------------------------------------------------------------------------------


def test_requete_mutante_sans_en_tete_csrf_refusee():
    with TestClient(app) as sans_en_tete:
        r = sans_en_tete.post(
            "/api/auth/login", json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE}
        )
    assert r.status_code == 403
    assert "CSRF" in r.json()["detail"]
