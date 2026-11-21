"""Chiffrement des données personnelles au repos et index aveugles.

- AES-256-GCM : chaque valeur est chiffrée avec un nonce aléatoire de 12 octets.
  Format stocké : version (1 octet) || nonce (12) || texte chiffré + tag (16).
- Index aveugle : HMAC-SHA256 de la valeur normalisée, avec une clé distincte. Il permet
  l'unicité (ex. un vote par numéro) et la recherche exacte sans déchiffrer la base.
"""

import base64
import hashlib
import hmac
import os
import re
import unicodedata
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from lds_api.core.config import get_settings

_VERSION = b"\x01"


class CryptoConfigError(RuntimeError):
    pass


def _decode_key(raw: str, name: str) -> bytes:
    if not raw:
        raise CryptoConfigError(f"{name} n'est pas défini (voir .env.example, `make keys`).")
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise CryptoConfigError(f"{name} doit faire 32 octets encodés en base64.")
    return key


class FieldCipher:
    def __init__(self, key: bytes) -> None:
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: str) -> bytes:
        nonce = os.urandom(12)
        return _VERSION + nonce + self._aead.encrypt(nonce, plaintext.encode("utf-8"), None)

    def decrypt(self, blob: bytes) -> str:
        if blob[:1] != _VERSION:
            raise ValueError("Version de chiffrement inconnue")
        nonce, ct = blob[1:13], blob[13:]
        return self._aead.decrypt(nonce, ct, None).decode("utf-8")


@lru_cache
def get_cipher() -> FieldCipher:
    return FieldCipher(
        _decode_key(get_settings().field_encryption_key.get_secret_value(), "FIELD_ENCRYPTION_KEY")
    )


@lru_cache
def _blind_key() -> bytes:
    return _decode_key(get_settings().blind_index_key.get_secret_value(), "BLIND_INDEX_KEY")


def normalize_phone(phone: str) -> str:
    """Normalise un numéro burkinabè au format international +226XXXXXXXX."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 8:
        digits = "226" + digits
    return "+" + digits


def normalize_identifier(value: str) -> str:
    """Normalisation générique (CNIB…) : majuscules, sans accents ni espaces."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[\s\-./]", "", value).upper()


def blind_index(value: str, *, purpose: str) -> str:
    """Empreinte HMAC déterministe ; `purpose` sépare les domaines (phone, cnib…)."""
    msg = f"{purpose}:{value}".encode()
    return hmac.new(_blind_key(), msg, hashlib.sha256).hexdigest()


def phone_index(phone: str) -> str:
    return blind_index(normalize_phone(phone), purpose="phone")


def cnib_index(cnib: str) -> str:
    return blind_index(normalize_identifier(cnib), purpose="cnib")
