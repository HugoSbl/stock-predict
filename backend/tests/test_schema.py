"""Schéma : migrations, partitionnement et contraintes métier portées par la base."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.db import engine
from tests.conftest import config_alembic

TABLES_ATTENDUES = {
    "alerte", "calendrier", "categorie", "commande_fournisseur", "entrepot", "fournisseur",
    "journal", "kpi_quotidien", "ligne_commande", "ligne_rejetee", "pays", "prevision", "produit",
    "produit_promotion", "promotion", "source_api", "stock", "stock_quotidien", "synchronisation",
    "utilisateur", "vente",
}  # fmt: skip


def test_toutes_les_tables_du_mld_existent():
    tables = set(inspect(engine).get_table_names())
    assert tables >= TABLES_ATTENDUES


def test_modeles_et_migrations_sont_synchronises():
    """Échoue si un modèle a changé sans migration : lancer `npm run migration -- "..."`."""
    command.check(config_alembic())


def test_vente_est_partitionnee_par_mois_avec_partition_par_defaut(connexion):
    partitions = set(
        connexion.execute(
            text(
                "SELECT inhrelid::regclass::text FROM pg_inherits WHERE inhparent = 'vente'::regclass"
            )
        ).scalars()
    )
    assert "vente_defaut" in partitions
    assert {"vente_2024_01", "vente_2025_06"} <= partitions
    assert len(partitions) >= 24


def test_creer_partitions_vente_est_idempotente(connexion):
    premiere = connexion.execute(
        text("SELECT creer_partitions_vente(DATE '2030-01-01', DATE '2030-03-31')")
    )
    assert premiere.scalar() == 3
    seconde = connexion.execute(
        text("SELECT creer_partitions_vente(DATE '2030-01-01', DATE '2030-03-31')")
    )
    assert seconde.scalar() == 0


def _referentiel_minimal(conn) -> None:
    conn.execute(
        text("""
        INSERT INTO pays VALUES ('FR', 'France', 20.00, 'EUR');
        INSERT INTO categorie (id_categorie, libelle_categorie) VALUES (1, 'Épicerie');
        INSERT INTO entrepot (id_entrepot, code_entrepot, nom_entrepot, ville, capacite_max, code_pays)
            VALUES (1, 'FR-LYS', 'Lyon-Sud', 'Lyon', 100000, 'FR');
        INSERT INTO produit (id_produit, reference, libelle, prix_unitaire_ht, seuil_alerte, id_categorie)
            VALUES (1, 'REF-4512', 'Lait UHT 1L', 0.89, 500, 1);
        INSERT INTO calendrier VALUES ('2025-06-15', 7, 24, 6, 2025, false, false, false, false);
    """)
    )


def test_une_vente_atterrit_dans_la_partition_de_son_mois(connexion):
    _referentiel_minimal(connexion)
    connexion.execute(
        text("""
        INSERT INTO vente (date_vente, quantite_vendue, prix_vente_ht, id_produit, id_entrepot)
        VALUES ('2025-06-15', 12, 0.89, 1, 1)
    """)
    )
    partition = connexion.execute(text("SELECT tableoid::regclass::text FROM vente")).scalar()
    assert partition == "vente_2025_06"


def test_doublon_strict_de_vente_refuse(connexion):
    _referentiel_minimal(connexion)
    insert = text("""
        INSERT INTO vente (date_vente, quantite_vendue, prix_vente_ht, id_produit, id_entrepot)
        VALUES ('2025-06-15', 12, 0.89, 1, 1)
    """)
    connexion.execute(insert)
    with pytest.raises(IntegrityError):
        connexion.execute(insert)


def test_seuil_alerte_negatif_refuse(connexion):
    _referentiel_minimal(connexion)
    with pytest.raises(IntegrityError):
        connexion.execute(text("UPDATE produit SET seuil_alerte = -1 WHERE id_produit = 1"))


def _alerte(statut: str = "OUVERTE", motif: str | None = None) -> text:
    return text(
        "INSERT INTO alerte (type_alerte, message, statut_alerte, motif, id_produit, id_entrepot) "
        "VALUES ('SOUS_SEUIL', 'Stock sous seuil', :statut, :motif, 1, 1)"
    ).bindparams(statut=statut, motif=motif)


def test_une_seule_alerte_ouverte_par_couple_et_type(connexion):
    _referentiel_minimal(connexion)
    connexion.execute(_alerte())
    connexion.execute(_alerte("TRAITEE"))  # les alertes fermées ne comptent pas
    with pytest.raises(IntegrityError):
        connexion.execute(_alerte())


def test_alerte_ignoree_exige_un_motif(connexion):
    _referentiel_minimal(connexion)
    connexion.execute(_alerte("IGNOREE", "Produit déréférencé"))
    with pytest.raises(IntegrityError):
        connexion.execute(_alerte("IGNOREE", "  "))


def test_valeur_hors_enumeration_refusee(connexion):
    with pytest.raises(IntegrityError):
        connexion.execute(
            text(
                "INSERT INTO utilisateur (nom, prenom, email, mdp_hash, role, actif, nb_echecs_connexion, "
                "doit_changer_mdp) VALUES ('X', 'Y', 'x@y.fr', 'h', 'SUPERADMIN', true, 0, false)"
            )
        )


def test_migration_reversible():
    command.downgrade(config_alembic(), "base")
    assert "vente" not in inspect(engine).get_table_names()
    command.upgrade(config_alembic(), "head")
    assert "vente" in inspect(engine).get_table_names()
