"""Conformité d'un effectif aux règles de la saison (fonction pure, sans base)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SquadRules:
    max_squad_players: int
    max_staff: int
    min_age: int
    youth_age_limit: int
    min_youth_players: int


@dataclass(frozen=True)
class Check:
    code: str
    label: str
    ok: bool
    detail: str


def check_squad(player_ages: list[int], staff_count: int, rules: SquadRules) -> list[Check]:
    n = len(player_ages)
    youth = sum(a < rules.youth_age_limit for a in player_ages)
    too_young = sum(a < rules.min_age for a in player_ages)
    return [
        Check(
            "max_players",
            f"Au plus {rules.max_squad_players} joueurs",
            n <= rules.max_squad_players,
            f"{n} joueur(s) inscrit(s)",
        ),
        Check(
            "max_staff",
            f"Au plus {rules.max_staff} encadreurs",
            staff_count <= rules.max_staff,
            f"{staff_count} encadreur(s) inscrit(s)",
        ),
        Check(
            "min_age",
            f"Âge minimum {rules.min_age} ans",
            too_young == 0,
            f"{too_young} joueur(s) sous l'âge minimum",
        ),
        Check(
            "youth_quota",
            f"Au moins {rules.min_youth_players} joueurs de moins de {rules.youth_age_limit} ans",
            youth >= rules.min_youth_players,
            f"{youth} joueur(s) de moins de {rules.youth_age_limit} ans",
        ),
    ]
