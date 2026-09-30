from fastapi import FastAPI

from app.api import health
from app.config import settings

app = FastAPI(
    title="StockPredict API",
    version=settings.app_version,
    # Tout est servi sous /api pour passer par le proxy Vite (D-17)
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)

app.include_router(health.router, prefix="/api")
