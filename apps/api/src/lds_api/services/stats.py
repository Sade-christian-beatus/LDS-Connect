"""Statistiques individuelles publiques (buteurs, passeurs), calculées depuis les feuilles
validées. Seul le nom d'usage est exposé (la compétition compte des mineurs)."""

import uuid

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lds_api.models import Match, MatchEvent, MatchSheet, Person, Team
from lds_api.models.enums import EventType, SheetStatus
from lds_api.schemas.fixtures import TeamRef

OFFICIAL = [SheetStatus.VALIDATED, SheetStatus.CLOSED]


class StatRow(BaseModel):
    rank: int
    person_id: uuid.UUID
    display_name: str
    team: TeamRef
    value: int  # buts ou passes décisives
    penalties: int = 0


class SeasonStats(BaseModel):
    scorers: list[StatRow]
    assists: list[StatRow]


def _ranked(rows, limit: int) -> list[StatRow]:
    """Classement avec ex aequo (même valeur → même rang)."""
    out: list[StatRow] = []
    previous, rank = None, 0
    for i, r in enumerate(rows, start=1):
        if r.value != previous:
            rank, previous = i, r.value
        r.rank = rank
        out.append(r)
        if len(out) >= limit:
            break
    return out


def season_stats(db: Session, season_id: uuid.UUID, *, limit: int = 20) -> SeasonStats:
    official = (
        select(MatchEvent)
        .join(MatchSheet, MatchSheet.id == MatchEvent.sheet_id)
        .join(Match, Match.id == MatchSheet.match_id)
        .where(Match.season_id == season_id, MatchSheet.status.in_(OFFICIAL))
        .subquery()
    )
    goals = func.count().filter(official.c.type.in_([EventType.GOAL, EventType.PENALTY_GOAL]))
    pens = func.count().filter(official.c.type == EventType.PENALTY_GOAL)
    scorer_rows = db.execute(
        select(official.c.person_id, official.c.team_id, goals.label("v"), pens.label("p"))
        .group_by(official.c.person_id, official.c.team_id)
        .having(goals > 0)
    ).all()
    assist_rows = db.execute(
        select(official.c.related_person_id, official.c.team_id, func.count().label("v"))
        .where(
            official.c.type.in_([EventType.GOAL, EventType.PENALTY_GOAL]),
            official.c.related_person_id.is_not(None),
        )
        .group_by(official.c.related_person_id, official.c.team_id)
    ).all()

    ids = {r[0] for r in scorer_rows} | {r[0] for r in assist_rows}
    names = dict(db.execute(select(Person.id, Person.display_name).where(Person.id.in_(ids))).all())
    team_ids = {r[1] for r in scorer_rows} | {r[1] for r in assist_rows}
    teams = {
        t.id: TeamRef.model_validate(t)
        for t in db.scalars(select(Team).where(Team.id.in_(team_ids)))
    }

    def build(rows, with_pens: bool) -> list[StatRow]:
        items = [
            StatRow(
                rank=0,
                person_id=r[0],
                display_name=names[r[0]],
                team=teams[r[1]],
                value=r[2],
                penalties=r[3] if with_pens else 0,
            )
            for r in rows
        ]
        # Plus de buts d'abord ; à égalité, moins de penalties, puis ordre alphabétique
        items.sort(key=lambda s: (-s.value, s.penalties, s.display_name))
        return _ranked(items, limit)

    return SeasonStats(scorers=build(scorer_rows, True), assists=build(assist_rows, False))
