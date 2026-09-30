"""API sources simulées : contrat, pagination, données salies (RG-01/RG-02) et pannes (UC-03 2a)."""

import time

import pytest

from app.etat import monde_courant

HIER = "2026-09-29"
TOUT = {"page_size": 5000}


def test_ventes_contrat_et_colonnes_non_mappees(client):
    r = client.get("/api/v1/sales", params={"date": HIER, "page_size": 10})
    assert r.status_code == 200
    corps = r.json()
    assert corps["page"] == 1 and corps["page_size"] == 10 and corps["pages"] >= 100
    ligne = corps["data"][0]
    assert {"sale_date", "sku", "warehouse_code", "qty", "unit_price_excl_tax"} <= ligne.keys()
    assert {"currency", "channel", "_ingested_at"} <= ligne.keys()  # à ignorer (RG-01)


def test_pagination_couvre_toutes_les_lignes_sans_recouvrement(client):
    total = client.get("/api/v1/sales", params={"date": HIER, "page_size": 1}).json()["total"]
    pages = [
        client.get("/api/v1/sales", params={"date": HIER, "page": p, "page_size": 700}).json()
        for p in (1, 2, 3)
    ]
    assert sum(len(p["data"]) for p in pages) == total
    assert pages[0]["data"][0] != pages[1]["data"][0]


def test_reponses_identiques_d_un_appel_a_l_autre(client):
    a = client.get("/api/v1/stock-levels", params={"date": HIER, **TOUT}).json()
    b = client.get("/api/v1/stock-levels", params={"date": HIER, **TOUT}).json()
    assert a == b


def test_environ_5_pourcent_de_lignes_invalides(client):
    lignes = client.get("/api/v1/sales", params={"date": HIER, **TOUT}).json()["data"]
    produits = {p.reference for p in monde_courant().produits}
    entrepots = {e.code_entrepot for e in monde_courant().entrepots}
    cles = [(x["sku"], x["warehouse_code"]) for x in lignes]
    invalides = sum(
        not isinstance(x["qty"], int)
        or x["qty"] < 0
        or x["sku"] not in produits
        or x["warehouse_code"] not in entrepots
        for x in lignes
    )
    doublons = len(cles) - len(set(cles))
    taux = (invalides + doublons) / len(lignes)
    assert 0.03 < taux < 0.08
    assert invalides > 0 and doublons > 0


def test_les_lignes_valides_correspondent_au_monde_simule(client):
    lignes = client.get("/api/v1/sales", params={"date": HIER, **TOUT}).json()["data"]
    attendu = monde_courant().ventes_du_jour(monde_courant().hier)
    attendu = {(v.reference, v.code_entrepot): v.quantite_vendue for v in attendu.itertuples()}
    valides = [x for x in lignes if (x["sku"], x["warehouse_code"]) in attendu]
    assert all(
        x["qty"] == attendu[(x["sku"], x["warehouse_code"])]
        for x in valides
        if isinstance(x["qty"], int) and x["qty"] >= 0
    )


def test_commandes_fournisseurs_une_ligne_par_produit(client):
    r = client.get("/api/v1/purchase-orders", params={"modifie_depuis": "2026-09-20", **TOUT})
    lignes = r.json()["data"]
    assert {x["status"] for x in lignes} >= {"EN_COURS", "LIVREE"}
    assert all(x["delivered_at"] is None for x in lignes if x["status"] == "EN_COURS")
    assert "buyer" in lignes[0]


def test_jour_futur_indisponible(client):
    r = client.get("/api/v1/sales", params={"date": "2026-09-30"})
    assert r.status_code == 404


@pytest.mark.parametrize("entete", [None, "Bearer mauvaise-cle"])
def test_cle_api_requise(client, entete):
    headers = {"Authorization": entete} if entete else {}
    r = client.get("/api/v1/sales", params={"date": HIER}, headers=headers or {"Authorization": ""})
    assert r.status_code == 401


def test_panne_auth_simulee(client):
    assert client.get("/api/v1/sales", params={"date": HIER, "fail": "auth"}).status_code == 401


def test_panne_500_simulee(client):
    assert client.get("/api/v1/sales", params={"date": HIER, "fail": "500"}).status_code == 500


def test_panne_timeout_simulee(client):
    debut = time.monotonic()
    r = client.get("/api/v1/stock-levels", params={"date": HIER, "fail": "timeout"})
    assert time.monotonic() - debut >= 0.3
    assert r.status_code == 504


def test_panne_permanente_par_variable_d_environnement(client, monkeypatch):
    monkeypatch.setenv("MOCK_PANNES", "purchase-orders=500")
    r = client.get("/api/v1/purchase-orders", params={"modifie_depuis": HIER})
    assert r.status_code == 500
    assert client.get("/api/v1/sales", params={"date": HIER}).status_code == 200
