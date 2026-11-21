from collections import Counter
from datetime import date

from sqlalchemy import func, select, text

from lds_api.models import (
    CompetitionRules,
    Person,
    Region,
    SquadMembership,
    Team,
    TeamEntry,
    User,
)
from lds_api.models.enums import MembershipKind, RoleCode


def age_on(birth: date, ref: date) -> int:
    return ref.year - birth.year - ((ref.month, ref.day) < (birth.month, birth.day))


def test_reference_data(db, seeded):
    assert db.scalar(select(func.count(Region.id))) == 17
    assert db.scalar(select(func.count(Team.id))) == 20
    entries = db.scalars(select(TeamEntry)).all()
    per_pool = Counter(e.pool.code for e in entries)
    assert per_pool == {"A": 10, "B": 10}
    assert sorted(e.draw_position for e in entries if e.pool.code == "A") == list(range(1, 11))

    kadiogo = db.scalar(select(Region).where(Region.name == "Kadiogo"))
    guiriko = db.scalar(select(Region).where(Region.name == "Guiriko"))
    assert db.scalar(select(func.count(Team.id)).where(Team.region_id == kadiogo.id)) == 3
    assert db.scalar(select(func.count(Team.id)).where(Team.region_id == guiriko.id)) == 2


def test_default_rules(db, seeded):
    rules = db.scalar(select(CompetitionRules).where(CompetitionRules.season_id == seeded.id))
    assert (rules.points_win, rules.points_draw, rules.points_loss) == (3, 1, 0)
    assert rules.max_squad_players == 30 and rules.max_staff == 7
    assert float(rules.min_local_starters_ratio) == 0.5
    assert rules.residence_min_months == 6 and rules.min_age == 16
    assert rules.prize_money["1"] == 24_000_000


def test_demo_squads_respect_rules(db, seeded):
    ref = date(2027, 1, 1)
    for team in db.scalars(select(Team)):
        members = db.scalars(select(SquadMembership).where(SquadMembership.team_id == team.id))
        kinds = Counter(m.kind for m in members)
        assert kinds == {MembershipKind.PLAYER: 30, MembershipKind.STAFF: 7}
        ages = [
            age_on(m.person.birth_date, ref)
            for m in db.scalars(
                select(SquadMembership).where(
                    SquadMembership.team_id == team.id,
                    SquadMembership.kind == MembershipKind.PLAYER,
                )
            )
        ]
        assert min(ages) >= 16
        assert sum(a < 19 for a in ages) >= 7


def test_one_demo_account_per_role(db, seeded):
    roles = Counter(code for u in db.scalars(select(User)) for code in u.role_codes)
    assert set(roles) == set(RoleCode)
    club = db.scalar(select(User).where(User.email == "club.vinnim@lds.local"))
    assert club.team_id is not None


def test_sensitive_fields_encrypted_at_rest(db, seeded):
    person = db.scalars(select(Person)).first()
    raw = db.execute(
        text("SELECT cnib_number, phone FROM persons WHERE id = :id"), {"id": person.id}
    ).one()
    assert person.cnib_number.encode() not in bytes(raw.cnib_number)
    assert person.phone.encode() not in bytes(raw.phone)


def test_seed_is_idempotent(db, seeded):
    from lds_api.seed import run

    run.run(db, demo=True)
    assert db.scalar(select(func.count(Team.id))) == 20
    assert db.scalar(select(func.count(Person.id))) == 740
