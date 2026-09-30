"""Graphiques de contrôle de la saisonnalité du monde simulé (critère d'acceptation du lot 1).

uv run python -m app.graphiques ../docs/donnees
"""

import sys
from datetime import timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.config import date_reference  # noqa: E402
from app.monde import construire_monde  # noqa: E402

# Palette catégorielle validée (ordre fixe, jamais cyclé) + encres de texte
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURFACE, TEXTE, TEXTE_2, GRILLE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
STATUT_CRITIQUE = "#c0392b"

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRILLE,
        "axes.labelcolor": TEXTE_2,
        "axes.titlecolor": TEXTE,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRILLE,
        "grid.linewidth": 0.8,
        "xtick.color": TEXTE_2,
        "ytick.color": TEXTE_2,
        "font.size": 10,
        "legend.frameon": False,
        "lines.linewidth": 2,
    }
)


def _ventes_longues(monde) -> pd.DataFrame:
    nb_jours, nb_couples = monde.ventes.shape
    couples = monde.couples
    return pd.DataFrame(
        {
            "jour": np.repeat(pd.to_datetime(monde.jours), nb_couples),
            "qte": monde.ventes.reshape(-1),
            "pays": np.tile(couples.entrepot.map(lambda e: e.code_pays).to_numpy(), nb_jours),
            "categorie": np.tile(
                couples.produit.map(lambda p: p.id_categorie).to_numpy(), nb_jours
            ),
            "produit": np.tile(couples.id_produit.to_numpy(), nb_jours),
        }
    )


def profil_hebdomadaire(df: pd.DataFrame, sortie: Path) -> None:
    jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    fig, ax = plt.subplots(figsize=(8, 4))
    largeur = 0.38
    for k, pays in enumerate(["FR", "DE"]):
        serie = df[df.pays == pays].groupby([df.jour.dt.date, df.jour.dt.dayofweek]).qte.sum()
        par_jour = serie.groupby(level=1).mean()
        indice = par_jour / par_jour.mean() * 100
        x = np.arange(7) + (k - 0.5) * (largeur + 0.02)
        barres = ax.bar(
            x, indice, largeur, color=SERIES[k], label="France" if pays == "FR" else "Allemagne"
        )
        for b, v in zip(barres, indice, strict=True):
            ax.annotate(
                f"{v:.0f}",
                (b.get_x() + b.get_width() / 2, v),
                ha="center",
                va="bottom",
                xytext=(0, 2),
                textcoords="offset points",
                fontsize=8,
                color=TEXTE_2,
            )
    ax.set_xticks(range(7), jours)
    ax.set_ylabel("Indice des ventes (moyenne = 100)")
    ax.set_title("Profil hebdomadaire — magasins fermés le dimanche en Allemagne")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(sortie / "saisonnalite_hebdomadaire.png", dpi=150)
    plt.close(fig)


