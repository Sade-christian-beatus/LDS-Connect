// Résultats d'un scrutin en barres horizontales (public et administration).
import type { BallotOut } from "@/lib/types";
import { TeamBadge } from "./TeamBadge";

type Results = NonNullable<BallotOut["results"]>;

export function ResultsBars({ results }: { results: Results }) {
  const max = Math.max(1, ...results.options.map((o) => o.votes));
  return (
    <ol className="space-y-2" aria-label="Résultats">
      {results.options.map((o) => (
        <li key={o.option_id} className="text-sm">
          <div className="flex items-center gap-2">
            <span className="w-5 text-right font-bold tabular-nums text-subtle">{o.rank}</span>
            {o.team && <TeamBadge team={o.team} size="sm" />}
            <span className="flex-1 font-medium">{o.label}</span>
            <span className="tabular-nums">
              {o.votes} voix · {(o.share * 100).toFixed(1).replace(".", ",")} %
            </span>
          </div>
          <div aria-hidden className="ml-7 mt-1 h-2 rounded bg-soft">
            <div className="h-2 rounded bg-lds-green" style={{ width: `${(o.votes / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ol>
  );
}
