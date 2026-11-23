"""Votes du public : scrutins, code SMS, enregistrement, contrôle, résultats, procès-verbal.

Données personnelles : le numéro n'apparaît en clair que dans le défi SMS (chiffré au repos) ;
les votes ne portent que son empreinte (index aveugle). L'adresse IP n'est jamais stockée
en clair (empreinte HMAC).
"""

import csv
import hashlib
import hmac
import io
import secrets
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from lds_api.core import ratelimit
from lds_api.core.config import get_settings
from lds_api.core.crypto import (
    _blind_key,
    blind_index,
    mask_phone,
    normalize_phone,
    phone_index,
)
from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain import voting as rules
from lds_api.models import (
    Ballot,
    BallotOption,
    LineupEntry,
    Match,
    MatchEvent,
    MatchSheet,
    OtpChallenge,
    Person,
    Season,
    SquadMembership,
    Staff,
    Team,
    Vote,
)
from lds_api.models.enums import (
    BallotKind,
    BallotStatus,
    EventType,
    MembershipKind,
    MembershipStatus,
    SheetStatus,
    StaffFunction,
    VoteStatus,
)
from lds_api.providers.sms import get_sms_provider
from lds_api.schemas import voting as vs
from lds_api.schemas.fixtures import TeamRef
from lds_api.services import audit, seasons

OTP_TTL = timedelta(minutes=10)
OTP_MAX_ATTEMPTS = 5
OTP_PER_PHONE = (3, 15 * 60)  # 3 codes par numéro par 15 minutes
OTP_PER_IP = (30, 60 * 60)  # 30 codes par connexion par heure
OFFICIAL = (SheetStatus.VALIDATED, SheetStatus.CLOSED)


def now() -> datetime:
    return datetime.now(UTC)


# --- Lecture -------------------------------------------------------------------------
def get_ballot(db: Session, ballot_id: uuid.UUID, *, public: bool = False) -> Ballot:
    b = db.scalar(
        select(Ballot).where(Ballot.id == ballot_id).options(selectinload(Ballot.options))
    )
    if b is None or (public and b.status == BallotStatus.DRAFT):
        raise NotFound("Scrutin")
    return b


def _state(b: Ballot, at: datetime) -> str:
    return rules.effective_state(b.status.value, b.opens_at, b.closes_at, at)


def _visible(b: Ballot, at: datetime) -> bool:
    return rules.results_visible(
        status=b.status.value,
        visibility=b.results_visibility.value,
        publish_at=b.results_publish_at,
        state=_state(b, at),
        now=at,
    )


def _teams(db: Session, ids) -> dict[uuid.UUID, TeamRef]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {
        t.id: TeamRef.model_validate(t) for t in db.scalars(select(Team).where(Team.id.in_(ids)))
    }


def _options(db: Session, b: Ballot) -> list[vs.OptionOut]:
    teams = _teams(db, (o.team_id for o in b.options))
    return [
        vs.OptionOut(
            id=o.id,
            label=o.label,
            team=teams.get(o.team_id),
            media_url=o.media_url,
            position=o.position,
        )
        for o in sorted(b.options, key=lambda o: (o.position, o.label))
    ]


def results(db: Session, b: Ballot) -> vs.Results:
    """Résultats : seuls les votes valides comptent (les votes suspects attendent l'examen)."""
    counts = dict(
        db.execute(
            select(Vote.option_id, func.count())
            .where(Vote.ballot_id == b.id, Vote.status == VoteStatus.VALID)
            .group_by(Vote.option_id)
        ).all()
    )
    participants = db.scalar(
        select(func.count(func.distinct(Vote.phone_index))).where(
            Vote.ballot_id == b.id, Vote.status == VoteStatus.VALID
        )
    )
    opts = _options(db, b)
    ordered = sorted(opts, key=lambda o: (-counts.get(o.id, 0), o.position, o.label))
    out, previous, rank = [], None, 0
    for i, o in enumerate(ordered, start=1):
        v = counts.get(o.id, 0)
        if v != previous:
            rank, previous = i, v
        out.append(
            vs.OptionResult(
                option_id=o.id,
                label=o.label,
                team=o.team,
                votes=v,
                share=round(v / participants, 4) if participants else 0.0,
                rank=rank,
            )
        )
    return vs.Results(participants=participants, options=out)


