from collections import Counter
from itertools import combinations, groupby, pairwise

import pytest

from lds_api.domain.round_robin import berger_rounds

TEAMS = [f"T{i}" for i in range(1, 11)]


def test_ten_teams_gives_nine_rounds_of_five():
    rounds = berger_rounds(TEAMS)
    assert len(rounds) == 9
    assert all(len(r) == 5 for r in rounds)


def test_every_pair_meets_exactly_once():
    rounds = berger_rounds(TEAMS)
    pairs = Counter(frozenset(m) for r in rounds for m in r)
    assert set(pairs) == {frozenset(p) for p in combinations(TEAMS, 2)}
    assert set(pairs.values()) == {1}


def test_each_team_plays_once_per_round():
    for r in berger_rounds(TEAMS):
        played = [t for m in r for t in m]
        assert sorted(played) == sorted(TEAMS)


def test_each_team_plays_nine_matches():
    counts = Counter(t for r in berger_rounds(TEAMS) for m in r for t in m)
    assert set(counts.values()) == {9}


def test_home_away_is_balanced():
    homes = Counter(m[0] for r in berger_rounds(TEAMS) for m in r)
    assert all(4 <= homes[t] <= 5 for t in TEAMS)


def test_home_away_alternates_with_minimal_breaks():
    rounds = berger_rounds(TEAMS)
    breaks = 0
    for t in TEAMS:
        sides = ["H" if m[0] == t else "A" for r in rounds for m in r if t in m]
        assert max(len(list(g)) for _, g in groupby(sides)) <= 2
        breaks += sum(a == b for a, b in pairwise(sides))
    assert breaks == len(TEAMS) - 2  # minimum théorique


def test_seed_is_reproducible_and_changes_order():
    a, b = berger_rounds(TEAMS, seed=42), berger_rounds(TEAMS, seed=42)
    assert a == b
    assert berger_rounds(TEAMS, seed=7) != a


@pytest.mark.parametrize("n", [3, 5, 9])
def test_odd_number_of_teams_has_byes(n):
    teams = TEAMS[:n]
    rounds = berger_rounds(teams)
    assert len(rounds) == n
    assert all(len(r) == (n - 1) // 2 for r in rounds)
    pairs = {frozenset(m) for r in rounds for m in r}
    assert len(pairs) == n * (n - 1) // 2


def test_too_few_or_duplicate_teams():
    with pytest.raises(ValueError):
        berger_rounds(["seule"])
    with pytest.raises(ValueError, match="double"):
        berger_rounds(["A", "B", "A", "C"])
