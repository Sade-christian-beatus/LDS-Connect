"""Paiement mobile money derrière une interface (agrégateur à définir par la Ligue).

Désactivé par défaut (PAYMENT_PROVIDER=disabled). En local : simulateur (apps/simulateurs)
qui rappelle l'URL de notification comme le ferait un agrégateur réel.
"""

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import httpx

from lds_api.core.config import get_settings


class PaymentDisabled(RuntimeError):
    pass


class InvalidSignature(RuntimeError):
    """Notification non signée ou signature fausse : elle ne vient pas de l'agrégateur."""


SIGNATURE_HEADER = "x-lds-signature"


def sign(secret: str, body: bytes) -> str:
    """Signature d'une notification : « sha256=<hmac hexadécimal du corps brut> »."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, body: bytes, headers: Mapping[str, str]) -> None:
    """Vérifie la signature HMAC du corps brut (comparaison en temps constant)."""
    received = headers.get(SIGNATURE_HEADER) or ""
    if not hmac.compare_digest(received.encode(), sign(secret, body).encode()):
        raise InvalidSignature("Signature de notification invalide")


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

    def parse_notification(self, body: bytes, headers: Mapping[str, str]) -> PaymentNotification:
        """Vérifie la signature de la notification (corps brut) puis la décode.

        Lève `InvalidSignature` si elle ne vient pas de l'agrégateur, `ValueError`/`KeyError`
        si elle est illisible.
        """
        ...


class SimulatorPaymentProvider:
    name = "simulator"

    def __init__(
        self, base_url: str, client: httpx.Client | None = None, webhook_secret: str = ""
    ) -> None:
        self._base = base_url.rstrip("/")
        # Vide en développement uniquement (refusé au démarrage en production)
        self._secret = webhook_secret
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

    def parse_notification(self, body: bytes, headers: Mapping[str, str]) -> PaymentNotification:
        # Le simulateur signe comme le fera le connecteur réel : HMAC-SHA256 du corps brut.
        if self._secret:
            verify_signature(self._secret, body, headers)
        payload = json.loads(body)
        return PaymentNotification(
            provider_reference=str(payload["id"]),
            reference=str(payload["reference"]),
            succeeded=payload.get("status") == "succeeded",
            amount=int(payload["amount"]),
        )


def get_payment_provider() -> PaymentProvider:
    s = get_settings()
    if s.payment_provider == "simulator":
        return SimulatorPaymentProvider(
            s.payment_simulator_url, webhook_secret=s.payment_webhook_secret.get_secret_value()
        )
    raise PaymentDisabled("Paiement désactivé (PAYMENT_PROVIDER=disabled)")
