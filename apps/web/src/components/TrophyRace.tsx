// Course aux cinq trophées de la Ligue : leader(s), poursuivants et critère de chaque
// distinction, à partir des feuilles validées, des votes publiés et des classements.
import Link from "next/link";
import type { Contender, Trophy } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

const ACCENT: Record<string, { ring: string; band: string; unit: (v: number) => string }> = {
  winner: { ring: "ring-lds-gold", band: "from-lds-gold to-amber-500", unit: (v) => `${v} pts` },
  top_scorer: { ring: "ring-lds-red/60", band: "from-lds-red to-red-700", unit: (v) => `${v} but${v > 1 ? "s" : ""}` },
  goalkeeper: { ring: "ring-sky-500/60", band: "from-sky-600 to-sky-800", unit: (v) => `${v} clean sheet${v > 1 ? "s" : ""}` },
  man_of_the_match: { ring: "ring-lds-green/60", band: "from-lds-green to-pitch", unit: (v) => `${v} fois` },
  best_player: { ring: "ring-violet-500/60", band: "from-violet-600 to-violet-900", unit: (v) => `${v} vote${v > 1 ? "s" : ""}` },
};

function Cup({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 64 64" className={className}>
      <path d="M20 8h24v14a12 12 0 0 1-24 0Z" fill="currentColor" />
      <path d="M20 12h-8a8 8 0 0 0 8 12M44 12h8a8 8 0 0 1-8 12" fill="none" stroke="currentColor" strokeWidth="3.5" />
      <rect x="29" y="33" width="6" height="11" fill="currentColor" opacity="0.8" />
      <path d="M22 44h20l3 8H19Z" fill="currentColor" opacity="0.9" />
    </svg>
  );
}

function Name({ c }: { c: Contender }) {
  const inner = <span className="truncate font-bold">{c.display_name}</span>;
  return c.person_id ? (
    <Link href={`/joueurs/${c.person_id}`} className="min-w-0 truncate hover:underline">
      {inner}
    </Link>
  ) : c.team ? (
    <Link href={`/equipes/${c.team.slug}`} className="min-w-0 truncate hover:underline">
      {inner}
    </Link>
  ) : (
    inner
  );
}

function TrophyCard({ t, compact }: { t: Trophy; compact: boolean }) {
  const a = ACCENT[t.code] ?? ACCENT.winner;
  const others = t.contenders.filter((c) => c.value > 0).filter((c) => !t.leaders.some((l) => l.display_name === c.display_name && l.team?.id === c.team?.id));
  const href = t.ballot_id ? `/votes/${t.ballot_id}` : t.code === "winner" ? "/classements" : "/statistiques#classements";
  return (
    <article className={`flex flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-sm ring-1 ${a.ring}`} aria-label={t.title}>
      <header className={`relative bg-gradient-to-br ${a.band} px-4 pb-3 pt-4 text-white`}>
        <Cup className="absolute -right-2 -top-1 h-16 w-16 text-white/20" />
        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-white/85">Trophée</p>
        <h3 className="text-lg font-black leading-tight">{t.title}</h3>
        <span className="mt-1.5 inline-block rounded-full bg-black/20 px-2 py-0.5 text-[11px] font-semibold">{t.status_label}</span>
      </header>
      <div className="flex flex-1 flex-col gap-3 p-4">
        {t.leaders.length === 0 ? (
          <p className="text-sm text-muted">
            {t.code === "best_player" && t.status === "upcoming" ? "Désigné par le vote du public en fin de saison." : "Aucun prétendant pour le moment."}
          </p>
        ) : (
          <ul className="space-y-2">
            {t.leaders.slice(0, compact ? 2 : 3).map((l) => (
              <li key={`${l.display_name}-${l.team?.id}`} className="flex items-center gap-2.5">
                {l.team && <TeamBadge team={l.team} size="md" />}
                <span className="min-w-0 flex-1 leading-tight">
                  <Name c={l} />
                  <span className="mt-0.5 block truncate text-xs text-subtle">
                    <strong className="font-black text-heading">{a.unit(l.value)}</strong>
                    {l.detail ? ` · ${l.detail}` : l.team ? ` · ${l.team.name}` : ""}
                  </span>
                </span>
              </li>
            ))}
            {t.leaders.length > (compact ? 2 : 3) && (
              <li className="text-xs text-subtle">et {t.leaders.length - (compact ? 2 : 3)} autre(s) à égalité</li>
            )}
          </ul>
        )}
        {!compact && others.length > 0 && (
          <ol className="space-y-1 border-t border-line pt-2 text-sm">
            {others.slice(0, 3).map((c) => (
              <li key={`${c.display_name}-${c.team?.id}`} className="flex items-center gap-2">
                <span className="w-5 text-center text-xs font-bold text-subtle">{c.rank}</span>
                {c.team && <TeamBadge team={c.team} size="sm" />}
                <span className="min-w-0 flex-1 truncate">
                  <Name c={c} />
                </span>
                <span className="whitespace-nowrap text-xs font-semibold text-muted">{a.unit(c.value)}</span>
              </li>
            ))}
          </ol>
        )}
        <p className="mt-auto text-[11px] leading-snug text-subtle">{t.criterion}</p>
        {!compact && (
          <Link href={href} className="text-xs font-semibold text-lds-green hover:underline dark:text-green-300">
            {t.ballot_id ? (t.status === "vote_open" ? "Voter →" : "Voir le vote →") : "Voir le classement →"}
          </Link>
        )}
      </div>
    </article>
  );
}

export function TrophyRace({ trophies, compact = false }: { trophies: Trophy[]; compact?: boolean }) {
  return (
    <div className={`grid gap-3 ${compact ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-5" : "sm:grid-cols-2 xl:grid-cols-5"}`}>
      {trophies.map((t) => (
        <TrophyCard key={t.code} t={t} compact={compact} />
      ))}
    </div>
  );
}
