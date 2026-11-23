import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { TeamBadge } from "@/components/TeamBadge";
import { formatDate, formatFcfa, formatTime } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { MatchTickets } from "@/lib/types";

export const metadata: Metadata = { title: "Billetterie" };

export default function BilletteriePage() {
  return (
    <>
      <PageHeader kicker="Mobile money" title="Billetterie">
        Achetez vos billets en ligne et payez par mobile money. Le billet s&apos;affiche sur votre téléphone : présentez le QR code à
        l&apos;entrée du stade, même sans connexion.{" "}
        <Link href="/billets" className="font-semibold text-lds-green underline dark:text-green-300">
          Retrouver mes billets
        </Link>
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement des matchs…</p>}>
        <OnSale />
      </Suspense>
    </>
  );
}

async function OnSale() {
  const list = await apiGet<MatchTickets[]>("/tickets/matches");
  if (list.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-line bg-surface p-8 text-center text-muted">
        Aucun billet en vente pour le moment. Revenez avant les prochains matchs !
      </p>
    );
  }
  return (
    <ul className="grid gap-4 md:grid-cols-2">
      {list.map(({ match: m, types }) => {
        const prices = types.filter((t) => t.state === "on_sale").map((t) => t.price_fcfa);
        const soldOut = types.length > 0 && types.every((t) => t.state === "sold_out");
        return (
          <li key={m.id}>
            <Link
              href={`/billetterie/${m.id}`}
              className="group block overflow-hidden rounded-2xl border border-line bg-surface shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="flex items-center justify-between bg-pitch px-4 py-2 text-xs font-semibold uppercase tracking-wide text-yellow-300">
                <span>{m.phase === "group" ? `Poule ${m.pool_code} · J${m.round_number}` : "Phase finale"}</span>
                <span className="text-green-100">
                  {formatDate(m.kickoff_at)} · {formatTime(m.kickoff_at)}
                </span>
              </div>
              <div className="flex items-center gap-3 px-4 py-4">
                {m.home && <TeamBadge team={m.home} />}
                <span className="flex-1 text-center text-lg font-bold leading-tight">
                  {m.home?.short_name ?? "?"} <span className="text-subtle">vs</span> {m.away?.short_name ?? "?"}
                </span>
                {m.away && <TeamBadge team={m.away} />}
              </div>
              <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
                <span className="text-muted">{m.venue ? `${m.venue.name}, ${m.venue.city}` : "Stade à confirmer"}</span>
                {soldOut ? (
                  <span className="rounded-full bg-red-100 px-3 py-1 font-bold text-lds-red">Complet</span>
                ) : prices.length ? (
                  <span className="rounded-full bg-lds-green px-3 py-1 font-bold text-white group-hover:bg-green-800">
                    dès {formatFcfa(Math.min(...prices))}
                  </span>
                ) : (
                  <span className="rounded-full bg-blue-50 dark:bg-blue-950/40 px-3 py-1 font-semibold text-blue-900 dark:text-blue-100">Bientôt</span>
                )}
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
