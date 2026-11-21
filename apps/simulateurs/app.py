"""Simulateurs locaux de LDS Connect : passerelle SMS et agrégateur de paiement factices.

Aucun appel vers un service réel. Les SMS « envoyés » sont conservés en mémoire et visibles
sur http://localhost:8090. Les paiements sont confirmés ou refusés à la main depuis cette page.
"""

import html
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
    return f"""<html><body style="font-family:sans-serif;max-width:420px;margin:2rem auto">
    <h2>Paiement simulé</h2><p>Référence : {html.escape(p['reference'])}<br>
    Montant : {p['amount']} {html.escape(p['currency'])}<br>Statut : {p['status']}</p>
    <form method="post" action="/payment/{pid}/success"><button>Payer</button></form>
    <form method="post" action="/payment/{pid}/fail"><button>Refuser</button></form>
    </body></html>"""


@app.post("/payment/{pid}/{outcome}")
def settle(pid: str, outcome: str):
    p = PAYMENTS.get(pid)
    if not p or outcome not in {"success", "fail"}:
        raise HTTPException(404)
    p["status"] = "succeeded" if outcome == "success" else "failed"
    try:
        httpx.post(p["callback_url"], json={"id": pid, "reference": p["reference"],
                                            "status": p["status"], "amount": p["amount"]},
                   timeout=5)
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