def _voters_by_status(db: Session, b: Ballot) -> Counter:
    rows = db.execute(
        select(Vote.status, func.count(func.distinct(Vote.phone_index)))
        .where(Vote.ballot_id == b.id)
        .group_by(Vote.status)
    ).all()
    return Counter(dict(rows))


def view(db: Session, b: Ballot, *, admin: bool = False) -> vs.BallotOut:
    at = now()
    visible = _visible(b, at)
    base = {
        "id": b.id,
        "kind": b.kind,
        "title": b.title,
        "description": b.description,
        "match_id": b.match_id,
        "opens_at": b.opens_at,
        "closes_at": b.closes_at,
        "state": _state(b, at),
        "max_choices": b.max_choices,
        "is_paid": b.is_paid,
        "results_visibility": b.results_visibility,
        "results_publish_at": b.results_publish_at,
        "results_visible": visible,
        "options": _options(db, b),
        "results": results(db, b) if (visible or admin) else None,
    }
    if not admin:
        return vs.BallotOut(**base)
    by = _voters_by_status(db, b)
    return vs.BallotAdminOut(
        **base,
        status=b.status,
        flagged_voters=by[VoteStatus.FLAGGED],
        rejected_voters=by[VoteStatus.REJECTED],
    )


def public_list(db: Session) -> list[vs.BallotOut]:
    season = seasons.current_season(db)
    ballots = db.scalars(
        select(Ballot)
        .where(Ballot.season_id == season.id, Ballot.status != BallotStatus.DRAFT)
        .options(selectinload(Ballot.options))
        .order_by(Ballot.closes_at.desc())
    )
    return [view(db, b) for b in ballots]


# --- Administration des scrutins ---------------------------------------------------------
def _check_dates(opens_at: datetime, closes_at: datetime, publish_at: datetime | None, visibility):
    if closes_at <= opens_at:
        raise BusinessError("La clôture doit suivre l'ouverture")
    if visibility == "scheduled" and publish_at is None:
        raise BusinessError("Indiquez la date de publication des résultats")


def _check_paid(is_paid: bool) -> None:
    if is_paid:
        raise BusinessError(
            "Le vote payant sera disponible avec la billetterie (paiement mobile money)",
            code="paid_vote_unavailable",
        )


def _set_options(db: Session, b: Ballot, options: list[vs.OptionIn]) -> None:
    for o in list(b.options):
        db.delete(o)
    db.flush()
    b.options = [BallotOption(position=i, **o.model_dump()) for i, o in enumerate(options)]


def create_ballot(db: Session, actor, body: vs.BallotIn) -> Ballot:
    _check_dates(body.opens_at, body.closes_at, body.results_publish_at, body.results_visibility)
    _check_paid(body.is_paid)
    season = seasons.current_season(db)
    data = body.model_dump(exclude={"options"})
    b = Ballot(season_id=season.id, status=BallotStatus.DRAFT, **data)
    db.add(b)
    db.flush()
    _set_options(db, b, body.options)
    db.flush()
    audit.record(db, actor, "create", "ballot", b.id, {"title": b.title, "kind": b.kind})
    return b


def update_ballot(db: Session, actor, b: Ballot, body: vs.BallotUpdate) -> Ballot:
    data = body.model_dump(exclude_unset=True)
    structural = {"opens_at", "max_choices", "options", "is_paid"} & set(data)
    if b.status != BallotStatus.DRAFT and structural:
        raise BusinessError(
            "Scrutin ouvert : propositions, ouverture et nombre de choix sont figés"
        )
    if "is_paid" in data:
        _check_paid(data["is_paid"])
    options = data.pop("options", None)
    for k, v in data.items():
        setattr(b, k, v)
    _check_dates(b.opens_at, b.closes_at, b.results_publish_at, b.results_visibility.value)
    changes = audit.diff(b)
    if options is not None:
        _set_options(db, b, [vs.OptionIn(**o) for o in options])
        changes["options"] = [None, len(options)]
    if changes:
        audit.record(db, actor, "update", "ballot", b.id, changes)
    return b


def open_ballot(db: Session, actor, b: Ballot) -> None:
    if b.status != BallotStatus.DRAFT:
        raise BusinessError("Seul un brouillon peut être ouvert")
    if len(b.options) < 2:
        raise BusinessError("Il faut au moins deux propositions")
    if b.max_choices > len(b.options):
        raise BusinessError("Plus de choix demandés que de propositions")
    if b.closes_at <= now():
        raise BusinessError("La date de clôture est déjà passée")
    b.status = BallotStatus.OPEN
    audit.record(db, actor, "open", "ballot", b.id)


