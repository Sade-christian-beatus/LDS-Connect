"""Règles d'éligibilité individuelles (fonctions pures)."""

import uuid
from datetime import date


def age_on(birth_date: date, reference: date) -> int:
    """Âge en années révolues à la date de référence."""
    before_birthday = (reference.month, reference.day) < (birth_date.month, birth_date.day)
    return reference.year - birth_date.year - before_birthday


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year, month = d.year + month_index // 12, month_index % 12 + 1
    # Fin de mois : le 31 janvier + 1 mois donne le 28/29 février
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError(d)


def is_local(
    *,
    residence_region_id: uuid.UUID | None,
    residence_since: date | None,
    team_region_id: uuid.UUID,
    on: date,
    min_months: int,
) -> bool:
    """Un joueur est « local » s'il réside dans la région de l'équipe depuis au moins
    `min_months` mois à la date `on`."""
    if residence_region_id is None or residence_since is None:
        return False
    if residence_region_id != team_region_id:
        return False
    return add_months(residence_since, min_months) <= on