def saisonnalite_annuelle(df: pd.DataFrame, sortie: Path) -> None:
    categories = {3: "Boissons", 5: "Surgelés", 2: "Épicerie sucrée", 4: "Produits laitiers"}
    mois = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for k, (cat, nom) in enumerate(categories.items()):
        sous = df[df.categorie == cat]
        quotidien = sous.groupby(sous.jour).qte.sum()
        par_mois = quotidien.groupby(quotidien.index.month).mean()
        indice = par_mois / par_mois.mean() * 100
        ax.plot(range(1, 13), indice, color=SERIES[k], marker="o", markersize=4, label=nom)
        ax.annotate(
            nom,
            (12, indice.iloc[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            color=TEXTE,
            fontsize=9,
        )
    ax.set_xticks(range(1, 13), mois)
    ax.set_xlim(0.7, 14.2)
    ax.set_ylabel("Indice mensuel (moyenne annuelle = 100)")
    ax.set_title("Saisonnalité annuelle par catégorie — été, Noël, Pâques")
    ax.legend(loc="upper left", ncols=2)
    fig.tight_layout()
    fig.savefig(sortie / "saisonnalite_annuelle.png", dpi=150)
    plt.close(fig)


def effet_promotions(monde, df: pd.DataFrame, sortie: Path) -> None:
    par_produit = df.groupby(["produit", "jour"]).qte.sum()
    fenetre = range(-14, 22)
    ratios = []
    for promo in monde.promotions:
        debut = pd.Timestamp(promo.date_debut)
        if debut - pd.Timedelta(days=28) < pd.Timestamp(monde.jours[0]):
            continue
        if debut + pd.Timedelta(days=21) > pd.Timestamp(monde.jours[-1]):
            continue
        for p in promo.id_produits:
            serie = par_produit.loc[p]
            reference = serie[debut - pd.Timedelta(days=28) : debut - pd.Timedelta(days=15)].mean()
            if reference > 0:
                ratios.append(
                    [serie.get(debut + pd.Timedelta(days=d), 0) / reference for d in fenetre]
                )
    # Pas de lissage centré : il ferait « monter » la courbe avant le début de la promotion.
    # Les campagnes démarrent des jours de semaine variés, la moyenne brute reste lisible.
    moyenne = np.array(ratios).mean(axis=0) * 100
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axvspan(0, 10, color=SERIES[0], alpha=0.08, lw=0)
    ax.annotate(
        "Période de promotion (7 à 14 j)",
        (0.5, 0.04),
        xycoords=("data", "axes fraction"),
        va="bottom",
        color=TEXTE_2,
        fontsize=9,
    )
    ax.plot(list(fenetre), moyenne, color=SERIES[0], marker="o", markersize=3)
    ax.axhline(100, color=TEXTE_2, lw=1, ls=(0, (4, 3)))
    ax.set_xlabel("Jours depuis le début de la promotion")
    ax.set_ylabel("Ventes vs référence (= 100)")
    ax.set_title(f"Effet promotion moyen — {len(ratios)} couples produit × campagne")
    fig.tight_layout()
    fig.savefig(sortie / "effet_promotions.png", dpi=150)
    plt.close(fig)


def exemple_stock(monde, sortie: Path) -> None:
    produit = monde.produits[0]
    couple = 0  # REF-4512 × Lyon-Sud
    jours = pd.to_datetime(monde.jours[-180:])
    stock = monde.stock_fin[-180:, couple]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(jours, stock, color=SERIES[0], label="Stock fin de journée")
    ax.axhline(produit.seuil_alerte, color=STATUT_CRITIQUE, lw=1.5, ls=(0, (4, 3)))
    ax.annotate(
        f"Seuil d'alerte ({produit.seuil_alerte})",
        (jours[0], produit.seuil_alerte),
        xytext=(0, 4),
        textcoords="offset points",
        color=STATUT_CRITIQUE,
        fontsize=9,
    )
    ruptures = stock == 0
    if ruptures.any():
        ax.scatter(
            jours[ruptures],
            stock[ruptures],
            s=36,
            color=STATUT_CRITIQUE,
            zorder=3,
            edgecolor=SURFACE,
            linewidth=2,
            label="Rupture",
        )
    ax.set_ylabel("Unités")
    ax.set_title(f"{produit.reference} {produit.libelle} — Lyon-Sud, 180 derniers jours")
    ax.legend(loc="upper right")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(sortie / "exemple_stock_reassort.png", dpi=150)
    plt.close(fig)


def main() -> None:
    sortie = Path(sys.argv[1] if len(sys.argv) > 1 else "graphiques")
    sortie.mkdir(parents=True, exist_ok=True)
    monde = construire_monde(date_reference())
    df = _ventes_longues(monde)
    profil_hebdomadaire(df, sortie)
    saisonnalite_annuelle(df, sortie)
    effet_promotions(monde, df, sortie)
    exemple_stock(monde, sortie)
    print(f"4 graphiques écrits dans {sortie} (monde au {monde.aujourd_hui - timedelta(days=1)})")


if __name__ == "__main__":
    main()
