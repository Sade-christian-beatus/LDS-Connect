"""Cohérence des événements d'un match et calcul du score (fonctions pures).

Convention : ``team`` est l'équipe du joueur concerné. Un but contre son camp (own_goal)
est donc compté pour l'équipe adverse.
"""

import uuid
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass

TeamId = Hashable

GOAL_TYPES = {"goal", "penalty_goal"}
CARD_TYPES = {"yellow_card", "second_yellow", "red_card"}


@dataclass(frozen=True)
class Event:
    type: str
    minute: int
    team: TeamId
    person: uuid.UUID
    related: uuid.UUID | None = None
    added_time: int | None = None

    @property
    def sort_key(self) -> tuple[int, int]:
        return (self.minute, self.added_time or 0)


@dataclass(frozen=True)
class TeamSheet:
    team: TeamId
    starters: frozenset[uuid.UUID]
    substitutes: frozenset[uuid.UUID]


def score(events: Iterable[Event], home: TeamId, away: TeamId) -> tuple[int, int]:
    h = a = 0
    for e in events:
        if e.type in GOAL_TYPES:
            h, a = (h + 1, a) if e.team == home else (h, a + 1)
        elif e.type == "own_goal":
            h, a = (h, a + 1) if e.team == home else (h + 1, a)
    return h, a


def check_events(
    events: Sequence[Event], sheets: Sequence[TeamSheet], *, max_substitutions: int
) -> list[str]:
    """Rejoue les événements dans l'ordre chronologique ; renvoie les incohérences."""
    errors: list[str] = []
    by_team = {s.team: s for s in sheets}
    on_pitch = {s.team: set(s.starters) for s in sheets}
    bench = {s.team: set(s.substitutes) for s in sheets}
    used_subs = dict.fromkeys(by_team, 0)
    yellows: dict[uuid.UUID, int] = {}
    sent_off: set[uuid.UUID] = set()

    for e in sorted(events, key=lambda x: x.sort_key):
        where = f"{e.minute}e min"
        if e.team not in by_team:
            errors.append(f"{where} : équipe inconnue")
            continue
        if e.person in sent_off:
            errors.append(f"{where} : joueur déjà exclu")
            continue

        if e.type == "substitution":
            if e.person not in on_pitch[e.team]:
                errors.append(f"{where} : le joueur sortant n'est pas sur le terrain")
            elif e.related is None or e.related not in bench[e.team]:
                errors.append(f"{where} : le joueur entrant n'est pas un remplaçant disponible")
            elif used_subs[e.team] >= max_substitutions:
                errors.append(f"{where} : plus de {max_substitutions} remplacements")
            else:
                on_pitch[e.team].discard(e.person)
                bench[e.team].discard(e.related)
                on_pitch[e.team].add(e.related)
                used_subs[e.team] += 1
            continue

        on_sheet = e.person in by_team[e.team].starters | by_team[e.team].substitutes
        if e.type in CARD_TYPES:
            # Un carton peut viser un remplaçant sur le banc
            if not on_sheet:
                errors.append(f"{where} : joueur absent de la feuille")
                continue
        elif e.person not in on_pitch[e.team]:
            errors.append(f"{where} : le joueur n'est pas sur le terrain")
            continue

        bad_assist = e.related == e.person or e.related not in on_pitch[e.team]
        if e.type in GOAL_TYPES and e.related is not None and bad_assist:
            errors.append(f"{where} : passeur décisif invalide")

        if e.type == "yellow_card":
            yellows[e.person] = yellows.get(e.person, 0) + 1
            if yellows[e.person] > 1:
                errors.append(f"{where} : deuxième jaune à saisir comme « second_yellow »")
        elif e.type == "second_yellow":
            if yellows.get(e.person, 0) != 1:
                errors.append(f"{where} : second jaune sans premier avertissement")
            sent_off.add(e.person)
            on_pitch[e.team].discard(e.person)
        elif e.type == "red_card":
            sent_off.add(e.person)
            on_pitch[e.team].discard(e.person)
    return errors
