"""Types de colonnes personnalisés."""

from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

from lds_api.core.crypto import get_cipher


class EncryptedString(TypeDecorator[str]):
    """Chaîne chiffrée en AES-256-GCM de façon transparente (stockée en BYTEA)."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> bytes | None:
        if value is None:
            return None
        return get_cipher().encrypt(value)

    def process_result_value(self, value: bytes | None, dialect) -> str | None:
        if value is None:
            return None
        return get_cipher().decrypt(bytes(value))
