"""Jetons signés Ed25519 pour les QR codes (licences, et plus tard billets et accréditations).

Format : ``<PRÉFIXE>.<données>.<signature>``
- données   : JSON canonique (clés triées, sans espaces) encodé en base64url sans « = »
- signature : Ed25519 sur les octets ASCII ``<PRÉFIXE>.<données>``, en base64url

Le champ ``kid`` des données désigne la clé de signature : la vérification hors ligne
choisit la clé publique correspondante, ce qui permet une rotation de clés.
Ce format est volontairement simple pour être réimplémenté côté navigateur
(apps/web/src/lib/signed-token.ts).
"""

import base64
import json
from collections.abc import Mapping
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

LICENCE_PREFIX = "LDS1"


class TokenError(ValueError):
    """Jeton mal formé, clé inconnue ou signature invalide."""


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def canonical_json(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load_private_key(pem_b64: str) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(base64.b64decode(pem_b64), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TokenError("La clé de signature doit être une clé Ed25519")
    return key


def public_key_raw(key: Ed25519PrivateKey | Ed25519PublicKey) -> bytes:
    pub = key.public_key() if isinstance(key, Ed25519PrivateKey) else key
    return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def sign(payload: Mapping[str, Any], key: Ed25519PrivateKey, *, prefix: str) -> str:
    if "kid" not in payload:
        raise TokenError("Le champ kid est obligatoire")
    body = b64url_encode(canonical_json(payload))
    signing_input = f"{prefix}.{body}".encode("ascii")
    return f"{prefix}.{body}.{b64url_encode(key.sign(signing_input))}"


def verify(token: str, public_keys: Mapping[str, bytes], *, prefix: str) -> dict[str, Any]:
    """Retourne les données si la signature est valide ; lève TokenError sinon.

    `public_keys` : {kid: clé publique Ed25519 brute (32 octets)}.
    """
    parts = token.strip().split(".")
    if len(parts) != 3 or parts[0] != prefix:
        raise TokenError("Format de jeton invalide")
    try:
        payload = json.loads(b64url_decode(parts[1]))
        signature = b64url_decode(parts[2])
    except (ValueError, json.JSONDecodeError) as exc:
        raise TokenError("Jeton illisible") from exc
    if not isinstance(payload, dict):
        raise TokenError("Jeton illisible")
    raw_key = public_keys.get(str(payload.get("kid")))
    if raw_key is None:
        raise TokenError("Clé de signature inconnue")
    try:
        Ed25519PublicKey.from_public_bytes(raw_key).verify(
            signature, f"{parts[0]}.{parts[1]}".encode("ascii")
        )
    except InvalidSignature as exc:
        raise TokenError("Signature invalide") from exc
    return payload
