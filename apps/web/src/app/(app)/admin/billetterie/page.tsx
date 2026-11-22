"use client";
// Billetterie : catégories de billets par match, suivi des ventes et des entrées.
import { useState } from "react";
import { Badge, Button, Dialog, Field, inputClass, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth";
import { formatDate, formatDateTime, formatFcfa, formatTime, fromLocalInput, SALE_STATE, toLocalInput } from "@/lib/format";
import type { AccessStats, Match, TicketOrderAdmin, TicketTypeAdmin } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function BilletteriePage() {
  return (
    <RequireAuth permission="ticket:manage">
      <Billetterie />
    </RequireAuth>
  );
}

const PRESETS = [
  { name: "Pelouse", price_fcfa: 500, quota: 3000 },
  { name: "Tribune", price_fcfa: 1000, quota: 1500 },
  { name: "Tribune d'honneur", price_fcfa: 5000, quota: 200 },
];

const ORDER_STATE: Record<string, { label: string; tone: "green" | "amber" | "red" | "stone" }> = {
  pending: { label: "Paiement en cours", tone: "amber" },
  paid: { label: "Payée", tone: "green" },
  failed: { label: "Paiement refusé", tone: "red" },
  expired: { label: "Expirée", tone: "stone" },
  cancelled: { label: "Annulée (à rembourser)", tone: "red" },
  refunded: { label: "Remboursée", tone: "stone" },
};

type Form = {
  id?: string;
  name: string;
  description: string;
  price_fcfa: string;
  quota: string;
  max_per_order: string;
  sales_open_at: string;
  sales_close_at: string;
};
const EMPTY: Form = { name: "", description: "", price_fcfa: "", quota: "", max_per_order: "10", sales_open_at: "", sales_close_at: "" };

function Billetterie() {
  const { api } = useAuth();
  const { data: matches } = useApi<Match[]>("/admin/ticketing/matches");
  const [matchId, setMatchId] = useState("");
  const { data: types, reload: reloadTypes } = useApi<TicketTypeAdmin[]>(matchId ? `/admin/ticket-types?match_id=${matchId}` : null);
  const [stateFilter, setStateFilter] = useState("");
  const { data: orders, reload: reloadOrders } = useApi<TicketOrderAdmin[]>(
    matchId ? `/admin/orders?match_id=${matchId}${stateFilter ? `&state=${stateFilter}` : ""}` : null,
  );
  const { data: stats } = useApi<AccessStats>(matchId ? `/access/matches/${matchId}/stats` : null);
  const [form, setForm] = useState<Form | null>(null);
  const [cancel, setCancel] = useState<{ code: string; reason: string } | null>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const match = matches?.find((m) => m.id === matchId);

  const fail = (e: unknown) => setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    const body = {
      name: form.name,
      description: form.description || null,
      price_fcfa: Number(form.price_fcfa),
      quota: form.quota ? Number(form.quota) : null,
      max_per_order: Number(form.max_per_order),
      sales_open_at: fromLocalInput(form.sales_open_at),
      sales_close_at: fromLocalInput(form.sales_close_at),
    };
    try {
      if (form.id) await api(`/admin/ticket-types/${form.id}`, { method: "PATCH", body: JSON.stringify(body) });
      else await api("/admin/ticket-types", { method: "POST", body: JSON.stringify({ ...body, match_id: matchId }) });
      setForm(null);
      setNotice({ tone: "ok", text: form.id ? "Catégorie modifiée" : "Catégorie ajoutée : les billets sont en vente" });
      reloadTypes();
    } catch (err) {
      fail(err);
    }
  }

  async function toggle(t: TicketTypeAdmin) {
    try {
      await api(`/admin/ticket-types/${t.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !t.is_active }) });
      reloadTypes();
    } catch (err) {
      fail(err);
    }
  }

  async function confirmCancel(e: React.FormEvent) {
    e.preventDefault();
    if (!cancel) return;
    try {
      await api(`/admin/tickets/${cancel.code}/cancel`, { method: "POST", body: JSON.stringify({ reason: cancel.reason }) });
      setCancel(null);
      setNotice({ tone: "ok", text: `Billet ${cancel.code} annulé : il sera refusé à l'entrée` });
      reloadOrders();
      reloadTypes();
    } catch (err) {
      fail(err);
    }
  }

  const sold = types?.reduce((n, t) => n + t.sold, 0) ?? 0;
  const revenue = types?.reduce((n, t) => n + t.revenue_fcfa, 0) ?? 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-green-900">Billetterie</h1>
          <p className="text-sm text-stone-600">Catégories de billets par match, ventes mobile money et entrées au stade.</p>
        </div>
        <label className="text-sm">
          Match
          <select aria-label="Match" className={`${inputClass} min-w-72`} value={matchId} onChange={(e) => setMatchId(e.target.value)}>
            <option value="">— choisir un match à venir —</option>
            {matches?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.home?.short_name ?? "?"} – {m.away?.short_name ?? "?"} · {formatDate(m.kickoff_at)} {formatTime(m.kickoff_at)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      {!matchId && <p className="rounded-lg border border-dashed border-stone-300 p-6 text-center text-stone-600">Choisissez un match pour gérer ses billets.</p>}

      {match && (
        <>
          <section className="grid gap-3 sm:grid-cols-4">
            <Kpi label="Billets vendus" value={sold.toLocaleString("fr-FR")} />
            <Kpi label="Recettes" value={formatFcfa(revenue)} />
            <Kpi label="Entrées enregistrées" value={stats ? (stats.admitted + stats.accreditations_admitted).toLocaleString("fr-FR") : "—"} />
            <Kpi label="Doubles entrées refusées" value={stats ? String(stats.duplicates) : "—"} />
          </section>

          <section className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">Catégories de billets</h2>
              <div className="flex flex-wrap gap-2">
                {PRESETS.filter((p) => !types?.some((t) => t.name === p.name)).map((p) => (
                  <Button key={p.name} variant="secondary" onClick={() => setForm({ ...EMPTY, name: p.name, price_fcfa: String(p.price_fcfa), quota: String(p.quota) })}>
                    + {p.name}
                  </Button>
                ))}
                <Button onClick={() => setForm({ ...EMPTY })}>+ Nouvelle catégorie</Button>
              </div>
            </div>
            {types && types.length === 0 && <p className="text-sm text-stone-600">Aucun billet en vente pour ce match.</p>}
            {types && types.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-left text-xs uppercase text-stone-500">
                    <tr>
                      <th className="py-2">Catégorie</th>
                      <th className="text-right">Prix</th>
                      <th className="text-right">Vendus</th>
                      <th className="text-right">Réservés</th>
                      <th className="text-right">Restants</th>
                      <th className="text-right">Recettes</th>
                      <th className="pl-3">Ventes</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {types.map((t) => {
                      const st = SALE_STATE[t.state];
                      return (
                        <tr key={t.id}>
                          <td className="py-2">
                            <span className="font-medium">{t.name}</span>
                            {t.description && <span className="block text-xs text-stone-500">{t.description}</span>}
                          </td>
                          <td className="text-right">{formatFcfa(t.price_fcfa)}</td>
                          <td className="text-right font-semibold">{t.sold}</td>
                          <td className="text-right text-stone-500">{t.reserved}</td>
                          <td className="text-right">{t.remaining ?? "∞"}</td>
                          <td className="text-right">{formatFcfa(t.revenue_fcfa)}</td>
                          <td className="pl-3">
                            <Badge tone={st.tone}>{st.label}</Badge>
                          </td>
                          <td className="space-x-2 whitespace-nowrap text-right">
                            <button
                              type="button"
                              className="text-xs underline"
                              onClick={() =>
                                setForm({
                                  id: t.id,
                                  name: t.name,
                                  description: t.description ?? "",
                                  price_fcfa: String(t.price_fcfa),
                                  quota: t.quota ? String(t.quota) : "",
                                  max_per_order: String(t.max_per_order),
                                  sales_open_at: toLocalInput(t.sales_open_at),
                                  sales_close_at: toLocalInput(t.sales_close_at),
                                })
                              }
                            >
                              Modifier
                            </button>
                            <button type="button" className="text-xs underline" onClick={() => toggle(t)}>
                              {t.is_active ? "Suspendre" : "Reprendre"}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-xs text-stone-500">
              Les ventes ferment au coup d&apos;envoi sauf date choisie. Pendant le paiement, les places sont réservées 15 minutes. Le prix
              ne peut plus changer après la première vente.
            </p>
          </section>

          <section className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold">Commandes ({orders?.length ?? 0})</h2>
              <select aria-label="Filtrer les commandes" className={`${inputClass} w-auto`} value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
                <option value="">Toutes</option>
                {Object.entries(ORDER_STATE).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v.label}
                  </option>
                ))}
              </select>
            </div>
            {orders && orders.length === 0 && <p className="text-sm text-stone-600">Aucune commande.</p>}
            <ul className="divide-y divide-stone-100 text-sm">
              {orders?.map((o) => {
                const st = ORDER_STATE[o.state] ?? { label: o.state, tone: "stone" as const };
                return (
                  <li key={o.reference} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
                    <span className="w-36 font-mono text-xs">{o.reference}</span>
                    <span className="min-w-40 flex-1">
                      {o.buyer_name} <span className="text-xs text-stone-500">{o.phone_hint}</span>
                    </span>
                    <span>
                      {o.quantity} × {o.type_name}
                    </span>
                    <span className="w-24 text-right font-semibold">{formatFcfa(o.amount_fcfa)}</span>
                    <span className="text-xs text-stone-500">{formatDateTime(o.paid_at ?? o.created_at)}</span>
                    <Badge tone={st.tone}>{st.label}</Badge>
                    {o.tickets.length > 0 && (
                      <span className="flex w-full flex-wrap gap-1 pl-40">
                        {o.tickets.map((c) => (
                          <button
                            key={c}
                            type="button"
                            title="Annuler ce billet"
                            onClick={() => setCancel({ code: c, reason: "" })}
                            className="rounded border border-stone-200 px-1.5 font-mono text-xs hover:border-lds-red hover:text-lds-red"
                          >
                            {c}
                          </button>
                        ))}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        </>
      )}

      <Dialog open={!!form} title={form?.id ? "Modifier la catégorie" : "Nouvelle catégorie de billets"} onClose={() => setForm(null)}>
        {form && (
          <form onSubmit={save} className="grid gap-3 sm:grid-cols-2">
            <Field label="Nom *">
              <input required minLength={2} className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Prix (FCFA) *">
              <input required type="number" min={0} step={100} className={inputClass} value={form.price_fcfa} onChange={(e) => setForm({ ...form, price_fcfa: e.target.value })} />
            </Field>
            <Field label="Nombre de places" hint="Vide = sans limite">
              <input type="number" min={1} className={inputClass} value={form.quota} onChange={(e) => setForm({ ...form, quota: e.target.value })} />
            </Field>
            <Field label="Maximum par commande">
              <input type="number" min={1} max={50} className={inputClass} value={form.max_per_order} onChange={(e) => setForm({ ...form, max_per_order: e.target.value })} />
            </Field>
            <Field label="Ouverture des ventes" hint="Vide = immédiatement">
              <input type="datetime-local" className={inputClass} value={form.sales_open_at} onChange={(e) => setForm({ ...form, sales_open_at: e.target.value })} />
            </Field>
            <Field label="Fin des ventes" hint="Vide = au coup d'envoi">
              <input type="datetime-local" className={inputClass} value={form.sales_close_at} onChange={(e) => setForm({ ...form, sales_close_at: e.target.value })} />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Description (facultatif)">
                <input className={inputClass} placeholder="Ex. places assises, côté ombre" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </Field>
            </div>
            <div className="flex justify-end gap-2 sm:col-span-2">
              <Button variant="secondary" onClick={() => setForm(null)}>
                Annuler
              </Button>
              <Button type="submit">Enregistrer</Button>
            </div>
          </form>
        )}
      </Dialog>

      <Dialog open={!!cancel} title={`Annuler le billet ${cancel?.code ?? ""}`} onClose={() => setCancel(null)}>
        {cancel && (
          <form onSubmit={confirmCancel} className="space-y-3">
            <p className="text-sm text-stone-600">Le billet sera refusé au contrôle. Le remboursement éventuel se fait hors plateforme.</p>
            <Field label="Motif *">
              <input required minLength={3} className={inputClass} value={cancel.reason} onChange={(e) => setCancel({ ...cancel, reason: e.target.value })} />
            </Field>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setCancel(null)}>
                Retour
              </Button>
              <Button type="submit" variant="danger">
                Annuler le billet
              </Button>
            </div>
          </form>
        )}
      </Dialog>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-3">
      <p className="text-xs uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-green-900">{value}</p>
    </div>
  );
}
