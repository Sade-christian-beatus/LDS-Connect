"""Suspensions automatiques consécutives aux cartons (fonction pure)."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class DisciplineRules:
    yellow_cards_threshold: int
    yellow_accumulation_ban_matches: int
    red_card_ban_matches: int
    second_yellow_ban_matches: int


@dataclass(frozen=True)
class Card:
    person: uuid.UUID
    type: str  # yellow_card | second_yellow | red_card


@dataclass(frozen=True)
class NewSuspension:
    person: uuid.UUID
    reason: str  # red_card | second_yellow | yellow_accumulation
    matches: int


def suspensions_for_match(
    cards: list[Card], prior_yellows: dict[uuid.UUID, int], rules: DisciplineRules
) -> list[NewSuspension]:
    """Suspensions déclenchées par les cartons d'un match validé.

    `prior_yellows` : avertissements simples déjà comptabilisés (période en cours).
    Un joueur exclu sur second jaune n'ajoute pas ses jaunes du match au cumul.
    """
    out: list[NewSuspension] = []
    by_person: dict[uuid.UUID, list[str]] = {}
    for c in cards:
        by_person.setdefault(c.person, []).append(c.type)

    for person, types in by_person.items():
        if "red_card" in types:
            out.append(NewSuspension(person, "red_card", rules.red_card_ban_matches))
            continue
        if "second_yellow" in types:
            out.append(NewSuspension(person, "second_yellow", rules.second_yellow_ban_matches))
            continue
        new_yellows = types.count("yellow_card")
        if new_yellows and rules.yellow_cards_threshold > 0:
            before = prior_yellows.get(person, 0)
            after = before + new_yellows
            crossed = after // rules.yellow_cards_threshold - before // rules.yellow_cards_threshold
            if crossed > 0:
                out.append(
                    NewSuspension(
                        person,
                        "yellow_accumulation",
                        rules.yellow_accumulation_ban_matches * crossed,
                    )
                )
    return out
