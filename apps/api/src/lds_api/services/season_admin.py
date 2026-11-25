"""Administration des saisons et de leurs règles (M1, M2), modification des stades (M3).

Les règles qui changent les classements, les suspensions ou les statistiques sont figées dès
qu'un match de la saison a commencé : les modifier en cours de route fausserait les résultats
déjà acquis. Toute modification est inscrite au journal d'audit avec son motif.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lds_api.core.errors import BusinessError, NotFound
from lds_api.domain.standings import KNOWN_CRITERIA
from lds_api.models import CompetitionRules, Match, Pool, Season, TeamEntry, Venue
from lds_api.models.enums import MatchStatus, SeasonStatus
from lds_api.schemas import seasons as s
from lds_api.services import audit
from lds_api.services import seasons as seasons_svc

LOCKED_AFTER_START = (
    "points_win",
    "points_draw",
    "points_loss",
    "tiebreakers",
    "min_age",
    "youth_age_limit",
    "age_reference_date",
    "match_duration_minutes",
    "yellow_cards_threshold",
    "yellow_accumulation_ban_matches",
    "red_card_ban_matches",
    "second_yellow_ban_matches",
    "reset_yellows_after_group_stage",
    "qualifiers_per_pool",
    "third_place_match",
    "knockout_pairings",
)
RULE_FIELDS = tuple(s.RulesFields.model_fields)
PRIZE_KEYS = {"1", "2", "3", "4", "quarter_finalist"}


def season_started(db: Session, season: Season) -> bool:
    started = db.scalar(
        select(func.count(Match.id)).where(
            Match.season_id == season.id,
            Match.status.in_([MatchStatus.LIVE, MatchStatus.FINISHED]),
        )
    )
    return bool(started)


def rules_out(db: Session, season: Season) -> s.RulesAdminOut:
    rules = seasons_svc.rules_for(db, season)
    data = {f: getattr(rules, f) for f in RULE_FIELDS}
    started = season_started(db, season)
    return s.RulesAdminOut(
        **data,
        season_id=season.id,
        season_started=started,
        locked_fields=list(LOCKED_AFTER_START) if started else [],
    )


def _validate(values: dict) -> None:
    tb = values["tiebreakers"]
    unknown = [c for c in tb if c not in KNOWN_CRITERIA]
    if unknown:
        raise BusinessError(f"Critère de départage inconnu : {', '.join(unknown)}")
    if len(set(tb)) != len(tb):
        raise BusinessError("Un critère de départage figure deux fois")
    if not values["points_win"] > values["points_draw"] >= values["points_loss"]:
        raise BusinessError("Barème incohérent : victoire > nul ≥ défaite")
    if values["youth_age_limit"] <= values["min_age"]:
        raise BusinessError("L'âge « jeune » doit dépasser l'âge minimum")
    if values["min_youth_players"] > values["max_squad_players"]:
        raise BusinessError("Plus de jeunes exigés que de joueurs autorisés")
    seeds = [seed for pair in values["knockout_pairings"] for seed in pair]
    if any(len(pair) != 2 for pair in values["knockout_pairings"]) or len(set(seeds)) != len(seeds):
        raise BusinessError("Croisements des quarts : paires de deux places distinctes")
    for seed in seeds:
        if len(seed) < 2 or not seed[1:].isdigit() or int(seed[1:]) > values["qualifiers_per_pool"]:
            raise BusinessError(f"Place inconnue dans les croisements : {seed}")
    if set(values["prize_money"]) - PRIZE_KEYS or any(
        v < 0 for v in values["prize_money"].values()
    ):
        raise BusinessError("Dotations : rangs 1 à 4 et « quarter_finalist », montants positifs")


def _plain(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, date):
        return v.isoformat()
    return v


def update_rules(db: Session, actor, season: Season, body: s.RulesUpdate) -> s.RulesAdminOut:
    rules = seasons_svc.rules_for(db, season)
    sent = body.model_dump(exclude_unset=True, exclude={"reason"})
    changes = {k: v for k, v in sent.items() if getattr(rules, k) != v}
    if not changes:
        return rules_out(db, season)
    if season_started(db, season):
        locked = sorted(set(changes) & set(LOCKED_AFTER_START))
        if locked:
            raise BusinessError(
                "Saison commencée : ces règles sont figées jusqu'à la fin de la saison ("
                + ", ".join(locked)
                + ")",
                code="rules_locked",
            )
    values = {f: getattr(rules, f) for f in RULE_FIELDS} | changes
    _validate(values)
    diff = {k: [_plain(getattr(rules, k)), _plain(v)] for k, v in changes.items()}
    for k, v in changes.items():
        setattr(rules, k, v)
    audit.record(db, actor, "update_rules", "season", season.id, {"reason": body.reason, **diff})
    db.flush()
    return rules_out(db, season)


# --- Saisons ---------------------------------------------------------------------------------
def list_seasons(db: Session) -> list[s.SeasonAdminOut]:
    teams = dict(
        db.execute(
            select(TeamEntry.season_id, func.count(TeamEntry.id)).group_by(TeamEntry.season_id)
        ).all()
    )
    matches = dict(
        db.execute(select(Match.season_id, func.count(Match.id)).group_by(Match.season_id)).all()
    )
    out = []
    for season in db.scalars(select(Season).order_by(Season.year.desc())):
        item = s.SeasonAdminOut.model_validate(season)
        item.teams = teams.get(season.id, 0)
        item.matches = matches.get(season.id, 0)
        out.append(item)
    return out


def create_season(db: Session, actor, body: s.SeasonCreate) -> Season:
    if body.ends_on <= body.starts_on:
        raise BusinessError("La fin de saison doit suivre son début")
    if db.scalar(select(Season).where(Season.year == body.year)):
        raise BusinessError(f"La saison {body.year} existe déjà")
    season = Season(
        name=body.name,
        year=body.year,
        starts_on=body.starts_on,
        ends_on=body.ends_on,
        status=SeasonStatus.DRAFT,
        is_current=False,
    )
    db.add(season)
    db.flush()
    current = db.scalar(select(Season).where(Season.is_current.is_(True)))
    copied = {"rules": False, "pools": 0, "teams": 0}
    if body.copy_from_current and current is not None:
        old_rules = seasons_svc.rules_for(db, current)
        values = {f: getattr(old_rules, f) for f in RULE_FIELDS}
        values["age_reference_date"] = None  # propre à chaque saison
        db.add(CompetitionRules(season_id=season.id, **values))
        pools = {}
        for p in db.scalars(select(Pool).where(Pool.season_id == current.id)):
            new = Pool(season_id=season.id, code=p.code, name=p.name, host_city=p.host_city)
            db.add(new)
            pools[p.id] = new
        db.flush()
        for e in db.scalars(select(TeamEntry).where(TeamEntry.season_id == current.id)):
            db.add(
                TeamEntry(
                    season_id=season.id,
                    team_id=e.team_id,
                    pool_id=pools[e.pool_id].id if e.pool_id in pools else None,
                    draw_position=e.draw_position,
                )
            )
            copied["teams"] += 1
        copied |= {"rules": True, "pools": len(pools)}
    else:
        db.add(CompetitionRules(season_id=season.id))
    db.flush()
    audit.record(
        db,
        actor,
        "create",
        "season",
        season.id,
        {"year": season.year, "copied_from": current.year if current else None, **copied},
    )
    return season


def rename_season(db: Session, actor, season_id, name: str) -> Season:
    season = db.get(Season, season_id)
    if season is None:
        raise NotFound("Saison")
    if season.name != name:
        audit.record(db, actor, "rename", "season", season.id, {"name": [season.name, name]})
        season.name = name
    db.flush()
    return season


def activate_season(db: Session, actor, season_id) -> Season:
    """Bascule la saison courante : la précédente est close, la nouvelle devient active."""
    season = db.get(Season, season_id)
    if season is None:
        raise NotFound("Saison")
    if season.is_current:
        return season
    if season.status == SeasonStatus.CLOSED:
        raise BusinessError("Saison close : elle ne peut pas redevenir la saison courante")
    previous = db.scalar(select(Season).where(Season.is_current.is_(True)))
    if previous is not None:
        if db.scalar(
            select(func.count(Match.id)).where(
                Match.season_id == previous.id, Match.status == MatchStatus.LIVE
            )
        ):
            raise BusinessError("Un match de la saison courante est en cours")
        previous.is_current = False
        previous.status = SeasonStatus.CLOSED
        db.flush()  # une seule saison courante à la fois
    season.is_current = True
    season.status = SeasonStatus.ACTIVE
    audit.record(
        db,
        actor,
        "activate",
        "season",
        season.id,
        {"year": season.year, "previous": previous.year if previous else None},
    )
    db.flush()
    return season


# --- Stades ----------------------------------------------------------------------------------
def update_venue(db: Session, actor, venue_id, body: s.VenueUpdate) -> Venue:
    v = db.get(Venue, venue_id)
    if v is None:
        raise NotFound("Stade")
    changes = {
        k: val for k, val in body.model_dump(exclude_unset=True).items() if getattr(v, k) != val
    }
    if "name" in changes and db.scalar(
        select(Venue).where(Venue.name == changes["name"], Venue.id != v.id)
    ):
        raise BusinessError("Un stade porte déjà ce nom")
    diff = {k: [getattr(v, k), val] for k, val in changes.items()}
    for k, val in changes.items():
        setattr(v, k, val)
    if diff:
        audit.record(db, actor, "update", "venue", v.id, diff)
    db.flush()
    return v
