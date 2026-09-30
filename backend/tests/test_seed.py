"""Chargement d'un export (seed) : contrat CSV, transaction tout-ou-rien, intégrité référentielle."""

import csv
import json
from pathlib import Path

import pytest
from psycopg.errors import ForeignKeyViolation
from sqlalchemy import text

from app import seed
from app.db import engine

MINI_EXPORT = {
    "pays": [
        ["code_pays", "nom_pays", "taux_tva", "devise"],
        ["FR", "France", "20.00", "EUR"],
    ],
    "categorie": [["id_categorie", "libelle_categorie"], [1, "Épicerie"]],
    "fournisseur": [
        ["id_fournisseur", "code_fournisseur", "nom_fournisseur", "pays_fournisseur", "delai_moyen_jours"],
        [1, "F-LACTA", "Lactalis", "France", 4],
    ],
    "entrepot": [
        ["id_entrepot", "code_entrepot", "nom_entrepot", "ville", "capacite_max", "code_pays"],
        [1, "FR-LYS", "Lyon-Sud", "Lyon", 900000, "FR"],
    ],
    "produit": [
        ["id_produit", "reference", "libelle", "prix_unitaire_ht", "seuil_alerte", "id_categorie", "id_fournisseur_habituel"],
        [1, "REF-4512", "Lait UHT 1L", "2.32", 520, 1, 1],
        [2, "REF-8830", "Pâtes 500g", "2.63", 450, 1, 1],
    ],
    "calendrier": [
        ["date_jour", "jour_semaine", "numero_semaine", "mois", "annee", "ferie_fr", "ferie_de", "vacances_fr", "vacances_de"],
        ["2025-06-14", 6, 24, 6, 2025, "False", "False", "False", "False"],
        ["2025-06-15", 7, 24, 6, 2025, "False", "False", "False", "False"],
    ],
    "promotion": [
        ["id_promotion", "libelle", "date_debut", "date_fin", "taux_remise"],
        [1, "Prix choc", "2025-06-14", "2025-06-20", "25.00"],
    ],
    "produit_promotion": [["id_promotion", "id_produit"], [1, 1]],
    "stock": [
        ["id_produit", "id_entrepot", "quantite_stock", "date_maj"],
        [1, 1, 1500, "2025-06-15T23:59:00+02:00"],
        [2, 1, 300, "2025-06-15T23:59:00+02:00"],
    ],
    "stock_quotidien": [
        ["id_produit", "id_entrepot", "date_releve", "quantite_stock"],
        [1, 1, "2025-06-14", 1600],
        [1, 1, "2025-06-15", 1500],
    ],
    "vente": [
        ["date_vente", "quantite_vendue", "prix_vente_ht", "id_produit", "id_entrepot"],
        ["2025-06-14", 100, "1.74", 1, 1],
        ["2025-06-15", 120, "1.74", 1, 1],
    ],
    "commande_fournisseur": [
        ["id_commande", "numero_commande", "date_achat", "date_livraison_estimee", "date_livraison_reelle", "statut", "id_fournisseur", "id_entrepot"],
        [1, "CF-20250614-LACTA-FR-LYS", "2025-06-14", "2025-06-18", "", "EN_COURS", 1, 1],
    ],
    "ligne_commande": [["id_commande", "id_produit", "quantite_commandee"], [1, 2, 400]],
}  # fmt: skip


def ecrire_export(dossier: Path, tables: dict) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    for nom, lignes in tables.items():
        with (dossier / f"{nom}.csv").open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(lignes)
    (dossier / "manifest.json").write_text(json.dumps({"graine": 1, "jusqu_a": "2025-06-15"}))
    return dossier


@pytest.fixture
def export(tmp_path):
    return ecrire_export(tmp_path / "seed", MINI_EXPORT)


@pytest.fixture(autouse=True)
def base_videe_apres():
    """Le seed commite : on remet la base de test à vide pour ne pas gêner les autres tests."""
    yield
    with engine.begin() as conn:
        conn.execute(
            text(f"TRUNCATE {', '.join(seed.TABLES_A_VIDER)}, journal RESTART IDENTITY CASCADE")
        )


def compter(table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()  # noqa: S608


def test_charge_toutes_les_tables_de_l_export(export):
    comptes = seed.charger(export, url_sources="http://mock:8100")
    assert comptes["vente"] == 2 and comptes["produit"] == 2
    assert compter("vente") == 2
    assert compter("ligne_commande") == 1


def test_configure_les_trois_connecteurs_sources(export):
    seed.charger(export, url_sources="http://mock:8100")
    with engine.connect() as conn:
        sources = conn.execute(
            text("SELECT nom, url, mapping_colonnes FROM source_api ORDER BY nom")
        ).all()
    assert [s.nom for s in sources] == ["ERP Ventes", "Portail Fournisseurs", "WMS Stocks"]
    assert sources[0].url == "http://mock:8100/api/v1/sales"
    assert sources[0].mapping_colonnes["qty"] == "quantite_vendue"


def test_sequences_repartent_apres_les_identifiants_charges(export):
    seed.charger(export)
    with engine.begin() as conn:
        nouvel_id = conn.execute(
            text(
                "INSERT INTO produit (reference, libelle, prix_unitaire_ht, seuil_alerte, id_categorie) "
                "VALUES ('REF-NEW', 'Nouveau', 1, 0, 1) RETURNING id_produit"
            )
        ).scalar_one()
    assert nouvel_id == 3


def test_le_chargement_est_journalise(export):
    seed.charger(export)
    with engine.connect() as conn:
        details = conn.execute(
            text("SELECT details FROM journal WHERE action = 'INITIALISATION_DONNEES'")
        ).scalar_one()
    assert details["lignes"]["vente"] == 2


def test_rechargement_idempotent(export):
    seed.charger(export)
    seed.charger(export)
    assert compter("vente") == 2
    assert compter("source_api") == 3


def test_reference_orpheline_annule_tout_le_chargement(export, tmp_path):
    seed.charger(export)
    corrompu = {**MINI_EXPORT, "vente": [*MINI_EXPORT["vente"], ["2025-06-15", 5, "1.00", 99, 1]]}
    with pytest.raises(seed.ExportInvalide, match="vente.id_produit"):
        seed.charger(ecrire_export(tmp_path / "corrompu", corrompu))
    assert compter("vente") == 2  # l'état précédent est intact (rollback)


def test_sans_superutilisateur_les_cles_etrangeres_sont_verifiees_par_postgres(
    export, tmp_path, monkeypatch
):
    monkeypatch.setattr(seed, "_est_superutilisateur", lambda conn: False)
    corrompu = {**MINI_EXPORT, "vente": [*MINI_EXPORT["vente"], ["2025-06-15", 5, "1.00", 99, 1]]}
    with pytest.raises(ForeignKeyViolation):
        seed.charger(ecrire_export(tmp_path / "corrompu", corrompu))


def test_export_incomplet_refuse(tmp_path):
    incomplet = ecrire_export(tmp_path / "incomplet", {"pays": MINI_EXPORT["pays"]})
    with pytest.raises(seed.ExportInvalide, match="manquants"):
        seed.charger(incomplet)
    with pytest.raises(seed.ExportInvalide, match="introuvable"):
        seed.charger(tmp_path / "absent")
