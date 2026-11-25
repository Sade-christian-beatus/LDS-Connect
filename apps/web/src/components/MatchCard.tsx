import Link from "next/link";
import { formatTime, PHASE_LABEL } from "@/lib/format";
import type { Match } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

function Side({ team, align, winner }: { team: Match["home"]; align: "left" | "right"; winner: boolean | null }) {
  if (!team) return <span className={`flex-1 text-sm italic text-subtle ${align === "right" ? "text-right" : ""}`}>À déterminer</span>;
  return (
    <Link
      href={`/equipes/${team.slug}`}
      className={`flex min-w-0 flex-1 items-center gap-2 hover:underline sm:gap-2.5 ${align === "right" ? "flex-row-reverse text-right" : ""}`}
    >
      <TeamBadge team={team} size="card" />
      {/* Noms d'un seul mot très longs (« Sennatantola ») : coupés plutôt que de déborder */}
      <span
        lang="fr"
        className={`line-clamp-2 min-w-0 hyphens-auto text-[13px] leading-tight [overflow-wrap:anywhere] sm:text-[15px] ${winner === false ? "text-muted" : "font-semibold"}`}
      >
        <span className="sm:hidden">{team.short_name}</span>
        <span className="hidden sm:inline">{team.name}</span>
      </span>
    </Link>
  );
}

/** Carte de match : bandes aux couleurs des équipes, score en grand. */
export function MatchCard({ match }: { match: Match }) {
  const live = match.status === "live";
  const done = match.status === "finished";
  const showScore = live || done;
  const hs = match.home_score ?? 0;
  const as = match.away_score ?? 0;
  const homeWins = done ? hs > as || (hs === as && (match.home_penalties ?? 0) > (match.away_penalties ?? 0)) : null;
  const awayWins = done ? as > hs || (hs === as && (match.away_penalties ?? 0) > (match.home_penalties ?? 0)) : null;
  return (
    <div
      className={`relative flex min-w-0 items-center gap-2 overflow-hidden rounded-xl border bg-surface px-3 py-3 shadow-sm sm:gap-3 sm:px-4 ${
        live ? "border-lds-red/60 ring-1 ring-lds-red/30" : "border-line"
      }`}
    >
      <span aria-hidden className="absolute inset-y-0 left-0 w-1.5" style={{ backgroundColor: match.home?.primary_color ?? "transparent" }} />
      <span aria-hidden className="absolute inset-y-0 right-0 w-1.5" style={{ backgroundColor: match.away?.primary_color ?? "transparent" }} />
      <Side team={match.home} align="left" winner={homeWins} />
      <div className="w-[4.25rem] shrink-0 text-center sm:w-24">
        {showScore ? (
          <div className={`text-2xl font-black tabular-nums tracking-tight ${live ? "text-lds-red" : ""}`}>
            {match.home_score}
            <span className="mx-1 text-subtle">–</span>
            {match.away_score}
          </div>
        ) : (
          <div className="inline-block rounded-lg bg-soft px-2.5 py-1 text-base font-bold tabular-nums">{formatTime(match.kickoff_at) || "—"}</div>
        )}
        <div className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-subtle">
          {live ? (
            <span className="inline-flex items-center gap-1 font-bold text-lds-red">
              <span className="h-1.5 w-1.5 animate-live rounded-full bg-lds-red" /> {match.live_minute ?? 0}&apos;
            </span>
          ) : done ? (
            match.home_penalties != null ? (
              `t.a.b. ${match.home_penalties}–${match.away_penalties}`
            ) : (
              "Terminé"
            )
          ) : match.status === "postponed" ? (
            "Reporté"
          ) : match.phase !== "group" ? (
            PHASE_LABEL[match.phase]
          ) : (
            `Journée ${match.round_number}`
          )}
        </div>
      </div>
      <Side team={match.away} align="right" winner={awayWins} />
    </div>
  );
}
