import type { Metadata } from "next";
import { Suspense } from "react";
import { ScorersTable } from "@/components/ScorersTable";
import { apiGet } from "@/lib/server-api";
import type { SeasonStats } from "@/lib/types";

export const metadata: Metadata = { title: "Statistiques" };

export default function StatistiquesPage() {
  return (
    <>
      <h1 className="text-2xl font-bold text-green-900">Statistiques</h1>
      <Suspense fallback={<p className="text-stone-500">Chargement des statistiques…</p>}>
        <Stats />
      </Suspense>
    </>
  );
}

async function Stats() {
  const stats = await apiGet<SeasonStats>("/stats?limit=30");
  return (
    <>
      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-2">
          <h2 className="text-lg font-bold text-green-900">Meilleurs buteurs</h2>
          <ScorersTable rows={stats.scorers} unit="buts" empty="Aucun but marqué pour le moment." />
        </section>
        <section className="space-y-2">
          <h2 className="text-lg font-bold text-green-900">Meilleurs passeurs</h2>
          <ScorersTable rows={stats.assists} unit="passes décisives" empty="Aucune passe décisive enregistrée." />
        </section>
      </div>
      <p className="text-xs text-stone-500">
        Matchs validés uniquement. À égalité de buts, le joueur ayant marqué le moins de penalties est classé devant.
      </p>
    </>
  );
}
