import Link from "next/link";
import type { PoolStandings } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

const FORM_COLOR: Record<string, string> = {
  V: "bg-green-600",
  N: "bg-stone-400",
  D: "bg-lds-red",
};

export function StandingsTable({ pool, compact = false }: { pool: PoolStandings; compact?: boolean }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
      <table className="w-full text-sm">
        <caption className="px-3 py-2 text-left font-semibold text-green-900">
          {pool.pool_name} — {pool.host_city}
          <span className="ml-2 text-xs font-normal text-stone-500">
            {pool.matches_played}/{pool.matches_total} matchs joués
          </span>
        </caption>
        <thead className="bg-stone-100 text-xs uppercase text-stone-600">
          <tr>
            <th className="px-2 py-1 text-left">#</th>
            <th className="px-2 py-1 text-left">Équipe</th>
            <th className="px-2 py-1" title="Matchs joués">J</th>
            {!compact && (
              <>
                <th className="px-2 py-1" title="Victoires">V</th>
                <th className="px-2 py-1" title="Nuls">N</th>
                <th className="px-2 py-1" title="Défaites">D</th>
                <th className="px-2 py-1" title="Buts pour">BP</th>
                <th className="px-2 py-1" title="Buts contre">BC</th>
              </>
            )}
            <th className="px-2 py-1" title="Différence de buts">Diff</th>
            <th className="px-2 py-1">Pts</th>
            {!compact && <th className="px-2 py-1 text-left">Forme</th>}
          </tr>
        </thead>
        <tbody>
          {pool.rows.map((r) => (
            <tr
              key={r.team.id}
              className={`border-t border-stone-100 ${r.qualified_zone ? "bg-green-50" : ""}`}
            >
              <td className="px-2 py-1 font-semibold tabular-nums">
                {r.rank}
                {r.needs_draw && r.played > 0 && (
                  <span title="Égalité non départagée" className="text-lds-red">*</span>
                )}
              </td>
              <td className="px-2 py-1">
                <Link href={`/equipes/${r.team.slug}`} className="flex items-center gap-2 hover:underline">
                  <TeamBadge team={r.team} size="sm" />
                  <span>{compact ? r.team.short_name : r.team.name}</span>
                </Link>
              </td>
              <td className="px-2 py-1 text-center tabular-nums">{r.played}</td>
              {!compact && (
                <>
                  <td className="px-2 py-1 text-center tabular-nums">{r.won}</td>
                  <td className="px-2 py-1 text-center tabular-nums">{r.drawn}</td>
                  <td className="px-2 py-1 text-center tabular-nums">{r.lost}</td>
                  <td className="px-2 py-1 text-center tabular-nums">{r.goals_for}</td>
                  <td className="px-2 py-1 text-center tabular-nums">{r.goals_against}</td>
                </>
              )}
              <td className="px-2 py-1 text-center tabular-nums">
                {r.goal_difference > 0 ? `+${r.goal_difference}` : r.goal_difference}
              </td>
              <td className="px-2 py-1 text-center font-bold tabular-nums">{r.points}</td>
              {!compact && (
                <td className="px-2 py-1">
                  <span className="flex gap-0.5">
                    {r.form.map((f, i) => (
                      <span
                        key={i}
                        title={{ V: "Victoire", N: "Nul", D: "Défaite" }[f]}
                        className={`inline-block h-4 w-4 rounded-sm text-center text-[10px] leading-4 text-white ${FORM_COLOR[f]}`}
                      >
                        {f}
                      </span>
                    ))}
                  </span>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-3 py-1 text-[11px] text-stone-500">
        En vert : zone de qualification pour les quarts de finale.
      </p>
    </div>
  );
}
