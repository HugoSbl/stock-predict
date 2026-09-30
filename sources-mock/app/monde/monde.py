"""Assemblage du monde : référentiels + simulation jour par jour des ventes, stocks et commandes.

Politique de réassort (par couple produit × entrepôt, revue quotidienne) :
  point de commande  s = r × (délai + 4)   ;   niveau cible  S = r × (délai + 18)
  r = demande moyenne attendue (base × saison) — les promotions ne sont PAS anticipées,
  d'où des ruptures réalistes pendant les promos. Les commandes sont groupées par
  fournisseur × entrepôt × jour. Retards aléatoires, annulations et grèves fournisseurs.
Ventes = min(demande, stock) : la demande non servie est perdue (ventes censurées).
"""

import math
from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import cached_property

import numpy as np
import pandas as pd

from app.monde import parametres as P
from app.monde.calendrier import generer_calendrier
from app.monde.catalogue import (
    CATEGORIES,
    ENTREPOTS,
    FOURNISSEURS,
    PAYS,
    Entrepot,
    Fournisseur,
    Produit,
    generer_produits,
)
from app.monde.demande import facteur_promotion, facteur_saison, intensite_demande, popularite_base
from app.monde.promotions import Promotion, generer_promotions

DISPERSION = 4.0  # forme de la loi gamma : demande surdispersée (négative binomiale)
PROBA_RETARD = 0.08
PROBA_ANNULATION = 0.01
REMISE_PRIX_DE = 0.97  # prix de vente légèrement plus bas en Allemagne
CLES = ["reference", "code_entrepot", "id_produit", "id_entrepot"]
COLONNES_VENTES = ["date_vente", *CLES, "quantite_vendue", "prix_vente_ht"]
COLONNES_STOCKS = ["date_releve", *CLES, "quantite_stock"]


@dataclass(frozen=True)
class Greve:
    id_fournisseur: int
    debut: date
    fin: date


@dataclass
class Monde:
    aujourd_hui: date
    produits: list[Produit]
    entrepots: list[Entrepot]
    fournisseurs: list[Fournisseur]
    promotions: list[Promotion]
    calendrier: pd.DataFrame  # jusqu'à DATE_FIN_REFERENTIELS
    jours: list[date]  # jours simulés : DATE_DEBUT … hier
    demande: np.ndarray  # jours × couples (demande réelle, non exportée)
    ventes: np.ndarray  # jours × couples
    stock_fin: np.ndarray  # jours × couples, stock en fin de journée
    remise: np.ndarray  # jours × produits, taux de remise en %
    commandes: pd.DataFrame
    lignes_commande: pd.DataFrame
    greves: list[Greve]

    @property
    def hier(self) -> date:
        return self.aujourd_hui - timedelta(days=1)

    @cached_property
    def couples(self) -> pd.DataFrame:
        """Index des colonnes des matrices : couple = (produit, entrepôt)."""
        return pd.DataFrame(
            [(p, e) for p in self.produits for e in self.entrepots], columns=["produit", "entrepot"]
        ).assign(
            reference=lambda df: df.produit.map(lambda p: p.reference),
            code_entrepot=lambda df: df.entrepot.map(lambda e: e.code_entrepot),
            id_produit=lambda df: df.produit.map(lambda p: p.id_produit),
            id_entrepot=lambda df: df.entrepot.map(lambda e: e.id_entrepot),
        )

    @cached_property
    def prix_de_base(self) -> np.ndarray:
        """Prix HT de vente hors promotion par couple (réduction pays incluse)."""
        return np.array(
            [
                p.prix_unitaire_ht * (REMISE_PRIX_DE if e.code_pays == "DE" else 1.0)
                for p in self.produits
                for e in self.entrepots
            ]
        )

    def index_jour(self, jour: date) -> int | None:
        i = (jour - P.DATE_DEBUT).days
        return i if 0 <= i < len(self.jours) else None

    def ventes_du_jour(self, jour: date) -> pd.DataFrame:
        """Ventes non nulles d'un jour : une ligne par couple (agrégat journalier, D-19)."""
        i = self.index_jour(jour)
        if i is None:
            return pd.DataFrame(columns=COLONNES_VENTES)
        remise = np.repeat(self.remise[i], len(self.entrepots))
        prix = np.round(self.prix_de_base * (1 - remise / 100), 2)
        df = self.couples[CLES].assign(
            date_vente=jour, quantite_vendue=self.ventes[i], prix_vente_ht=prix
        )
        return df[df.quantite_vendue > 0][COLONNES_VENTES].reset_index(drop=True)

    def stocks_du_jour(self, jour: date) -> pd.DataFrame:
        i = self.index_jour(jour)
        if i is None:
            return pd.DataFrame(columns=COLONNES_STOCKS)
        return self.couples[CLES].assign(date_releve=jour, quantite_stock=self.stock_fin[i])[
            COLONNES_STOCKS
        ]