def close_ballot(db: Session, actor, b: Ballot) -> None:
    if b.status != BallotStatus.OPEN:
        raise BusinessError("Le scrutin n'est pas ouvert")
    b.status = BallotStatus.CLOSED
    audit.record(db, actor, "close", "ballot", b.id)


def publish_results(db: Session, actor, b: Ballot) -> None:
    if _state(b, now()) != rules.CLOSED:
        raise BusinessError("Les résultats se publient une fois le scrutin clos")
    b.status = BallotStatus.PUBLISHED
    audit.record(db, actor, "publish_results", "ballot", b.id)
    if b.kind == BallotKind.MAN_OF_THE_MATCH:
        from lds_api.services import talents  # import local : talents dépend de voting

        db.flush()
        talents.refresh(
            db, db.get(Season, b.season_id), {o.person_id for o in b.options if o.person_id}
        )


# --- Propositions suggérées ------------------------------------------------------------------
def candidates(db: Session, kind: str, *, match_id=None, team_id=None) -> list[vs.Candidate]:
    season = seasons.current_season(db)
    teams = {t.id: t for t in db.scalars(select(Team))}

    def person_candidate(p: Person, team_id) -> vs.Candidate:
        t = teams.get(team_id)
        return vs.Candidate(
            label=p.display_name, sublabel=t.name if t else None, person_id=p.id, team_id=team_id
        )

    if kind == "match":
        if match_id is None:
            raise BusinessError("Indiquez le match")
        rows = db.execute(
            select(Person, LineupEntry.team_id)
            .join(LineupEntry, LineupEntry.person_id == Person.id)
            .join(MatchSheet, MatchSheet.id == LineupEntry.sheet_id)
            .where(MatchSheet.match_id == match_id)
            .order_by(LineupEntry.team_id, LineupEntry.shirt_number)
        ).all()
        if not rows:
            raise BusinessError("Aucune composition enregistrée pour ce match")
        return [person_candidate(p, t) for p, t in rows]

    if kind in ("players", "coaches"):
        q = (
            select(Person, SquadMembership.team_id)
            .join(SquadMembership, SquadMembership.person_id == Person.id)
            .where(
                SquadMembership.season_id == season.id,
                SquadMembership.status == MembershipStatus.ACTIVE,
            )
            .order_by(SquadMembership.team_id, Person.last_name)
        )
        if kind == "players":
            q = q.where(SquadMembership.kind == MembershipKind.PLAYER)
        else:
            q = q.join(Staff, Staff.person_id == Person.id).where(
                Staff.function == StaffFunction.HEAD_COACH
            )
        if team_id:
            q = q.where(SquadMembership.team_id == team_id)
        return [person_candidate(p, t) for p, t in db.execute(q).all()]

    if kind == "goals":
        rows = db.execute(
            select(MatchEvent, Person, Match)
            .join(Person, Person.id == MatchEvent.person_id)
            .join(MatchSheet, MatchSheet.id == MatchEvent.sheet_id)
            .join(Match, Match.id == MatchSheet.match_id)
            .where(
                Match.season_id == season.id,
                MatchSheet.status.in_(OFFICIAL),
                MatchEvent.type.in_([EventType.GOAL, EventType.PENALTY_GOAL]),
            )
            .order_by(Match.kickoff_at, MatchEvent.minute)
        ).all()
        out = []
        for e, p, m in rows:
            opponent = teams.get(m.away_team_id if e.team_id == m.home_team_id else m.home_team_id)
            team = teams.get(e.team_id)
            out.append(
                vs.Candidate(
                    label=f"{p.display_name} ({team.short_name if team else ''}) "
                    f"{e.minute}e min contre {opponent.short_name if opponent else '?'}",
                    sublabel=m.kickoff_at.date().isoformat() if m.kickoff_at else None,
                    person_id=p.id,
                    team_id=e.team_id,
                    match_event_id=e.id,
                )
            )
        return out

    if kind == "teams":
        return [
            vs.Candidate(label=t.name, sublabel=None, team_id=t.id)
            for t in sorted(teams.values(), key=lambda t: t.name)
        ]
    raise BusinessError("Type de propositions inconnu")


