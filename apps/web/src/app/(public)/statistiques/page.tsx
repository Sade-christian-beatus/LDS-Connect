import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ScorersTable } from "@/components/ScorersTable";
import { SeasonName } from "@/components/SeasonFacts";
import { TrophyRace } from "@/components/TrophyRace";
import { apiGet } from "@/lib/server-api";
import type { Contender, SeasonStats, StatRow, TrophyRace as Race } from "@/lib/types";

export const metadata: Metadata = { title: "Statistiques et trophées" };

export default function StatistiquesPage() {
  return (
    <>
      <PageHeader kicker={<SeasonName />} title="Statistiques et trophées">
        La course aux cinq trophées de la Ligue et les classements individuels, calculés à partir des feuilles de match
        validées et des votes publiés.
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement des statistiques…</p>}>
        <Stats />
      </Suspense>
    </>
  );
}

/** Classement d'un trophée affiché avec le même tableau que les buteurs. */
const asRows = (rows: Contender[]): StatRow[] =>
  rows.filter((r) => r.person_id && r.team).map((r) => ({ ...r, person_id: r.person_id!, team: r.team!, penalties: 0 }));

async function Stats() {
  const [stats, race] = await Promise.all([apiGet<SeasonStats>("/stats?limit=10"), apiGet<Race>("/trophies")]);
  const by = Object.fromEntries(race.trophies.map((t) => [t.code, t]));
  return (
    <>
      <section aria-labelledby="course" className="space-y-3">
        <h2 id="course" className="text-xl font-black tracking-tight text-heading">
          La course aux trophées
        </h2>
        <TrophyRace trophies={race.trophies} />
      </section>
      <section id="classements" aria-label="Classements individuels" className="grid gap-6 md:grid-cols-2">
        <div className="space-y-2">
          <h2 className="text-xl font-black tracking-tight text-heading">Meilleurs buteurs</h2>
          <ScorersTable rows={stats.scorers} unit="buts" empty="Aucun but marqué pour le moment." />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-black tracking-tight text-heading">Meilleurs gardiens</h2>
          <ScorersTable rows={asRows(by.goalkeeper?.contenders ?? [])} unit="clean sheets" empty="Aucun gardien n'a encore joué." />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-black tracking-tight text-heading">Hommes du match</h2>
          <ScorersTable rows={asRows(by.man_of_the_match?.contenders ?? [])} unit="distinctions" empty="Aucun homme du match désigné pour le moment." />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-black tracking-tight text-heading">Meilleurs passeurs</h2>
          <ScorersTable rows={stats.assists} unit="passes décisives" empty="Aucune passe décisive enregistrée." />
        </div>
      </section>
      <p className="text-xs text-subtle">
        Classements statistiques indicatifs : l&apos;attribution officielle des trophées suit le règlement de la Ligue. À
        égalité de buts, le joueur ayant marqué le moins de penalties est classé devant ; à égalité de clean sheets, le
        gardien ayant joué le plus de matchs.
      </p>
    </>
  );
}
