"""Statistiques publiques : seules les feuilles validées comptent ; nom d'usage seulement."""

import uuid

from sqlalchemy import select

from lds_api.models import Match, MatchEvent, MatchSheet, Pool
from lds_api.models.enums import EventType, SheetStatus


def _sheet(db, status, events):
    pool = db.scalar(select(Pool).where(Pool.code == "A"))
    m = db.scalar(
        select(Match).where(Match.pool_id == pool.id).order_by(Match.id).offset(len(events))
    )
    sheet = MatchSheet(match_id=m.id, status=status, version=1)
    db.add(sheet)
    db.flush()
    for etype, person, related, team in events:
        db.add(
            MatchEvent(
                sheet_id=sheet.id,
                team_id=team,
                type=etype,
                minute=10,
                person_id=person,
                related_person_id=related,
                client_uuid=uuid.uuid4(),
            )
        )
    db.flush()
    return m


def _players(db, team_id, n):
    from lds_api.models import SquadMembership
    from lds_api.models.enums import MembershipKind

    return [
        m.person_id
        for m in db.scalars(
            select(SquadMembership)
            .where(
                SquadMembership.team_id == team_id, SquadMembership.kind == MembershipKind.PLAYER
            )
            .limit(n)
        )
    ]


def test_scorers_and_assists(client, db, seeded):
    pool = db.scalar(select(Pool).where(Pool.code == "A"))
    m = db.scalar(select(Match).where(Match.pool_id == pool.id).order_by(Match.round_number))
    a, b, c = _players(db, m.home_team_id, 3)
    validated = [
        (EventType.GOAL, a, b, m.home_team_id),
        (EventType.PENALTY_GOAL, a, None, m.home_team_id),
        (EventType.GOAL, c, b, m.home_team_id),
        (EventType.OWN_GOAL, b, None, m.home_team_id),  # ne compte pas comme but marqué
    ]
    _sheet(db, SheetStatus.VALIDATED, validated)
    _sheet(
        db, SheetStatus.SUBMITTED, [(EventType.GOAL, c, None, m.home_team_id)] * 5
    )  # non officiel

    r = client.get("/api/v1/stats").json()
    scorers = r["scorers"]
    assert [(s["value"], s["penalties"]) for s in scorers] == [(2, 1), (1, 0)]
    assert scorers[0]["person_id"] == str(a) and scorers[0]["rank"] == 1
    assert r["assists"][0]["person_id"] == str(b) and r["assists"][0]["value"] == 2
    assert set(scorers[0]) == {"rank", "person_id", "display_name", "team", "value", "penalties"}
    assert "birth" not in client.get("/api/v1/stats").text
