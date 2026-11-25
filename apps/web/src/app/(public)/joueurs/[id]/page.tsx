import Link from "next/link";
import { SeasonName } from "@/components/SeasonFacts";
import { Suspense } from "react";
import { MatchLogList, StatTiles } from "@/components/PlayerStats";
import { TeamBadge } from "@/components/TeamBadge";
import { POSITION_LABEL } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { PublicPlayerProfile } from "@/lib/types";

export default function JoueurPage({ params }: PageProps<"/joueurs/[id]">) {
  return (
    <Suspense fallback={<p className="text-subtle">Chargement du joueur…</p>}>
      <Player params={params} />
    </Suspense>
  );
}

async function Player({ params }: { params: PageProps<"/joueurs/[id]">["params"] }) {
  const { id } = await params;
  const p = await apiGet<PublicPlayerProfile>(`/players/${encodeURIComponent(id)}`);
  return (
    <>
      <title>{`${p.display_name} · ${p.team.short_name} · LDS Connect`}</title>
      <header
        className="relative overflow-hidden rounded-2xl p-6 text-white shadow-lg sm:p-8"
        style={{ background: `linear-gradient(120deg, ${p.team.primary_color} 0%, #0a3a1e 85%)` }}
      >
        <span
          aria-hidden
          className="pointer-events-none absolute -right-4 -top-10 select-none text-[10rem] font-black leading-none text-white/10 tabular-nums"
        >
          {p.shirt_number ?? ""}
        </span>
        <div className="relative flex items-center gap-5">
          <span
            className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl text-4xl font-black tabular-nums shadow-lg ring-4 ring-white/20"
            style={{ backgroundColor: p.team.primary_color, color: p.team.secondary_color }}
          >
            {p.shirt_number ?? "–"}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-lds-gold">
              {POSITION_LABEL[p.position]} · {p.age} ans
            </p>
            <h1 className="truncate text-3xl font-black leading-tight sm:text-4xl">{p.display_name}</h1>
            <Link href={`/equipes/${p.team.slug}`} className="mt-1 inline-flex items-center gap-2 text-sm font-semibold text-white/90 hover:underline">
              <TeamBadge team={p.team} size="sm" />
              {p.team.name}
            </Link>
          </div>
        </div>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-black tracking-tight text-heading">
          <SeasonName />
        </h2>
        <StatTiles stats={p.stats} goalkeeper={p.position === "GK"} />
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-black tracking-tight text-heading">Match par match</h2>
        <MatchLogList matches={p.matches} teamId={p.team.id} />
      </section>
      <p className="text-xs text-subtle">
        Statistiques issues des feuilles de match validées. Par respect pour les joueurs mineurs, seuls le nom d&apos;usage, le
        poste, l&apos;équipe et l&apos;âge sont publiés.
      </p>
    </>
  );
}
