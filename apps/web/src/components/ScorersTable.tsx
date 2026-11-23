import Link from "next/link";
import type { StatRow } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

const MEDAL = ["bg-lds-gold text-pitch", "bg-stone-300 text-stone-800", "bg-amber-700 text-white"];

export function ScorersTable({ rows, unit, empty }: { rows: StatRow[]; unit: string; empty: string }) {
  if (rows.length === 0) return <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">{empty}</p>;
  return (
    <ol className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      {rows.map((r) => (
        <li key={`${r.person_id}-${r.team.id}`} className="flex items-center gap-3 px-4 py-2.5 text-sm">
          <span
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-black tabular-nums ${
              r.rank <= 3 ? MEDAL[r.rank - 1] : "bg-soft text-muted"
            }`}
          >
            {r.rank}
          </span>
          <TeamBadge team={r.team} size="sm" />
          <span className="min-w-0 flex-1">
            <Link href={`/joueurs/${r.person_id}`} className="block truncate font-semibold hover:underline">
              {r.display_name}
            </Link>
            <Link href={`/equipes/${r.team.slug}`} className="block truncate text-xs text-subtle hover:underline">
              {r.team.name}
            </Link>
          </span>
          {r.penalties > 0 && <span className="text-xs text-subtle">dont {r.penalties} pén.</span>}
          <span className="text-right" title={unit}>
            <span className="text-xl font-black tabular-nums text-heading">{r.value}</span>
            <span className="ml-1 text-[11px] text-subtle">{r.value === 1 ? unit.replace(/s\b/g, "") : unit}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
