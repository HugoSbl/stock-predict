"""Chargement en base d'un export du monde simulé (données de développement).

    python -m app.seed /data/seed

Vide les données métier (référentiels, activité, prévisions, alertes, synchronisations) puis
recharge tout par COPY dans une seule transaction : en cas d'erreur, la base reste inchangée.
Les comptes utilisateurs et le journal d'audit sont conservés. Contrat : docs/donnees.md.
"""

import argparse
import csv
import json
import os
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.db import Base, engine
from app.models import Journal, SourceApi
from app.models.enums import TypeDonneesSource

# Ordre de chargement (dépendances de clés étrangères)
TABLES = [
    "pays",
    "categorie",
    "fournisseur",
    "entrepot",
    "produit",
    "calendrier",
    "promotion",
    "produit_promotion",
    "stock",
    "stock_quotidien",
    "vente",
    "commande_fournisseur",
    "ligne_commande",
]

# Tables vidées avant chargement (utilisateur et journal conservés)
TABLES_A_VIDER = [
    *TABLES,
    "prevision",
    "alerte",
    "kpi_quotidien",
    "ligne_rejetee",
    "synchronisation",
    "source_api",
]

# Clés techniques fournies par l'export : les séquences doivent repartir après le max
SEQUENCES = {
    "categorie": "id_categorie",
    "fournisseur": "id_fournisseur",
    "entrepot": "id_entrepot",
    "produit": "id_produit",
    "promotion": "id_promotion",
    "commande_fournisseur": "id_commande",
}

# Connecteurs vers les API sources simulées (D-04) : colonne source → colonne cible
SOURCES = [
    {
        "nom": "ERP Ventes",
        "chemin": "/api/v1/sales",
        "type_donnees": TypeDonneesSource.VENTES,
        "mapping_colonnes": {
            "sale_date": "date_vente",
            "sku": "reference",
            "warehouse_code": "code_entrepot",
            "qty": "quantite_vendue",
            "unit_price_excl_tax": "prix_vente_ht",
        },
    },
    {
        "nom": "WMS Stocks",
        "chemin": "/api/v1/stock-levels",
        "type_donnees": TypeDonneesSource.STOCKS,
        "mapping_colonnes": {
            "snapshot_date": "date_releve",
            "sku": "reference",
            "warehouse_code": "code_entrepot",
            "on_hand": "quantite_stock",
        },
    },
    {
        "nom": "Portail Fournisseurs",
        "chemin": "/api/v1/purchase-orders",
        "type_donnees": TypeDonneesSource.COMMANDES,
        "mapping_colonnes": {
            "po_number": "numero_commande",
            "supplier_code": "code_fournisseur",
            "warehouse_code": "code_entrepot",
            "ordered_at": "date_achat",
            "expected_delivery": "date_livraison_estimee",
            "delivered_at": "date_livraison_reelle",
            "status": "statut",
            "sku": "reference",
            "qty": "quantite_commandee",
        },
    },
]


class ExportInvalide(Exception):
    pass


def lire_manifeste(dossier: Path) -> dict:
    chemin = dossier / "manifest.json"
    if not chemin.exists():
        raise ExportInvalide(f"{chemin} introuvable : lancer d'abord l'export (npm run seed)")
    manifeste = json.loads(chemin.read_text())
    manquants = [t for t in TABLES if not (dossier / f"{t}.csv").exists()]
    if manquants:
        raise ExportInvalide(f"Fichiers manquants dans l'export : {', '.join(manquants)}")
    return manifeste


def _copier(conn: Connection, table: str, chemin: Path) -> int:
    with chemin.open(newline="", encoding="utf-8") as f:
        colonnes = next(csv.reader(f))
    liste = ", ".join(f'"{c}"' for c in colonnes)
    curseur = conn.connection.dbapi_connection.cursor()
    with (
        chemin.open("rb") as f,
        curseur.copy(f"COPY {table} ({liste}) FROM STDIN WITH (FORMAT csv, HEADER true)") as copie,
    ):
        while bloc := f.read(1 << 20):
            copie.write(bloc)
    return curseur.rowcount


