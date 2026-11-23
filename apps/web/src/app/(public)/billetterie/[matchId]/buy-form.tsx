"use client";
// Achat sans compte : catégorie, quantité, nom et numéro, puis paiement mobile money.
import { useState } from "react";
import { formatDateTime, formatFcfa } from "@/lib/format";
import { rememberOrder } from "@/lib/my-tickets";
import type { OrderCreated, TicketType } from "@/lib/types";

export function BuyForm({ types }: { types: TicketType[] }) {
  const firstOnSale = types.find((t) => t.state === "on_sale");
  const [typeId, setTypeId] = useState(firstOnSale?.id ?? "");
  const [qty, setQty] = useState(1);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const tt = types.find((t) => t.id === typeId);
  const max = tt ? Math.min(tt.max_per_order, tt.remaining ?? tt.max_per_order) : 1;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!tt) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/tickets/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_type_id: tt.id, quantity: qty, buyer_name: name, phone }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) throw new Error("Trop de commandes : patientez quelques minutes.");
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Commande impossible, réessayez.");
      const created = data as OrderCreated;
      rememberOrder({ reference: created.reference, key: created.access_key, savedAt: Date.now() });
      window.location.href = created.checkout_url; // page de paiement de l'opérateur
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pas de connexion : vérifiez votre réseau.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <fieldset className="space-y-2">
        <legend className="mb-2 text-lg font-bold text-green-900">1. Choisissez vos places</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {types.map((t) => {
            const on = t.id === typeId;
            const available = t.state === "on_sale";
            return (
              <label
                key={t.id}
                className={`relative flex cursor-pointer flex-col gap-1 rounded-xl border-2 bg-white p-4 transition ${
                  on ? "border-lds-green shadow-md" : "border-stone-200"
                } ${available ? "" : "cursor-not-allowed opacity-60"}`}
              >
                <input
                  type="radio"
                  name="type"
                  className="sr-only"
                  disabled={!available}
                  checked={on}
                  onChange={() => {
                    setTypeId(t.id);
                    setQty(1);
                  }}
                />
                <span className="flex items-baseline justify-between gap-2">
                  <span className="text-lg font-bold">{t.name}</span>
                  <span className="text-xl font-black text-lds-green">{formatFcfa(t.price_fcfa)}</span>
                </span>
                {t.description && <span className="text-sm text-stone-600">{t.description}</span>}
                <span className="text-xs text-stone-500">
                  {t.state === "on_sale" && (t.remaining != null && t.remaining < 50 ? `Plus que ${t.remaining} places !` : "Places disponibles")}
                  {t.state === "sold_out" && "Complet"}
                  {t.state === "not_open" && `Ouverture des ventes le ${formatDateTime(t.sales_open_at)}`}
                  {t.state === "closed" && "Ventes closes"}
                </span>
                {on && <span className="absolute right-3 top-3 hidden h-3 w-3 rounded-full bg-lds-green sm:block" aria-hidden />}
              </label>
            );
          })}
        </div>
      </fieldset>

      {tt && tt.state === "on_sale" && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-4 shadow-sm">
            <span className="font-semibold">Nombre de billets</span>
            <div className="flex items-center gap-3">
              <button type="button" aria-label="Un billet de moins" onClick={() => setQty(Math.max(1, qty - 1))} className="h-10 w-10 rounded-full border-2 border-stone-300 text-xl font-bold">
                −
              </button>
              <output aria-label="Nombre de billets" className="w-8 text-center text-2xl font-black tabular-nums">
                {qty}
              </output>
              <button type="button" aria-label="Un billet de plus" onClick={() => setQty(Math.min(max, qty + 1))} className="h-10 w-10 rounded-full border-2 border-stone-300 text-xl font-bold">
                +
              </button>
            </div>
          </div>

          <fieldset className="space-y-3">
            <legend className="mb-2 text-lg font-bold text-green-900">2. Vos coordonnées</legend>
            <label className="block text-sm font-medium">
              Nom et prénom
              <input required minLength={2} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2.5 text-base" />
            </label>
            <label className="block text-sm font-medium">
              Numéro mobile money
              <input
                required
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="70 12 34 56"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2.5 text-base"
              />
            </label>
            <p className="text-xs text-stone-500">
              Numéros du Burkina Faso. Vous recevrez par SMS le lien de vos billets. Votre numéro ne sert qu&apos;à cette commande.
            </p>
          </fieldset>

          <div className="sticky bottom-0 -mx-4 border-t border-stone-200 bg-white/95 px-4 py-3 backdrop-blur sm:static sm:mx-0 sm:rounded-xl sm:border sm:shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-stone-500">Total</p>
                <p className="text-2xl font-black text-green-900">{formatFcfa(tt.price_fcfa * qty)}</p>
              </div>
              <button type="submit" disabled={busy} className="rounded-xl bg-lds-green px-6 py-3 text-lg font-bold text-white shadow disabled:opacity-60">
                {busy ? "Un instant…" : "Payer par mobile money"}
              </button>
            </div>
            <p className="mt-1 text-xs text-stone-500">Vos places sont réservées 15 minutes pendant le paiement.</p>
          </div>
        </>
      )}

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-lds-red">
          {error}
        </p>
      )}
    </form>
  );
}
