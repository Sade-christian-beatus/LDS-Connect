import pytest

from lds_api.domain.standings import Points, Result, compute_standings

FULL = [
    "points",
    "head_to_head_points",
    "head_to_head_goal_difference",
    "head_to_head_goals_for",
    "goal_difference",
    "goals_for",
    "fair_play",
    "drawing_of_lots",
]


def R(h, a, hg, ag):  # noqa: N802
    return Result(h, a, hg, ag)


def order(rows):
    return [r.team for r in rows]


def test_basic_table_counts():
    rows = compute_standings(["A", "B", "C"], [R("A", "B", 2, 0), R("B", "C", 1, 1)])
    a, b, c = (next(r for r in rows if r.team == t) for t in "ABC")
    assert (a.played, a.won, a.points, a.goal_difference) == (1, 1, 3, 2)
    assert (b.played, b.drawn, b.lost, b.points, b.goals_for, b.goals_against) == (
        2,
        1,
        1,
        1,
        1,
        3,
    )
    assert c.points == 1 and c.form == ["N"]
    assert order(rows) == ["A", "C", "B"]  # C devant B à la différence de buts
    assert [r.rank for r in rows] == [1, 2, 3]


def test_custom_points_scale():
    rows = compute_standings(["A", "B"], [R("A", "B", 0, 0)], points=Points(win=2, draw=1, loss=0))
    assert [r.points for r in rows] == [1, 1]


def test_team_without_matches_is_listed():
    rows = compute_standings(["A", "B", "C"], [R("A", "B", 1, 0)])
    assert {r.team: r.played for r in rows}["C"] == 0


def test_head_to_head_beats_goal_difference():
    # A et B à égalité de points ; B a battu A mais A a une meilleure différence générale
    results = [R("B", "A", 1, 0), R("A", "C", 5, 0), R("B", "C", 0, 1), R("C", "D", 0, 0)]
    results += [R("A", "D", 1, 0), R("B", "D", 1, 0)]
    rows = compute_standings(["A", "B", "C", "D"], results, tiebreakers=FULL)
    assert rows[0].points == rows[1].points == 6
    assert order(rows)[:2] == ["B", "A"]
    general = compute_standings(
        ["A", "B", "C", "D"], results, tiebreakers=["points", "goal_difference"]
    )
    assert order(general)[:2] == ["A", "B"]


def test_three_way_tie_reapplies_head_to_head_to_subgroup():
    # Mini-ligue à trois : 3 pts et différence 0 chacun ; A s'en détache aux buts marqués (3).
    # B et C restent à égalité (2 buts chacun) ; ré-appliqué aux seules B et C, le critère
    # des points directs place B (vainqueur de C) devant.
    results = [R("A", "B", 2, 1), R("B", "C", 1, 0), R("C", "A", 2, 1)]
    rows = compute_standings(["A", "B", "C"], results, tiebreakers=FULL)
    assert order(rows) == ["A", "B", "C"]
    assert not any(r.needs_draw for r in rows)


def test_fair_play_and_unresolved_tie_flagged():
    results = [R("A", "B", 1, 1)]
    rows = compute_standings(["A", "B"], results, tiebreakers=FULL, fair_play={"A": 5, "B": 2})
    assert order(rows) == ["B", "A"] and not rows[0].needs_draw

    rows = compute_standings(["A", "B"], results, tiebreakers=FULL)
    assert all(r.needs_draw for r in rows)
    assert [r.rank for r in rows] == [1, 1]


def test_drawing_of_lots_order_applied():
    rows = compute_standings(["A", "B"], [R("A", "B", 0, 0)], tiebreakers=FULL, lots=["B", "A"])
    assert order(rows) == ["B", "A"] and not rows[0].needs_draw


def test_unknown_criterion_rejected():
    with pytest.raises(ValueError, match="inconnus"):
        compute_standings(["A"], [], tiebreakers=["points", "age_moyen"])


def test_full_pool_of_ten_points_conservation():
    teams = [f"T{i}" for i in range(10)]
    from lds_api.domain.round_robin import berger_rounds

    results = []
    for k, rnd in enumerate(berger_rounds(teams)):
        for j, (h, a) in enumerate(rnd):
            results.append(R(h, a, (k + j) % 3, (k * j) % 2))
    rows = compute_standings(teams, results, tiebreakers=FULL)
    assert all(r.played == 9 for r in rows)
    draws = sum(r.home_goals == r.away_goals for r in results)
    assert sum(r.points for r in rows) == 3 * (45 - draws) + 2 * draws
    assert sum(r.goal_difference for r in rows) == 0
