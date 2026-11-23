"use client";
// Billets d'une commande : suivi du paiement, puis billets à QR code, gardés sur l'appareil
// pour être présentés à l'entrée même sans connexion.
import { useBrandLogo } from "@/lib/brand";
import { BrandLogo } from "@/components/BrandLogo";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { MatchHero } from "@/components/MatchHero";
import { formatFcfa } from "@/lib/format";
import { type CachedOrder, cachedOrder, cacheOrder, rememberOrder, savedOrders, svgDataUrl } from "@/lib/my-tickets";
import type { TicketOrder } from "@/lib/types";

export function OrderView({ reference }: { reference: string }) {
  return (
    <Suspense>
      <View reference={reference} />
    </Suspense>
  );
}

function View({ reference }: { reference: string }) {
  const params = useSearchParams();
  const logo = useBrandLogo();
  const [key, setKey] = useState<string | null>(params.get("k"));
  const [data, setData] = useState<CachedOrder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);

  // Clé du lien, ou à défaut celle gardée sur cet appareil ; copie locale affichée d'abord
  useEffect(() => {
    Promise.resolve().then(() => {
      const k = params.get("k") ?? savedOrders().find((o) => o.reference === reference)?.key ?? null;
      setKey(k);
      const cached = cachedOrder(reference);
      if (cached) setData(cached);
      if (!k && !cached) setError("Lien incomplet : ouvrez le lien reçu par SMS.");
    });
  }, [params, reference]);

  const load = useCallback(async () => {
    if (!key) return;
    try {
      const res = await fetch(`/api/v1/tickets/orders/${encodeURIComponent(reference)}?k=${encodeURIComponent(key)}`, { cache: "no-store" });
      if (res.status === 404) {
        setError("Commande introuvable : vérifiez le lien reçu par SMS.");
        return;
      }
      if (!res.ok) throw new Error();
      const order = (await res.json()) as TicketOrder;
      const prev = cachedOrder(reference);
      const qr: Record<string, string> = { ...(prev?.qr ?? {}) };
      for (const t of order.tickets) {
        if (qr[t.code]) continue;
        const svg = await fetch(
          `/api/v1/tickets/orders/${encodeURIComponent(reference)}/tickets/${encodeURIComponent(t.code)}.svg?k=${encodeURIComponent(key)}`,
        );
        if (svg.ok) qr[t.code] = await svg.text();
      }
      const next = { order, qr, savedAt: Date.now() };
      cacheOrder(reference, next);
      rememberOrder({ reference, key, savedAt: prev?.savedAt ?? Date.now(), label: `${order.match.home?.short_name} – ${order.match.away?.short_name}` });
      setData(next);
      setOffline(false);
      setError(null);
    } catch {
      setOffline(true);
    }
  }, [key, reference]);

  useEffect(() => {
    Promise.resolve().then(load);
  }, [load]);

  // Paiement en cours : on interroge jusqu'à la confirmation de l'opérateur
  const pending = data?.order.state === "pending";
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [pending, load]);

  if (error && !data) {
    return (
      <div className="rounded-xl bg-red-50 dark:bg-red-950/40 p-5 text-lds-red">
        <p className="font-semibold">{error}</p>
        <Link href="/billets" className="mt-2 inline-block text-sm underline">
          Mes billets sur cet appareil
        </Link>
      </div>
    );
  }
  if (!data) return <p className="text-subtle">Chargement de vos billets…</p>;
  const o = data.order;

  return (
    <div className="space-y-5">
      <title>{`Billets ${o.reference} · LDS Connect`}</title>
      <div className="flex items-center justify-between gap-2 print:hidden">
        <Link href="/billets" className="text-sm text-lds-green underline">
          ← Mes billets
        </Link>
        {offline && <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">Hors connexion · copie enregistrée</span>}
      </div>

      {o.state === "pending" && (
        <div role="status" className="flex items-center gap-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 p-5 text-amber-950 dark:text-amber-100">
          <span aria-hidden className="h-8 w-8 animate-spin rounded-full border-4 border-amber-300 border-t-amber-700" />
          <div>
            <p className="text-lg font-bold">Paiement en attente de confirmation…</p>
            <p className="text-sm">Validez le paiement sur votre téléphone. Cette page se met à jour toute seule.</p>
          </div>
        </div>
      )}
      {(o.state === "failed" || o.state === "expired") && (
        <div role="alert" className="rounded-xl bg-red-50 dark:bg-red-950/40 p-5 text-lds-red">
          <p className="text-lg font-bold">{o.state === "failed" ? "Le paiement n'a pas abouti." : "Le délai de paiement est dépassé."}</p>
          <p className="text-sm text-muted">Aucun billet n&apos;a été émis. Vous pouvez recommencer votre achat.</p>
          <Link href={`/billetterie/${o.match.id}`} className="mt-3 inline-block rounded-lg bg-lds-green px-4 py-2 font-semibold text-white">
            Recommencer
          </Link>
        </div>
      )}
      {o.state === "cancelled" && (
        <div role="alert" className="rounded-xl bg-red-50 dark:bg-red-950/40 p-5 text-lds-red">
          <p className="text-lg font-bold">Commande annulée : il ne restait plus de places.</p>
          <p className="text-sm text-muted">Votre paiement vous sera remboursé. Référence à rappeler : {o.reference}</p>
        </div>
      )}

      {o.state === "paid" && (
        <div className="rounded-xl bg-qualify p-4 text-heading print:hidden">
          <p className="text-lg font-bold">C&apos;est payé ! Voici vos {o.tickets.length} billet(s).</p>
          <p className="text-sm">
            Ils restent disponibles sur ce téléphone, même sans connexion. Un QR code = une entrée. Lien également envoyé par SMS au{" "}
            {o.phone_hint}.
          </p>
        </div>
      )}

      {o.tickets.length > 0 ? (
        <ul className="grid gap-5 md:grid-cols-2">
          {o.tickets.map((t, i) => (
            <li key={t.code} className="break-inside-avoid">
              <article aria-label={`Billet ${t.code}`} className="overflow-hidden rounded-2xl bg-surface shadow-lg ring-1 ring-line">
                <MatchHero match={o.match} compact />
                <div className="relative flex flex-col items-center gap-2 border-t-2 border-dashed border-line p-5">
                  <BrandLogo logoUrl={logo} size="md" className="absolute right-4 top-4 shadow-none ring-1 ring-line" />
                  <span aria-hidden className="absolute -left-3 -top-3 h-6 w-6 rounded-full bg-canvas" />
                  <span aria-hidden className="absolute -right-3 -top-3 h-6 w-6 rounded-full bg-canvas" />
                  <p className="text-xs uppercase tracking-widest text-subtle">
                    Billet {i + 1}/{o.tickets.length}
                  </p>
                  <p className="text-2xl font-black text-heading">{t.type_name}</p>
                  <div className="relative">
                    {data.qr[t.code] ? (
                      // eslint-disable-next-line @next/next/no-img-element -- QR SVG gardé sur l'appareil
                      <img src={svgDataUrl(data.qr[t.code])} alt={`QR code du billet ${t.code}`} className="h-56 w-56 rounded-lg bg-white p-1" />
                    ) : (
                      <div className="h-56 w-56 animate-pulse rounded bg-soft" />
                    )}
                    {t.status !== "valid" && (
                      <span className="absolute inset-0 flex items-center justify-center bg-white/85 text-xl font-black uppercase text-lds-red">
                        {t.status === "used" ? "Déjà utilisé" : "Annulé"}
                      </span>
                    )}
                  </div>
                  <p className="font-mono text-lg tracking-wider">{t.code}</p>
                  <p className="text-sm text-muted">{o.buyer_name}</p>
                </div>
              </article>
            </li>
          ))}
        </ul>
      ) : (
        o.state !== "paid" && <MatchHero match={o.match} compact />
      )}

      <dl className="grid grid-cols-2 gap-2 rounded-xl bg-surface p-4 text-sm shadow-sm sm:grid-cols-4">
        <div>
          <dt className="text-xs text-subtle">Commande</dt>
          <dd className="font-mono">{o.reference}</dd>
        </div>
        <div>
          <dt className="text-xs text-subtle">Places</dt>
          <dd>
            {o.quantity} × {o.type_name}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-subtle">Montant</dt>
          <dd className="font-semibold">{formatFcfa(o.amount_fcfa)}</dd>
        </div>
        <div>
          <dt className="text-xs text-subtle">Acheteur</dt>
          <dd>{o.buyer_name}</dd>
        </div>
      </dl>
      {o.state === "paid" && (
        <button type="button" onClick={() => window.print()} className="rounded-lg border border-line bg-surface px-4 py-2 text-sm print:hidden">
          Imprimer les billets
        </button>
      )}
    </div>
  );
}
