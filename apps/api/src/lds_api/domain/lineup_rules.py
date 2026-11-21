"""Contrôle automatique d'une composition d'équipe (fonction pure).

Vérifié à la soumission et à la validation de la feuille de match :
nombre de titulaires et de remplaçants, appartenance à l'effectif, licence valide,
suspensions, âge minimum, numéros uniques, capitaine, gardien, et règle des locaux
(au moins X % de joueurs locaux parmi les titulaires).
"""

import math
import uuid
from dataclasses import dataclass
from decimal import Decimal

STARTER = "starter"
SUBSTITUTE = "substitute"


@dataclass(frozen=True)
class LineupRules:
    starters_count: int
    max_substitutes: int
    min_local_starters_ratio: Decimal
    min_age: int


@dataclass(frozen=True)
class Candidate:
    """Un joueur inscrit sur la feuille, enrichi des informations du registre."""

    person_id: uuid.UUID
    name: str
    role: str  # starter | substitute
    shirt_number: int | None
    is_captain: bool
    is_goalkeeper: bool
    is_squad_member: bool
    licence_ok: bool  # licence active et valide à la date du match
    is_suspended: bool
    is_local: bool
    age: int


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    person_id: uuid.UUID | None = None


def min_local_starters(starters_count: int, ratio: Decimal) -> int:
    """Nombre minimal de locaux parmi les titulaires (arrondi au supérieur : 50 % de 11 → 6)."""
    return math.ceil(Decimal(starters_count) * ratio)


def check_lineup(cands: list[Candidate], rules: LineupRules) -> list[Violation]:
    v: list[Violation] = []
    starters = [c for c in cands if c.role == STARTER]
    subs = [c for c in cands if c.role == SUBSTITUTE]

    if len(starters) != rules.starters_count:
        v.append(
            Violation(
                "starters_count",
                f"{len(starters)} titulaire(s) au lieu de {rules.starters_count}",
            )
        )
    if len(subs) > rules.max_substitutes:
        v.append(
            Violation(
                "substitutes_count",
                f"{len(subs)} remplaçants (maximum {rules.max_substitutes})",
            )
        )

    for c in cands:
        if not c.is_squad_member:
            v.append(Violation("not_in_squad", f"{c.name} n'est pas dans l'effectif", c.person_id))
        if not c.licence_ok:
            v.append(Violation("licence", f"{c.name} : licence non valide", c.person_id))
        if c.is_suspended:
            v.append(Violation("suspended", f"{c.name} est suspendu", c.person_id))
        if c.age < rules.min_age:
            v.append(Violation("min_age", f"{c.name} : moins de {rules.min_age} ans", c.person_id))
        if c.shirt_number is None:
            v.append(
                Violation("shirt_missing", f"{c.name} : numéro de maillot manquant", c.person_id)
            )

    numbers = [c.shirt_number for c in cands if c.shirt_number is not None]
    dupes = sorted({n for n in numbers if numbers.count(n) > 1})
    if dupes:
        v.append(Violation("shirt_duplicate", f"Numéros en double : {', '.join(map(str, dupes))}"))

    captains = [c for c in cands if c.is_captain]
    if len(captains) != 1:
        v.append(Violation("captain", "Un capitaine et un seul doit être désigné"))
    elif captains[0].role != STARTER:
        v.append(Violation("captain", "Le capitaine doit être titulaire", captains[0].person_id))

    if sum(c.is_goalkeeper for c in starters) != 1:
        v.append(Violation("goalkeeper", "Un gardien et un seul parmi les titulaires"))

    required = min_local_starters(rules.starters_count, rules.min_local_starters_ratio)
    locals_ = sum(c.is_local for c in starters)
    if starters and locals_ < required:
        v.append(
            Violation(
                "local_players",
                f"Règle des locaux : {locals_} local(aux) parmi les titulaires, "
                f"{required} requis ({rules.min_local_starters_ratio:.0%})",
            )
        )
    return v
