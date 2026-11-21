import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { MatchCard } from "@/components/MatchCard";
import { formatDate } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Match } from "@/lib/types";

export const metadata: Metadata = { title: "Calendrier" };

export default function CalendrierPage({ searchParams }: PageProps<"/calendrier">) {
  return (
    <>
      <h1 className="text-2xl font-bold text-green-900">Calendrier</h1>
      <Suspense fallback={<p className="text-stone-500">Chargement du calendrier…</p>}>
        <Calendar searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Calendar({ searchParams }: { searchParams: PageProps<"/calendrier">["searchParams"] }) {
  const sp = await searchParams;
  const pool = sp.poule === "B" ? "B" : "A";
  const matches = await apiGet<Match[]>(`/matches?pool=${pool}`);
  const rounds = new Map<number, Match[]>();
  for (const m of matches) {
    const r = m.round_number ?? 0;
    rounds.set(r, [...(rounds.get(r) ?? []), m]);
  }
  return (
    <>
      <div className="flex gap-2" role="tablist" aria-label="Poule">
        {(["A", "B"] as const).map((p) => (
          <Link
            key={p}
            role="tab"
            aria-selected={p === pool}
            href={`/calendrier?poule=${p}`}
            className={`rounded-full px-4 py-1 text-sm font-semibold ${
              p === pool ? "bg-lds-green text-white" : "bg-white text-green-900 ring-1 ring-stone-300"
            }`}
          >
            Poule {p} · {p === "A" ? "Ouagadougou" : "Bobo-Dioulasso"}
          </Link>
        ))}
      </div>
      {[...rounds.entries()]
        .sort(([a], [b]) => a - b)
        .map(([round, list]) => (
          <section key={round} className="space-y-2">
            <h2 className="font-bold text-green-900">
              Journée {round}
              <span className="ml-2 text-sm font-normal text-stone-500">
                {formatDate(list[0]?.kickoff_at)}
              </span>
            </h2>
            {list.map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
          </section>
        ))}
      <p className="text-xs text-stone-500">Horaires à l&apos;heure de Ouagadougou (GMT).</p>
    </>
  );
}
