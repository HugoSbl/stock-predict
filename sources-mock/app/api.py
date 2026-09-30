"""API des systèmes sources simulés (D-14) : ERP Ventes, WMS Stocks, Portail Fournisseurs.

Noms de colonnes « côté source » (anglais) : le mapping vers le schéma cible est porté par la
configuration des connecteurs (source_api.mapping_colonnes, D-04).
"""

import asyncio
import math
from datetime import date, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel

from app.config import cle_api, delai_timeout_secondes, pannes_permanentes
from app.etat import monde_courant
from app.monde import Monde
from app.salissage import salir

router = APIRouter(prefix="/api/v1")

Panne = Literal["timeout", "auth", "500"]
TAILLE_PAGE_MAX = 5000
TAUX_SALISSAGE_COMMANDES = 0.02


class Page(BaseModel):
    data: list[dict[str, Any]]
    page: int
    page_size: int
    total: int
    pages: int


async def controle_acces(
    request: Request,
    fail: Annotated[Panne | None, Query(description="Simule une panne de la source")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Pannes simulées (paramètre `fail` ou MOCK_PANNES) puis authentification par clé d'API."""
    source = request.url.path.rstrip("/").rsplit("/", 1)[-1]
    panne = fail or pannes_permanentes().get(source)
    if panne == "timeout":
        await asyncio.sleep(delai_timeout_secondes())
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Source trop lente")
    if panne == "500":
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Erreur interne de la source")
    if panne == "auth" or authorization != f"Bearer {cle_api()}":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Clé d'API invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )


Pagination = Annotated[int, Query(ge=1)]
TaillePage = Annotated[int, Query(ge=1, le=TAILLE_PAGE_MAX)]


def _paginer(lignes: list[dict[str, Any]], page: int, page_size: int) -> Page:
    debut = (page - 1) * page_size
    return Page(
        data=lignes[debut : debut + page_size],
        page=page,
        page_size=page_size,
        total=len(lignes),
        pages=max(1, math.ceil(len(lignes) / page_size)),
    )


def _jour_disponible(monde: Monde, jour: date) -> None:
    if monde.index_jour(jour) is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Aucune donnée pour le {jour} (disponible du {monde.jours[0]} au {monde.hier})",
        )


@router.get("/sales", response_model=Page, dependencies=[Depends(controle_acces)])
def ventes(
    date: Annotated[date, Query(description="Jour de vente (données disponibles jusqu'à hier)")],
    page: Pagination = 1,
    page_size: TaillePage = 1000,
) -> Page:
    """ERP Ventes : ventes agrégées du jour par produit × entrepôt."""
    monde = monde_courant()
    _jour_disponible(monde, date)
    lignes = [
        {
            "sale_date": v.date_vente.isoformat(),
            "sku": v.reference,
            "warehouse_code": v.code_entrepot,
            "qty": int(v.quantite_vendue),
            "unit_price_excl_tax": float(v.prix_vente_ht),
            # Colonnes non mappées (RG-01)
            "currency": "EUR",
            "channel": "STORE",
            "_ingested_at": f"{date + timedelta(days=1)}T01:12:00Z",
        }
        for v in monde.ventes_du_jour(date).itertuples()
    ]
    return _paginer(salir(lignes, "sales", date.isoformat(), "qty"), page, page_size)


@router.get("/stock-levels", response_model=Page, dependencies=[Depends(controle_acces)])
def stocks(
    date: Annotated[date, Query(description="Jour du relevé de fin de journée")],
    page: Pagination = 1,
    page_size: TaillePage = 1000,
) -> Page:
    """WMS Stocks : relevé de stock de fin de journée par produit × entrepôt."""
    monde = monde_courant()
    _jour_disponible(monde, date)
    lignes = [
        {
            "snapshot_date": s.date_releve.isoformat(),
            "sku": s.reference,
            "warehouse_code": s.code_entrepot,
            "on_hand": int(s.quantite_stock),
            # Colonnes non mappées (RG-01)
            "unit": "EA",
            "bin_location": f"{s.code_entrepot[-3:]}-{s.id_produit % 40:02d}-{s.id_produit % 7}",
        }
        for s in monde.stocks_du_jour(date).itertuples()
    ]
    return _paginer(salir(lignes, "stock-levels", date.isoformat(), "on_hand"), page, page_size)


@router.get("/purchase-orders", response_model=Page, dependencies=[Depends(controle_acces)])
def commandes(
    modifie_depuis: Annotated[
        date, Query(description="Commandes passées, livrées ou encore ouvertes depuis cette date")
    ],
    page: Pagination = 1,
    page_size: TaillePage = 1000,
) -> Page:
    """Portail Fournisseurs : lignes de commandes fournisseurs (une ligne par produit commandé)."""
    monde = monde_courant()
    c = monde.commandes_au(monde.hier)
    livree_depuis = c.date_livraison_reelle.notna() & (
        c.date_livraison_reelle.map(lambda d: d is not None and d >= modifie_depuis)
    )
    selection = c[
        (c.date_achat >= modifie_depuis)
        | livree_depuis
        | (c.statut == "EN_COURS")
        | ((c.statut == "ANNULEE") & (c.date_livraison_estimee >= modifie_depuis))
    ]
    detail = selection.merge(monde.lignes_commande, on="id_commande").sort_values(
        ["id_commande", "id_produit"]
    )
    lignes = [
        {
            "po_number": cmd.numero_commande,
            "supplier_code": cmd.code_fournisseur,
            "warehouse_code": cmd.code_entrepot,
            "ordered_at": cmd.date_achat.isoformat(),
            "expected_delivery": cmd.date_livraison_estimee.isoformat(),
            "delivered_at": cmd.date_livraison_reelle.isoformat()
            if cmd.date_livraison_reelle
            else None,
            "status": cmd.statut,
            "sku": cmd.reference,
            "qty": int(cmd.quantite_commandee),
            # Colonne non mappée (RG-01)
            "buyer": "achats@globalretail.example",
        }
        for cmd in detail.itertuples()
    ]
    lignes = salir(
        lignes, "purchase-orders", modifie_depuis.isoformat(), "qty", TAUX_SALISSAGE_COMMANDES
    )
    return _paginer(lignes, page, page_size)
