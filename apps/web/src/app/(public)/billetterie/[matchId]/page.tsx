import Link from "next/link";
import { Suspense } from "react";
import { MatchHero } from "@/components/MatchHero";
import { apiGet } from "@/lib/server-api";
import type { MatchTickets } from "@/lib/types";
import { BuyForm } from "./buy-form";

export default function MatchTicketsPage({ params }: PageProps<"/billetterie/[matchId]">) {
  return (
    <Suspense fallback={<p className="text-stone-500">Chargement…</p>}>
      <Content params={params} />
    </Suspense>
  );
}

async function Content({ params }: { params: PageProps<"/billetterie/[matchId]">["params"] }) {
  const { matchId } = await params;
  const data = await apiGet<MatchTickets>(`/tickets/matches/${encodeURIComponent(matchId)}`);
  const m = data.match;
  return (
    <>
      <title>{`Billets ${m.home?.short_name ?? ""} – ${m.away?.short_name ?? ""} · LDS Connect`}</title>
      <Link href="/billetterie" className="text-sm text-lds-green underline">
        ← Tous les matchs
      </Link>
      <MatchHero match={m} />
      {data.types.length === 0 ? (
        <p className="rounded-xl bg-stone-100 p-4">Aucun billet n&apos;est proposé pour ce match.</p>
      ) : (
        <BuyForm types={data.types} />
      )}
    </>
  );
}
