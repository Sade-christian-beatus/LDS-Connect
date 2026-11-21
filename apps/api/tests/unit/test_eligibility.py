import uuid
from datetime import date

import pytest

from lds_api.domain.eligibility import add_months, age_on, is_local

REGION = uuid.uuid4()
OTHER = uuid.uuid4()


@pytest.mark.parametrize(
    ("birth", "ref", "expected"),
    [
        (date(2010, 1, 1), date(2027, 1, 1), 17),
        (date(2010, 1, 2), date(2027, 1, 1), 16),
        (date(2008, 2, 29), date(2027, 2, 28), 18),
        (date(2008, 2, 29), date(2027, 3, 1), 19),
    ],
)
def test_age_on(birth, ref, expected):
    assert age_on(birth, ref) == expected


def test_add_months_end_of_month():
    assert add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert add_months(date(2026, 7, 15), 6) == date(2027, 1, 15)


@pytest.mark.parametrize(
    ("since", "region", "expected"),
    [
        (date(2026, 7, 1), REGION, True),  # exactement 6 mois
        (date(2026, 7, 2), REGION, False),  # un jour de moins
        (date(2020, 1, 1), REGION, True),
        (date(2020, 1, 1), OTHER, False),  # autre région
        (None, REGION, False),
    ],
)
def test_is_local(since, region, expected):
    assert (
        is_local(
            residence_region_id=region,
            residence_since=since,
            team_region_id=REGION,
            on=date(2027, 1, 1),
            min_months=6,
        )
        is expected
    )
