"""Protection CSRF (D-12) : toute requête mutante vers /api doit porter X-Requested-With.

Un formulaire ou une image d'un site tiers ne peut pas ajouter cet en-tête, et un appel `fetch`
cross-origin qui l'ajoute déclenche un preflight CORS refusé. Complète le cookie SameSite=Strict.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

EN_TETE = "x-requested-with"
VALEUR = "StockPredict"
METHODES_MUTANTES = {"POST", "PUT", "PATCH", "DELETE"}


class ProtectionCsrf(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (
            request.method in METHODES_MUTANTES
            and request.url.path.startswith("/api/")
            and request.headers.get(EN_TETE) != VALEUR
        ):
            return JSONResponse({"detail": "Requête refusée (protection CSRF)"}, status_code=403)
        return await call_next(request)
