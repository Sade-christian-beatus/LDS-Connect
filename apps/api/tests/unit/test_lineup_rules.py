import uuid
from dataclasses import replace
from decimal import Decimal

import pytest

from lds_api.domain.lineup_rules import (
    SUBSTITUTE,
    Candidate,
    LineupRules,
    check_lineup,
    min_local_starters,
)

RULES = LineupRules(
    starters_count=11, max_substitutes=9, min_local_starters_ratio=Decimal("0.5"), min_age=16
)


def cand(i: int, *, role="starter", local=True, **kw) -> Candidate:
    base = Candidate(
        person_id=uuid.UUID(int=i),
        name=f"Joueur {i}",
        role=role,
        shirt_number=i,
        is_captain=False,
        is_goalkeeper=False,
        is_squad_member=True,
        licence_ok=True,
        is_suspended=False,
        is_local=local,
        age=22,
    )
    return replace(base, **kw)


def lineup(locals_count: int = 11, subs: int = 7) -> list[Candidate]:
    starters = [cand(i, local=i <= locals_count) for i in range(1, 12)]
    starters[0] = replace(starters[0], is_goalkeeper=True, is_captain=True)
    return starters + [cand(i, role=SUBSTITUTE) for i in range(12, 12 + subs)]


def codes(cands):
    return {v.code for v in check_lineup(cands, RULES)}


def test_valid_lineup():
    assert check_lineup(lineup(), RULES) == []


@pytest.mark.parametrize(
    ("ratio", "count", "expected"), [("0.5", 11, 6), ("0.5", 10, 5), ("0.6", 11, 7)]
)
def test_min_local_rounding(ratio, count, expected):
    assert min_local_starters(count, Decimal(ratio)) == expected


def test_local_rule_six_of_eleven_passes_five_fails():
    assert "local_players" not in codes(lineup(locals_count=6))
    violations = check_lineup(lineup(locals_count=5), RULES)
    local = [v for v in violations if v.code == "local_players"]
    assert local and "5 local(aux)" in local[0].message and "6 requis" in local[0].message


def test_local_substitutes_do_not_count():
    cands = lineup(locals_count=5, subs=0) + [cand(30, role=SUBSTITUTE, local=True)]
    assert "local_players" in codes(cands)


def test_starters_and_substitutes_count():
    assert "starters_count" in codes(lineup()[:10] + lineup()[11:])
    assert "substitutes_count" in codes(lineup(subs=10))


def test_individual_eligibility():
    base = lineup()
    base[3] = replace(base[3], licence_ok=False)
    base[4] = replace(base[4], is_suspended=True)
    base[5] = replace(base[5], is_squad_member=False)
    base[6] = replace(base[6], age=15)
    found = codes(base)
    assert {"licence", "suspended", "not_in_squad", "min_age"} <= found


def test_shirts_captain_goalkeeper():
    base = lineup()
    base[2] = replace(base[2], shirt_number=base[1].shirt_number)
    base[0] = replace(base[0], is_goalkeeper=False, is_captain=False)
    found = codes(base)
    assert {"shirt_duplicate", "captain", "goalkeeper"} <= found


def test_captain_must_start():
    base = lineup()
    base[0] = replace(base[0], is_captain=False)
    base[-1] = replace(base[-1], is_captain=True)
    assert "captain" in codes(base)