def _generer_greves(rng: np.random.Generator) -> list[Greve]:
    greves = []
    for f in FOURNISSEURS:
        for annee in range(P.DATE_DEBUT.year, P.DATE_FIN_REFERENTIELS.year + 1):
            if rng.random() < 0.35:
                debut = date(annee, 1, 1) + timedelta(days=int(rng.integers(0, 350)))
                greves.append(
                    Greve(f.id_fournisseur, debut, debut + timedelta(days=int(rng.integers(7, 16))))
                )
    return greves


def _simuler(
    rng: np.random.Generator,
    intensite: np.ndarray,
    rythme_attendu: np.ndarray,
    produits: list[Produit],
    entrepots: list[Entrepot],
    greves: list[Greve],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple]]:
    nb_jours, nb_couples = intensite.shape
    nb_e = len(entrepots)
    delai = {f.id_fournisseur: f.delai_moyen_jours for f in FOURNISSEURS}
    fournisseur_couple = np.repeat([p.id_fournisseur_habituel for p in produits], nb_e)
    entrepot_couple = np.tile([e.id_entrepot for e in entrepots], len(produits))
    delai_couple = np.array([delai[f] for f in fournisseur_couple])
    # Groupes de commande : fournisseur × entrepôt
    groupes = [(f.id_fournisseur, e.id_entrepot) for f in FOURNISSEURS for e in entrepots]
    groupe_couple = np.array(
        [groupes.index((f, e)) for f, e in zip(fournisseur_couple, entrepot_couple, strict=True)]
    )
    greves_par_fournisseur: dict[int, list[Greve]] = {}
    for g in greves:
        greves_par_fournisseur.setdefault(g.id_fournisseur, []).append(g)

    marge = 90  # arrivées au-delà de la fenêtre simulée
    arrivees = np.zeros((nb_jours + marge, nb_couples), dtype=np.int64)
    annulations = np.zeros((nb_jours + marge, nb_couples), dtype=np.int64)
    stock = np.ceil(rythme_attendu[0] * (delai_couple + 10)).astype(np.int64)
    en_commande = np.zeros(nb_couples, dtype=np.int64)

    demande = np.zeros((nb_jours, nb_couples), dtype=np.int32)
    ventes = np.zeros((nb_jours, nb_couples), dtype=np.int32)
    stock_fin = np.zeros((nb_jours, nb_couples), dtype=np.int32)
    commandes: list[tuple] = []  # (jour, groupe, arrivée, annulée, [(couple, qté)])

    for d in range(nb_jours):
        # Tirages de taille fixe chaque jour : les jours passés ne dépendent pas de la durée simulée
        gamma = rng.gamma(DISPERSION, 1.0 / DISPERSION, size=nb_couples)
        alea_delai = rng.integers(-1, 3, size=len(groupes))
        alea_retard = rng.random(len(groupes))
        retard = rng.integers(5, 11, size=len(groupes))
        alea_annulation = rng.random(len(groupes))
        alea_greve = rng.integers(1, 4, size=len(groupes))

        stock += arrivees[d]
        en_commande -= arrivees[d] + annulations[d]

        dem = rng.poisson(intensite[d] * gamma)
        vendu = np.minimum(dem, stock)
        stock -= vendu
        demande[d], ventes[d], stock_fin[d] = dem, vendu, stock

        # Réassort
        r = rythme_attendu[d]
        position = stock + en_commande
        a_commander = position <= r * (delai_couple + 4)
        if not a_commander.any():
            continue
        quantite = np.ceil(np.maximum(r * (delai_couple + 18) - position, 10) / 10) * 10
        for g in np.unique(groupe_couple[a_commander]):
            couples = np.flatnonzero(a_commander & (groupe_couple == g))
            f_id = groupes[g][0]
            duree = max(1, delai[f_id] + int(alea_delai[g]))
            if alea_retard[g] < PROBA_RETARD:
                duree += int(retard[g])
            arrivee = d + duree
            jour_arrivee = P.DATE_DEBUT + timedelta(days=arrivee)
            for greve in greves_par_fournisseur.get(f_id, []):
                if greve.debut <= jour_arrivee <= greve.fin:
                    arrivee = (greve.fin - P.DATE_DEBUT).days + int(alea_greve[g])
            arrivee = min(arrivee, nb_jours + marge - 1)
            annulee = bool(alea_annulation[g] < PROBA_ANNULATION)
            qtes = quantite[couples].astype(np.int64)
            en_commande[couples] += qtes
            (annulations if annulee else arrivees)[arrivee, couples] += qtes
            commandes.append(
                (d, g, arrivee, annulee, list(zip(couples.tolist(), qtes.tolist(), strict=True)))
            )

    return demande, ventes, stock_fin, (commandes, groupes)


