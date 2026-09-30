import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def date_figee():
    """Date de référence figée : mêmes données à chaque exécution des tests."""
    mp = pytest.MonkeyPatch()
    mp.setenv("MOCK_DATE_REFERENCE", "2026-09-30")
    mp.setenv("MOCK_TIMEOUT_SECONDES", "0.3")
    mp.delenv("MOCK_PANNES", raising=False)
    yield
    mp.undo()


@pytest.fixture(scope="session")
def client(date_figee):
    from app.main import app

    with TestClient(app) as c:
        c.headers["Authorization"] = "Bearer dev-mock-key"
        yield c
