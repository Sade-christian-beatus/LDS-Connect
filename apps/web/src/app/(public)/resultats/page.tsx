import type { Metadata } from "next";
import { Suspense } from "react";
import { MatchCard } from "@/components/MatchCard";
import { apiGet } from "@/lib/server-api";
import type { Match } from "@/lib/types";

export const metadata: Metadata = { title: "Résultats" };

export default function ResultatsPage() {
  return (
    <>
      <h1 className="text-2xl font-bold text-green-900">Résultats</h1>
      <Suspense fallback={<p className="text-stone-500">Chargement des résultats…</p>}>
        <Results />
      </Suspense>
    </>
  );
}

async function Results() {
  const matches = await apiGet<Match[]>("/matches?status=finished");
  if (matches.length === 0) {
    return <p className="text-stone-600">Aucun match joué pour le moment.</p>;
  }
  const groups = new Map<string, Match[]>();
  for (const m of [...matches].reverse()) {
    const key = m.phase === "group" ? `Poule ${m.pool_code} · Journée ${m.round_number}` : m.phase;
    groups.set(key, [...(groups.get(key) ?? []), m]);
  }
  return (
    <>
      {[...groups.entries()].map(([title, list]) => (
        <section key={title} className="space-y-2">
          <h2 className="font-bold text-green-900">{title}</h2>
          {list.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </section>
      ))}
    </>
  );
}
