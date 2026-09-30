from datetime import UTC, datetime


def maintenant() -> datetime:
    """Point unique d'accès à l'heure courante (remplaçable dans les tests)."""
    return datetime.now(UTC)
