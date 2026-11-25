import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { SeasonName } from "@/components/SeasonFacts";
import { ScorersTable } from "@/components/ScorersTable";
import { TeamBadge } from "@/components/TeamBadge";
import { apiGet } from "@/lib/server-api";
import type { SeasonStats } from "@/lib/types";

export const metadata: Metadata = { title: "Statistiques" };

export default function StatistiquesPage() {
  return (
    <>
      <PageHeader kicker={<SeasonName />} title="Statistiques">
        Buteurs et passeurs décisifs, calculés à partir des feuilles de match validées.
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement des statistiques…</p>}>
        <Stats />
      </Suspense>
    </>
  );
}

async function Stats() {
  const stats = await apiGet<SeasonStats>("/stats?limit=30");
  const leader = stats.scorers[0];
  // Rang 1 partagé : on présente tous les ex aequo, pas un seul joueur au hasard
  const leaders = stats.scorers.filter((r) => r.rank === 1);
  return (
    <>
      {leaders.length > 1 && (
        <section aria-label="Meilleurs buteurs" className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-pitch to-[#0a3a1e] p-6 text-white shadow-lg">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-lds-gold">Meilleurs buteurs · ex aequo</p>
              <p className="text-2xl font-black sm:text-3xl">{leaders.length} joueurs en tête</p>
            </div>
            <p className="text-right">
              <span className="block text-6xl font-black leading-none tabular-nums">{leaders[0].value}</span>
              <span className="text-xs uppercase tracking-wider text-white/80">buts chacun</span>
            </p>
          </div>
          <ul className="mt-4 flex flex-wrap gap-2">
            {leaders.slice(0, 8).map((r) => (
              <li key={`${r.person_id}-${r.team.id}`} className="flex items-center gap-2 rounded-full bg-white/10 py-1 pl-1 pr-3 text-sm">
                <TeamBadge team={r.team} size="sm" />
                <span className="font-semibold">{r.display_name}</span>
              </li>
            ))}
            {leaders.length > 8 && <li className="self-center text-sm text-white/80">et {leaders.length - 8} autres</li>}
          </ul>
        </section>
      )}
      {leaders.length === 1 && leader && (
        <section
          aria-label="Meilleur buteur"
          className="relative flex items-center gap-5 overflow-hidden rounded-2xl p-6 text-white shadow-lg"
          style={{ background: `linear-gradient(120deg, ${leader.team.primary_color}, #0a3a1e 70%)` }}
        >
          <TeamBadge team={leader.team} size="hero" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-lds-gold">Meilleur buteur</p>
            <p className="truncate text-2xl font-black sm:text-3xl">{leader.display_name}</p>
            <p className="text-sm text-white/80">{leader.team.name}</p>
          </div>
          <p className="text-right">
            <span className="block text-6xl font-black leading-none tabular-nums">{leader.value}</span>
            <span className="text-xs uppercase tracking-wider text-white/80">buts</span>
          </p>
        </section>
      )}
      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-2">
          <h2 className="text-xl font-black tracking-tight text-heading">Meilleurs buteurs</h2>
          <ScorersTable rows={stats.scorers} unit="buts" empty="Aucun but marqué pour le moment." />
        </section>
        <section className="space-y-2">
          <h2 className="text-xl font-black tracking-tight text-heading">Meilleurs passeurs</h2>
          <ScorersTable rows={stats.assists} unit="passes décisives" empty="Aucune passe décisive enregistrée." />
        </section>
      </div>
      <p className="text-xs text-subtle">
        Matchs validés uniquement. À égalité de buts, le joueur ayant marqué le moins de penalties est classé devant.
      </p>
    </>
  );
}
