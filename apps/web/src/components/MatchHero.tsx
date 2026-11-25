// Bandeau d'un match (accueil, billetterie, billets) : équipes en grand, date, stade.
import { PitchLines } from "./Illustrations";
import { formatDate, formatTime, PHASE_LABEL } from "@/lib/format";
import type { Match } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

function Team({ team }: { team: Match["home"] }) {
  return (
    <div className="flex min-w-0 flex-1 flex-col items-center gap-2 text-center">
      {team ? <TeamBadge team={team} size="hero" /> : <span className="h-16 w-16 rounded-2xl bg-white/10 sm:h-24 sm:w-24" />}
      <span className="line-clamp-2 text-sm font-bold leading-tight sm:text-base">{team?.name ?? "À déterminer"}</span>
    </div>
  );
}

export function MatchHero({ match, children, compact = false }: { match: Match; children?: React.ReactNode; compact?: boolean }) {
  const live = match.status === "live";
  const done = match.status === "finished";
  const stage = match.phase === "group" ? `Poule ${match.pool_code} · Journée ${match.round_number}` : PHASE_LABEL[match.phase];
  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-green-950 via-green-900 to-lds-green text-white shadow-lg">
      <PitchLines className="text-white/[0.07]" />
      <div aria-hidden className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full border-[24px] border-white/5" />
      <div aria-hidden className="pointer-events-none absolute -bottom-20 -left-10 h-48 w-48 rounded-full border-[18px] border-yellow-400/10" />
      <div className={`relative ${compact ? "p-4" : "p-5 sm:p-7"}`}>
        <p className="text-center text-xs font-semibold uppercase tracking-widest text-yellow-300">{stage}</p>
        <div className="mt-3 flex items-center gap-3">
          <Team team={match.home} />
          <div className="w-28 shrink-0 text-center">
            {live || done ? (
              <p className={`text-4xl font-black tabular-nums ${live ? "text-yellow-300" : ""}`}>
                {match.home_score}–{match.away_score}
              </p>
            ) : (
              <p className="text-3xl font-black tabular-nums">{formatTime(match.kickoff_at) || "—"}</p>
            )}
            <p className="mt-1 text-xs text-green-100">
              {live ? `● En direct ${match.live_minute ?? 0}'` : done ? "Terminé" : formatDate(match.kickoff_at)}
            </p>
          </div>
          <Team team={match.away} />
        </div>
        {match.venue && (
          <p className="mt-4 text-center text-sm text-green-100">
            {match.venue.name} · {match.venue.city}
          </p>
        )}
        {children && <div className="mt-4">{children}</div>}
      </div>
      <div aria-hidden className="flex h-1.5">
        <span className="flex-1 bg-lds-red" />
        <span className="flex-1 bg-yellow-400" />
        <span className="flex-1 bg-lds-green" />
      </div>
    </div>
  );
}
