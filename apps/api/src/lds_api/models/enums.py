"""Énumérations métier (stockées en VARCHAR pour faciliter les migrations)."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def str_enum(enum_cls: type[StrEnum], length: int = 32) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class RoleCode(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN_COMPETITION = "admin_competition"
    GESTIONNAIRE_CLUB = "gestionnaire_club"
    DELEGUE_MATCH = "delegue_match"
    CELLULE_TECHNIQUE = "cellule_technique"
    CONTROLEUR_ACCES = "controleur_acces"


class SeasonStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class Gender(StrEnum):
    MALE = "M"
    FEMALE = "F"


class Position(StrEnum):
    GOALKEEPER = "GK"
    DEFENDER = "DF"
    MIDFIELDER = "MF"
    FORWARD = "FW"


class Foot(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


class StaffFunction(StrEnum):
    HEAD_COACH = "head_coach"
    ASSISTANT_COACH = "assistant_coach"
    GOALKEEPER_COACH = "goalkeeper_coach"
    FITNESS_COACH = "fitness_coach"
    DOCTOR = "doctor"
    PHYSIO = "physio"
    TEAM_MANAGER = "team_manager"
    KIT_MANAGER = "kit_manager"
    OTHER = "other"


class MembershipKind(StrEnum):
    PLAYER = "player"
    STAFF = "staff"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"


class LicenceStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class MatchPhase(StrEnum):
    GROUP = "group"
    QUARTER_FINAL = "quarter_final"
    SEMI_FINAL = "semi_final"
    THIRD_PLACE = "third_place"
    FINAL = "final"


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class SheetStatus(StrEnum):
    DRAFT = "draft"  # brouillon
    SUBMITTED = "submitted"  # soumise
    VALIDATED = "validated"  # validée par le délégué
    CLOSED = "closed"  # clôturée (verrouillée définitivement)


class LineupRole(StrEnum):
    STARTER = "starter"
    SUBSTITUTE = "substitute"


class EventType(StrEnum):
    GOAL = "goal"
    PENALTY_GOAL = "penalty_goal"
    OWN_GOAL = "own_goal"
    PENALTY_MISSED = "penalty_missed"
    YELLOW_CARD = "yellow_card"
    SECOND_YELLOW = "second_yellow"
    RED_CARD = "red_card"
    SUBSTITUTION = "substitution"


class SuspensionReason(StrEnum):
    YELLOW_ACCUMULATION = "yellow_accumulation"
    RED_CARD = "red_card"
    SECOND_YELLOW = "second_yellow"
    DISCIPLINARY = "disciplinary"


class SuspensionStatus(StrEnum):
    ACTIVE = "active"
    SERVED = "served"
    CANCELLED = "cancelled"


# --- Phase 2 : votes ---------------------------------------------------------
class BallotKind(StrEnum):
    MAN_OF_THE_MATCH = "man_of_the_match"
    GOAL_OF_THE_MONTH = "goal_of_the_month"
    PLAYER_OF_THE_SEASON = "player_of_the_season"
    COACH_OF_THE_SEASON = "coach_of_the_season"
    TEAM_OF_THE_SEASON = "team_of_the_season"
    SPECIAL = "special"


class BallotStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    PUBLISHED = "published"


class ResultsVisibility(StrEnum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"


class VoteStatus(StrEnum):
    VALID = "valid"
    FLAGGED = "flagged"
    REJECTED = "rejected"


# --- Phase 2 : billetterie ----------------------------------------------------
class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderKind(StrEnum):
    TICKETS = "tickets"
    PAID_VOTE = "paid_vote"


class TicketStatus(StrEnum):
    VALID = "valid"
    USED = "used"
    CANCELLED = "cancelled"


class AccreditationCategory(StrEnum):
    PRESS = "press"
    OFFICIAL = "official"
    TEAM = "team"
    SECURITY = "security"
    VOLUNTEER = "volunteer"
    PARTNER = "partner"
