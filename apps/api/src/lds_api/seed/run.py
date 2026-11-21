"""Chargement des données de départ.

- Données de référence (toujours) : rôles, saison 2027, règles par défaut, 17 régions,
  2 poules, 20 équipes, stades génériques.
- Données de démonstration (hors production uniquement) : un compte par rôle et des
  effectifs fictifs (30 joueurs + 7 encadreurs par équipe).
"""

import random
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from lds_api.core.config import get_settings
from lds_api.core.crypto import cnib_index, phone_index
from lds_api.core.security import hash_password
from lds_api.core.text import slugify
from lds_api.db.base import Base
from lds_api.models import (
    CompetitionRules,
    Person,
    Player,
    Pool,
    Region,
    Role,
    Season,
    SquadMembership,
    Staff,
    Team,
    TeamEntry,
    User,
    Venue,
)
from lds_api.models.enums import MembershipKind, SeasonStatus
from lds_api.seed import fake_people, reference

SEASON_YEAR = 2027
SEASON_START = date(2027, 1, 1)
SEASON_END = date(2027, 6, 30)


class SeedError(RuntimeError):
    pass


def reset_database(db: Session) -> None:
    """Vide toutes les tables (développement uniquement)."""
    if get_settings().environment == "production":
        raise SeedError("La remise à zéro est interdite en production.")
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    db.commit()


def seed_reference(db: Session) -> Season:
    for code, label in reference.ROLE_LABELS.items():
        if not db.scalar(select(Role).where(Role.code == code)):
            db.add(Role(code=code, label=label))

    season = db.scalar(select(Season).where(Season.year == SEASON_YEAR))
    if season:
        return season

    season = Season(
        name="Saison 2027 — phase pilote",
        year=SEASON_YEAR,
        starts_on=SEASON_START,
        ends_on=SEASON_END,
        status=SeasonStatus.ACTIVE,
        is_current=True,
    )
    db.add(season)
    db.flush()
    db.add(CompetitionRules(season_id=season.id, age_reference_date=SEASON_START))

    regions = {}
    for name in reference.REGIONS:
        regions[name] = Region(name=name, slug=slugify(name))
        db.add(regions[name])

    pools = {}
    for code, name, city in reference.POOLS:
        pools[code] = Pool(season_id=season.id, code=code, name=name, host_city=city)
        db.add(pools[code])

    for name, city in reference.VENUES:
        db.add(Venue(name=name, city=city, is_confirmed=False))
    db.flush()

    draw_position = {"A": 0, "B": 0}
    for t in reference.TEAMS:
        team = Team(
            region_id=regions[t.region].id,
            name=t.name,
            short_name=t.short_name,
            acronym=t.acronym,
            slug=slugify(t.name),
            primary_color=t.primary_color,
            secondary_color=t.secondary_color,
            city=pools[t.pool].host_city,
        )
        db.add(team)
        db.flush()
        draw_position[t.pool] += 1
        db.add(
            TeamEntry(
                season_id=season.id,
                team_id=team.id,
                pool_id=pools[t.pool].id,
                draw_position=draw_position[t.pool],
            )
        )
    db.flush()
    return season


def seed_demo(db: Session, season: Season, *, rng_seed: int = 2027) -> None:
    if get_settings().environment == "production":
        raise SeedError("Les données de démonstration sont interdites en production.")
    if db.scalar(select(User).where(User.email == reference.DEMO_USERS[0][0])):
        return  # déjà chargées

    roles = {r.code: r for r in db.scalars(select(Role))}
    teams_by_short = {t.short_name: t for t in db.scalars(select(Team))}
    pw = hash_password(reference.DEMO_PASSWORD)
    for email, full_name, role, team_short in reference.DEMO_USERS:
        db.add(
            User(
                email=email,
                full_name=full_name,
                password_hash=pw,
                roles=[roles[role]],
                team_id=teams_by_short[team_short].id if team_short else None,
            )
        )

    rng = random.Random(rng_seed)
    regions = list(db.scalars(select(Region)))
    ref = SEASON_START
    for team in db.scalars(select(Team).order_by(Team.name)):
        others = [r for r in regions if r.id != team.region_id]
        for fp in fake_people.fake_squad(rng, ref):
            person = _person(fp.person)
            db.add(person)
            db.flush()
            db.add(
                Player(
                    person_id=person.id,
                    position=fp.position,
                    preferred_foot=fp.foot,
                    residence_region_id=(
                        team.region_id if fp.resides_in_team_region else rng.choice(others).id
                    ),
                    residence_since=fp.residence_since,
                    residence_verified=True,
                )
            )
            db.add(_membership(season, team, person, MembershipKind.PLAYER, fp.shirt_number))
        for staff_person, function in fake_people.fake_staff(rng, ref):
            person = _person(staff_person)
            db.add(person)
            db.flush()
            db.add(Staff(person_id=person.id, function=function))
            db.add(_membership(season, team, person, MembershipKind.STAFF, None))
    db.flush()


def _person(fp: fake_people.FakePerson) -> Person:
    return Person(
        first_name=fp.first_name,
        last_name=fp.last_name,
        display_name=fp.display_name,
        birth_date=fp.birth_date,
        cnib_number=fp.cnib,
        cnib_index=cnib_index(fp.cnib),
        phone=fp.phone,
        phone_index=phone_index(fp.phone),
    )


def _membership(season, team, person, kind, shirt) -> SquadMembership:
    return SquadMembership(
        season_id=season.id,
        team_id=team.id,
        person_id=person.id,
        kind=kind,
        shirt_number=shirt,
        joined_on=SEASON_START,
        contract_signed=True,
        cnss_declared=True,
    )


def run(db: Session, *, demo: bool = True, reset: bool = False) -> Season:
    if reset:
        reset_database(db)
    season = seed_reference(db)
    if demo:
        seed_demo(db, season)
    db.commit()
    return season
