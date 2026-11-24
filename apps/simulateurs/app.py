"""Simulateurs locaux de LDS Connect : passerelle SMS et agrégateur de paiement factices.

Aucun appel vers un service réel. Les SMS « envoyés » sont conservés en mémoire et visibles
sur http://localhost:8090. Les paiements sont confirmés ou refusés à la main depuis cette page.
"""

import hashlib
import hmac
import html
import json
import os
import uuid
from collections import deque
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Simulateurs LDS Connect (SMS + paiement)")

SMS_INBOX: deque[dict] = deque(maxlen=500)
PAYMENTS: dict[str, dict] = {}

# Même secret que l'API (PAYMENT_WEBHOOK_SECRET) : les notifications sont signées comme le
# ferait un agrégateur réel (HMAC-SHA256 du corps brut, en-tête X-LDS-Signature).
WEBHOOK_SECRET = os.environ.get("PAYMENT_WEBHOOK_SECRET", "")


class SmsIn(BaseModel):
    to: str
    message: str
    sender: str = "LDS"


class PaymentIn(BaseModel):
    reference: str
    amount: int
    currency: str = "XOF"
    phone: str | None = None
    callback_url: str
    return_url: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/sms/send")
def send_sms(sms: SmsIn) -> dict:
    msg_id = str(uuid.uuid4())
    SMS_INBOX.appendleft(
        {"id": msg_id, "at": datetime.now(UTC).isoformat(), **sms.model_dump()}
    )
    return {"id": msg_id, "status": "delivered"}


@app.get("/sms/messages")
def list_sms(to: str | None = None) -> list[dict]:
    return [m for m in SMS_INBOX if to is None or m["to"] == to]


@app.post("/payment/init")
def init_payment(p: PaymentIn) -> dict:
    pid = str(uuid.uuid4())
    PAYMENTS[pid] = {"id": pid, "status": "pending", **p.model_dump()}
    return {"id": pid, "status": "pending", "checkout_url": f"/payment/{pid}"}


@app.get("/payment/{pid}", response_class=HTMLResponse)
def checkout(pid: str) -> str:
    p = PAYMENTS.get(pid)
    if not p:
        raise HTTPException(404)
    amount = f"{p['amount']:,}".replace(",", " ")
    phone = html.escape(p.get("phone") or "")
    done = p["status"] != "pending"
    buttons = (
        f"<p class='st'>Statut : <b>{html.escape(p['status'])}</b></p>"
        if done
        else f"""<form method="post" action="/payment/{pid}/success">
        <button class="ok">Confirmer le paiement</button></form>
        <form method="post" action="/payment/{pid}/fail"><button class="ko">Refuser</button></form>"""
    )
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Paiement simulé</title><style>
    body{{font-family:system-ui,sans-serif;background:#f4f4f5;margin:0;padding:1.5rem}}
    .c{{max-width:380px;margin:auto;background:#fff;border-radius:16px;padding:1.5rem;
    box-shadow:0 4px 20px #0001}}.tag{{background:#fef3c7;color:#92400e;font-size:.75rem;
    padding:.25rem .5rem;border-radius:99px;font-weight:600}}h1{{font-size:1.2rem}}
    .amt{{font-size:2rem;font-weight:800;margin:.5rem 0}}button{{width:100%;padding:.9rem;
    border:0;border-radius:12px;font-size:1rem;font-weight:700;margin-top:.6rem;cursor:pointer}}
    .ok{{background:#15803d;color:#fff}}.ko{{background:#e4e4e7}}.m{{color:#52525b;font-size:.9rem}}
    </style></head><body><div class="c"><span class="tag">SIMULATEUR — aucun argent réel</span>
    <h1>Paiement mobile money</h1><p class="m">Référence {html.escape(p["reference"])}</p>
    <p class="amt">{amount} FCFA</p><p class="m">Débit du numéro {phone}</p>
    {buttons}</div></body></html>"""


@app.post("/payment/{pid}/{outcome}")
def settle(pid: str, outcome: str):
    p = PAYMENTS.get(pid)
    if not p or outcome not in {"success", "fail"}:
        raise HTTPException(404)
    p["status"] = "succeeded" if outcome == "success" else "failed"
    try:
        body = json.dumps(
            {"id": pid, "reference": p["reference"], "status": p["status"], "amount": p["amount"]}
        ).encode()
        headers = {"content-type": "application/json"}
        if WEBHOOK_SECRET:
            digest = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
            headers["x-lds-signature"] = f"sha256={digest}"
        r = httpx.post(p["callback_url"], content=body, headers=headers, timeout=5)
        if r.status_code >= 400:
            p["callback_error"] = f"HTTP {r.status_code} : {r.text[:200]}"
    except httpx.HTTPError as exc:
        p["callback_error"] = str(exc)
    return RedirectResponse(p.get("return_url") or f"/payment/{pid}", status_code=303)


@app.get("/", response_class=HTMLResponse)
def inbox() -> str:
    rows = "".join(
        f"<tr><td>{html.escape(m['at'][:19])}</td><td>{html.escape(m['to'])}</td>"
        f"<td>{html.escape(m['message'])}</td></tr>"
        for m in SMS_INBOX
    )
    pays = "".join(
        f"<tr><td><a href='/payment/{p['id']}'>{html.escape(p['reference'])}</a></td>"
        f"<td>{p['amount']}</td><td>{p['status']}</td></tr>"
        for p in PAYMENTS.values()
    )
    return f"""<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">
    <title>Simulateurs LDS</title></head><body style="font-family:sans-serif;margin:2rem">
    <h1>SMS simulés</h1><table border=1 cellpadding=4><tr><th>Date</th><th>Destinataire</th>
    <th>Message</th></tr>{rows}</table>
    <h1>Paiements simulés</h1><table border=1 cellpadding=4><tr><th>Référence</th>
    <th>Montant</th><th>Statut</th></tr>{pays}</table></body></html>"""
