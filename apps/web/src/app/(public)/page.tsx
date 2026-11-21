import Link from "next/link";
import { Suspense } from "react";
import { LiveScores } from "@/components/LiveScores";
import { MatchCard } from "@/components/MatchCard";
import { StandingsTable } from "@/components/StandingsTable";
import { formatDate } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Match, PoolStandings, Season } from "@/lib/types";

export default function Accueil() {
  return (
    <>
      <section className="rounded-xl bg-gradient-to-br from-lds-green to-green-900 p-6 text-white">
        <p className="text-sm uppercase tracking-wide text-lds-gold">Phase pilote 2027</p>
        <h1 className="mt-1 text-3xl font-bold">Ligue de la Souveraineté</h1>
        <p className="mt-2 max-w-2xl text-green-50">
          20 équipes issues des 17 régions, deux poules : poule A à Ouagadougou, poule B à
          Bobo-Dioulasso. Les quatre premiers de chaque poule se qualifient pour les quarts de finale.
        </p>
      </section>
      <Suspense fallback={<p className="text-stone-500">Chargement…</p>}>
        <HomeContent />
      </Suspense>
    </>
  );
}

async function HomeContent() {
  const [season, matches, standings] = await Promise.all([
    apiGet<Season>("/seasons/current"),
    apiGet<Match[]>("/matches"),
    apiGet<PoolStandings[]>("/standings"),
  ]);
  const upcoming = matches.filter((m) => m.status === "scheduled" && m.home).slice(0, 6);
  const results = matches.filter((m) => m.status === "finished").slice(-6).reverse();
  return (
    <>
      <LiveScores initial={matches.filter((m) => m.status === "live")} />
      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-2">
          <h2 className="text-lg font-bold text-green-900">Prochains matchs</h2>
          {upcoming.length === 0 && <p className="text-sm text-stone-500">Aucun match programmé.</p>}
          {upcoming.map((m) => (
            <div key={m.id}>
              <p className="text-xs text-stone-500">
                {formatDate(m.kickoff_at)} · {m.venue?.city ?? ""}
              </p>
              <MatchCard match={m} />
            </div>
          ))}
          <Link href="/calendrier" className="text-sm font-medium text-lds-green underline">
            Tout le calendrier
          </Link>
        </section>
        <section className="space-y-2">
          <h2 className="text-lg font-bold text-green-900">Derniers résultats</h2>
          {results.length === 0 && (
            <p className="text-sm text-stone-500">
              Coup d&apos;envoi de la {season.name.toLowerCase()} le{" "}
              {new Date(season.starts_on).toLocaleDateString("fr-FR")}.
            </p>
          )}
          {results.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </section>
      </div>
      <section className="grid gap-4 md:grid-cols-2">
        {standings.map((p) => (
          <StandingsTable key={p.pool_code} pool={p} compact />
        ))}
      </section>
    </>
  );
}
