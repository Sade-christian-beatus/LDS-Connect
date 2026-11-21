"""Utilitaires de texte."""

import re
import unicodedata


def slugify(value: str) -> str:
    """« Nando Bõn-yẽesã » → « nando-bon-yeesa »."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value
