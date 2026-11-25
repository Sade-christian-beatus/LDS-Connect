"""Codes à usage unique basés sur le temps (TOTP, RFC 6238) : 6 chiffres, pas de 30 s, SHA-1.

C'est l'algorithme des applications d'authentification courantes (Google Authenticator,
Microsoft Authenticator, FreeOTP, Aegis…). Implémenté ici avec la bibliothèque standard.
"""

import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote, urlencode

STEP_SECONDS = 30
DIGITS = 6


def new_secret() -> str:
    """Secret de 160 bits encodé en base32 (format attendu par les applications)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret: str) -> bytes:
    padded = secret.upper() + "=" * (-len(secret) % 8)
    return base64.b32decode(padded)


def code_at(secret: str, step: int) -> str:
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def step_for(timestamp: float) -> int:
    return int(timestamp // STEP_SECONDS)


def verify(
    secret: str, code: str, timestamp: float, *, last_step: int | None = None, window: int = 1
) -> int | None:
    """Pas de temps du code s'il est valide (±1 pas toléré pour le décalage des horloges).

    Un code déjà utilisé (pas ≤ `last_step`) est refusé : il ne peut pas être rejoué.
    """
    code = "".join(c for c in code if c.isdigit())
    if len(code) != DIGITS:
        return None
    now = step_for(timestamp)
    for step in range(now - window, now + window + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, account: str, issuer: str = "LDS Connect") -> str:
    """Adresse « otpauth:// » à afficher en QR code pour l'application d'authentification."""
    label = quote(f"{issuer}:{account}")
    params = urlencode(
        {"secret": secret, "issuer": issuer, "digits": DIGITS, "period": STEP_SECONDS}
    )
    return f"otpauth://totp/{label}?{params}"