def _cles_etrangeres_orphelines(conn: Connection) -> list[str]:
    """Vérification ensembliste de toutes les clés étrangères des tables chargées (modèles)."""
    anomalies = []
    for table in TABLES:
        for fk in Base.metadata.tables[table].foreign_key_constraints:
            enfant = [c.name for c in fk.columns]
            parent = [e.column.name for e in fk.elements]
            jointure = " AND ".join(f"e.{c} = p.{pc}" for c, pc in zip(enfant, parent, strict=True))
            non_nul = " AND ".join(f"e.{c} IS NOT NULL" for c in enfant)
            nb = conn.execute(
                text(
                    f"SELECT count(*) FROM {table} e "  # noqa: S608 (noms issus des modèles)
                    f"WHERE {non_nul} AND NOT EXISTS "
                    f"(SELECT 1 FROM {fk.referred_table.name} p WHERE {jointure})"
                )
            ).scalar_one()
            if nb:
                anomalies.append(f"{table}.{','.join(enfant)} : {nb} référence(s) orpheline(s)")
    return anomalies


def _est_superutilisateur(conn: Connection) -> bool:
    return conn.execute(
        text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
    ).scalar_one()


def charger(dossier: Path, url_sources: str | None = None) -> dict[str, int]:
    """Charge l'export, renvoie le nombre de lignes par table. Transaction unique : tout ou rien."""
    manifeste = lire_manifeste(dossier)
    url_sources = url_sources or os.environ.get("SOURCES_BASE_URL", "http://sources-mock:8100")
    comptes: dict[str, int] = {}
    with engine.begin() as conn:
        # Noms de tables : constantes internes, jamais issues d'une saisie (S608 non applicable)
        conn.execute(text(f"TRUNCATE {', '.join(TABLES_A_VIDER)} RESTART IDENTITY CASCADE"))
        conn.execute(
            text("SELECT creer_partitions_vente(DATE '2024-01-01', CAST(:fin AS date) + 365)"),
            {"fin": manifeste["jusqu_a"]},
        )
        # Chargement en masse : les triggers de clés étrangères (vérification ligne à ligne, ~10×
        # plus lent) sont suspendus pendant le COPY, puis l'intégrité est revérifiée en une passe
        # ensembliste. Les contraintes CHECK et UNIQUE restent actives. Sans droit superutilisateur,
        # chargement classique.
        rapide = _est_superutilisateur(conn)
        if rapide:
            conn.execute(text("SET LOCAL session_replication_role = replica"))
        for table in TABLES:
            comptes[table] = _copier(conn, table, dossier / f"{table}.csv")
        if rapide:
            conn.execute(text("SET LOCAL session_replication_role = origin"))
            if anomalies := _cles_etrangeres_orphelines(conn):
                raise ExportInvalide("Intégrité référentielle violée : " + " ; ".join(anomalies))
        for table, colonne in SEQUENCES.items():
            conn.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{colonne}'), "  # noqa: S608
                    f"COALESCE((SELECT max({colonne}) FROM {table}), 0) + 1, false)"
                )
            )
        conn.execute(
            SourceApi.__table__.insert(),
            [
                {
                    "nom": s["nom"],
                    "url": url_sources.rstrip("/") + s["chemin"],
                    "type_donnees": s["type_donnees"],
                    "mapping_colonnes": s["mapping_colonnes"],
                    "frequence_cron": "0 2 * * *",
                    "actif": True,
                    "nom_variable_secret": "SOURCES_API_KEY",
                }
                for s in SOURCES
            ],
        )
        comptes["source_api"] = len(SOURCES)
        conn.execute(
            Journal.__table__.insert().values(
                action="INITIALISATION_DONNEES",
                details={
                    "jusqu_a": manifeste["jusqu_a"],
                    "graine": manifeste["graine"],
                    "lignes": comptes,
                },
            )
        )
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ANALYZE"))
    return comptes


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("dossier", type=Path)
    args = parser.parse_args()
    debut = time.monotonic()
    comptes = charger(args.dossier)
    print(f"Seed chargé en {time.monotonic() - debut:.1f} s :")
    for table, n in comptes.items():
        print(f"  {table:<22} {n:>10,} lignes".replace(",", " "))


if __name__ == "__main__":
    main()
