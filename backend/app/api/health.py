from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.db import engine

router = APIRouter(tags=["système"])


class HealthOut(BaseModel):
    status: Literal["ok", "degrade"]
    database: Literal["ok", "indisponible"]
    version: str


@router.get("/health", response_model=HealthOut)
def health(response: Response) -> HealthOut:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "indisponible"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthOut(
        status="ok" if database == "ok" else "degrade",
        database=database,
        version=settings.app_version,
    )
