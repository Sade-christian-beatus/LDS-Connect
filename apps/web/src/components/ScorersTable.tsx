import Link from "next/link";
import type { StatRow } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

export function ScorersTable({ rows, unit, empty }: { rows: StatRow[]; unit: string; empty: string }) {
  if (rows.length === 0) return <p className="text-sm text-stone-600">{empty}</p>;
  return (
    <ol className="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white">
      {rows.map((r) => (
        <li key={`${r.person_id}-${r.team.id}`} className="flex items-center gap-3 px-3 py-2 text-sm">
          <span className={`w-6 text-right font-bold tabular-nums ${r.rank === 1 ? "text-lds-gold" : "text-stone-500"}`}>{r.rank}</span>
          <TeamBadge team={r.team} size="sm" />
          <span className="flex-1">
            <span className="font-medium">{r.display_name}</span>
            <Link href={`/equipes/${r.team.slug}`} className="block text-xs text-stone-500 hover:underline">
              {r.team.name}
            </Link>
          </span>
          <span className="rounded-full bg-lds-green px-2.5 py-0.5 text-sm font-bold tabular-nums text-white" title={unit}>
            {r.value}
          </span>
          {r.penalties > 0 && <span className="text-xs text-stone-500">dont {r.penalties} pén.</span>}
        </li>
      ))}
    </ol>
  );
}
