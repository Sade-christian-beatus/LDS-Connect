import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { MatchCard } from "@/components/MatchCard";
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
      <h1 className="text-2xl font-bold text-green-900">Résultats</h1>
      <Suspense fallback={<p className="text-stone-500">Chargement des résultats…</p>}>
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
      <nav className="flex gap-2" aria-label="Filtrer les résultats">
        {TABS.map((t) => (
          <Link
            key={t.key}
            href={t.key === "tous" ? "/resultats" : `/resultats?vue=${t.key}`}
            aria-current={tab === t.key ? "page" : undefined}
            className={`rounded-full px-4 py-1 text-sm font-semibold ${
              tab === t.key ? "bg-lds-green text-white" : "bg-white text-green-900 ring-1 ring-stone-300"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </nav>
      {matches.length === 0 && <p className="text-stone-600">Aucun match joué pour le moment.</p>}
      {[...days.entries()].map(([day, list]) => (
        <section key={day} className="space-y-2">
          <h2 className="text-sm font-bold uppercase tracking-wide text-lds-red">{day}</h2>
          {list.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </section>
      ))}
    </>
  );
}
