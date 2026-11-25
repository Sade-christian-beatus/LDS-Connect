"""Configuration commune des tests : clés éphémères, jamais de secret réel."""

import os
import warnings

# Annonce du passage de TestClient à « httpx2 », émise à l'import (avant les filtres de
# pyproject) : sans effet sur les tests.
warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")

from lds_api.cli import generate_keys  # noqa: E402

# Les clés sont générées avant tout import de la configuration de l'application.
for _k, _v in generate_keys().items():
    os.environ[_k] = _v
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+psycopg://lds:lds-dev-password@localhost:5432/lds_test"
)
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
# Base Redis dédiée aux tests (elle est vidée) : jamais celle de l'application
_redis = os.environ.get("REDIS_URL", "redis://localhost:6379/0").rsplit("/", 1)[0]
os.environ["REDIS_URL"] = f"{_redis}/15"
