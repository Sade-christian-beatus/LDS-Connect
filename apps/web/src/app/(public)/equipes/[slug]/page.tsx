import { Suspense } from "react";
import { MatchCard } from "@/components/MatchCard";
import { TeamBadge } from "@/components/TeamBadge";
import { POSITION_LABEL, STAFF_LABEL } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Match, PublicTeamDetail } from "@/lib/types";

export default function EquipePage({ params }: PageProps<"/equipes/[slug]">) {
  return (
    <Suspense fallback={<p className="text-stone-500">Chargement de l&apos;équipe…</p>}>
      <Team params={params} />
    </Suspense>
  );
}

async function Team({ params }: { params: PageProps<"/equipes/[slug]">["params"] }) {
  const { slug } = await params;
  const [team, matches] = await Promise.all([
    apiGet<PublicTeamDetail>(`/teams/${encodeURIComponent(slug)}`),
    apiGet<Match[]>(`/matches?team=${encodeURIComponent(slug)}`),
  ]);
  const order = ["GK", "DF", "MF", "FW"] as const;
  return (
    <>
      <title>{`${team.name} · LDS Connect`}</title>
      <header className="flex items-center gap-4">
        <TeamBadge team={team} size="lg" />
        <div>
          <h1 className="text-2xl font-bold text-green-900">{team.name}</h1>
          <p className="text-sm text-stone-600">
            Région {team.region.name} · Poule {team.pool_code}
          </p>
        </div>
      </header>

      <section className="space-y-2">
        <h2 className="text-lg font-bold text-green-900">Matchs</h2>
        {matches.map((m) => (
          <MatchCard key={m.id} match={m} />
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-bold text-green-900">Effectif ({team.players.length} joueurs)</h2>
        {order.map((pos) => {
          const players = team.players.filter((p) => p.position === pos);
          if (!players.length) return null;
          return (
            <div key={pos}>
              <h3 className="text-sm font-semibold uppercase text-stone-600">{POSITION_LABEL[pos]}s</h3>
              <ul className="mt-1 grid gap-1 sm:grid-cols-2 md:grid-cols-3">
                {players.map((p, i) => (
                  <li key={i} className="flex items-center gap-2 rounded bg-white px-2 py-1 text-sm">
                    <span className="w-6 text-right font-bold tabular-nums text-stone-500">
                      {p.shirt_number ?? "–"}
                    </span>
                    <span className="flex-1">{p.display_name}</span>
                    <span className="text-xs text-stone-500">{p.age} ans</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-bold text-green-900">Encadrement</h2>
        <ul className="grid gap-1 sm:grid-cols-2">
          {team.staff.map((s, i) => (
            <li key={i} className="rounded bg-white px-2 py-1 text-sm">
              <span className="font-medium">{s.display_name}</span>
              <span className="text-stone-500"> — {STAFF_LABEL[s.function]}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
