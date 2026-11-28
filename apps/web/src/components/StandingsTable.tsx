import Link from "next/link";
import type { PoolStandings } from "@/lib/types";
import { formSpeech } from "@/lib/a11y";
import { TeamBadge } from "./TeamBadge";

const FORM_COLOR: Record<string, string> = {
  V: "bg-green-600",
  N: "bg-stone-400",
  D: "bg-lds-red",
};

/** En-tête de colonne : l'abréviation à l'écran, le mot entier pour le lecteur d'écran. */
function Abbr({ short, long }: { short: string; long: string }) {
  return (
    <>
      <span aria-hidden title={long}>
        {short}
      </span>
      <span className="sr-only">{long}</span>
    </>
  );
}

export function StandingsTable({
  pool,
  compact = false,
  headingLevel = 3,
}: {
  pool: PoolStandings;
  compact?: boolean;
  headingLevel?: 2 | 3;
}) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const progress = pool.matches_total ? Math.round((pool.matches_played / pool.matches_total) * 100) : 0;
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      <div className="flex items-end justify-between gap-3 bg-pitch px-4 py-3 text-white">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-lds-gold">{pool.host_city}</p>
          <Heading className="text-lg font-black leading-tight">{pool.pool_name}</Heading>
        </div>
        <div className="w-28 text-right text-[11px] text-green-100">
          <span aria-hidden>
            {pool.matches_played}/{pool.matches_total} matchs
          </span>
          <span className="sr-only">
            {pool.matches_played} matchs joués sur {pool.matches_total}
          </span>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/15">
            <div className="h-full rounded-full bg-lds-gold" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div>
      {/* Zone défilante sur téléphone : atteignable au clavier pour faire défiler le tableau */}
      <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={`Tableau du classement, ${pool.pool_name}`}>
        <table className="w-full text-sm">
          <caption className="sr-only">
            Classement {pool.pool_name} — {pool.host_city}
          </caption>
          <thead className="text-[11px] uppercase tracking-wide text-subtle">
            <tr className="border-b border-line">
              <th className="py-2 pl-4 pr-2 text-left">
                <Abbr short="#" long="Rang" />
              </th>
              <th className="px-2 py-2 text-left">Équipe</th>
              <th className="px-2 py-2">
                <Abbr short="J" long="Matchs joués" />
              </th>
              {!compact && (
                <>
                  <th className="px-2 py-2">
                <Abbr short="V" long="Victoires" />
              </th>
                  <th className="px-2 py-2">
                <Abbr short="N" long="Nuls" />
              </th>
                  <th className="px-2 py-2">
                <Abbr short="D" long="Défaites" />
              </th>
                  <th className="hidden px-2 py-2 sm:table-cell">
                <Abbr short="BP" long="Buts pour" />
              </th>
                  <th className="hidden px-2 py-2 sm:table-cell">
                <Abbr short="BC" long="Buts contre" />
              </th>
                </>
              )}
              <th className="px-2 py-2">
                <Abbr short="Diff" long="Différence de buts" />
              </th>
              <th className="px-2 py-2">
                <Abbr short="Pts" long="Points" />
              </th>
              {!compact && <th className="hidden px-2 py-2 text-left md:table-cell">Forme</th>}
            </tr>
          </thead>
          <tbody>
            {pool.rows.map((r) => (
              <tr key={r.team.id} className={`border-b border-line last:border-0 ${r.qualified_zone ? "bg-qualify" : ""}`}>
                <td className="relative py-2 pl-4 pr-2 font-bold tabular-nums">
                  {r.qualified_zone && <span aria-hidden className="absolute inset-y-0 left-0 w-1 bg-lds-green" />}
                  {r.rank}
                  {r.needs_draw && r.played > 0 && (
                    <>
                      <span aria-hidden title="Égalité non départagée" className="text-lds-red">
                        *
                      </span>
                      <span className="sr-only">, égalité à départager</span>
                    </>
                  )}
                  {r.qualified_zone && <span className="sr-only">, place qualificative</span>}
                </td>
                <td className="px-2 py-2">
                  <Link href={`/equipes/${r.team.slug}`} className="flex items-center gap-2.5 hover:underline">
                    <TeamBadge team={r.team} size="sm" />
                    <span className="font-medium">
                      {compact ? (
                        r.team.short_name
                      ) : (
                        <>
                          <span className="sm:hidden">{r.team.short_name}</span>
                          <span className="hidden sm:inline">{r.team.name}</span>
                        </>
                      )}
                    </span>
                  </Link>
                </td>
                <td className="px-2 py-2 text-center tabular-nums text-muted">{r.played}</td>
                {!compact && (
                  <>
                    <td className="px-2 py-2 text-center tabular-nums text-muted">{r.won}</td>
                    <td className="px-2 py-2 text-center tabular-nums text-muted">{r.drawn}</td>
                    <td className="px-2 py-2 text-center tabular-nums text-muted">{r.lost}</td>
                    <td className="hidden px-2 py-2 text-center tabular-nums text-muted sm:table-cell">{r.goals_for}</td>
                    <td className="hidden px-2 py-2 text-center tabular-nums text-muted sm:table-cell">{r.goals_against}</td>
                  </>
                )}
                <td className="px-2 py-2 text-center tabular-nums text-muted">
                  {r.goal_difference > 0 ? `+${r.goal_difference}` : r.goal_difference}
                </td>
                <td className="px-2 py-2 text-center">
                  <span className="inline-block min-w-8 rounded-md bg-soft px-1.5 py-0.5 text-base font-black tabular-nums">{r.points}</span>
                </td>
                {!compact && (
                  <td className="hidden px-2 py-2 md:table-cell">
                    <span className="sr-only">{formSpeech(r.form) || "aucun match"}</span>
                    <span aria-hidden className="flex gap-1">
                      {r.form.map((f, i) => (
                        <span
                          key={i}
                          title={{ V: "Victoire", N: "Nul", D: "Défaite" }[f]}
                          className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white ${FORM_COLOR[f]}`}
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
      </div>
      <p className="flex items-center gap-2 px-4 py-2 text-[11px] text-subtle">
        <span aria-hidden className="h-3 w-1 rounded bg-lds-green" /> Qualifiés pour les quarts de finale
      </p>
    </div>
  );
}
