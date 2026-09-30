"""Monde simulé courant, reconstruit automatiquement quand la date de référence change."""

import threading
from datetime import date

from app.config import date_reference
from app.monde import Monde, construire_monde

_verrou = threading.Lock()
_cache: dict[date, Monde] = {}


def monde_courant() -> Monde:
    jour = date_reference()
    with _verrou:
        if jour not in _cache:
            _cache.clear()
            _cache[jour] = construire_monde(jour)
        return _cache[jour]
