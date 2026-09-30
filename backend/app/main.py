import logging

from fastapi import APIRouter, FastAPI

from app.api import auth, health
from app.config import SECRET_JWT_DEV, settings
from app.securite.csrf import ProtectionCsrf

if settings.jwt_secret == SECRET_JWT_DEV:
    logging.getLogger("uvicorn.error").warning(
        "JWT_SECRET non défini : secret de développement utilisé (interdit en production)"
    )

app = FastAPI(
    title="StockPredict API",
    version=settings.app_version,
    # Tout est servi sous /api pour passer par le proxy Vite (D-17)
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)
app.add_middleware(ProtectionCsrf)

# Routes publiques : liste fermée (vérifiée par tests/test_controle_acces.py)
publiques = APIRouter(prefix="/api")
publiques.include_router(health.router)
publiques.include_router(auth.router)
app.include_router(publiques)

# Routes métier : chaque route DOIT déclarer ses rôles avec exiger_role(...) (RG-13, D-26)
metier = APIRouter(prefix="/api")
app.include_router(metier)
