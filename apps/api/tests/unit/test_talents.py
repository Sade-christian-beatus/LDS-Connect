"""Statistiques individuelles d'un match (fonctions pures)."""

import uuid

from lds_api.domain.talents import Event, LineupLine, match_lines, per_90, totals

H, A = uuid.uuid4(), uuid.uuid4()
GK, ST, SUB, BENCH, DEF = (uuid.uuid4() for _ in range(5))
AWAY_GK = uuid.uuid4()

LINEUP = [
    LineupLine(GK, H, starter=True, goalkeeper=True),
    LineupLine(ST, H, starter=True),
    LineupLine(DEF, H, starter=True),
    LineupLine(SUB, H, starter=False),
    LineupLine(BENCH, H, starter=False),
    LineupLine(AWAY_GK, A, starter=True, goalkeeper=True),
]


def lines(events, conceded=None, duration=90):
    out = match_lines(LINEUP, events, duration=duration, conceded=conceded or {H: 0, A: 2})
    return {line.person_id: line for line in out}


def test_minutes_substitution_and_bench():
    r = lines([Event("substitution", 60, ST, H, related_person_id=SUB)])
    assert r[ST].minutes == 60 and r[ST].started and r[ST].played
    assert r[SUB].minutes == 30 and not r[SUB].started and r[SUB].played
    assert r[BENCH].minutes == 0 and not r[BENCH].played
    assert r[GK].minutes == 90


def test_goals_assists_cards_and_sending_off():
    r = lines(
        [
            Event("goal", 10, ST, H, related_person_id=DEF),
            Event("penalty_goal", 30, ST, H),
            Event("own_goal", 40, DEF, H),
            Event("yellow_card", 50, DEF, H),
            Event("second_yellow", 70, DEF, H),
        ]
    )
    assert r[ST].goals == 2 and r[ST].penalty_goals == 1
    assert r[DEF].assists == 1 and r[DEF].goals == 0  # un but contre son camp n'est pas un but
    assert r[DEF].yellow_cards == 1 and r[DEF].red_cards == 1 and r[DEF].minutes == 70


def test_clean_sheet_only_for_full_match_goalkeeper():
    assert lines([])[GK].clean_sheet
    assert not lines([])[AWAY_GK].clean_sheet  # équipe qui a encaissé
    assert not lines([], conceded={H: 1, A: 0})[GK].clean_sheet
    assert not lines([Event("substitution", 80, GK, H, related_person_id=BENCH)])[GK].clean_sheet
    assert not lines([])[ST].clean_sheet  # pas gardien


def test_extra_time_extends_the_match():
    r = lines([Event("goal", 112, ST, H)])
    assert r[GK].minutes == 112


def test_duration_comes_from_rules():
    assert lines([], duration=80)[GK].minutes == 80


def test_totals_and_ratio():
    a = lines([Event("goal", 10, ST, H)])[ST]
    b = lines([Event("substitution", 45, ST, H, related_person_id=SUB)])[ST]
    t = totals([a, b])
    assert (t.appearances, t.starts, t.minutes_played, t.goals) == (2, 2, 135, 1)
    assert per_90(t.goals, t.minutes_played) == 0.67
    assert per_90(1, 60) is None
