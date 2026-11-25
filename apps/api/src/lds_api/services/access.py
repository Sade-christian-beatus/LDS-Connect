"""Contrôle d'accès au stade : billets et accréditations, en ligne ou hors ligne.

Avant le match, chaque appareil télécharge le « manifeste » (billets du match et leur état,
accréditations révoquées) et les clés publiques ; il vérifie ensuite les QR seul (signature
Ed25519) et met les passages en file d'attente. À la synchronisation, le serveur rejoue les
passages : le premier passage d'un billet (heure de l'appareil) est l'entrée, les suivants
sont des doubles entrées, même s'ils viennent d'appareils différents restés hors ligne.
"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lds_api.core.errors import NotFound
from lds_api.domain import signed_token
from lds_api.domain import ticketing as rules
from lds_api.models import AccessScan, Accreditation, Match, Ticket, TicketType
from lds_api.models.enums import ScanResult, TicketStatus
from lds_api.schemas import ticketing as ts
from lds_api.services import fixtures, licences

PREFIXES = (signed_token.TICKET_PREFIX, signed_token.ACCREDITATION_PREFIX)


def manifest(db: Session, match_id: uuid.UUID) -> ts.Manifest:
    m = db.scalar(fixtures.match_query().where(Match.id == match_id))
    if m is None:
        raise NotFound("Match introuvable")
    rows = db.execute(
        select(Ticket.code, Ticket.status, TicketType.name, Ticket.scanned_at)
        .join(TicketType, TicketType.id == Ticket.ticket_type_id)
        .where(Ticket.match_id == match_id)
        .order_by(Ticket.code)
    )
    revoked = db.scalars(
        select(Accreditation.code).where(
            Accreditation.season_id == m.season_id, Accreditation.revoked_at.is_not(None)
        )
    )
    return ts.Manifest(
        match=fixtures.to_out(m),
        generated_at=datetime.now(UTC),
        tickets=[ts.ManifestTicket(c=c, s=s, t=t, e=e) for c, s, t, e in rows],
        revoked_accreditations=list(revoked),
    )


def _parse(token: str) -> tuple[str, dict | None, str]:
    token = token.strip()
    prefix = token.split(".", 1)[0]
    if prefix not in PREFIXES:
        return "unknown", None, "QR non reconnu (ni billet ni accréditation LDS)"
    try:
        payload = signed_token.verify(token, licences.public_keys(), prefix=prefix)
    except signed_token.TokenError:
        return "unknown", None, "Signature invalide : QR falsifié ou abîmé"
    kind = "ticket" if prefix == signed_token.TICKET_PREFIX else "accreditation"
    return kind, payload, ""


def _scan_ticket(db: Session, actor, scan: ts.ScanIn, payload: dict, token: str):
    t = db.scalar(select(Ticket).where(Ticket.code == payload.get("c")).with_for_update())
    if t is None or t.token != token.strip():
        return None, rules.Decision(ScanResult.INVALID, "Billet inconnu ou remplacé")
    label = db.scalar(select(TicketType.name).where(TicketType.id == t.ticket_type_id))
    refusal = rules.zone_refusal(kind="ticket", gate_zone=scan.zone)
    if refusal:
        return (t, label), rules.Decision(ScanResult.INVALID, refusal)
    first = db.scalar(
        select(AccessScan)
        .where(AccessScan.ticket_id == t.id, AccessScan.result == ScanResult.ADMITTED)
        .order_by(AccessScan.scanned_at)
        .limit(1)
    )
    decision = rules.decide_ticket(
        ticket_status=t.status.value,
        ticket_match_id=t.match_id,
        scan_match_id=scan.match_id,
        first_entry=rules.PriorEntry(first.scanned_at, first.device) if first else None,
        scanned_at=scan.scanned_at,
    )
    if decision.result == ScanResult.ADMITTED:
        if first is not None:
            # Passage hors ligne plus ancien que l'entrée connue : il devient l'entrée
            first.result = ScanResult.DUPLICATE
            first.detail = f"Déjà entré à {scan.scanned_at:%H:%M} (synchronisé plus tard)"
        t.status = TicketStatus.USED
        t.scanned_at = scan.scanned_at
        t.scanned_by_id = getattr(actor, "id", None)
        t.scan_device = scan.device
    return (t, label), decision


def _scan_accreditation(db: Session, scan: ts.ScanIn, payload: dict, token: str):
    a = db.scalar(select(Accreditation).where(Accreditation.code == payload.get("c")))
    if a is None or a.token != token.strip():
        return None, rules.Decision(ScanResult.INVALID, "Accréditation inconnue ou remplacée")
    day: date = scan.scanned_at.date()
    if a.revoked_at is not None:
        return a, rules.Decision(ScanResult.INVALID, "Accréditation révoquée")
    if not (a.valid_from <= day <= a.valid_until):
        return a, rules.Decision(ScanResult.INVALID, "Accréditation hors de sa période de validité")
    refusal = rules.zone_refusal(kind="accreditation", gate_zone=scan.zone, zones=a.zones)
    if refusal:
        return a, rules.Decision(ScanResult.INVALID, refusal)
    # Une accréditation permet plusieurs entrées et sorties
    return a, rules.Decision(ScanResult.ADMITTED, f"Accréditation {a.category.value} valide")


def record(db: Session, actor, scans: list[ts.ScanIn]) -> list[ts.ScanOut]:
    out = []
    for scan in sorted(scans, key=lambda s: s.scanned_at):
        known = db.scalar(select(AccessScan).where(AccessScan.client_id == scan.client_id))
        if known is not None:  # renvoi d'un passage déjà synchronisé
            out.append(_out(db, known))
            continue
        kind, payload, error = _parse(scan.token)
        row = AccessScan(
            client_id=scan.client_id,
            match_id=scan.match_id,
            scanned_at=scan.scanned_at,
            offline=scan.offline,
            device=scan.device,
            zone=scan.zone or None,
            scanned_by_id=getattr(actor, "id", None),
        )
        label = None
        if kind == "unknown":
            row.result, row.detail = ScanResult.INVALID, error
        elif kind == "ticket":
            found, d = _scan_ticket(db, actor, scan, payload, scan.token)
            row.result, row.detail, row.code = d.result, d.detail, payload.get("c")
            if found:
                row.ticket_id, label = found[0].id, found[1]
        else:
            a, d = _scan_accreditation(db, scan, payload, scan.token)
            row.result, row.detail, row.code = d.result, d.detail, payload.get("c")
            if a is not None:
                row.accreditation_id, label = a.id, a.full_name
        db.add(row)
        db.flush()
        out.append(
            ts.ScanOut(
                client_id=row.client_id,
                result=row.result,
                detail=row.detail or "",
                kind=kind,
                code=row.code,
                label=label,
            )
        )
    return out


def _out(db: Session, row: AccessScan) -> ts.ScanOut:
    kind, label = "unknown", None
    if row.ticket_id:
        kind = "ticket"
        label = db.scalar(
            select(TicketType.name)
            .join(Ticket, Ticket.ticket_type_id == TicketType.id)
            .where(Ticket.id == row.ticket_id)
        )
    elif row.accreditation_id:
        kind = "accreditation"
        label = db.scalar(
            select(Accreditation.full_name).where(Accreditation.id == row.accreditation_id)
        )
    return ts.ScanOut(
        client_id=row.client_id,
        result=row.result,
        detail=row.detail or "",
        kind=kind,
        code=row.code,
        label=label,
    )


def stats(db: Session, match_id: uuid.UUID) -> ts.AccessStats:
    sold = db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.match_id == match_id, Ticket.status != TicketStatus.CANCELLED
        )
    )
    rows = db.execute(
        select(AccessScan.result, AccessScan.accreditation_id.is_not(None), func.count())
        .where(AccessScan.match_id == match_id)
        .group_by(AccessScan.result, AccessScan.accreditation_id.is_not(None))
    ).all()
    count = {(r, acc): n for r, acc, n in rows}
    by_device = dict(
        db.execute(
            select(func.coalesce(AccessScan.device, "?"), func.count())
            .where(AccessScan.match_id == match_id, AccessScan.result == ScanResult.ADMITTED)
            .group_by(AccessScan.device)
        ).all()
    )
    return ts.AccessStats(
        match_id=match_id,
        tickets_sold=sold or 0,
        admitted=count.get((ScanResult.ADMITTED, False), 0),
        duplicates=count.get((ScanResult.DUPLICATE, False), 0),
        invalid=sum(
            n for (r, _), n in count.items() if r in (ScanResult.INVALID, ScanResult.WRONG_MATCH)
        ),
        accreditations_admitted=count.get((ScanResult.ADMITTED, True), 0),
        by_device=by_device,
    )
