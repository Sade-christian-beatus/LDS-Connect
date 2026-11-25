"""Tableau de bord de l'administration (audit B5) : l'essentiel de la journée en un écran."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from lds_api.core.deps import Actor, DbSession, require
from lds_api.core.rbac import Perm
from lds_api.models import Ballot, Licence, Match, MatchSheet, Order, Ticket, TicketType, Vote
from lds_api.models.enums import (
    BallotStatus,
    LicenceStatus,
    MatchStatus,
    OrderStatus,
    SheetStatus,
    TicketStatus,
    VoteStatus,
)
from lds_api.schemas.fixtures import MatchOut
from lds_api.services import fixtures, seasons

router = APIRouter(prefix="/admin", tags=["tableau de bord"])


class Counts(BaseModel):
    licences_active: int
    licences_blocked: int  # suspendues ou révoquées
    sheets_to_validate: int  # soumises par le délégué, pas encore validées
    matches_played: int
    matches_total: int
    tickets_sold: int
    revenue_fcfa: int
    refunds_due: int
    ballots_open: int
    votes_valid: int
    votes_flagged: int  # mis de côté par la détection d'abus, à examiner


class DashboardOut(BaseModel):
    season: str
    live: list[MatchOut]
    upcoming: list[MatchOut]  # prochains matchs (7 jours)
    counts: Counts


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DbSession, actor: Actor = Depends(require(Perm.AUDIT_READ))):  # noqa: B008
    season = seasons.current_season(db)
    now = datetime.now(UTC)
    in_season = Match.season_id == season.id
    live = db.scalars(fixtures.match_query().where(in_season, Match.status == MatchStatus.LIVE))
    upcoming = db.scalars(
        fixtures.match_query()
        .where(
            in_season,
            Match.status == MatchStatus.SCHEDULED,
            Match.kickoff_at >= now - timedelta(hours=3),
            Match.kickoff_at <= now + timedelta(days=7),
        )
        .order_by(Match.kickoff_at)
        .limit(8)
    )

    def count(*where) -> int:
        return db.scalar(select(func.count()).where(*where)) or 0

    by_status = (
        select(Licence.status, func.count())
        .where(Licence.season_id == season.id)
        .group_by(Licence.status)
    )
    lic = {row[0]: row[1] for row in db.execute(by_status)}
    season_matches = select(Match.id).where(in_season)
    season_types = select(TicketType.id).where(TicketType.match_id.in_(season_matches))
    in_season_orders = Order.ticket_type_id.in_(season_types)
    paid = (Order.status == OrderStatus.PAID, Order.paid_at.is_not(None), in_season_orders)
    revenue = select(func.coalesce(func.sum(Order.amount_fcfa), 0)).where(*paid)
    counts = Counts(
        licences_active=lic.get(LicenceStatus.ACTIVE, 0),
        licences_blocked=lic.get(LicenceStatus.SUSPENDED, 0) + lic.get(LicenceStatus.REVOKED, 0),
        sheets_to_validate=count(
            MatchSheet.status == SheetStatus.SUBMITTED,
            MatchSheet.match_id.in_(season_matches),
        ),
        matches_played=count(in_season, Match.status == MatchStatus.FINISHED),
        matches_total=count(in_season),
        tickets_sold=count(
            Ticket.status != TicketStatus.CANCELLED,
            Ticket.match_id.in_(season_matches),
        ),
        revenue_fcfa=db.scalar(revenue) or 0,
        refunds_due=count(
            Order.status == OrderStatus.CANCELLED, Order.paid_at.is_not(None), in_season_orders
        ),
        ballots_open=count(Ballot.status == BallotStatus.OPEN),
        votes_valid=count(Vote.status == VoteStatus.VALID),
        votes_flagged=count(Vote.status == VoteStatus.FLAGGED),
    )
    return DashboardOut(
        season=season.name,
        live=[fixtures.to_out(m) for m in live],
        upcoming=[fixtures.to_out(m) for m in upcoming],
        counts=counts,
    )
