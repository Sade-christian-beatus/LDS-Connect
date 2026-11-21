"""Registre : effectifs, joueurs, encadreurs (avec audit et contrôles de règles)."""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from lds_api.core.crypto import cnib_index, phone_index
from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain.eligibility import age_on, is_local
from lds_api.domain.squad_rules import SquadRules, check_squad
from lds_api.models import (
    Person,
    Player,
    Season,
    SquadMembership,
    Staff,
    Team,
    TeamEntry,
)
from lds_api.models.enums import MembershipKind, MembershipStatus
from lds_api.schemas import registry as s
from lds_api.services import audit, seasons


def get_team(db: Session, team_id: uuid.UUID) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise NotFound("Équipe")
    return team


def public_team(db: Session, team: Team, season: Season) -> s.PublicTeam:
    entry = db.scalar(
        select(TeamEntry).where(TeamEntry.team_id == team.id, TeamEntry.season_id == season.id)
    )
    out = s.PublicTeam.model_validate(team)
    out.pool_code = entry.pool.code if entry and entry.pool else None
    return out


def active_members(db: Session, team_id: uuid.UUID, season_id: uuid.UUID, kind=None):
    q = (
        select(SquadMembership)
        .where(
            SquadMembership.team_id == team_id,
            SquadMembership.season_id == season_id,
            SquadMembership.status == MembershipStatus.ACTIVE,
        )
        .options(
            selectinload(SquadMembership.person).selectinload(Person.player),
            selectinload(SquadMembership.person).selectinload(Person.staff),
            selectinload(SquadMembership.licence),
        )
        .order_by(SquadMembership.shirt_number.nulls_last())
    )
    if kind:
        q = q.where(SquadMembership.kind == kind)
    return list(db.scalars(q))


def _squad_rules(rules) -> SquadRules:
    return SquadRules(
        max_squad_players=rules.max_squad_players,
        max_staff=rules.max_staff,
        min_age=rules.min_age,
        youth_age_limit=rules.youth_age_limit,
        min_youth_players=rules.min_youth_players,
    )


def squad(db: Session, team: Team) -> s.Squad:
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    ref = seasons.reference_date(season, rules)
    today = max(date.today(), season.starts_on)
    members = []
    player_ages, staff_count = [], 0
    for m in active_members(db, team.id, season.id):
        p = m.person
        age = age_on(p.birth_date, ref)
        item = s.SquadMember(
            membership_id=m.id,
            person_id=p.id,
            kind=m.kind,
            status=m.status,
            first_name=p.first_name,
            last_name=p.last_name,
            display_name=p.display_name,
            birth_date=p.birth_date,
            age=age,
            shirt_number=m.shirt_number,
            birth_place=p.birth_place,
            nationality=p.nationality,
            guardian_consent_on=p.guardian_consent_on,
            is_minor=age < 18,
            has_cnib=p.cnib_index is not None,
            has_phone=p.phone_index is not None,
            licence=s.LicenceBrief.model_validate(m.licence) if m.licence else None,
        )
        if m.kind == MembershipKind.PLAYER and p.player:
            pl = p.player
            player_ages.append(age)
            item.position = pl.position
            item.residence_region = pl.residence_region.name if pl.residence_region else None
            item.residence_region_id = pl.residence_region_id
            item.residence_since = pl.residence_since
            item.residence_verified = pl.residence_verified
            # Serait local une fois la résidence vérifiée : à traiter par l'administration
            item.residence_pending = not pl.residence_verified and is_local(
                residence_region_id=pl.residence_region_id,
                residence_since=pl.residence_since,
                residence_verified=True,
                team_region_id=team.region_id,
                on=today,
                min_months=rules.residence_min_months,
            )
            item.preferred_foot = pl.preferred_foot
            item.fbf_licence_number = pl.fbf_licence_number
            item.is_local = is_local(
                residence_region_id=pl.residence_region_id,
                residence_since=pl.residence_since,
                residence_verified=pl.residence_verified,
                team_region_id=team.region_id,
                on=today,
                min_months=rules.residence_min_months,
            )
        elif m.kind == MembershipKind.STAFF and p.staff:
            staff_count += 1
            item.function = p.staff.function
            item.qualification = p.staff.qualification
        members.append(item)
    checks = check_squad(player_ages, staff_count, _squad_rules(rules))
    return s.Squad(
        team=public_team(db, team, season),
        members=members,
        compliance=[s.RuleCheck(**c.__dict__) for c in checks],
    )


