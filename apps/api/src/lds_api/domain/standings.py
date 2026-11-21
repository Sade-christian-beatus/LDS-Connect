"""Calcul du classement d'une poule (fonction pure, critères paramétrables).

Critères disponibles (dans l'ordre défini par `CompetitionRules.tiebreakers`) :

- ``points``                        points (barème de la saison)
- ``goal_difference``               différence de buts générale
- ``goals_for``                     buts marqués
- ``goals_against``                 buts encaissés (le moins est le mieux)
- ``wins``                          nombre de victoires
- ``head_to_head_points``           points dans les confrontations directes entre ex aequo
- ``head_to_head_goal_difference``  différence de buts dans ces confrontations
- ``head_to_head_goals_for``        buts marqués dans ces confrontations
- ``fair_play``                     points de fair-play (le moins est le mieux)
- ``drawing_of_lots``               tirage au sort : ordre saisi par la commission, sinon
                                    égalité signalée (``needs_draw``)

Confrontations directes : quand un critère direct sépare une partie seulement des ex aequo,
les critères directs sont ré-appliqués aux seules équipes encore à égalité (méthode UEFA).
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass, field
from itertools import groupby

TeamId = Hashable

HEAD_TO_HEAD = {
    "head_to_head_points",
    "head_to_head_goal_difference",
    "head_to_head_goals_for",
}
KNOWN_CRITERIA = HEAD_TO_HEAD | {
    "points",
    "goal_difference",
    "goals_for",
    "goals_against",
    "wins",
    "fair_play",
    "drawing_of_lots",
}


@dataclass(frozen=True)
class Points:
    win: int = 3
    draw: int = 1
    loss: int = 0


@dataclass(frozen=True)
class Result:
    home: TeamId
    away: TeamId
    home_goals: int
    away_goals: int


@dataclass
class Row:
    team: TeamId
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    fair_play: int = 0
    form: list[str] = field(default_factory=list)  # V / N / D, du plus ancien au plus récent
    rank: int = 0
    needs_draw: bool = False

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


def _table(teams: Iterable[TeamId], results: Iterable[Result], pts: Points) -> dict[TeamId, Row]:
    rows = {t: Row(team=t) for t in teams}
    for r in results:
        if r.home not in rows or r.away not in rows:
            continue
        h, a = rows[r.home], rows[r.away]
        for row, gf, ga in ((h, r.home_goals, r.away_goals), (a, r.away_goals, r.home_goals)):
            row.played += 1
            row.goals_for += gf
            row.goals_against += ga
            if gf > ga:
                row.won += 1
                row.points += pts.win
                row.form.append("V")
            elif gf == ga:
                row.drawn += 1
                row.points += pts.draw
                row.form.append("N")
            else:
                row.lost += 1
                row.points += pts.loss
                row.form.append("D")
    return rows


def compute_standings(
    teams: Sequence[TeamId],
    results: Sequence[Result],
    *,
    points: Points = Points(),  # noqa: B008 — dataclass immuable
    tiebreakers: Sequence[str] = ("points", "goal_difference", "goals_for"),
    fair_play: dict[TeamId, int] | None = None,
    lots: Sequence[TeamId] | None = None,
) -> list[Row]:
    """Classement trié. `results` : matchs terminés uniquement (dans l'ordre chronologique)."""
    unknown = set(tiebreakers) - KNOWN_CRITERIA
    if unknown:
        raise ValueError(f"Critères inconnus : {sorted(unknown)}")
    criteria = list(tiebreakers)
    rows = _table(teams, results, points)
    for t, fp in (fair_play or {}).items():
        if t in rows:
            rows[t].fair_play = fp
    lots_rank = {t: i for i, t in enumerate(lots or [])}
    first_h2h = next((i for i, c in enumerate(criteria) if c in HEAD_TO_HEAD), None)

    def key_fn(criterion: str, group: list[TeamId]) -> Callable[[TeamId], int]:
        if criterion in HEAD_TO_HEAD:
            members = set(group)
            mini = _table(
                group,
                [r for r in results if r.home in members and r.away in members],
                points,
            )
            attr = {
                "head_to_head_points": lambda t: mini[t].points,
                "head_to_head_goal_difference": lambda t: mini[t].goal_difference,
                "head_to_head_goals_for": lambda t: mini[t].goals_for,
            }[criterion]
            return attr
        return {
            "points": lambda t: rows[t].points,
            "goal_difference": lambda t: rows[t].goal_difference,
            "goals_for": lambda t: rows[t].goals_for,
            "goals_against": lambda t: -rows[t].goals_against,
            "wins": lambda t: rows[t].won,
            "fair_play": lambda t: -rows[t].fair_play,
            # Ordre saisi par la commission ; à défaut, toutes les équipes restent à égalité
            "drawing_of_lots": lambda t: -lots_rank.get(t, 0) if lots_rank else 0,
        }[criterion]

    def rank(group: list[TeamId], idx: int) -> list[list[TeamId]]:
        if len(group) <= 1 or idx >= len(criteria):
            return [group]
        criterion = criteria[idx]
        key = key_fn(criterion, group)
        ordered = sorted(group, key=key, reverse=True)
        out: list[list[TeamId]] = []
        for _, sub in groupby(ordered, key=key):
            sub = list(sub)
            restart = (
                criterion in HEAD_TO_HEAD and first_h2h is not None and 1 < len(sub) < len(group)
            )
            out.extend(rank(sub, first_h2h if restart else idx + 1))
        return out

    # Ordre initial stable et lisible pour les égalités non départagées
    initial = sorted(rows, key=lambda t: str(t))
    position = 1
    ranked: list[Row] = []
    for block in rank(initial, 0):
        for t in block:
            row = rows[t]
            row.rank = position
            row.needs_draw = len(block) > 1
            ranked.append(row)
        position += len(block)
    return ranked
