"""Configuration de l'application, lue exclusivement depuis les variables d'environnement."""

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

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
    # Rôles tenus d'activer la double authentification (codes séparés par des virgules).
    # Non renseigné : super administrateur et administration en production, aucun ailleurs
    # (démonstration et tests sans application d'authentification).
    mfa_required_roles: str | None = None

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
    # Secret partagé avec l'agrégateur : signature HMAC-SHA256 de ses notifications
    payment_webhook_secret: SecretStr = SecretStr("")
    # Durées de conservation en jours (purge : python -m lds_api.cli purge ; 0 = sans limite)
    retention_otp_days: int = 30  # après la clôture du scrutin
    retention_unpaid_orders_days: int = 30
    retention_paid_order_phone_days: int = 0  # à fixer par la Ligue (obligations comptables)

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

    @property
    def mfa_roles(self) -> set[str]:
        if self.mfa_required_roles is None:
            if self.environment == "production":
                return {"super_admin", "admin_competition"}
            return set()
        return {r.strip() for r in self.mfa_required_roles.split(",") if r.strip()}

    def production_problems(self) -> list[str]:
        """Réglages incompatibles avec une mise en service (vérifiés au démarrage en production)."""
        problems: list[str] = []
        if len(self.jwt_secret.get_secret_value()) < 32:
            problems.append("JWT_SECRET doit compter au moins 32 caractères")
        for name in ("field_encryption_key", "blind_index_key", "licence_signing_key"):
            if not getattr(self, name).get_secret_value():
                problems.append(f"{name.upper()} est vide (make keys)")
        if "super_admin" not in self.mfa_roles:
            problems.append("MFA_REQUIRED_ROLES doit inclure super_admin (double authentification)")
        if not self.refresh_cookie_secure:
            problems.append("REFRESH_COOKIE_SECURE doit valoir true (HTTPS)")
        if self.payment_provider == "simulator":
            problems.append("PAYMENT_PROVIDER=simulator : aucun paiement réel ne serait encaissé")
        if (
            self.payment_provider != "disabled"
            and not self.payment_webhook_secret.get_secret_value()
        ):
            problems.append(
                "PAYMENT_WEBHOOK_SECRET est vide : notifications de paiement non vérifiées"
            )
        if self.sms_provider == "simulator":
            problems.append("SMS_PROVIDER=simulator : aucun SMS ne partirait")
        for name in ("public_base_url", "api_base_url"):
            url = getattr(self, name)
            if not url.startswith("https://") or _is_local(url):
                problems.append(f"{name.upper()} doit être une adresse publique en https")
        for origin in self.cors_origins:
            if origin == "*" or _is_local(origin):
                problems.append(f"CORS_ORIGINS contient une origine de développement : {origin}")
        return problems


def _is_local(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    local = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}  # noqa: S104 — liste de refus
    return host in local or host.endswith(".local")


def enforce_production_settings(settings: Settings) -> None:
    """Refuse de démarrer en production avec une configuration de développement."""
    if settings.environment != "production":
        return
    problems = settings.production_problems()
    if problems:
        raise RuntimeError("Configuration refusée pour la production :\n- " + "\n- ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
