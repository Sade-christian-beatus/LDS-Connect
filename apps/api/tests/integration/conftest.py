"""Base de test : migrée et seedée une fois par session ; chaque test tourne dans une
transaction annulée à la fin (les commits des services deviennent des points de sauvegarde)."""

import contextlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from lds_api.core import ratelimit
from lds_api.core.config import get_settings
from lds_api.db.session import get_db
from lds_api.main import app
from lds_api.models import Season
from lds_api.seed import run as seed_run
from lds_api.seed.reference import DEMO_PASSWORD

API_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = get_settings().database_url
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    eng = create_engine(url)
    with Session(eng, autoflush=False) as s:
        seed_run.run(s, demo=True)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def seeded(db: Session) -> Season:
    return db.scalar(select(Season).where(Season.year == seed_run.SEASON_YEAR))


@pytest.fixture(autouse=True)
def _clean_redis() -> None:
    """Base Redis de test (n° 15) vidée avant chaque test : cache et limitation de débit."""
    with contextlib.suppress(Exception):  # Redis absent : cache et limitation ignorés
        ratelimit.get_redis().flushdb()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client: TestClient, email: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def as_admin(client) -> dict[str, str]:
    return login(client, "admin@lds.local")


@pytest.fixture
def as_club(client) -> dict[str, str]:
    return login(client, "club.vinnim@lds.local")


@pytest.fixture
def as_delegate(client) -> dict[str, str]:
    return login(client, "delegue@lds.local")


@pytest.fixture
def as_controller(client) -> dict[str, str]:
    return login(client, "controle@lds.local")
