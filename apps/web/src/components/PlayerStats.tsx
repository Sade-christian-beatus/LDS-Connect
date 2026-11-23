// Chiffres d'un joueur et son parcours match par match (site public et espace officiels).
import Link from "next/link";
import type { MatchLog, StatValues } from "@/lib/types";

export function StatTiles({ stats, goalkeeper = false }: { stats: StatValues; goalkeeper?: boolean }) {
  const tiles: [string, string | number][] = [
    ["Matchs", stats.appearances],
    ["Titularisations", stats.starts],
    ["Minutes", stats.minutes_played.toLocaleString("fr-FR")],
    goalkeeper ? ["Clean sheets", stats.clean_sheets] : ["Buts", stats.goals],
    ["Passes décisives", stats.assists],
    ["Buts / 90 min", stats.goals_per_90 != null ? stats.goals_per_90.toLocaleString("fr-FR") : "—"],
    ["Cartons", `${stats.yellow_cards} J · ${stats.red_cards} R`],
    ["Homme du match", stats.man_of_the_match],
  ];
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map(([label, value]) => (
        <div key={label} className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
          <dt className="text-xs font-semibold uppercase tracking-wide text-subtle">{label}</dt>
          <dd className="mt-1 text-2xl font-black tabular-nums text-heading">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function MatchLogList({ matches, teamId }: { matches: MatchLog[]; teamId?: string }) {
  if (matches.length === 0) {
    return <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">Aucun match officiel joué pour le moment.</p>;
  }
  return (
    <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      {matches.map((l) => {
        const m = l.match;
        const home = m.home?.id === (teamId ?? l.team_id);
        const opp = home ? m.away : m.home;
        const mine = home ? m.home_score : m.away_score;
        const theirs = home ? m.away_score : m.home_score;
        const res = mine == null || theirs == null ? null : mine > theirs ? "V" : mine === theirs ? "N" : "D";
        return (
          <li key={m.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black text-white ${
                res === "V" ? "bg-green-600" : res === "D" ? "bg-lds-red" : "bg-stone-400"
              }`}
              title={res === "V" ? "Victoire" : res === "D" ? "Défaite" : "Nul"}
            >
              {res ?? "–"}
            </span>
            <span className="min-w-40 flex-1">
              <span className="font-semibold">
                {home ? "contre" : "à"} {opp ? <Link href={`/equipes/${opp.slug}`} className="hover:underline">{opp.short_name}</Link> : "?"}
              </span>
              <span className="ml-2 tabular-nums text-muted">
                {mine}–{theirs}
              </span>
              <span className="block text-xs text-subtle">
                {m.kickoff_at ? new Date(m.kickoff_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }) : ""}
                {m.round_number ? ` · J${m.round_number}` : ""}
              </span>
            </span>
            <span className="w-20 text-xs text-muted">
              {l.started ? "Titulaire" : "Entré"} · {l.minutes}&apos;
            </span>
            <span className="flex min-w-24 justify-end gap-1.5 text-xs">
              {l.goals > 0 && <span className="rounded-full bg-qualify px-2 py-0.5 font-bold">⚽ {l.goals}</span>}
              {l.assists > 0 && <span className="rounded-full bg-soft px-2 py-0.5 font-bold">🅰 {l.assists}</span>}
              {l.yellow_cards > 0 && <span className="inline-block h-4 w-3 rounded-sm bg-yellow-400" title="Carton jaune" />}
              {l.red_cards > 0 && <span className="inline-block h-4 w-3 rounded-sm bg-lds-red" title="Carton rouge" />}
              {l.clean_sheet && <span className="rounded-full bg-soft px-2 py-0.5 font-bold">Clean sheet</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