def construire_monde(aujourd_hui: date) -> Monde:
    minimum = P.DATE_DEBUT + timedelta(days=366)  # une année complète (calibrage des seuils)
    if aujourd_hui < minimum:
        raise ValueError(f"aujourd_hui doit être au moins le {minimum}")
    graines = np.random.SeedSequence(P.GRAINE).spawn(5)
    rng_catalogue, rng_base, rng_promos, rng_greves, rng_simulation = (
        np.random.default_rng(g) for g in graines
    )

    produits = generer_produits(rng_catalogue, P.NB_PRODUITS)
    entrepots = list(ENTREPOTS)
    calendrier = generer_calendrier(P.DATE_DEBUT, P.DATE_FIN_REFERENTIELS)
    promotions = generer_promotions(
        rng_promos, P.DATE_DEBUT, P.DATE_FIN_REFERENTIELS, len(produits)
    )
    greves = _generer_greves(rng_greves)
    base = popularite_base(rng_base, produits, entrepots)

    jours_idx = pd.date_range(P.DATE_DEBUT, aujourd_hui - timedelta(days=1), freq="D")
    effet_promo, remise = facteur_promotion(jours_idx, promotions, len(produits))
    intensite = intensite_demande(
        jours_idx, calendrier, produits, entrepots, base, effet_promo, P.DATE_DEBUT
    )
    # Rythme anticipé par le réassort : base × saison (sans promo ni jour de semaine)
    saison = np.repeat(facteur_saison(jours_idx, produits), len(entrepots), axis=1)
    rythme_attendu = base[None, :] * saison

    demande, ventes, stock_fin, (commandes, groupes) = _simuler(
        rng_simulation, intensite, rythme_attendu, produits, entrepots, greves
    )

    # Seuil d'alerte produit (RG-11), calibré comme le ferait le métier : 10e percentile du stock
    # observé sur la première année, tous entrepôts confondus (arrondi à la dizaine). Fenêtre fixe :
    # le seuil ne change pas d'un jour à l'autre.
    calibrage = stock_fin[:365].reshape(-1, len(produits), len(entrepots))
    seuils = np.percentile(calibrage, 10, axis=(0, 2))
    produits = [
        replace(p, seuil_alerte=max(10, int(math.ceil(s / 10) * 10)))
        for p, s in zip(produits, seuils, strict=True)
    ]

    tables_commandes, tables_lignes = _tables_commandes(
        commandes, groupes, produits, entrepots, aujourd_hui
    )
    return Monde(
        aujourd_hui=aujourd_hui,
        produits=produits,
        entrepots=entrepots,
        fournisseurs=list(FOURNISSEURS),
        promotions=promotions,
        calendrier=calendrier,
        jours=[d.date() for d in jours_idx],
        demande=demande,
        ventes=ventes,
        stock_fin=stock_fin,
        remise=remise,
        commandes=tables_commandes,
        lignes_commande=tables_lignes,
        greves=greves,
    )


def _tables_commandes(commandes, groupes, produits, entrepots, aujourd_hui):
    """Statut vu le jour J : livrée (ou annulée) si l'échéance est passée, sinon en cours."""
    delai = {f.id_fournisseur: f.delai_moyen_jours for f in FOURNISSEURS}
    code_f = {f.id_fournisseur: f.code_fournisseur for f in FOURNISSEURS}
    code_e = {e.id_entrepot: e.code_entrepot for e in entrepots}
    nb_e = len(entrepots)
    hier_idx = (aujourd_hui - P.DATE_DEBUT).days - 1
    lignes_c, lignes_l = [], []
    for id_commande, (d, g, arrivee, annulee, lignes) in enumerate(commandes, start=1):
        f_id, e_id = groupes[g]
        date_achat = P.DATE_DEBUT + timedelta(days=d)
        statut = ("ANNULEE" if annulee else "LIVREE") if arrivee <= hier_idx else "EN_COURS"
        lignes_c.append(
            {
                "id_commande": id_commande,
                "numero_commande": f"CF-{date_achat:%Y%m%d}-{code_f[f_id][2:]}-{code_e[e_id]}",
                "date_achat": date_achat,
                "date_livraison_estimee": date_achat + timedelta(days=delai[f_id]),
                "date_livraison_reelle": (
                    P.DATE_DEBUT + timedelta(days=arrivee) if statut == "LIVREE" else None
                ),
                "statut": statut,
                "id_fournisseur": f_id,
                "code_fournisseur": code_f[f_id],
                "id_entrepot": e_id,
                "code_entrepot": code_e[e_id],
            }
        )
        for couple, qte in lignes:
            produit = produits[couple // nb_e]
            lignes_l.append(
                {
                    "id_commande": id_commande,
                    "id_produit": produit.id_produit,
                    "reference": produit.reference,
                    "quantite_commandee": qte,
                }
            )
    return pd.DataFrame(lignes_c), pd.DataFrame(lignes_l)


__all__ = ["CATEGORIES", "PAYS", "Monde", "construire_monde"]
