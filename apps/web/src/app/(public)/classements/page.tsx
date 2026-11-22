import type { Metadata } from "next";
import { Suspense } from "react";
import { BracketTree } from "@/components/BracketTree";
import { StandingsTable } from "@/components/StandingsTable";
import { apiGet } from "@/lib/server-api";
import type { Match, PoolStandings } from "@/lib/types";

export const metadata: Metadata = { title: "Classements" };

export default function ClassementsPage() {
  return (
    <>
      <h1 className="text-2xl font-bold text-green-900">Classements</h1>
      <Suspense fallback={<p className="text-stone-500">Chargement des classements…</p>}>
        <Tables />
      </Suspense>
    </>
  );
}

async function Tables() {
  const [standings, bracket] = await Promise.all([
    apiGet<PoolStandings[]>("/standings"),
    apiGet<Match[]>("/bracket"),
  ]);
  return (
    <>
      {standings.map((p) => (
        <StandingsTable key={p.pool_code} pool={p} />
      ))}
      <p className="text-xs text-stone-500">
        Départage selon les critères de la saison (points, confrontations directes, différence de
        buts…). * égalité à départager par la commission.
      </p>
      <section className="space-y-3">
        <h2 className="text-xl font-bold text-green-900">Phases finales</h2>
        <BracketTree matches={bracket} />
      </section>
    </>
  );
}
