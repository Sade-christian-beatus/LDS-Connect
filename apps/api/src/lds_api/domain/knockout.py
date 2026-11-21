"""Tableau des phases finales (fonctions pures).

Quarts de finale définis par les croisements de la saison (ex. ["A1", "B4"]), puis :
SF1 = vainqueur QF1 – vainqueur QF2 ; SF2 = vainqueur QF3 – vainqueur QF4 ;
P3 (3e place) = perdants des demi-finales ; F = vainqueurs des demi-finales.
"""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass

TeamId = Hashable

# Case → (source domicile, source extérieur) ; « W:X » vainqueur de X, « L:X » perdant de X
LATER_ROUNDS: dict[str, tuple[str, str]] = {
    "SF1": ("W:QF1", "W:QF2"),
    "SF2": ("W:QF3", "W:QF4"),
    "P3": ("L:SF1", "L:SF2"),
    "F": ("W:SF1", "W:SF2"),
}
SLOT_PHASE = {
    "QF1": "quarter_final",
    "QF2": "quarter_final",
    "QF3": "quarter_final",
    "QF4": "quarter_final",
    "SF1": "semi_final",
    "SF2": "semi_final",
    "P3": "third_place",
    "F": "final",
}


@dataclass(frozen=True)
class KnockoutResult:
    home: TeamId
    away: TeamId
    home_goals: int
    away_goals: int
    home_penalties: int | None = None
    away_penalties: int | None = None


def winner_loser(r: KnockoutResult) -> tuple[TeamId, TeamId]:
    """Vainqueur et perdant ; en cas d'égalité, les tirs au but sont obligatoires."""
    if r.home_goals != r.away_goals:
        return (r.home, r.away) if r.home_goals > r.away_goals else (r.away, r.home)
    if r.home_penalties is None or r.away_penalties is None:
        raise ValueError("Match nul en phase finale : tirs au but requis")
    if r.home_penalties == r.away_penalties:
        raise ValueError("Les tirs au but doivent désigner un vainqueur")
    return (r.home, r.away) if r.home_penalties > r.away_penalties else (r.away, r.home)


def quarter_finals(
    pairings: Sequence[Sequence[str]],
    final_rankings: Mapping[str, Sequence[TeamId]],
    qualifiers_per_pool: int,
) -> dict[str, tuple[TeamId, TeamId]]:
    """`final_rankings` : {"A": [1er, 2e, …], "B": […]} ; « A1 » = 1er de la poule A."""

    def resolve(code: str) -> TeamId:
        pool, pos = code[0], int(code[1:])
        if pos > qualifiers_per_pool:
            raise ValueError(f"{code} n'est pas qualifiable ({qualifiers_per_pool} par poule)")
        return final_rankings[pool][pos - 1]

    return {f"QF{i + 1}": (resolve(h), resolve(a)) for i, (h, a) in enumerate(pairings)}


def resolve_later_rounds(
    results: Mapping[str, KnockoutResult], *, third_place: bool = True
) -> dict[str, tuple[TeamId | None, TeamId | None]]:
    """Équipes connues des demi-finales, du match pour la 3e place et de la finale."""
    outcome: dict[str, tuple[TeamId, TeamId]] = {}
    for slot, r in results.items():
        try:
            outcome[slot] = winner_loser(r)
        except ValueError:
            continue

    def source(ref: str) -> TeamId | None:
        kind, slot = ref.split(":")
        if slot not in outcome:
            return None
        return outcome[slot][0] if kind == "W" else outcome[slot][1]

    return {
        slot: (source(h), source(a))
        for slot, (h, a) in LATER_ROUNDS.items()
        if third_place or slot != "P3"
    }


def final_positions(
    results: Mapping[str, KnockoutResult], *, third_place: bool = True
) -> dict[TeamId, str]:
    """Positions finales connues → clé de dotation (« 1 », « 2 », « 3 », « 4 »,
    « quarter_finalist »)."""
    positions: dict[TeamId, str] = {}
    for slot in ("QF1", "QF2", "QF3", "QF4"):
        if slot in results:
            _, loser = winner_loser(results[slot])
            positions[loser] = "quarter_finalist"
    if "F" in results:
        w, loser = winner_loser(results["F"])
        positions[w], positions[loser] = "1", "2"
    if third_place and "P3" in results:
        w, loser = winner_loser(results["P3"])
        positions[w], positions[loser] = "3", "4"
    return positions
