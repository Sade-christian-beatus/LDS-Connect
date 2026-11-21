"use client";
import { useMemo, useState } from "react";
import { POSITION_LABEL } from "@/lib/format";
import type { LineupEntryIn, TeamSheet } from "@/lib/types";
import { suggestLineup } from "./suggest";

type Role = "starter" | "substitute" | null;
type Choice = { role: Role; gk: boolean; captain: boolean };

type Props = {
  side: TeamSheet;
  startersCount: number;
  maxSubs: number;
  editable: boolean;
  onSave: (entries: LineupEntryIn[]) => Promise<void>;
};

function fromLineup(side: TeamSheet): Record<string, Choice> {
  return Object.fromEntries(
    side.lineup.map((e) => [e.person_id, { role: e.role, gk: !!e.is_goalkeeper, captain: !!e.is_captain }]),
  );
}

export function LineupEditor({ side, startersCount, maxSubs, editable, onSave }: Props) {
  const [choices, setChoices] = useState<Record<string, Choice>>(() => fromLineup(side));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const serverKey = JSON.stringify(side.lineup);
  const [seenKey, setSeenKey] = useState(serverKey);

  // Nouvelle version reçue du serveur : on la reprend si rien n'est en cours de modification
  if (serverKey !== seenKey) {
    setSeenKey(serverKey);
    if (!dirty) setChoices(fromLineup(side));
  }

  const set = (id: string, patch: Partial<Choice>) => {
    setDirty(true);
    setChoices((prev) => {
      const next = { ...prev };
      const cur = next[id] ?? { role: null, gk: false, captain: false };
      if (patch.captain) for (const k of Object.keys(next)) next[k] = { ...next[k], captain: false };
      next[id] = { ...cur, ...patch };
      if (next[id].role === null) next[id] = { role: null, gk: false, captain: false };
      return next;
    });
  };

  const cands = side.candidates;
  const stats = useMemo(() => {
    const starters = cands.filter((c) => choices[c.person_id]?.role === "starter");
    return {
      starters: starters.length,
      subs: cands.filter((c) => choices[c.person_id]?.role === "substitute").length,
      locals: starters.filter((c) => c.is_local).length,
    };
  }, [cands, choices]);

  const entries = (): LineupEntryIn[] =>
    cands
      .filter((c) => choices[c.person_id]?.role)
      .map((c) => ({
        person_id: c.person_id,
        role: choices[c.person_id].role!,
        shirt_number: c.shirt_number,
        is_goalkeeper: choices[c.person_id].gk,
        is_captain: choices[c.person_id].captain,
      }));

  const localsOk = stats.locals >= side.local_starters_required;
  return (
    <section className="space-y-3" aria-label={`Composition ${side.team.name}`}>
      <div className="sticky top-10 z-[5] flex flex-wrap gap-2 bg-stone-50 py-2 text-sm">
        <Counter label="Titulaires" value={`${stats.starters}/${startersCount}`} ok={stats.starters === startersCount} />
        <Counter label="Remplaçants" value={`${stats.subs}/${maxSubs}`} ok={stats.subs <= maxSubs} />
        <Counter
          label="Locaux titulaires"
          value={`${stats.locals} (min. ${side.local_starters_required})`}
          ok={localsOk}
        />
      </div>

      {!dirty && side.violations.length > 0 && side.lineup.length > 0 && (
        <ul className="rounded border border-red-200 bg-red-50 p-2 text-sm text-lds-red" role="alert">
          {side.violations.map((v, i) => (
            <li key={i}>• {v.message}</li>
          ))}
        </ul>
      )}
      {!dirty && side.lineup.length > 0 && side.violations.length === 0 && (
        <p className="rounded bg-green-50 p-2 text-sm text-green-800">✓ Composition conforme</p>
      )}

      {editable && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded border border-lds-green px-3 py-1.5 text-sm text-lds-green"
            onClick={() => {
              const s = suggestLineup(cands, startersCount, maxSubs, side.local_starters_required);
              setDirty(true);
              setChoices(
                Object.fromEntries(
                  s.map((e) => [e.person_id, { role: e.role, gk: !!e.is_goalkeeper, captain: !!e.is_captain }]),
                ),
              );
            }}
          >
            Proposer une composition conforme
          </button>
          <button
            type="button"
            disabled={!dirty || saving}
            className="rounded bg-lds-green px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
            onClick={async () => {
              setSaving(true);
              try {
                await onSave(entries());
                setDirty(false);
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Enregistrement…" : "Enregistrer la composition"}
          </button>
        </div>
      )}

      <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white">
        {cands.map((c) => {
          const ch = choices[c.person_id] ?? { role: null, gk: false, captain: false };
          const blocked = !c.licence_ok || c.is_suspended;
          return (
            <li key={c.person_id} className={`flex flex-wrap items-center gap-2 px-2 py-1.5 text-sm ${blocked ? "opacity-60" : ""}`}>
              <span className="w-6 text-right font-bold tabular-nums">{c.shirt_number ?? "–"}</span>
              <span className="min-w-0 flex-1">
                <span className="font-medium">{c.full_name}</span>
                <span className="ml-1 text-xs text-stone-500">
                  {POSITION_LABEL[c.position]} · {c.age} ans
                </span>
                <span className="ml-1 inline-flex gap-1 text-[10px] font-semibold uppercase">
                  {c.is_local ? (
                    <span className="rounded bg-green-100 px-1 text-green-800">Local</span>
                  ) : (
                    <span className="rounded bg-stone-100 px-1 text-stone-600">Non local</span>
                  )}
                  {!c.licence_ok && <span className="rounded bg-red-100 px-1 text-lds-red">Licence</span>}
                  {c.is_suspended && <span className="rounded bg-red-100 px-1 text-lds-red">Suspendu</span>}
                </span>
              </span>
              {editable ? (
                <span className="flex items-center gap-1">
                  {(["starter", "substitute"] as const).map((r) => (
                    <button
                      key={r}
                      type="button"
                      aria-pressed={ch.role === r}
                      onClick={() => set(c.person_id, { role: ch.role === r ? null : r })}
                      className={`rounded px-2 py-0.5 text-xs ${ch.role === r ? "bg-lds-green text-white" : "bg-stone-100"}`}
                    >
                      {r === "starter" ? "Titulaire" : "Remplaçant"}
                    </button>
                  ))}
                  {ch.role === "starter" && (
                    <>
                      <label className="flex items-center gap-0.5 text-xs" title="Gardien">
                        <input type="checkbox" checked={ch.gk} onChange={(e) => set(c.person_id, { gk: e.target.checked })} />
                        G
                      </label>
                      <label className="flex items-center gap-0.5 text-xs" title="Capitaine">
                        <input
                          type="radio"
                          name={`captain-${side.team.id}`}
                          checked={ch.captain}
                          onChange={() => set(c.person_id, { captain: true })}
                        />
                        C
                      </label>
                    </>
                  )}
                </span>
              ) : (
                ch.role && (
                  <span className="text-xs text-stone-600">
                    {ch.role === "starter" ? "Titulaire" : "Remplaçant"}
                    {ch.gk ? " · G" : ""}
                    {ch.captain ? " · C" : ""}
                  </span>
                )
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function Counter({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <span className={`rounded-full px-3 py-1 font-semibold ${ok ? "bg-green-100 text-green-800" : "bg-red-100 text-lds-red"}`}>
      {label} : {value}
    </span>
  );
}
