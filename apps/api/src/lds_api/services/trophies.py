"""Course aux trophées de la Ligue : les cinq distinctions et leurs prétendants, à partir des
données officielles (feuilles de match validées, votes publiés, classements).

Ce sont des classements statistiques : l'attribution finale suit le règlement de la Ligue.
- Vainqueur : champion si la finale est jouée, sinon les leaders des poules.
- Meilleur buteur : buts sur les feuilles validées (moins de penalties devant à égalité).
- Meilleur gardien : clean sheets, puis matchs joués.
- Homme du match : nombre de distinctions reçues (scrutins publiés).
- Meilleur joueur : vote du public « joueur de la saison » s'il existe, sinon à venir.
"""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from lds_api.domain import voting as vote_rules
from lds_api.models import Ballot, Match, Person, Player, PlayerStat, Team
from lds_api.models.enums import BallotKind, MatchPhase, MatchStatus, Position
from lds_api.schemas.fixtures import TeamRef
from lds_api.services import seasons, standings, stats


class Contender(BaseModel):
    rank: int
    person_id: uuid.UUID | None = None
    display_name: str
    team: TeamRef | None = None
    value: int
    detail: str = ""


class Trophy(BaseModel):
    code: str  # winner | top_scorer | goalkeeper | man_of_the_match | best_player
    title: str
    criterion: str
    status: str  # awarded | provisional | vote_open | vote_closed | upcoming
    status_label: str
    leaders: list[Contender]  # rang 1 (ex aequo compris)
    contenders: list[Contender]  # classement (top N)
    ballot_id: uuid.UUID | None = None


class TrophyRace(BaseModel):
    season: str
    trophies: list[Trophy]


def _rank(rows: list[Contender], key) -> list[Contender]:
    """Classement avec ex aequo : même clé, même rang."""
    rows.sort(key=key)
    previous, rank = None, 0
    for i, r in enumerate(rows, start=1):
        k = key(r)
        if k != previous:
            rank, previous = i, k
        r.rank = rank
    return rows


def _leaders(rows: list[Contender]) -> list[Contender]:
    return [r for r in rows if r.rank == 1 and r.value > 0]


def _winner(db: Session, season) -> Trophy:
    final = db.scalar(
        select(Match).where(Match.season_id == season.id, Match.phase == MatchPhase.FINAL)
    )
    title, criterion = "Vainqueur de la Ligue", "Finale, après les poules et les phases finales"
    if final and final.status == MatchStatus.FINISHED and final.winner_team_id:
        team = TeamRef.model_validate(db.get(Team, final.winner_team_id))
        champ = Contender(rank=1, display_name=team.name, team=team, value=1, detail="Champion")
        return Trophy(
            code="winner", title=title, criterion=criterion, status="awarded",
            status_label="Attribué", leaders=[champ], contenders=[champ],
        )  # fmt: skip
    rows = []
    for pool in standings.all_standings(db):
        if pool.rows:
            top = pool.rows[0]
            rows.append(
                Contender(
                    rank=1,
                    display_name=top.team.name,
                    team=top.team,
                    value=top.points,
                    detail=f"1er de la poule {pool.pool_code} · {top.points} pts",
                )
            )
    return Trophy(
        code="winner", title=title, criterion=criterion, status="provisional",
        status_label="En course : leaders des poules", leaders=rows, contenders=rows,
    )  # fmt: skip


