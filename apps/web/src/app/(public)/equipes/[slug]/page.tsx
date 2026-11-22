import { Suspense } from "react";
import { MatchCard } from "@/components/MatchCard";
import { TeamBadge } from "@/components/TeamBadge";
import { POSITION_LABEL, STAFF_LABEL } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { Match, PublicTeamDetail } from "@/lib/types";

export default function EquipePage({ params }: PageProps<"/equipes/[slug]">) {
  return (
    <Suspense fallback={<p className="text-subtle">Chargement de l&apos;équipe…</p>}>
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
  const played = matches.filter((m) => m.status === "finished");
  const wins = played.filter((m) => {
    const mine = m.home?.id === team.id ? m.home_score : m.away_score;
    const theirs = m.home?.id === team.id ? m.away_score : m.home_score;
    const pens = m.home?.id === team.id ? [m.home_penalties, m.away_penalties] : [m.away_penalties, m.home_penalties];
    return (mine ?? 0) > (theirs ?? 0) || (mine === theirs && (pens[0] ?? 0) > (pens[1] ?? 0));
  }).length;
  return (
    <>
      <title>{`${team.name} · LDS Connect`}</title>
      <header
        className="relative overflow-hidden rounded-2xl p-6 text-white shadow-lg sm:p-8"
        style={{ background: `linear-gradient(120deg, ${team.primary_color} 0%, ${team.primary_color} 35%, #0a3a1e 100%)` }}
      >
        <div aria-hidden className="pointer-events-none absolute -right-10 -top-10 h-48 w-48 rounded-full border-[20px] border-white/10" />
        <div className="relative flex items-center gap-5">
          <span className="rounded-full bg-white/15 p-1.5 backdrop-blur">
            <TeamBadge team={team} size="lg" />
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-white/80">
              Région {team.region.name} · Poule {team.pool_code}
            </p>
            <h1 className="text-3xl font-black leading-tight sm:text-4xl">{team.name}</h1>
          </div>
        </div>
        <dl className="relative mt-5 grid max-w-md grid-cols-3 gap-2 text-center">
          {[
            [String(team.players.length), "joueurs"],
            [String(played.length), "matchs joués"],
            [String(wins), "victoires"],
          ].map(([v, l]) => (
            <div key={l} className="rounded-xl bg-black/20 py-2 backdrop-blur">
              <dt className="sr-only">{l}</dt>
              <dd className="text-2xl font-black tabular-nums">{v}</dd>
              <dd className="text-[11px] uppercase tracking-wide text-white/80">{l}</dd>
            </div>
          ))}
        </dl>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-black tracking-tight text-heading">Matchs</h2>
        <div className="grid gap-3 lg:grid-cols-2">
          {matches.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-black tracking-tight text-heading">Effectif ({team.players.length} joueurs)</h2>
        {order.map((pos) => {
          const players = team.players.filter((p) => p.position === pos);
          if (!players.length) return null;
          return (
            <div key={pos}>
              <h3 className="text-xs font-bold uppercase tracking-widest text-lds-red">{POSITION_LABEL[pos]}s</h3>
              <ul className="mt-2 grid gap-2 sm:grid-cols-2 md:grid-cols-3">
                {players.map((p, i) => (
                  <li key={i} className="flex items-center gap-3 rounded-xl border border-line bg-surface px-3 py-2 text-sm">
                    <span
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-black tabular-nums"
                      style={{ backgroundColor: team.primary_color, color: team.secondary_color }}
                    >
                      {p.shirt_number ?? "–"}
                    </span>
                    <span className="flex-1 font-medium">{p.display_name}</span>
                    <span className="text-xs text-subtle">{p.age} ans</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </section>

      <section className="space-y-2">
        <h2 className="text-xl font-black tracking-tight text-heading">Encadrement</h2>
        <ul className="grid gap-2 sm:grid-cols-2">
          {team.staff.map((s, i) => (
            <li key={i} className="rounded-xl border border-line bg-surface px-3 py-2 text-sm">
              <span className="font-medium">{s.display_name}</span>
              <span className="text-subtle"> — {STAFF_LABEL[s.function]}</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