def _count(db, team_id, season_id, kind) -> int:
    return db.scalar(
        select(func.count(SquadMembership.id)).where(
            SquadMembership.team_id == team_id,
            SquadMembership.season_id == season_id,
            SquadMembership.kind == kind,
            SquadMembership.status == MembershipStatus.ACTIVE,
        )
    )


def _apply_identity(person: Person, data: dict) -> None:
    for field in ("first_name", "last_name", "birth_date", "birth_place", "nationality"):
        if field in data:
            setattr(person, field, data[field])
    if "guardian_consent_on" in data:
        person.guardian_consent_on = data["guardian_consent_on"]
    if "cnib_number" in data:
        person.cnib_number = data["cnib_number"] or None
        person.cnib_index = cnib_index(data["cnib_number"]) if data["cnib_number"] else None
    if "phone" in data:
        person.phone = data["phone"] or None
        person.phone_index = phone_index(data["phone"]) if data["phone"] else None
    if data.get("display_name"):
        person.display_name = data["display_name"]
    elif not person.display_name:
        person.display_name = f"{person.first_name[0]}. {person.last_name}"


def _check_cnib_unique(db: Session, cnib: str | None, exclude: uuid.UUID | None = None) -> None:
    if not cnib:
        return
    q = select(Person.id).where(Person.cnib_index == cnib_index(cnib))
    if exclude:
        q = q.where(Person.id != exclude)
    if db.scalar(q):
        raise BusinessError("Ce numéro CNIB est déjà enregistré", code="duplicate_cnib")


def _check_shirt(db, team_id, season_id, shirt, exclude_membership=None) -> None:
    if shirt is None:
        return
    q = select(SquadMembership.id).where(
        SquadMembership.team_id == team_id,
        SquadMembership.season_id == season_id,
        SquadMembership.shirt_number == shirt,
    )
    if exclude_membership:
        q = q.where(SquadMembership.id != exclude_membership)
    if db.scalar(q):
        raise BusinessError(f"Le numéro {shirt} est déjà attribué", code="duplicate_shirt")


def create_player(db: Session, actor, team: Team, body: s.PlayerCreate) -> SquadMembership:
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    if _count(db, team.id, season.id, MembershipKind.PLAYER) >= rules.max_squad_players:
        raise BusinessError(
            f"Effectif complet ({rules.max_squad_players} joueurs maximum)", code="squad_full"
        )
    age = age_on(body.birth_date, seasons.reference_date(season, rules))
    if age < rules.min_age:
        raise BusinessError(
            f"Âge minimum non atteint : {age} ans (minimum {rules.min_age})", code="min_age"
        )
    _check_cnib_unique(db, body.cnib_number)
    _check_shirt(db, team.id, season.id, body.shirt_number)

    data = body.model_dump()
    person = Person(display_name="")
    _apply_identity(person, data)
    db.add(person)
    db.flush()
    db.add(
        Player(
            person_id=person.id,
            position=body.position,
            preferred_foot=body.preferred_foot,
            residence_region_id=body.residence_region_id,
            residence_since=body.residence_since,
            fbf_licence_number=body.fbf_licence_number,
        )
    )
    m = SquadMembership(
        season_id=season.id,
        team_id=team.id,
        person_id=person.id,
        kind=MembershipKind.PLAYER,
        shirt_number=body.shirt_number,
        joined_on=max(date.today(), season.starts_on),
    )
    db.add(m)
    db.flush()
    audit.record(db, actor, "create", "player", person.id, audit.snapshot(person))
    return m


def create_staff(db: Session, actor, team: Team, body: s.StaffCreate) -> SquadMembership:
    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    if _count(db, team.id, season.id, MembershipKind.STAFF) >= rules.max_staff:
        raise BusinessError(
            f"Encadrement complet ({rules.max_staff} encadreurs maximum)", code="staff_full"
        )
    _check_cnib_unique(db, body.cnib_number)
    person = Person(display_name="")
    _apply_identity(person, body.model_dump())
    db.add(person)
    db.flush()
    db.add(Staff(person_id=person.id, function=body.function, qualification=body.qualification))
    m = SquadMembership(
        season_id=season.id,
        team_id=team.id,
        person_id=person.id,
        kind=MembershipKind.STAFF,
        joined_on=max(date.today(), season.starts_on),
    )
    db.add(m)
    db.flush()
    audit.record(db, actor, "create", "staff", person.id, audit.snapshot(person))
    return m


def membership_for(db: Session, person_id: uuid.UUID) -> SquadMembership:
    season = seasons.current_season(db)
    m = db.scalar(
        select(SquadMembership).where(
            SquadMembership.person_id == person_id, SquadMembership.season_id == season.id
        )
    )
    if m is None:
        raise NotFound("Membre d'effectif")
    return m