def _player_rows(db: Session, season, column, *, goalkeepers=False, limit=5) -> list[Contender]:
    q = (
        select(PlayerStat, Person.display_name, Team)
        .join(Person, Person.id == PlayerStat.person_id)
        .join(Team, Team.id == PlayerStat.team_id)
        .where(PlayerStat.season_id == season.id)
    )
    if goalkeepers:
        q = q.join(Player, Player.person_id == PlayerStat.person_id).where(
            Player.position == Position.GOALKEEPER, PlayerStat.appearances > 0
        )
    else:
        q = q.where(column > 0)
    games: dict[uuid.UUID, int] = {}
    rows = []
    for st, name, team in db.execute(q):
        games[st.person_id] = st.appearances
        detail = f"{st.appearances} match(s)"
        if goalkeepers:
            detail += f" · {st.minutes_played} min"
        rows.append(
            Contender(
                rank=0,
                person_id=st.person_id,
                display_name=name,
                team=TeamRef.model_validate(team),
                value=getattr(st, column.key),
                detail=detail,
            )
        )
    if goalkeepers:  # à égalité de clean sheets, le gardien qui a le plus joué devant
        return _rank(rows, key=lambda r: (-r.value, -games[r.person_id]))[:limit]
    return _rank(rows, key=lambda r: (-r.value,))[:limit]


def _best_player(db: Session, season) -> Trophy:
    from lds_api.services import voting

    title = "Meilleur joueur"
    criterion = "Vote du public « joueur de la saison »"
    ballot = db.scalar(
        select(Ballot)
        .where(Ballot.season_id == season.id, Ballot.kind == BallotKind.PLAYER_OF_THE_SEASON)
        .order_by(Ballot.opens_at.desc())
    )
    if ballot is None:
        return Trophy(
            code="best_player", title=title, criterion=criterion, status="upcoming",
            status_label="Vote à venir en fin de saison", leaders=[], contenders=[],
        )  # fmt: skip
    at = datetime.now(UTC)
    state = vote_rules.effective_state(ballot.status.value, ballot.opens_at, ballot.closes_at, at)
    contenders: list[Contender] = []
    if voting._visible(ballot, at):
        res = voting.results(db, ballot)
        contenders = [
            Contender(rank=o.rank, display_name=o.label, team=o.team, value=o.votes,
                      detail=f"{round(o.share * 100)} % des votants")
            for o in res.options[:5]
        ]  # fmt: skip
    awarded = ballot.status.value == "published"
    labels = {"open": "Vote ouvert", "closed": "Vote clos, résultats à venir"}
    return Trophy(
        code="best_player",
        title=title,
        criterion=criterion,
        status="awarded" if awarded else ("vote_open" if state == "open" else "vote_closed"),
        status_label="Attribué" if awarded else labels.get(state, "Vote à venir"),
        leaders=[c for c in contenders if c.rank == 1 and c.value > 0],
        contenders=contenders,
        ballot_id=ballot.id,
    )


def race(db: Session) -> TrophyRace:
    season = seasons.current_season(db)
    scorers = stats.season_stats(db, season.id, limit=5).scorers
    top_scorers = [
        Contender(rank=r.rank, person_id=r.person_id, display_name=r.display_name, team=r.team,
                  value=r.value, detail=f"dont {r.penalties} pén." if r.penalties else "")
        for r in scorers
    ]  # fmt: skip
    keepers = _player_rows(db, season, PlayerStat.clean_sheets, goalkeepers=True)
    motm = _player_rows(db, season, PlayerStat.man_of_the_match)
    provisional = "provisional"
    return TrophyRace(
        season=season.name,
        trophies=[
            _winner(db, season),
            Trophy(code="top_scorer", title="Meilleur buteur", status=provisional,
                   criterion="Buts sur les feuilles de match validées",
                   status_label="Classement en cours", leaders=_leaders(top_scorers),
                   contenders=top_scorers),
            Trophy(code="goalkeeper", title="Meilleur gardien", status=provisional,
                   criterion="Matchs sans encaisser de but (clean sheets), puis matchs joués",
                   status_label="Classement en cours", leaders=_leaders(keepers),
                   contenders=keepers),
            Trophy(code="man_of_the_match", title="Homme du match", status=provisional,
                   criterion="Distinctions d'homme du match reçues (votes publiés)",
                   status_label="Classement en cours", leaders=_leaders(motm),
                   contenders=motm),
            _best_player(db, season),
        ],
    )  # fmt: skip
