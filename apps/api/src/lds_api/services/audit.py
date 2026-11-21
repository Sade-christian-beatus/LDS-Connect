"""Écriture du journal d'audit, dans la même transaction que la modification auditée."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from lds_api.models import AuditLog

# Champs jamais recopiés en clair dans le journal
SENSITIVE_FIELDS = {"cnib_number", "phone", "password_hash", "token"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def diff(obj: Any) -> dict[str, list[Any]]:
    """Différence {champ: [avant, après]} des attributs modifiés d'un objet (avant flush)."""
    changes: dict[str, list[Any]] = {}
    state = inspect(obj)
    for attr in state.mapper.column_attrs:
        hist = state.attrs[attr.key].history
        if not hist.has_changes():
            continue
        before = hist.deleted[0] if hist.deleted else None
        after = hist.added[0] if hist.added else None
        if attr.key in SENSITIVE_FIELDS:
            changes[attr.key] = ["***", "***"]
        else:
            changes[attr.key] = [_jsonable(before), _jsonable(after)]
    return changes


def snapshot(obj: Any) -> dict[str, Any]:
    """Valeurs de toutes les colonnes (pour une création ou une suppression)."""
    state = inspect(obj)
    return {
        a.key: "***" if a.key in SENSITIVE_FIELDS else _jsonable(getattr(obj, a.key))
        for a in state.mapper.column_attrs
    }


def record(
    db: Session,
    actor: Any,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """`actor` : un deps.Actor, ou None pour une action système."""
    entry = AuditLog(
        actor_user_id=getattr(actor, "id", None),
        actor_label=getattr(actor, "label", "système"),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        changes=_jsonable(changes) if changes else None,
        ip_address=getattr(actor, "ip", None),
        request_id=getattr(actor, "request_id", None),
    )
    db.add(entry)
    return entry
