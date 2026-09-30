"""Le monde simulé : déterminisme, cohérence physique des stocks et saisonnalité visible (RG-07)."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.monde import construire_monde
from app.monde.catalogue import PRODUITS_MAQUETTES

AUJOURD_HUI = date(2026, 9, 30)


@pytest.fixture(scope="module")
def monde():
    return construire_monde(AUJOURD_HUI)


@pytest.fixture(scope="module")
def ventes(monde):
    """Ventes quotidiennes en format long, avec pays et catégorie."""
    couples = monde.couples
    nb_jours, nb_couples = monde.ventes.shape
    df = pd.DataFrame(
        {
            "jour": np.repeat(pd.to_datetime(monde.jours), nb_couples),
            "couple": np.tile(np.arange(nb_couples), nb_jours),
            "qte": monde.ventes.reshape(-1),
        }
    )
    df["pays"] = couples.entrepot.map(lambda e: e.code_pays).to_numpy()[df.couple]
    df["categorie"] = couples.produit.map(lambda p: p.id_categorie).to_numpy()[df.couple]
    df["produit"] = couples.id_produit.to_numpy()[df.couple]
    return df


# --- Déterminisme -----------------------------------------------------------------------------


def test_deux_constructions_donnent_exactement_les_memes_donnees(monde):
    autre = construire_monde(AUJOURD_HUI)
    assert np.array_equal(monde.ventes, autre.ventes)
    assert np.array_equal(monde.stock_fin, autre.stock_fin)
    assert monde.commandes.equals(autre.commandes)


def test_le_passe_ne_change_pas_quand_le_temps_avance(monde):
    plus_tot = construire_monde(date(2026, 3, 1))
    n = len(plus_tot.jours)
    assert np.array_equal(plus_tot.ventes, monde.ventes[:n])
    assert [p.seuil_alerte for p in plus_tot.produits] == [p.seuil_alerte for p in monde.produits]


def test_historique_couvre_depuis_le_debut_jusqu_a_hier(monde):
    assert monde.jours[0] == date(2024, 10, 1)
    assert monde.jours[-1] == date(2026, 9, 29)


# --- Référentiels -----------------------------------------------------------------------------


def test_catalogue_contient_les_produits_des_maquettes(monde):
    references = {p.reference for p in monde.produits}
    assert len(monde.produits) == 300
    assert len(references) == 300
    assert {ref for ref, _, _ in PRODUITS_MAQUETTES} <= references


def test_six_entrepots_repartis_sur_deux_pays(monde):
    assert sorted(e.code_pays for e in monde.entrepots) == ["DE", "DE", "DE", "FR", "FR", "FR"]


def test_calendrier_feries_distincts_par_pays(monde):
    cal = monde.calendrier.set_index("date_jour")
    assert cal.loc[date(2025, 12, 25), ["ferie_fr", "ferie_de"]].tolist() == [True, True]
    assert cal.loc[date(2025, 7, 14), ["ferie_fr", "ferie_de"]].tolist() == [True, False]
    assert cal.loc[date(2025, 10, 3), ["ferie_fr", "ferie_de"]].tolist() == [False, True]
    assert cal.loc[date(2025, 8, 1), "vacances_fr"]


# --- Cohérence physique -----------------------------------------------------------------------


def test_stock_jamais_negatif_et_ventes_bornees_par_la_demande(monde):
    assert monde.stock_fin.min() >= 0
    assert (monde.ventes <= monde.demande).all()


def test_taux_de_service_realiste(monde):
    taux = monde.ventes.sum() / monde.demande.sum()
    assert 0.93 < taux < 0.99


def test_des_ruptures_existent_sans_etre_la_norme(monde):
    part_ruptures = (monde.stock_fin == 0).mean()
    assert 0.005 < part_ruptures < 0.10


def test_commandes_coherentes(monde):
    c = monde.commandes
    assert c.numero_commande.is_unique
    assert set(c.statut) == {"LIVREE", "EN_COURS", "ANNULEE"}
    assert c.loc[c.statut == "LIVREE", "date_livraison_reelle"].notna().all()
    assert c.loc[c.statut != "LIVREE", "date_livraison_reelle"].isna().all()
    assert (monde.lignes_commande.quantite_commandee > 0).all()
    assert set(monde.lignes_commande.id_commande) == set(c.id_commande)


def test_seuils_d_alerte_plausibles(monde):
    seuil = np.repeat([p.seuil_alerte for p in monde.produits], len(monde.entrepots))
    part_sous_seuil = (monde.stock_fin[-1] < seuil).mean()
    assert 0.03 < part_sous_seuil < 0.25


# --- Saisonnalité (critère d'acceptation du lot 1) --------------------------------------------


def test_samedi_nettement_plus_fort_que_mardi(ventes):
    fr = ventes[ventes.pays == "FR"]
    par_jour = fr.groupby(fr.jour.dt.dayofweek).qte.mean()
    assert par_jour[5] > 1.4 * par_jour[1]


def test_dimanche_ferme_en_allemagne(ventes):
    de = ventes[(ventes.pays == "DE") & (ventes.jour.dt.dayofweek == 6)]
    assert de.qte.sum() == 0


def test_jour_ferie_fait_chuter_les_ventes_francaises(ventes):
    fr = ventes[ventes.pays == "FR"].groupby("jour").qte.sum()
    jeudis_normaux = fr[(fr.index.dayofweek == 3) & (fr.index.month.isin([5, 6]))]
    assert fr[pd.Timestamp("2025-05-01")] < 0.5 * jeudis_normaux.median()


def test_boissons_plus_vendues_en_ete_qu_en_hiver(ventes):
    boissons = ventes[ventes.categorie == 3].groupby(ventes.jour.dt.month).qte.mean()
    assert boissons[7] > 1.5 * boissons[1]


def test_pic_de_noel_sur_l_epicerie_sucree(ventes):
    sucre = ventes[ventes.categorie == 2]
    noel = sucre[(sucre.jour >= "2025-12-15") & (sucre.jour <= "2025-12-24")].qte.mean()
    novembre = sucre[(sucre.jour >= "2025-11-01") & (sucre.jour <= "2025-11-30")].qte.mean()
    assert noel > 1.4 * novembre


def test_les_promotions_font_monter_les_ventes(monde, ventes):
    hausses = []
    par_produit_jour = ventes.groupby(["produit", "jour"]).qte.sum()
    for promo in monde.promotions:
        avant = pd.Timestamp(promo.date_debut) - pd.Timedelta(days=21)
        if avant < pd.Timestamp(monde.jours[0]) or promo.date_fin >= monde.jours[-1]:
            continue
        for p in promo.id_produits:
            serie = par_produit_jour.loc[p]
            pendant = serie[pd.Timestamp(promo.date_debut) : pd.Timestamp(promo.date_fin)].mean()
            reference = serie[avant : pd.Timestamp(promo.date_debut) - pd.Timedelta(days=1)].mean()
            if reference > 0:
                hausses.append(pendant / reference)
    assert np.median(hausses) > 1.3
