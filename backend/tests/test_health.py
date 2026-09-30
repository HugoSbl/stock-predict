from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api import health as health_module
from app.main import app

client = TestClient(app)


def test_health_ok_quand_la_base_repond():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_health_degrade_quand_la_base_est_indisponible(monkeypatch):
    class EngineEnPanne:
        def connect(self):
            raise OperationalError("SELECT 1", {}, Exception("connexion refusée"))

    monkeypatch.setattr(health_module, "engine", EngineEnPanne())
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degrade", "database": "indisponible", "version": "0.1.0"}


def test_openapi_expose_sous_api():
    assert client.get("/api/openapi.json").status_code == 200
