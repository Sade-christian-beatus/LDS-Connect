import uuid

from lds_api.domain.discipline import Card, DisciplineRules, NewSuspension, suspensions_for_match

RULES = DisciplineRules(
    yellow_cards_threshold=3,
    yellow_accumulation_ban_matches=1,
    red_card_ban_matches=2,
    second_yellow_ban_matches=1,
)
X, Y = uuid.UUID(int=1), uuid.UUID(int=2)


def test_red_card():
    assert suspensions_for_match([Card(X, "red_card")], {}, RULES) == [
        NewSuspension(X, "red_card", 2)
    ]


def test_second_yellow_does_not_feed_accumulation():
    cards = [Card(X, "yellow_card"), Card(X, "second_yellow")]
    assert suspensions_for_match(cards, {X: 2}, RULES) == [NewSuspension(X, "second_yellow", 1)]


def test_accumulation_threshold_crossed():
    assert suspensions_for_match([Card(X, "yellow_card")], {X: 1}, RULES) == []
    assert suspensions_for_match([Card(X, "yellow_card")], {X: 2}, RULES) == [
        NewSuspension(X, "yellow_accumulation", 1)
    ]
    # 5 → 6 : nouveau seuil franchi
    assert suspensions_for_match([Card(X, "yellow_card")], {X: 5}, RULES)[0].matches == 1


def test_several_players():
    cards = [Card(X, "yellow_card"), Card(Y, "red_card")]
    result = suspensions_for_match(cards, {X: 2}, RULES)
    assert {s.person for s in result} == {X, Y}
