"""Export du monde simulé en CSV propres, un fichier par table cible (colonnes = schéma backend).

    python -m app.export /data/seed [--jusqu-a AAAA-MM-JJ]

Contrat d'échange avec `backend/app/seed.py` (voir docs/donnees.md). Données sans salissage :
le seed charge un historique propre ; les lignes invalides ne concernent que les API (lot 3).
"""

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from datetime import date, datetime, timedelta
from datetime import time as heure
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import FUSEAU, date_reference
from app.monde import Monde, construire_monde
from app.monde import parametres as P
from app.monde.catalogue import CATEGORIES, PAYS

COLONNES_COMMANDE = [
    "id_commande",
    "numero_commande",
    "date_achat",
    "date_livraison_estimee",
    "date_livraison_reelle",
    "statut",
    "id_fournisseur",
    "id_entrepot",
]


def tables(monde: Monde, jusqu_a: date) -> dict[str, pd.DataFrame]:
    n = monde.index_jour(jusqu_a)
    if n is None:
        raise ValueError(f"--jusqu-a doit être entre {monde.jours[0]} et {monde.hier}")
    n += 1
    fin_calendrier = monde.aujourd_hui + timedelta(days=P.HORIZON_CALENDRIER_JOURS)
    couples = monde.couples
    nb_couples = len(couples)

    # Ventes : matrices jours × couples aplaties, lignes nulles exclues (agrégat journalier, D-19)
    jours = np.repeat(np.array(monde.jours[:n], dtype="datetime64[D]"), nb_couples)
    remise = np.repeat(monde.remise[:n], len(monde.entrepots), axis=1)
    prix = np.round(monde.prix_de_base[None, :] * (1 - remise / 100), 2).reshape(-1)
    qte = monde.ventes[:n].reshape(-1)
    id_produit = np.tile(couples.id_produit.to_numpy(), n)
    id_entrepot = np.tile(couples.id_entrepot.to_numpy(), n)
    vendu = qte > 0
    vente = pd.DataFrame(
        {
            "date_vente": jours[vendu],
            "quantite_vendue": qte[vendu],
            "prix_vente_ht": prix[vendu],
            "id_produit": id_produit[vendu],
            "id_entrepot": id_entrepot[vendu],
        }
    )
    stock_quotidien = pd.DataFrame(
        {
            "id_produit": id_produit,
            "id_entrepot": id_entrepot,
            "date_releve": jours,
            "quantite_stock": monde.stock_fin[:n].reshape(-1),
        }
    )
    releve = datetime.combine(jusqu_a, heure(23, 59), FUSEAU).isoformat()
    stock = couples[["id_produit", "id_entrepot"]].assign(
        quantite_stock=monde.stock_fin[n - 1], date_maj=releve
    )

    # Commandes telles que connues le jour jusqu_a
    c = monde.commandes_au(jusqu_a)
    lignes = monde.lignes_commande[monde.lignes_commande.id_commande.isin(c.id_commande)]

    promotions = [p for p in monde.promotions if p.date_debut <= fin_calendrier]
    calendrier = monde.calendrier[
        (monde.calendrier.date_jour >= P.DATE_DEBUT)
        & (monde.calendrier.date_jour <= fin_calendrier)
    ]
    return {
        "pays": pd.DataFrame([asdict(p) for p in PAYS]),
        "categorie": pd.DataFrame(
            [
                {"id_categorie": c.id_categorie, "libelle_categorie": c.libelle_categorie}
                for c in CATEGORIES
            ]
        ),
        "fournisseur": pd.DataFrame([asdict(f) for f in monde.fournisseurs]),
        "entrepot": pd.DataFrame([asdict(e) for e in monde.entrepots]).drop(columns="taille"),
        "produit": pd.DataFrame([asdict(p) for p in monde.produits]),
        "calendrier": calendrier,
        "promotion": pd.DataFrame(
            [{k: v for k, v in asdict(p).items() if k != "id_produits"} for p in promotions]
        ),
        "produit_promotion": pd.DataFrame(
            [
                {"id_promotion": p.id_promotion, "id_produit": i}
                for p in promotions
                for i in p.id_produits
            ]
        ),
        "vente": vente,
        "stock_quotidien": stock_quotidien,
        "stock": stock,
        "commande_fournisseur": c[COLONNES_COMMANDE],
        "ligne_commande": lignes.drop(columns="reference"),
    }


def exporter(sortie: Path, jusqu_a: date | None = None) -> dict:
    debut = time.monotonic()
    monde = construire_monde(date_reference())
    jusqu_a = jusqu_a or monde.hier
    sortie.mkdir(parents=True, exist_ok=True)
    fichiers = {}
    for nom, df in tables(monde, jusqu_a).items():
        chemin = sortie / f"{nom}.csv"
        df.to_csv(chemin, index=False, float_format="%.2f")
        fichiers[nom] = {
            "lignes": len(df),
            "sha256": hashlib.sha256(chemin.read_bytes()).hexdigest(),
        }
    manifeste = {
        "graine": P.GRAINE,
        "date_reference": monde.aujourd_hui.isoformat(),
        "jusqu_a": jusqu_a.isoformat(),
        "genere_le": datetime.now(FUSEAU).isoformat(timespec="seconds"),
        "fichiers": fichiers,
    }
    (sortie / "manifest.json").write_text(json.dumps(manifeste, indent=2, ensure_ascii=False))
    manifeste["duree_secondes"] = round(time.monotonic() - debut, 1)
    return manifeste


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("sortie", type=Path)
    parser.add_argument(
        "--jusqu-a",
        type=date.fromisoformat,
        default=None,
        help="dernier jour d'historique (défaut : hier)",
    )
    args = parser.parse_args()
    m = exporter(args.sortie, args.jusqu_a)
    print(
        f"Export du monde simulé (graine {m['graine']}, historique jusqu'au {m['jusqu_a']}) "
        f"en {m['duree_secondes']} s → {args.sortie}"
    )
    for nom, info in m["fichiers"].items():
        print(f"  {nom:<22} {info['lignes']:>10,} lignes".replace(",", " "))


if __name__ == "__main__":
    main()