def update_player(db: Session, actor, m: SquadMembership, body: s.PlayerUpdate) -> None:
    from fastapi import HTTPException, status

    from lds_api.core.rbac import Perm

    data = body.model_dump(exclude_unset=True)
    person, player = m.person, m.person.player
    if player is None:
        raise NotFound("Joueur")
    can_verify = actor.can(Perm.RESIDENCE_VERIFY)
    if "residence_verified" in data and not can_verify:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La vérification de résidence relève de l'administration"
        )
    residence_changed = any(
        k in data and data[k] != getattr(player, k)
        for k in ("residence_region_id", "residence_since")
    )
    if residence_changed and not can_verify:
        # Nouvelle déclaration du club : le statut « local » attend une nouvelle vérification
        data["residence_verified"] = False
    if "cnib_number" in data:
        _check_cnib_unique(db, data["cnib_number"], exclude=person.id)
    if "shirt_number" in data:
        _check_shirt(db, m.team_id, m.season_id, data["shirt_number"], m.id)
        m.shirt_number = data["shirt_number"]
    _apply_identity(person, data)
    for field in (
        "position",
        "preferred_foot",
        "residence_region_id",
        "residence_since",
        "residence_verified",
        "fbf_licence_number",
    ):
        if field in data:
            setattr(player, field, data[field])
    changes = {**audit.diff(person), **audit.diff(player), **audit.diff(m)}
    if changes:
        audit.record(db, actor, "update", "player", person.id, changes)


def update_staff(db: Session, actor, m: SquadMembership, body: s.StaffUpdate) -> None:
    data = body.model_dump(exclude_unset=True)
    person, staff = m.person, m.person.staff
    if staff is None:
        raise NotFound("Encadreur")
    if "cnib_number" in data:
        _check_cnib_unique(db, data["cnib_number"], exclude=person.id)
    _apply_identity(person, data)
    for field in ("function", "qualification"):
        if field in data:
            setattr(staff, field, data[field])
    changes = {**audit.diff(person), **audit.diff(staff)}
    if changes:
        audit.record(db, actor, "update", "staff", person.id, changes)


def release(db: Session, actor, m: SquadMembership) -> None:
    from lds_api.models.enums import LicenceStatus

    if m.status == MembershipStatus.RELEASED:
        return
    m.status = MembershipStatus.RELEASED
    m.left_on = date.today()
    m.shirt_number = None
    if m.licence and m.licence.status == LicenceStatus.ACTIVE:
        m.licence.status = LicenceStatus.REVOKED
        m.licence.status_reason = "Départ de l'effectif"
    audit.record(db, actor, "release", "membership", m.id, {"person_id": m.person_id})


def read_sensitive(db: Session, actor, person: Person) -> s.SensitiveData:
    """Lecture de la CNIB et du téléphone : toujours journalisée."""
    audit.record(db, actor, "read_sensitive", "person", person.id, {"fields": ["cnib", "phone"]})
    return s.SensitiveData(person_id=person.id, cnib_number=person.cnib_number, phone=person.phone)


def overview(db: Session, team: Team) -> s.TeamOverview:
    """Synthèse : effectifs, quotas, licences et anomalies d'une équipe."""
    from lds_api.models.enums import LicenceStatus

    season = seasons.current_season(db)
    rules = seasons.rules_for(db, season)
    sq = squad(db, team)
    players = [m for m in sq.members if m.kind == MembershipKind.PLAYER]
    staff = [m for m in sq.members if m.kind == MembershipKind.STAFF]
    active = sum(1 for m in sq.members if m.licence and m.licence.status == LicenceStatus.ACTIVE)
    missing = sum(1 for m in sq.members if m.licence is None)
    blocked = sum(1 for m in sq.members if m.licence and m.licence.status != LicenceStatus.ACTIVE)
    issues = [f"{c.label} ({c.detail})" for c in sq.compliance if not c.ok]
    if missing:
        issues.append(f"{missing} licence(s) à délivrer")
    if blocked:
        issues.append(f"{blocked} licence(s) suspendue(s) ou révoquée(s)")
    return s.TeamOverview(
        team=sq.team,
        players=len(players),
        staff=len(staff),
        youth_players=sum(1 for m in players if m.age < rules.youth_age_limit),
        local_players=sum(1 for m in players if m.is_local),
        licences_active=active,
        licences_missing=missing,
        licences_blocked=blocked,
        compliant=not issues,
        issues=issues,
    )
