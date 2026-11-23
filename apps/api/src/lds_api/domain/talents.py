"""Statistiques individuelles d'un match, calculées depuis la composition et les événements
de la feuille validée (fonctions pures, sans base de données)."""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LineupLine:
    person_id: uuid.UUID
    team_id: uuid.UUID
    starter: bool
    goalkeeper: bool = False


@dataclass(frozen=True)
class Event:
    type: str  # valeur de models.enums.EventType
    minute: int
    person_id: uuid.UUID
    team_id: uuid.UUID
    related_person_id: uuid.UUID | None = None


@dataclass
class MatchLine:
    person_id: uuid.UUID
    team_id: uuid.UUID
    started: bool = False
    played: bool = False
    minutes: int = 0
    goals: int = 0
    penalty_goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    clean_sheet: bool = False


GOALS = {"goal", "penalty_goal"}
SENT_OFF = {"red_card", "second_yellow"}


def match_lines(
    lineup: Iterable[LineupLine],
    events: Iterable[Event],
    *,
    duration: int,
    conceded: dict[uuid.UUID, int],
) -> list[MatchLine]:
    """Une ligne par joueur inscrit sur la feuille.

    - Minutes : de l'entrée (coup d'envoi ou remplacement) à la sortie (remplacement,
      expulsion) ou à la fin du match. La fin est la durée réglementaire, prolongée si des
      événements ont lieu après (prolongations).
    - Clean sheet : gardien titulaire resté sur le terrain tout le match, équipe sans but
      encaissé.
    """
    events = sorted(events, key=lambda e: e.minute)
    end = max([duration, *(e.minute for e in events)])
    lines: dict[uuid.UUID, MatchLine] = {}
    on: dict[uuid.UUID, int] = {}
    off: dict[uuid.UUID, int] = {}
    goalkeepers: set[uuid.UUID] = set()

    for entry in lineup:
        lines[entry.person_id] = MatchLine(entry.person_id, entry.team_id, started=entry.starter)
        if entry.starter:
            on[entry.person_id] = 0
            if entry.goalkeeper:
                goalkeepers.add(entry.person_id)

    for e in events:
        line = lines.get(e.person_id)
        if e.type == "substitution":
            off.setdefault(e.person_id, e.minute)
            if e.related_person_id in lines:
                on.setdefault(e.related_person_id, e.minute)
            continue
        if line is None:
            continue
        if e.type in GOALS:
            line.goals += 1
            line.penalty_goals += e.type == "penalty_goal"
            if e.type == "goal" and e.related_person_id in lines:
                lines[e.related_person_id].assists += 1
        elif e.type == "yellow_card":
            line.yellow_cards += 1
        elif e.type in SENT_OFF:
            line.red_cards += 1
            off.setdefault(e.person_id, e.minute)

    for pid, line in lines.items():
        if pid in on:
            start, stop = on[pid], off.get(pid, end)
            line.played = True
            line.minutes = max(0, min(stop, end) - start)
            line.clean_sheet = (
                pid in goalkeepers and pid not in off and conceded.get(line.team_id, 0) == 0
            )
    return list(lines.values())


@dataclass
class Totals:
    appearances: int = 0
    starts: int = 0
    minutes_played: int = 0
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    clean_sheets: int = 0
    matches: list[MatchLine] = field(default_factory=list)


def totals(lines: Iterable[MatchLine]) -> Totals:
    t = Totals()
    for line in lines:
        t.matches.append(line)
        t.appearances += line.played
        t.starts += line.started
        t.minutes_played += line.minutes
        t.goals += line.goals
        t.assists += line.assists
        t.yellow_cards += line.yellow_cards
        t.red_cards += line.red_cards
        t.clean_sheets += line.clean_sheet
    return t


def per_90(value: int, minutes: int) -> float | None:
    """Ratio sur 90 minutes (None en dessous de 90 minutes jouées : non significatif)."""
    return round(value * 90 / minutes, 2) if minutes >= 90 else None
