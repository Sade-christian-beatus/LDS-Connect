// Tableau des phases finales en arbre : quarts et demi-finale de chaque côté, finale au centre.
import { scoreSpeech } from "@/lib/a11y";
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
    return side === "home" ? (match.home_penalties ?? 0) > (match.away_penalties ?? 0) : (match.away_penalties ?? 0) > (match.home_penalties ?? 0);
  };
  const row = (side: "home" | "away") => {
    const team = match?.[side];
    const score = side === "home" ? match?.home_score : match?.away_score;
    const pens = side === "home" ? match?.home_penalties : match?.away_penalties;
    return (
      <div className={`flex items-center gap-2 px-2 py-1 ${winner(side) ? "font-bold" : ""}`}>
        {team ? <TeamBadge team={team} size="sm" /> : <span className="h-7 w-7 rounded-full bg-stone-200" />}
        <span className={`flex-1 truncate text-sm ${team ? "" : "italic text-subtle"}`}>{team?.short_name ?? "À déterminer"}</span>
        {score != null && (
          <span className="tabular-nums">
            {score}
            {pens != null && <sup className="ml-0.5 text-[10px] text-subtle">({pens})</sup>}
          </span>
        )}
      </div>
    );
  };
  return (
    <div className="w-full rounded-lg border border-line bg-surface shadow-sm">
      <div className="flex justify-between border-b border-line px-2 py-0.5 text-[10px] uppercase tracking-wide text-subtle">
        <span>{title}</span>
        {match?.status === "live" ? (
          <span className="font-semibold text-lds-red">● En direct</span>
        ) : (
          match?.kickoff_at && (
            <span>
              {formatDate(match.kickoff_at).split(" ").slice(0, 3).join(" ")} · {formatTime(match.kickoff_at)}
            </span>
          )
        )}
      </div>
      {row("home")}
      {row("away")}
    </div>
  );
}

/** Phrase lue par le lecteur d'écran pour un match du tableau. */
function slotSpeech(match: Match | undefined, title: string) {
  if (!match) return `${title} : à déterminer.`;
  const teams = `${match.home?.name ?? "à déterminer"} contre ${match.away?.name ?? "à déterminer"}`;
  const score = scoreSpeech(match);
  const when = match.kickoff_at ? `, ${formatDate(match.kickoff_at)} à ${formatTime(match.kickoff_at)}` : "";
  return `${title} : ${teams}${score ? `, ${score}` : when}.`;
}

const ORDER: [string, string][] = [
  ["QF1", "Quart de finale 1"],
  ["QF2", "Quart de finale 2"],
  ["QF3", "Quart de finale 3"],
  ["QF4", "Quart de finale 4"],
  ["SF1", "Demi-finale 1"],
  ["SF2", "Demi-finale 2"],
  ["P3", "Match pour la 3e place"],
  ["F", "Finale"],
];

export function BracketTree({ matches }: { matches: Match[] }) {
  const by = Object.fromEntries(matches.map((m) => [m.bracket_slot, m]));
  if (matches.length === 0) return <p className="text-sm text-muted">Le tableau final sera publié à l&apos;issue de la phase de poules.</p>;
  return (
    <>
      {/* Lecteur d'écran : les matchs dans l'ordre de la compétition (l'arbre se lit en miroir) */}
      <ol className="sr-only">
        {ORDER.filter(([slot]) => slot !== "P3" || by.P3).map(([slot, title]) => (
          <li key={slot}>{slotSpeech(by[slot], title)}</li>
        ))}
      </ol>
      <div aria-hidden className="overflow-x-auto">
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
    </>
  );
}
