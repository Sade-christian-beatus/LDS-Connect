import { Trophy } from "@/components/Illustrations";
import type { Metadata } from "next";
import { Suspense } from "react";
import { BracketTree } from "@/components/BracketTree";
import { PageHeader } from "@/components/PageHeader";
import { StandingsTable } from "@/components/StandingsTable";
import { apiGet } from "@/lib/server-api";
import type { Match, PoolStandings } from "@/lib/types";

export const metadata: Metadata = { title: "Classements" };

export default function ClassementsPage() {
  return (
    <>
      <PageHeader kicker="Saison 2027" title="Classements">
        Les quatre premiers de chaque poule se qualifient pour les quarts de finale.
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement des classements…</p>}>
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
      <div className="grid gap-6 xl:grid-cols-2">
        {standings.map((p) => (
          <StandingsTable key={p.pool_code} pool={p} />
        ))}
      </div>
      <p className="text-xs text-subtle">
        Départage selon les critères de la saison (points, confrontations directes, différence de
        buts…). * égalité à départager par la commission.
      </p>
      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-2xl font-black tracking-tight text-heading">
          <Trophy className="h-9 w-9" />
          Phases finales
        </h2>
        <BracketTree matches={bracket} />
      </section>
    </>
  );
}
