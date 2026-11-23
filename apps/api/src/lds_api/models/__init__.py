"""Import de tous les modèles (nécessaire à Alembic et aux relations)."""

from lds_api.models.audit import AuditLog
from lds_api.models.auth import RefreshToken, Role, User, user_roles
from lds_api.models.discipline import Suspension
from lds_api.models.fixtures import Match, Venue
from lds_api.models.matchsheet import LineupEntry, MatchEvent, MatchSheet
from lds_api.models.registry import (
    CompetitionRules,
    Licence,
    Person,
    Player,
    Pool,
    Region,
    Season,
    SquadMembership,
    Staff,
    Team,
    TeamEntry,
)
from lds_api.models.talents import PlayerStat, TalentNote, TalentWatch
from lds_api.models.ticketing import AccessScan, Accreditation, Order, Ticket, TicketType
from lds_api.models.voting import Ballot, BallotOption, OtpChallenge, Vote

__all__ = [
    "AccessScan",
    "Accreditation",
    "AuditLog",
    "Ballot",
    "BallotOption",
    "CompetitionRules",
    "Licence",
    "LineupEntry",
    "Match",
    "MatchEvent",
    "MatchSheet",
    "Order",
    "OtpChallenge",
    "Person",
    "Player",
    "PlayerStat",
    "Pool",
    "RefreshToken",
    "Region",
    "Role",
    "Season",
    "SquadMembership",
    "Staff",
    "Suspension",
    "Team",
    "TeamEntry",
    "TalentNote",
    "TalentWatch",
    "Ticket",
    "TicketType",
    "User",
    "Venue",
    "Vote",
    "user_roles",
]
