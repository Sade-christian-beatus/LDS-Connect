"""Génération d'un calendrier aller simple par la méthode du cercle (tables de Berger).

Pour n équipes (n pair) : n-1 journées de n/2 matchs ; chaque paire se rencontre une fois.
Pour n impair, une équipe fictive (exempt) est ajoutée : l'équipe qui la rencontre est
au repos. Domicile/extérieur est alterné pour équilibrer (simple convention : tous les
matchs d'une poule se jouent dans la même ville).
"""

import random
from collections.abc import Sequence


def berger_rounds[T](teams: Sequence[T], *, seed: int | None = None) -> list[list[tuple[T, T]]]:
    """Retourne la liste des journées ; chaque journée est une liste de (domicile, extérieur).

    `seed` : si fourni, l'ordre des équipes est mélangé de façon reproductible (tirage).
    """
    if len(teams) < 2:
        raise ValueError("Il faut au moins deux équipes")
    if len(set(teams)) != len(teams):
        raise ValueError("Équipes en double")

    order: list[T | None] = list(teams)
    if seed is not None:
        random.Random(seed).shuffle(order)  # noqa: S311 — tirage reproductible, pas crypto
    if len(order) % 2:
        order.append(None)  # exempt

    n = len(order)
    fixed, rotating = order[0], order[1:]
    rounds: list[list[tuple[T, T]]] = []
    for r in range(n - 1):
        current = [fixed, *rotating]
        pairs: list[tuple[T, T]] = []
        for i in range(n // 2):
            a, b = current[i], current[n - 1 - i]
            if a is None or b is None:
                continue  # exempt : pas de match
            # Alternance : l'équipe fixe change de côté à chaque journée ; pour les autres,
            # le sens dépend de la parité de la position. Comme chaque équipe avance d'une
            # position par journée, elle alterne domicile/extérieur (n-2 ruptures au total).
            home_first = (r % 2 == 0) if i == 0 else (i % 2 == 1)
            pairs.append((a, b) if home_first else (b, a))
        rounds.append(pairs)
        rotating = [rotating[-1], *rotating[:-1]]
    return rounds
