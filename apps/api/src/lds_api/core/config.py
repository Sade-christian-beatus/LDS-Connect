"""Configuration de l'application, lue exclusivement depuis les variables d'environnement."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    # .env à la racine du dépôt (exécution depuis apps/api) ou dans le dossier courant
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Général
    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "LDS Connect"
    public_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    # Liste séparée par des virgules
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    # Proxys de confiance (reverse proxy, réseau Docker) : seuls eux peuvent indiquer
    # l'adresse réelle du visiteur par X-Forwarded-For. Adresses ou réseaux, séparés par
    # des virgules. Sans cela, derrière un proxy, tous les visiteurs auraient la même IP.
    trusted_proxies: str = "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # Base de données et cache
    database_url: str = "postgresql+psycopg://lds:lds@localhost:5432/lds"
    redis_url: str = "redis://localhost:6379/0"

    # Authentification
    jwt_secret: SecretStr = SecretStr("dev-only-change-me")
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 14
    refresh_cookie_secure: bool = False

    # Chiffrement des données personnelles (AES-256-GCM) — clé base64 de 32 octets
    field_encryption_key: SecretStr = SecretStr("")
    # Clé HMAC pour les index aveugles (unicité/recherche sur champs chiffrés) — base64
    blind_index_key: SecretStr = SecretStr("")

    # Signature des licences (Ed25519) — clé privée PEM en base64, identifiant de clé
    licence_signing_key: SecretStr = SecretStr("")
    licence_key_id: str = "lds-2027-1"
    # Anciennes clés publiques encore acceptées après une rotation : « kid:clé_base64url,… »
    licence_previous_public_keys: str = ""

    # Fournisseurs (interfaces + simulateurs)
    sms_provider: Literal["simulator", "console"] = "simulator"
    # Votes du public : indicatifs autorisés (séparés par des virgules), Burkina Faso par défaut
    vote_allowed_country_codes: str = "226"
    # Indicatifs acceptés pour l'achat de billets (numéro de l'acheteur)
    ticket_allowed_country_codes: str = "226"
    sms_simulator_url: str = "http://localhost:8090"
    payment_provider: Literal["simulator", "disabled"] = "disabled"
    payment_simulator_url: str = "http://localhost:8090"
    # Adresse de l'API vue par l'agrégateur pour ses notifications (vide = API_BASE_URL)
    payment_callback_base_url: str = ""
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_path: str = "./var/storage"
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None

    # Courriel (Mailpit en local)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "no-reply@lds.local"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
