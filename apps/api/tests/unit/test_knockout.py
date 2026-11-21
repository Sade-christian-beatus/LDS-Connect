import pytest

from lds_api.domain.knockout import (
    KnockoutResult,
    final_positions,
    quarter_finals,
    resolve_later_rounds,
    winner_loser,
)

PAIRINGS = [["A1", "B4"], ["B2", "A3"], ["B1", "A4"], ["A2", "B3"]]
RANKINGS = {"A": ["a1", "a2", "a3", "a4", "a5"], "B": ["b1", "b2", "b3", "b4", "b5"]}


def K(h, a, hg, ag, hp=None, ap=None):  # noqa: N802
    return KnockoutResult(h, a, hg, ag, hp, ap)


def test_quarter_finals_from_pairings():
    qf = quarter_finals(PAIRINGS, RANKINGS, 4)
    assert qf == {
        "QF1": ("a1", "b4"),
        "QF2": ("b2", "a3"),
        "QF3": ("b1", "a4"),
        "QF4": ("a2", "b3"),
    }


def test_non_qualified_position_rejected():
    with pytest.raises(ValueError):
        quarter_finals([["A5", "B1"]], RANKINGS, 4)


def test_penalties_decide_draws():
    assert winner_loser(K("x", "y", 1, 1, 4, 5)) == ("y", "x")
    with pytest.raises(ValueError, match="tirs au but"):
        winner_loser(K("x", "y", 0, 0))


def test_full_bracket_and_prize_positions():
    results = {
        "QF1": K("a1", "b4", 2, 0),
        "QF2": K("b2", "a3", 1, 1, 3, 4),
        "QF3": K("b1", "a4", 0, 1),
        "QF4": K("a2", "b3", 3, 2),
    }
    later = resolve_later_rounds(results)
    assert later["SF1"] == ("a1", "a3") and later["SF2"] == ("a4", "a2")
    assert later["F"] == (None, None)

    results |= {"SF1": K("a1", "a3", 0, 2), "SF2": K("a4", "a2", 1, 0)}
    later = resolve_later_rounds(results)
    assert later["F"] == ("a3", "a4") and later["P3"] == ("a1", "a2")

    results |= {"F": K("a3", "a4", 2, 1), "P3": K("a1", "a2", 0, 0, 5, 4)}
    pos = final_positions(results)
    assert pos == {
        "a3": "1",
        "a4": "2",
        "a1": "3",
        "a2": "4",
        "b4": "quarter_finalist",
        "b2": "quarter_finalist",
        "b1": "quarter_finalist",
        "b3": "quarter_finalist",
    }


def test_without_third_place_match():
    later = resolve_later_rounds({}, third_place=False)
    assert "P3" not in later
