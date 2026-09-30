"""Monde simulé des systèmes sources (D-14).

Tout est déterministe (graine fixe) et « stable par préfixe » : les chiffres d'un jour donné ne
dépendent que des jours précédents, jamais de la date à laquelle on lance la simulation. Toute
l'équipe obtient donc les mêmes données, et chaque nouveau jour s'ajoute sans modifier le passé.
"""

from app.monde.monde import Monde, construire_monde

__all__ = ["Monde", "construire_monde"]
