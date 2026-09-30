"""API sources simulées (D-14) : ERP Ventes, WMS Stocks, Portail Fournisseurs.

Documentation interactive : /docs. Authentification : `Authorization: Bearer <MOCK_API_KEY>`.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.etat import monde_courant


@asynccontextmanager
async def lifespan(_: FastAPI):
    monde_courant()  # construit le monde au démarrage plutôt qu'à la première requête
    yield


app = FastAPI(title="StockPredict — sources simulées", version="0.2.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
