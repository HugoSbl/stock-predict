"""Base de test dédiée (<base>_test), recréée à chaque session puis migrée avec Alembic.

DATABASE_URL est redirigée AVANT l'import de l'application : les tests ne touchent jamais la base
de développement.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

URL_DEV = make_url(
    os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://stockpredict:stockpredict@localhost:5432/stockpredict"
    )
)
URL_TEST = URL_DEV.set(database=f"{URL_DEV.database}_test")
os.environ["DATABASE_URL"] = URL_TEST.render_as_string(hide_password=False)

RACINE_BACKEND = Path(__file__).resolve().parents[1]


def recreer_base_de_test() -> None:
    admin = create_engine(URL_DEV.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{URL_TEST.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{URL_TEST.database}"'))
    admin.dispose()


def config_alembic():
    from alembic.config import Config

    return Config(str(RACINE_BACKEND / "alembic.ini"))


@pytest.fixture(scope="session", autouse=True)
def base_migree():
    from alembic import command

    recreer_base_de_test()
    command.upgrade(config_alembic(), "head")
    yield


@pytest.fixture
def connexion():
    """Connexion dans une transaction annulée en fin de test : aucune donnée ne persiste."""
    from app.db import engine

    with engine.connect() as conn:
        transaction = conn.begin()
        yield conn
        transaction.rollback()
