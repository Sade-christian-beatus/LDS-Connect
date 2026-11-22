// Tableau des phases finales en arbre : quarts et demi-finale de chaque côté, finale au centre.
import { formatDate, formatTime } from "@/lib/format";
import type { Match } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

function Slot({ match, title }: { match?: Match; title: string }) {
  const done = match?.status === "finished";
  const winner = (side: "home" | "away") => {
    if (!done || !match) return false;
    const h = match.home_score ?? 0;
    const a = match.away_score ?? 0;
    if (h !== a) return side === "home" ? h > a : a > h;
    return side === "home"
      ? (match.home_penalties ?? 0) > (match.away_penalties ?? 0)
      : (match.away_penalties ?? 0) > (match.home_penalties ?? 0);
  };
  const row = (side: "home" | "away") => {
    const team = match?.[side];
    const score = side === "home" ? match?.home_score : match?.away_score;
    const pens = side === "home" ? match?.home_penalties : match?.away_penalties;
    return (
      <div className={`flex items-center gap-2 px-2 py-1 ${winner(side) ? "font-bold" : ""}`}>
        {team ? <TeamBadge team={team} size="sm" /> : <span className="h-7 w-7 rounded-full bg-stone-200" />}
        <span className={`flex-1 truncate text-sm ${team ? "" : "italic text-stone-400"}`}>{team?.short_name ?? "À déterminer"}</span>
        {score != null && (
          <span className="tabular-nums">
            {score}
            {pens != null && <sup className="ml-0.5 text-[10px] text-stone-500">({pens})</sup>}
          </span>
        )}
      </div>
    );
  };
  return (
    <div className="w-full rounded-lg border border-stone-200 bg-white shadow-sm">
      <div className="flex justify-between border-b border-stone-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-stone-500">
        <span>{title}</span>
        {match?.status === "live" ? (
          <span className="font-semibold text-lds-red">● En direct</span>
        ) : (
          match?.kickoff_at && <span>{formatDate(match.kickoff_at).split(" ").slice(0, 3).join(" ")} · {formatTime(match.kickoff_at)}</span>
        )}
      </div>
      {row("home")}
      {row("away")}
    </div>
  );
}

export function BracketTree({ matches }: { matches: Match[] }) {
  const by = Object.fromEntries(matches.map((m) => [m.bracket_slot, m]));
  if (matches.length === 0) return <p className="text-sm text-stone-600">Le tableau final sera publié à l&apos;issue de la phase de poules.</p>;
  return (
    <div className="overflow-x-auto">
      <div className="grid min-w-[56rem] grid-cols-5 items-center gap-4">
        <div className="space-y-6">
          <Slot match={by.QF1} title="Quart 1" />
          <Slot match={by.QF2} title="Quart 2" />
        </div>
        <Slot match={by.SF1} title="Demi-finale 1" />
        <div className="space-y-3 text-center">
          <div className="text-4xl" aria-hidden>
            🏆
          </div>
          <Slot match={by.F} title="Finale" />
          {by.P3 && (
            <div className="pt-4">
              <Slot match={by.P3} title="3e place" />
            </div>
          )}
        </div>
        <Slot match={by.SF2} title="Demi-finale 2" />
        <div className="space-y-6">
          <Slot match={by.QF3} title="Quart 3" />
          <Slot match={by.QF4} title="Quart 4" />
        </div>
      </div>
    </div>
  );
}
