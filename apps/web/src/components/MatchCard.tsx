import Link from "next/link";
import { formatTime, PHASE_LABEL } from "@/lib/format";
import type { Match } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

function Side({ team, align }: { team: Match["home"]; align: "left" | "right" }) {
  if (!team) return <span className="flex-1 text-sm italic text-stone-400">À déterminer</span>;
  return (
    <Link
      href={`/equipes/${team.slug}`}
      className={`flex flex-1 items-center gap-2 hover:underline ${align === "right" ? "flex-row-reverse text-right" : ""}`}
    >
      <TeamBadge team={team} size="sm" />
      <span className="text-sm font-medium leading-tight">{team.name}</span>
    </Link>
  );
}

export function MatchCard({ match }: { match: Match }) {
  const live = match.status === "live";
  const done = match.status === "finished";
  const showScore = live || done;
  return (
    <div className="flex items-center gap-3 rounded-lg border border-stone-200 bg-white px-3 py-2">
      <Side team={match.home} align="left" />
      <div className="w-24 text-center">
        {showScore ? (
          <div className={`text-lg font-bold tabular-nums ${live ? "text-lds-red" : ""}`}>
            {match.home_score} – {match.away_score}
          </div>
        ) : (
          <div className="text-sm font-semibold text-stone-700">{formatTime(match.kickoff_at)}</div>
        )}
        <div className="text-[11px] text-stone-500">
          {live ? (
            <span className="font-semibold text-lds-red">● En direct {match.live_minute ?? 0}&apos;</span>
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
            `J${match.round_number}`
          )}
        </div>
      </div>
      <Side team={match.away} align="right" />
    </div>
  );
}