# --- Vote du public : code SMS puis confirmation -------------------------------------------------
def _ip_hash(ip: str | None) -> str | None:
    return blind_index(ip, purpose="ip") if ip else None


def _code_hash(challenge_id: uuid.UUID, code: str) -> str:
    return hmac.new(_blind_key(), f"otp:{challenge_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _already_voted(db: Session, b: Ballot, pidx: str) -> bool:
    return (
        db.scalar(select(Vote.id).where(Vote.ballot_id == b.id, Vote.phone_index == pidx).limit(1))
        is not None
    )


def request_code(db: Session, b: Ballot, body: vs.CodeRequest, ip: str | None) -> vs.CodeSent:
    at = now()
    if _state(b, at) != rules.OPEN:
        raise BusinessError("Ce scrutin n'est pas ouvert", code="ballot_not_open")
    if b.is_paid:
        raise BusinessError("Vote payant indisponible", code="paid_vote_unavailable")
    try:
        choices = rules.validate_choices(body.choices, {o.id for o in b.options}, b.max_choices)
    except rules.ChoiceError as exc:
        raise BusinessError(str(exc), code="invalid_choices") from exc

    phone = normalize_phone(body.phone)
    allowed = [c.strip() for c in get_settings().vote_allowed_country_codes.split(",") if c.strip()]
    if not rules.phone_allowed(phone, allowed):
        raise BusinessError(
            "Numéro non accepté (numéros du Burkina Faso uniquement)", code="phone_not_allowed"
        )
    pidx = phone_index(phone)
    if _already_voted(db, b, pidx):
        raise BusinessError("Ce numéro a déjà voté pour ce scrutin", code="already_voted")
    ratelimit.hit(f"otp:phone:{pidx}", limit=OTP_PER_PHONE[0], window_seconds=OTP_PER_PHONE[1])
    if ip:
        ratelimit.hit(f"otp:ip:{_ip_hash(ip)}", limit=OTP_PER_IP[0], window_seconds=OTP_PER_IP[1])

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OtpChallenge(
        id=uuid.uuid4(),
        phone_index=pidx,
        phone=phone,
        purpose="vote",
        ballot_id=b.id,
        choices=[str(c) for c in choices],
        created_at=at,
        expires_at=at + OTP_TTL,
        attempts=0,
        ip_hash=_ip_hash(ip),
    )
    challenge.code_hash = _code_hash(challenge.id, code)
    db.add(challenge)
    db.flush()
    try:
        get_sms_provider().send(phone, f"LDS : votre code de vote est {code} (valable 10 min).")
    except Exception as exc:  # noqa: BLE001 — tout échec d'envoi doit être signalé proprement
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Envoi du SMS impossible, réessayez plus tard"
        ) from exc
    return vs.CodeSent(
        challenge_id=challenge.id, expires_at=challenge.expires_at, phone_hint=mask_phone(phone)
    )


def _recent_for_fraud(db: Session, b: Ballot, at: datetime) -> list[rules.RecentVote]:
    since = at - rules.FraudRules().window
    rows = db.scalars(
        select(OtpChallenge)
        .join(Vote, Vote.otp_challenge_id == OtpChallenge.id)
        .where(Vote.ballot_id == b.id, Vote.rank == 1, Vote.cast_at >= since)
    )
    return [rules.RecentVote(c.phone, c.ip_hash, c.consumed_at or at) for c in rows]


def cast_vote(
    db: Session, b: Ballot, body: vs.VoteIn, ip: str | None, user_agent: str | None
) -> None:
    at = now()
    c = db.get(OtpChallenge, body.challenge_id)
    invalid = BusinessError(
        "Code incorrect ou expiré : demandez un nouveau code", code="invalid_code"
    )
    if c is None or c.ballot_id != b.id or c.consumed_at is not None or c.expires_at < at:
        raise invalid
    if c.attempts >= OTP_MAX_ATTEMPTS:
        raise invalid
    if _state(b, at) != rules.OPEN:
        raise BusinessError("Ce scrutin n'est plus ouvert", code="ballot_not_open")
    if not hmac.compare_digest(c.code_hash, _code_hash(c.id, body.code.strip())):
        # L'essai est compté même si la suite de la requête échoue
        db.execute(
            update(OtpChallenge).where(OtpChallenge.id == c.id).values(attempts=c.attempts + 1)
        )
        db.commit()
        raise invalid

    reasons = rules.fraud_reasons(
        phone=c.phone, ip_hash=_ip_hash(ip), now=at, recent=_recent_for_fraud(db, b, at)
    )
    vote_status = VoteStatus.FLAGGED if reasons else VoteStatus.VALID
    ua_hash = blind_index(user_agent, purpose="ua") if user_agent else None
    c.consumed_at = at
    for rank, option_id in enumerate(c.choices or [], start=1):
        db.add(
            Vote(
                ballot_id=b.id,
                option_id=uuid.UUID(option_id),
                rank=rank,
                phone_index=c.phone_index,
                otp_challenge_id=c.id,
                cast_at=at,
                ip_hash=_ip_hash(ip),
                user_agent_hash=ua_hash,
                status=vote_status,
                flag_reason="; ".join(reasons) or None,
            )
        )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise BusinessError("Ce numéro a déjà voté pour ce scrutin", code="already_voted") from None


