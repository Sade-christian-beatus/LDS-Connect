"""Votes du public : consultation et vote (public), scrutins et contrôle (administration)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from lds_api.core.deps import Actor, DbSession, client_ip, require
from lds_api.core.errors import NotFound
from lds_api.core.rbac import Perm
from lds_api.models import Ballot
from lds_api.models.enums import VoteStatus
from lds_api.schemas import voting as vs
from lds_api.services import seasons
from lds_api.services import voting as svc

router = APIRouter(tags=["votes"])
VoteManager = Annotated[Actor, Depends(require(Perm.VOTE_MANAGE))]


# --- Public ---------------------------------------------------------------------------
@router.get("/ballots", response_model=list[vs.BallotOut])
def list_ballots(db: DbSession):
    """Scrutins ouverts, à venir et clos (résultats selon la règle de publication)."""
    return svc.public_list(db)


@router.get("/ballots/{ballot_id}", response_model=vs.BallotOut)
def get_ballot(ballot_id: uuid.UUID, db: DbSession):
    return svc.view(db, svc.get_ballot(db, ballot_id, public=True))


@router.post("/ballots/{ballot_id}/code", response_model=vs.CodeSent)
def request_code(ballot_id: uuid.UUID, body: vs.CodeRequest, request: Request, db: DbSession):
    """Envoie un code par SMS au numéro indiqué ; les choix restent en attente du code."""
    b = svc.get_ballot(db, ballot_id, public=True)
    sent = svc.request_code(db, b, body, client_ip(request))
    db.commit()
    return sent


@router.post("/ballots/{ballot_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
def cast_vote(ballot_id: uuid.UUID, body: vs.VoteIn, request: Request, db: DbSession):
    """Confirme le vote avec le code reçu. Réponse identique que le vote soit compté
    immédiatement ou mis de côté pour examen (pas d'indice pour un fraudeur)."""
    b = svc.get_ballot(db, ballot_id, public=True)
    svc.cast_vote(db, b, body, client_ip(request), request.headers.get("user-agent"))
    db.commit()


# --- Administration ---------------------------------------------------------------------------
@router.get("/admin/ballots", response_model=list[vs.BallotAdminOut])
def admin_list(db: DbSession, actor: VoteManager):
    season = seasons.current_season(db)
    ballots = db.scalars(
        select(Ballot)
        .where(Ballot.season_id == season.id)
        .options(selectinload(Ballot.options))
        .order_by(Ballot.opens_at.desc())
    )
    return [svc.view(db, b, admin=True) for b in ballots]


@router.get("/admin/ballots/candidates", response_model=list[vs.Candidate])
def ballot_candidates(
    db: DbSession,
    actor: VoteManager,
    kind: Annotated[str, Query(description="match | players | coaches | goals | teams")],
    match_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
):
    """Propositions suggérées (joueurs d'un match, entraîneurs, buts marqués…)."""
    return svc.candidates(db, kind, match_id=match_id, team_id=team_id)


@router.post(
    "/admin/ballots", response_model=vs.BallotAdminOut, status_code=status.HTTP_201_CREATED
)
def create_ballot(body: vs.BallotIn, db: DbSession, actor: VoteManager):
    b = svc.create_ballot(db, actor, body)
    db.commit()
    return svc.view(db, svc.get_ballot(db, b.id), admin=True)


@router.get("/admin/ballots/{ballot_id}", response_model=vs.BallotAdminOut)
def admin_get(ballot_id: uuid.UUID, db: DbSession, actor: VoteManager):
    return svc.view(db, svc.get_ballot(db, ballot_id), admin=True)


@router.patch("/admin/ballots/{ballot_id}", response_model=vs.BallotAdminOut)
def update_ballot(ballot_id: uuid.UUID, body: vs.BallotUpdate, db: DbSession, actor: VoteManager):
    b = svc.update_ballot(db, actor, svc.get_ballot(db, ballot_id), body)
    db.commit()
    return svc.view(db, svc.get_ballot(db, b.id), admin=True)


@router.post("/admin/ballots/{ballot_id}/{action}", response_model=vs.BallotAdminOut)
def ballot_action(ballot_id: uuid.UUID, action: str, db: DbSession, actor: VoteManager):
    """Actions : open (ouvrir), close (clore avant la date), publish (publier les résultats)."""
    b = svc.get_ballot(db, ballot_id)
    actions = {"open": svc.open_ballot, "close": svc.close_ballot, "publish": svc.publish_results}
    if action not in actions:
        raise NotFound("Action")
    actions[action](db, actor, b)
    db.commit()
    return svc.view(db, b, admin=True)


@router.get("/admin/ballots/{ballot_id}/voters", response_model=list[vs.VoterOut])
def ballot_voters(
    ballot_id: uuid.UUID,
    db: DbSession,
    actor: VoteManager,
    status_: Annotated[VoteStatus | None, Query(alias="status")] = None,
):
    return svc.voters(db, svc.get_ballot(db, ballot_id), status_)


@router.post("/admin/ballots/{ballot_id}/voters/{voter}/review")
def review_voter(
    ballot_id: uuid.UUID, voter: str, body: vs.ReviewIn, db: DbSession, actor: VoteManager
) -> dict:
    n = svc.review(db, actor, svc.get_ballot(db, ballot_id), voter, body.decision)
    db.commit()
    return {"updated_votes": n}


@router.get("/admin/ballots/{ballot_id}/report", response_model=vs.ReportOut)
def ballot_report(ballot_id: uuid.UUID, db: DbSession, actor: VoteManager):
    """Données du procès-verbal (page imprimable / PDF côté interface)."""
    out = svc.report(db, actor, svc.get_ballot(db, ballot_id))
    db.commit()
    return out


def _csv(content: str, filename: str) -> Response:
    # BOM UTF-8 : ouverture correcte des accents dans Excel
    return Response(
        "﻿" + content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/admin/ballots/{ballot_id}/journal.csv", response_class=Response)
def journal_csv(ballot_id: uuid.UUID, db: DbSession, actor: VoteManager):
    return _csv(
        svc.journal_csv(db, svc.get_ballot(db, ballot_id)), f"journal-votes-{ballot_id}.csv"
    )


@router.get("/admin/ballots/{ballot_id}/results.csv", response_class=Response)
def results_csv(ballot_id: uuid.UUID, db: DbSession, actor: VoteManager):
    return _csv(svc.results_csv(db, svc.get_ballot(db, ballot_id)), f"resultats-{ballot_id}.csv")
