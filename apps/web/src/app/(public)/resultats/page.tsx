import type { Metadata } from "next";
import { Suspense } from "react";
import { MatchCard } from "@/components/MatchCard";
import { PageHeader, Pills } from "@/components/PageHeader";
import { formatDate } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Match } from "@/lib/types";

export const metadata: Metadata = { title: "Résultats" };

const TABS = [
  { key: "tous", label: "Tous" },
  { key: "poules", label: "Poules" },
  { key: "finales", label: "Phases finales" },
] as const;

export default function ResultatsPage({ searchParams }: PageProps<"/resultats">) {
  return (
    <>
      <PageHeader kicker="Saison 2027" title="Résultats">
        Scores officiels, validés à partir des feuilles de match.
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement des résultats…</p>}>
        <Results searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function Results({ searchParams }: { searchParams: PageProps<"/resultats">["searchParams"] }) {
  const sp = await searchParams;
  const tab = TABS.find((t) => t.key === sp.vue)?.key ?? "tous";
  const all = await apiGet<Match[]>("/matches?status=finished");
  const matches = all.filter((m) =>
    tab === "poules" ? m.phase === "group" : tab === "finales" ? m.phase !== "group" : true,
  );

  // Groupés par jour, du plus récent au plus ancien
  const days = new Map<string, Match[]>();
  for (const m of [...matches].reverse()) {
    const key = formatDate(m.kickoff_at);
    days.set(key, [...(days.get(key) ?? []), m]);
  }

  return (
    <>
      <Pills
        label="Filtrer les résultats"
        items={TABS.map((t) => ({
          href: t.key === "tous" ? "/resultats" : `/resultats?vue=${t.key}`,
          label: t.label,
          active: tab === t.key,
        }))}
      />
      {matches.length === 0 && <p className="text-muted">Aucun match joué pour le moment.</p>}
      {[...days.entries()].map(([day, list]) => (
        <section key={day} className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-lds-red">{day}</h2>
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