# --- Contrôle et procès-verbal ------------------------------------------------------------------
def voters(db: Session, b: Ballot, status_filter: VoteStatus | None = None) -> list[vs.VoterOut]:
    labels = {o.id: o.label for o in b.options}
    q = (
        select(Vote)
        .where(Vote.ballot_id == b.id)
        .order_by(Vote.cast_at, Vote.phone_index, Vote.rank)
    )
    if status_filter:
        q = q.where(Vote.status == status_filter)
    grouped: dict[str, vs.VoterOut] = {}
    for v in db.scalars(q):
        item = grouped.get(v.phone_index)
        if item is None:
            item = grouped[v.phone_index] = vs.VoterOut(
                voter=v.phone_index[:16],
                cast_at=v.cast_at,
                status=v.status,
                flag_reason=v.flag_reason,
                connection=v.ip_hash[:10] if v.ip_hash else None,
                choices=[],
            )
        item.choices.append(labels.get(v.option_id, "?"))
    return list(grouped.values())


def review(db: Session, actor, b: Ballot, voter: str, decision: VoteStatus) -> int:
    if decision == VoteStatus.FLAGGED:
        raise BusinessError("Décision attendue : valide ou rejeté")
    if len(voter) < 16:
        raise BusinessError("Votant inconnu")
    rows = list(
        db.scalars(select(Vote).where(Vote.ballot_id == b.id, Vote.phone_index.startswith(voter)))
    )
    if not rows:
        raise NotFound("Votant")
    before = rows[0].status
    for v in rows:
        v.status = decision
    audit.record(
        db, actor, "review_vote", "ballot", b.id, {"voter": voter, "status": [before, decision]}
    )
    return len(rows)


def journal_csv(db: Session, b: Ballot) -> str:
    """Journal complet des votes (aucun numéro en clair : empreintes uniquement)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["horodatage_utc", "votant", "rang", "proposition", "statut", "motif", "connexion"])
    labels = {o.id: o.label for o in b.options}
    for v in db.scalars(
        select(Vote)
        .where(Vote.ballot_id == b.id)
        .order_by(Vote.cast_at, Vote.phone_index, Vote.rank)
    ):
        w.writerow(
            [
                v.cast_at.astimezone(UTC).isoformat(timespec="seconds"),
                v.phone_index[:16],
                v.rank,
                labels.get(v.option_id, "?"),
                v.status.value,
                v.flag_reason or "",
                v.ip_hash[:10] if v.ip_hash else "",
            ]
        )
    return buf.getvalue()


def results_csv(db: Session, b: Ballot) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["rang", "proposition", "equipe", "voix", "part_des_votants"])
    for r in results(db, b).options:
        w.writerow([r.rank, r.label, r.team.name if r.team else "", r.votes, f"{r.share:.2%}"])
    return buf.getvalue()


def report(db: Session, actor, b: Ballot) -> vs.ReportOut:
    by = _voters_by_status(db, b)
    journal = journal_csv(db, b)
    audit.record(db, actor, "report", "ballot", b.id)
    return vs.ReportOut(
        ballot=view(db, b, admin=True),
        generated_at=now(),
        generated_by=actor.label,
        valid_voters=by[VoteStatus.VALID],
        flagged_voters=by[VoteStatus.FLAGGED],
        rejected_voters=by[VoteStatus.REJECTED],
        journal_sha256=hashlib.sha256(journal.encode()).hexdigest(),
    )
