"""Garde-fous de démarrage : une configuration de développement est refusée en production."""

import pytest

from lds_api.core.config import Settings, enforce_production_settings
from lds_api.providers.sms import ConsoleSmsProvider, SmsUnavailable

GOOD = {
    "environment": "production",
    "jwt_secret": "x" * 40,
    "field_encryption_key": "k",
    "blind_index_key": "b",
    "licence_signing_key": "s",
    "refresh_cookie_secure": True,
    "payment_provider": "disabled",
    "sms_provider": "console",
    "public_base_url": "https://lds.example.bf",
    "api_base_url": "https://lds.example.bf",
    "cors_origins": "https://lds.example.bf",
}


def settings(**over: object) -> Settings:
    return Settings(**{**GOOD, **over})


def test_production_configuration_accepted() -> None:
    enforce_production_settings(settings())


@pytest.mark.parametrize(
    ("over", "needle"),
    [
        ({"jwt_secret": "court"}, "JWT_SECRET"),
        ({"field_encryption_key": ""}, "FIELD_ENCRYPTION_KEY"),
        ({"refresh_cookie_secure": False}, "REFRESH_COOKIE_SECURE"),
        ({"payment_provider": "simulator"}, "PAYMENT_PROVIDER"),
        ({"sms_provider": "simulator"}, "SMS_PROVIDER"),
        ({"public_base_url": "http://lds.example.bf"}, "PUBLIC_BASE_URL"),
        ({"api_base_url": "https://localhost:8000"}, "API_BASE_URL"),
        ({"cors_origins": "https://lds.example.bf,http://localhost:3000"}, "CORS_ORIGINS"),
        ({"cors_origins": "*"}, "CORS_ORIGINS"),
    ],
)
def test_development_settings_refused(over: dict, needle: str) -> None:
    with pytest.raises(RuntimeError, match=needle):
        enforce_production_settings(settings(**over))


def test_other_environments_not_checked() -> None:
    enforce_production_settings(settings(environment="development", refresh_cookie_secure=False))


def test_console_sms_refused_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lds_api.providers.sms.get_settings", lambda: settings())
    with pytest.raises(SmsUnavailable):
        ConsoleSmsProvider().send("+22670000000", "code 123456")
