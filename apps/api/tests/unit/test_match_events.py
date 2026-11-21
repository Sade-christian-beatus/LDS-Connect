import uuid

from lds_api.domain.match_events import Event, TeamSheet, check_events, score

H, A = "home", "away"
P = [uuid.UUID(int=i) for i in range(40)]
SHEETS = [
    TeamSheet(H, frozenset(P[0:11]), frozenset(P[11:18])),
    TeamSheet(A, frozenset(P[20:31]), frozenset(P[31:38])),
]


def check(events, max_subs=5):
    return check_events(events, SHEETS, max_substitutions=max_subs)


def test_score_counts_own_goals_for_opponent():
    events = [
        Event("goal", 10, H, P[9]),
        Event("penalty_goal", 30, A, P[29]),
        Event("own_goal", 50, A, P[22]),
        Event("penalty_missed", 60, H, P[8]),
    ]
    assert score(events, H, A) == (2, 1)


def test_valid_sequence():
    events = [
        Event("goal", 5, H, P[9], related=P[8]),
        Event("yellow_card", 20, A, P[25]),
        Event("substitution", 60, H, P[9], related=P[11]),
        Event("goal", 70, H, P[11]),
        Event("yellow_card", 80, H, P[14]),  # remplaçant sur le banc : autorisé
    ]
    assert check(events) == []


def test_substitution_rules():
    assert check([Event("substitution", 60, H, P[12], related=P[13])])  # sortant absent
    assert check([Event("substitution", 60, H, P[1], related=P[30])])  # entrant d'une autre équipe
    twice = [
        Event("substitution", 60, H, P[1], related=P[11]),
        Event("substitution", 70, H, P[2], related=P[11]),
    ]
    assert any("entrant" in e for e in check(twice))
    many = [Event("substitution", 50 + i, H, P[i], related=P[11 + i]) for i in range(1, 7)]
    assert any("plus de 5" in e for e in check(many))


def test_player_who_left_cannot_score():
    events = [
        Event("substitution", 60, H, P[9], related=P[11]),
        Event("goal", 70, H, P[9]),
    ]
    assert any("pas sur le terrain" in e for e in check(events))


def test_sent_off_player_no_further_events():
    events = [Event("red_card", 30, H, P[4]), Event("goal", 40, H, P[4])]
    assert any("exclu" in e for e in check(events))


def test_second_yellow_rules():
    ok = [Event("yellow_card", 10, H, P[3]), Event("second_yellow", 50, H, P[3])]
    assert check(ok) == []
    assert check([Event("second_yellow", 50, H, P[3])])
    assert check([Event("yellow_card", 10, H, P[3]), Event("yellow_card", 50, H, P[3])])


def test_events_sorted_by_minute_and_added_time():
    events = [
        Event("goal", 45, H, P[11], added_time=3),
        Event("substitution", 45, H, P[9], related=P[11], added_time=1),
    ]
    assert check(events) == []


def test_invalid_assist():
    assert check([Event("goal", 5, H, P[9], related=P[9])])
    assert check([Event("goal", 5, H, P[9], related=P[25])])
