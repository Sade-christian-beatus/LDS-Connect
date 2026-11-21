"""Envoi de SMS derrière une interface : simulateur local par défaut.

Un connecteur réel (opérateur ou agrégateur retenu par la Ligue) s'ajoute en implémentant
`SmsProvider` puis en l'enregistrant dans `get_sms_provider` — aucun autre code ne change.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from lds_api.core.config import get_settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmsResult:
    provider_id: str
    accepted: bool


class SmsProvider(Protocol):
    def send(self, to: str, message: str) -> SmsResult: ...


class SimulatorSmsProvider:
    """Passerelle factice (apps/simulateurs) : les SMS s'affichent sur http://localhost:8090."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=5)

    def send(self, to: str, message: str) -> SmsResult:
        r = self._client.post("/sms/send", json={"to": to, "message": message, "sender": "LDS"})
        r.raise_for_status()
        return SmsResult(provider_id=r.json()["id"], accepted=True)


class ConsoleSmsProvider:
    """Affiche le SMS dans les journaux (développement sans simulateur)."""

    def send(self, to: str, message: str) -> SmsResult:
        log.info("SMS (console) vers %s : %s", to[:-4] + "****", message)
        return SmsResult(provider_id="console", accepted=True)


def get_sms_provider() -> SmsProvider:
    s = get_settings()
    if s.sms_provider == "simulator":
        return SimulatorSmsProvider(s.sms_simulator_url)
    return ConsoleSmsProvider()
