"use client";
import { useLiveQuery } from "dexie-react-hooks";
import Link from "next/link";
import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { TeamBadge } from "@/components/TeamBadge";
import { NetworkError, useAuth } from "@/lib/auth";
import { formatDate, formatTime, PHASE_LABEL, SHEET_STATUS_LABEL } from "@/lib/format";
import { db } from "@/lib/offline/db";
import type { DelegateMatch } from "@/lib/types";

export default function DeleguePage() {
  return (
    <RequireAuth permission="sheet:edit">
      <MatchList />
    </RequireAuth>
  );
}

function MatchList() {
  const { api } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const key = showAll ? "delegate:all" : "delegate:upcoming";
  const cached = useLiveQuery(() => db.lists.get(key), [key]);

  useEffect(() => {
    api<DelegateMatch[]>(`/delegate/matches${showAll ? "?all=true" : ""}`)
      .then((matches) => db.lists.put({ key, matches, savedAt: Date.now() }))
      .then(() => setError(null))
      .catch((e) => {
        if (!(e instanceof NetworkError)) setError(e.message);
      });
  }, [api, key, showAll]);

  const matches = cached?.matches ?? [];
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-green-900">Mes matchs</h1>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          Toute la saison
        </label>
      </div>
      {error && <p className="rounded bg-red-50 p-2 text-sm text-lds-red">{error}</p>}
      {cached && (
        <p className="text-xs text-stone-500">
          Liste enregistrée sur l&apos;appareil le {new Date(cached.savedAt).toLocaleString("fr-FR")}
        </p>
      )}
      {matches.length === 0 && <p className="text-stone-600">Aucun match à traiter.</p>}
      <ul className="space-y-2">
        {matches.map((m) => (
          <li key={m.id}>
            <Link
              href={`/delegue/match/${m.id}`}
              className="block rounded-lg border border-stone-200 bg-white p-3 hover:border-lds-green"
            >
              <div className="flex justify-between text-xs text-stone-500">
                <span>
                  {formatDate(m.kickoff_at)} · {formatTime(m.kickoff_at)}
                </span>
                <span>
                  {m.phase === "group" ? `Poule ${m.pool_code} · J${m.round_number}` : PHASE_LABEL[m.phase]}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-2 font-medium">
                {m.home && <TeamBadge team={m.home} size="sm" />}
                <span className="flex-1">{m.home?.short_name}</span>
                <span className="tabular-nums">
                  {m.home_score ?? ""} – {m.away_score ?? ""}
                </span>
                <span className="flex-1 text-right">{m.away?.short_name}</span>
                {m.away && <TeamBadge team={m.away} size="sm" />}
              </div>
              <div className="mt-1 text-xs font-semibold text-lds-green">
                {m.sheet_status ? SHEET_STATUS_LABEL[m.sheet_status] : "Feuille non ouverte"}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
