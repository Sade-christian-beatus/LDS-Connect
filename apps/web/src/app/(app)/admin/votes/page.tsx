"use client";
import Link from "next/link";
import { Badge } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { BALLOT_KIND_LABEL, ballotBadge, formatDateTime } from "@/lib/format";
import type { BallotAdmin } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function VotesAdminPage() {
  return (
    <RequireAuth permission="vote:manage">
      <BallotList />
    </RequireAuth>
  );
}

function BallotList() {
  const { data, error } = useApi<BallotAdmin[]>("/admin/ballots");
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold text-green-900">Votes du public</h1>
        <Link href="/admin/votes/nouveau" className="rounded bg-lds-green px-3 py-1.5 text-sm font-semibold text-white">
          + Nouveau scrutin
        </Link>
      </div>
      <p className="text-sm text-stone-600">
        Un vote par numéro de téléphone et par scrutin, confirmé par code SMS. Les votes suspects (votes en masse) sont mis
        de côté et ne comptent qu&apos;après examen.
      </p>
      {error && <p className="text-lds-red">{error}</p>}
      {data && data.length === 0 && <p className="text-stone-600">Aucun scrutin pour le moment.</p>}
      <ul className="space-y-2">
        {data?.map((b) => {
          const st = ballotBadge(b);
          return (
            <li key={b.id}>
              <Link
                href={`/admin/votes/${b.id}`}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-stone-200 bg-white p-3 hover:border-lds-green"
              >
                <span className="flex-1">
                  <span className="block font-semibold">{b.title}</span>
                  <span className="text-xs text-stone-500">
                    {BALLOT_KIND_LABEL[b.kind]} · du {formatDateTime(b.opens_at)} au {formatDateTime(b.closes_at)}
                  </span>
                </span>
                <span className="text-sm tabular-nums">{b.results?.participants ?? 0} votant(s)</span>
                {b.flagged_voters > 0 && <Badge tone="red">{b.flagged_voters} à examiner</Badge>}
                <Badge tone={st.tone}>{st.label}</Badge>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
