"""Contrôle d'accès par rôle (RG-13) : refus par défaut, vérifié côté serveur."""

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import auth
from app.db import SessionLocal, engine
from app.main import app
from app.models import Utilisateur
from app.models.enums import Role
from app.securite.csrf import ProtectionCsrf
from app.securite.dependances import exiger_role
from app.securite.mots_de_passe import hacher

# Seules routes accessibles sans rôle. Ajouter une route ici doit être une décision explicite.
ROUTES_PUBLIQUES = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/me",  # authentifiée, mais sans rôle : sert à savoir qui est connecté
    "/api/auth/mot-de-passe",  # authentifiée : doit rester accessible pendant le changement forcé
}
MOT_DE_PASSE = "Lait-UHT-4512-demo"


def _roles_declares(dependant) -> set:
    roles = set()
    for dep in dependant.dependencies:
        roles |= getattr(dep.call, "roles_autorises", set())
        roles |= _roles_declares(dep)
    return roles


def routes_sans_role(application: FastAPI) -> list[str]:
    """Routes /api hors liste publique qui ne déclarent aucun rôle via exiger_role(...).

    iter_route_contexts parcourt aussi les routeurs inclus (FastAPI ≥ 0.140 ne les aplatit plus).
    """
    return [
        f"{','.join(sorted(rc.methods or []))} {rc.path}"
        for rc in iter_route_contexts(application.routes)
        if (rc.path or "").startswith("/api")
        and rc.path not in ROUTES_PUBLIQUES
        and hasattr(rc, "dependant")
        and not _roles_declares(rc.dependant)
    ]


def test_toute_route_non_publique_declare_ses_roles():
    """Refus par défaut : une route métier sans exiger_role(...) fait échouer la CI."""
    fautives = routes_sans_role(app)
    assert fautives == [], f"Routes sans exiger_role(...) : {fautives}"


def test_les_routes_publiques_existent():
    """Garde-fou : si l'inspection ne voyait aucune route, le test précédent passerait à vide."""
    chemins = {rc.path for rc in iter_route_contexts(app.routes)}
    assert chemins >= ROUTES_PUBLIQUES


def test_l_inspection_detecte_une_route_non_protegee():
    temoin = FastAPI()
    routeur = APIRouter(prefix="/api")

    @routeur.get("/oubliee")
    def oubliee():
        return {}

    @routeur.get("/protegee", dependencies=[Depends(exiger_role(Role.ADMIN))])
    def protegee():
        return {}

    sous_routeur = APIRouter(dependencies=[Depends(exiger_role(Role.ANALYSTE))])

    @sous_routeur.get("/protegee-par-le-routeur")
    def protegee_par_le_routeur():
        return {}

    routeur.include_router(sous_routeur)
    temoin.include_router(routeur)
    assert routes_sans_role(temoin) == ["GET /api/oubliee"]


# --- Comportement de exiger_role sur une application de test ---------------------------------


@pytest.fixture(scope="module")
def client_test():
    test_app = FastAPI()
    test_app.add_middleware(ProtectionCsrf)
    test_app.include_router(auth.router, prefix="/api")
    routes = APIRouter(prefix="/api")

    @routes.get("/reserve-admin", dependencies=[Depends(exiger_role(Role.ADMIN))])
    def reserve_admin():
        return {"ok": True}

    @routes.get("/pour-tous", dependencies=[Depends(exiger_role(*Role))])
    def pour_tous():
        return {"ok": True}

    @routes.get("/personne", dependencies=[Depends(exiger_role())])
    def personne():
        return {"ok": True}

    test_app.include_router(routes)
    with TestClient(test_app, headers={"X-Requested-With": "StockPredict"}) as c:
        yield c


@pytest.fixture(autouse=True)
def comptes():
    with SessionLocal() as db:
        for role in Role:
            db.add(
                Utilisateur(
                    nom=role.value,
                    prenom="Test",
                    email=f"{role.value.lower()}@globalretail.example",
                    mdp_hash=hacher(MOT_DE_PASSE),
                    role=role,
                    actif=True,
                    nb_echecs_connexion=0,
                    doit_changer_mdp=False,
                )
            )
        db.add(
            Utilisateur(
                nom="Nouveau",
                prenom="Test",
                email="nouveau@globalretail.example",
                mdp_hash=hacher(MOT_DE_PASSE),
                role=Role.ADMIN,
                actif=True,
                nb_echecs_connexion=0,
                doit_changer_mdp=True,
            )
        )
        db.commit()
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE journal, utilisateur RESTART IDENTITY CASCADE"))


def se_connecter(client, email):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": email, "mot_de_passe": MOT_DE_PASSE})
    assert r.status_code == 200


def test_sans_session_401(client_test):
    client_test.cookies.clear()
    assert client_test.get("/api/reserve-admin").status_code == 401


@pytest.mark.parametrize(
    ("role", "attendu"), [("admin", 200), ("responsable", 403), ("analyste", 403)]
)
def test_route_reservee_admin(client_test, role, attendu):
    se_connecter(client_test, f"{role}@globalretail.example")
    assert client_test.get("/api/reserve-admin").status_code == attendu


def test_route_ouverte_a_tous_les_roles(client_test):
    for role in Role:
        se_connecter(client_test, f"{role.value.lower()}@globalretail.example")
        assert client_test.get("/api/pour-tous").status_code == 200


def test_sans_role_declare_personne_ne_passe(client_test):
    se_connecter(client_test, "admin@globalretail.example")
    assert client_test.get("/api/personne").status_code == 403


def test_changement_de_mot_de_passe_force_bloque_les_routes_metier(client_test):
    se_connecter(client_test, "nouveau@globalretail.example")
    r = client_test.get("/api/reserve-admin")
    assert r.status_code == 403
    assert r.json()["detail"] == "Changement de mot de passe requis"
    assert client_test.get("/api/auth/me").json()["doit_changer_mdp"] is True
    client_test.post(
        "/api/auth/mot-de-passe",
        json={"mot_de_passe_actuel": MOT_DE_PASSE, "nouveau_mot_de_passe": "Nouveau-Secret-2026"},
    )
    assert client_test.get("/api/reserve-admin").status_code == 200


def test_changement_de_role_applique_immediatement(client_test):
    se_connecter(client_test, "admin@globalretail.example")
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE utilisateur SET role = 'ANALYSTE' WHERE email = 'admin@globalretail.example'"
            )
        )
    assert client_test.get("/api/reserve-admin").status_code == 403
