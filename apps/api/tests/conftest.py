"""Configuration commune des tests : clés éphémères, jamais de secret réel."""

import os

from lds_api.cli import generate_keys

# Les clés sont générées avant tout import de la configuration de l'application.
for _k, _v in generate_keys().items():
    os.environ[_k] = _v
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+psycopg://lds:lds-dev-password@localhost:5432/lds_test"
)
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
