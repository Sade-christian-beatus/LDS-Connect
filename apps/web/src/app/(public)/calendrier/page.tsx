import type { Metadata } from "next";
import { SeasonName } from "@/components/SeasonFacts";
import { Suspense } from "react";
import { MatchCard } from "@/components/MatchCard";
import { PageHeader, Pills } from "@/components/PageHeader";
import { formatDate } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Match } from "@/lib/types";

export const metadata: Metadata = { title: "Calendrier" };

export default function CalendrierPage({ searchParams }: PageProps<"/calendrier">) {
  return (
    <>
      <PageHeader kicker={<SeasonName />} title="Calendrier">
        9 journées par poule, puis les phases finales. Horaires à l&apos;heure de Ouagadougou (GMT).
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement du calendrier…</p>}>
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
      <Pills
        label="Poule"
        items={(["A", "B"] as const).map((p) => ({
          href: `/calendrier?poule=${p}`,
          label: `Poule ${p} · ${p === "A" ? "Ouagadougou" : "Bobo-Dioulasso"}`,
          active: p === pool,
        }))}
      />
      {[...rounds.entries()]
        .sort(([a], [b]) => a - b)
        .map(([round, list]) => (
          <section key={round} className="space-y-3">
            <h2 className="sticky top-[6.75rem] z-10 -mx-4 flex items-baseline gap-3 bg-canvas/90 px-4 py-2 backdrop-blur">
              <span className="rounded-lg bg-pitch px-2.5 py-1 text-sm font-black text-lds-gold">J{round}</span>
              <span className="font-bold text-heading">Journée {round}</span>
              <span className="text-sm text-subtle">{formatDate(list[0]?.kickoff_at)}</span>
            </h2>
            <div className="grid gap-3 lg:grid-cols-2">
              {list.map((m) => (
                <MatchCard key={m.id} match={m} />
              ))}
            </div>
          </section>
        ))}
    </>
  );
}
