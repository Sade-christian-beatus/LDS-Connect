"""Export complet des données (propriété de la Ligue) en JSON et CSV, une table par fichier.

- Données chiffrées (CNIB, téléphones) : masquées par défaut ; déchiffrées seulement avec
  `include_sensitive=True` (action journalisée). Le fichier produit est alors sensible.
- Jamais exportés : hachages de mots de passe, jetons de session, codes OTP.
"""

import csv
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

import lds_api.models  # noqa: F401 — enregistre toutes les tables
from lds_api.db.base import Base
from lds_api.db.types import EncryptedString
from lds_api.services import audit

EXCLUDED_TABLES = {"refresh_tokens"}
EXCLUDED_COLUMNS = {("users", "password_hash"), ("otp_challenges", "code_hash")}


def _order_state(row, now: datetime) -> str:
    """État affiché d'une commande : « expired » n'est pas stocké, il se déduit de l'échéance."""
    status = _plain(row["status"])
    if status == "pending" and row["expires_at"] is not None and row["expires_at"] < now:
        return "expired"
    return status


# Colonnes calculées ajoutées à l'export (lisibilité des fichiers hors de la plateforme)
DERIVED = {"orders": {"effective_status": _order_state}}


def _plain(value):
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes | memoryview):
        return None
    return value


def export_all(db: Session, out_dir: Path, *, include_sensitive: bool = False) -> dict[str, int]:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    target = out_dir / f"export-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    counts: dict[str, int] = {}
    now = datetime.now(UTC)
    for table in Base.metadata.sorted_tables:
        if table.name in EXCLUDED_TABLES:
            continue
        cols = [c for c in table.columns if (table.name, c.name) not in EXCLUDED_COLUMNS]
        cols.sort(key=lambda c: not c.primary_key)  # identifiant en première colonne
        rows = []
        for row in db.execute(select(*cols)).mappings():
            item = {}
            for c in cols:
                if isinstance(c.type, EncryptedString) and not include_sensitive:
                    item[c.name] = "***" if row[c.name] is not None else None
                else:
                    item[c.name] = _plain(row[c.name])
            for name, fn in DERIVED.get(table.name, {}).items():
                item[name] = fn(row, now)
            rows.append(item)
        counts[table.name] = len(rows)
        (target / f"{table.name}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        with (target / f"{table.name}.csv").open("w", newline="", encoding="utf-8") as fh:
            fields = [c.name for c in cols] + list(DERIVED.get(table.name, {}))
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for r in rows:
                writer.writerow(
                    {k: json.dumps(v, ensure_ascii=False) if isinstance(v, dict | list) else v
                     for k, v in r.items()}
                )  # fmt: skip
    manifest = {
        "generated_at": stamp,
        "include_sensitive": include_sensitive,
        "tables": counts,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    audit.record(
        db,
        None,
        "export_sensitive" if include_sensitive else "export",
        "database",
        None,
        {"directory": target.name, "tables": len(counts)},
    )
    db.commit()
    return {"directory": str(target), **counts}
