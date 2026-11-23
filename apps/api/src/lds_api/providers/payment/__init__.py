"""Paiement mobile money derrière une interface (agrégateur à définir par la Ligue).

Désactivé par défaut (PAYMENT_PROVIDER=disabled). En local : simulateur (apps/simulateurs)
qui rappelle l'URL de notification comme le ferait un agrégateur réel.
"""

from dataclasses import dataclass
from typing import Protocol

import httpx

from lds_api.core.config import get_settings


class PaymentDisabled(RuntimeError):
    pass


@dataclass(frozen=True)
class PaymentSession:
    provider_reference: str
    checkout_url: str


@dataclass(frozen=True)
class PaymentNotification:
    provider_reference: str
    reference: str
    succeeded: bool
    amount: int


class PaymentProvider(Protocol):
    name: str

    def create(
        self,
        *,
        reference: str,
        amount_fcfa: int,
        phone: str | None,
        callback_url: str,
        return_url: str | None = None,
    ) -> PaymentSession:
        """`return_url` : page où l'agrégateur renvoie l'acheteur après le paiement."""
        ...

    def parse_notification(self, payload: dict) -> PaymentNotification:
        """Valide et décode la notification de l'agrégateur (signature à vérifier ici)."""
        ...


class SimulatorPaymentProvider:
    name = "simulator"

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=base_url, timeout=5)

    def create(
        self, *, reference, amount_fcfa, phone, callback_url, return_url=None
    ) -> PaymentSession:
        r = self._client.post(
            "/payment/init",
            json={
                "reference": reference,
                "amount": amount_fcfa,
                "currency": "XOF",
                "phone": phone,
                "callback_url": callback_url,
                "return_url": return_url,
            },
        )
        r.raise_for_status()
        data = r.json()
        return PaymentSession(data["id"], f"{self._base}{data['checkout_url']}")

    def parse_notification(self, payload: dict) -> PaymentNotification:
        # Le simulateur ne signe pas ses notifications : un connecteur réel DOIT vérifier
        # la signature de l'agrégateur avant d'accepter le paiement.
        return PaymentNotification(
            provider_reference=str(payload["id"]),
            reference=str(payload["reference"]),
            succeeded=payload.get("status") == "succeeded",
            amount=int(payload["amount"]),
        )


def get_payment_provider() -> PaymentProvider:
    s = get_settings()
    if s.payment_provider == "simulator":
        return SimulatorPaymentProvider(s.payment_simulator_url)
    raise PaymentDisabled("Paiement désactivé (PAYMENT_PROVIDER=disabled)")
