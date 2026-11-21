"use client";
import { useMemo, useState } from "react";
import { EVENT_LABEL } from "@/lib/format";
import type { EventIn, EventType, Sheet } from "@/lib/types";

const TYPES: EventType[] = [
  "goal",
  "penalty_goal",
  "own_goal",
  "penalty_missed",
  "yellow_card",
  "second_yellow",
  "red_card",
  "substitution",
];

type Props = {
  sheet: Sheet;
  editable: boolean;
  onAdd: (e: EventIn) => Promise<void>;
  onDelete: (eventId: string) => Promise<void>;
};

/** Joueurs sur le terrain d'une équipe, d'après la composition et les événements déjà saisis. */
function onPitch(sheet: Sheet, side: "home" | "away"): Set<string> {
  const team = sheet[side];
  const set = new Set(team.lineup.filter((e) => e.role === "starter").map((e) => e.person_id));
  for (const e of sheet.events) {
    if (e.team_id !== team.team.id) continue;
    if (e.type === "substitution") {
      set.delete(e.person_id);
      if (e.related_person_id) set.add(e.related_person_id);
    }
    if (e.type === "red_card" || e.type === "second_yellow") set.delete(e.person_id);
  }
  return set;
}

export function EventsPanel({ sheet, editable, onAdd, onDelete }: Props) {
  const [side, setSide] = useState<"home" | "away">("home");
  const [type, setType] = useState<EventType>("goal");
  const [minute, setMinute] = useState("");
  const [person, setPerson] = useState("");
  const [related, setRelated] = useState("");
  const [busy, setBusy] = useState(false);

  const team = sheet[side];
  const names = useMemo(
    () => Object.fromEntries(team.lineup.map((e) => [e.person_id, `${e.shirt_number ?? ""} ${e.display_name}`])),
    [team],
  );
  const pitch = onPitch(sheet, side);
  const isCard = type.includes("card") || type === "second_yellow";
  const players = team.lineup.filter((e) => (isCard ? true : pitch.has(e.person_id)));
  const bench = team.lineup.filter(
    (e) =>
      e.role === "substitute" &&
      !pitch.has(e.person_id) &&
      !sheet.events.some((ev) => ev.type === "substitution" && ev.related_person_id === e.person_id),
  );
  const relatedOptions = type === "substitution" ? bench : players.filter((p) => p.person_id !== person && pitch.has(p.person_id));
  const showRelated = type === "substitution" || type === "goal" || type === "penalty_goal";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!person || minute === "") return;
    setBusy(true);
    try {
      await onAdd({
        client_uuid: crypto.randomUUID(),
        team_id: team.team.id,
        type,
        minute: Number(minute),
        person_id: person,
        related_person_id: related || null,
      });
      setPerson("");
      setRelated("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3">
      {editable && (
        <form onSubmit={submit} className="space-y-2 rounded-lg border border-stone-200 bg-white p-3" aria-label="Nouvel événement">
          <div className="grid grid-cols-2 gap-2">
            {(["home", "away"] as const).map((s) => (
              <button
                key={s}
                type="button"
                aria-pressed={side === s}
                onClick={() => {
                  setSide(s);
                  setPerson("");
                  setRelated("");
                }}
                className={`rounded py-2 text-sm font-semibold ${side === s ? "bg-lds-green text-white" : "bg-stone-100"}`}
              >
                {sheet[s].team.short_name}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-[1fr_5rem] gap-2">
            <label className="text-xs">
              Type
              <select aria-label="Type" value={type} onChange={(e) => setType(e.target.value as EventType)} className="mt-0.5 w-full rounded border px-2 py-2 text-sm">
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {EVENT_LABEL[t]}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs">
              Minute
              <input
                aria-label="Minute"
                type="number"
                inputMode="numeric"
                min={0}
                max={130}
                required
                value={minute}
                onChange={(e) => setMinute(e.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-2 text-sm"
              />
            </label>
          </div>
          <label className="block text-xs">
            {type === "substitution" ? "Joueur sortant" : "Joueur"}
            <select
              aria-label={type === "substitution" ? "Joueur sortant" : "Joueur"}
              required
              value={person}
              onChange={(e) => setPerson(e.target.value)} className="mt-0.5 w-full rounded border px-2 py-2 text-sm">
              <option value="">— choisir —</option>
              {players.map((p) => (
                <option key={p.person_id} value={p.person_id}>
                  {names[p.person_id]}
                </option>
              ))}
            </select>
          </label>
          {showRelated && (
            <label className="block text-xs">
              {type === "substitution" ? "Joueur entrant" : "Passeur décisif (facultatif)"}
              <select
                aria-label={type === "substitution" ? "Joueur entrant" : "Passeur décisif"}
                required={type === "substitution"}
                value={related}
                onChange={(e) => setRelated(e.target.value)}
                className="mt-0.5 w-full rounded border px-2 py-2 text-sm"
              >
                <option value="">— {type === "substitution" ? "choisir" : "aucun"} —</option>
                {relatedOptions.map((p) => (
                  <option key={p.person_id} value={p.person_id}>
                    {names[p.person_id]}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button type="submit" disabled={busy} className="w-full rounded bg-lds-green py-2 font-semibold text-white disabled:opacity-60">
            Ajouter l&apos;événement
          </button>
        </form>
      )}

      <ol className="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white" aria-label="Événements du match">
        {sheet.events.length === 0 && <li className="p-3 text-sm text-stone-500">Aucun événement.</li>}
        {sheet.events.map((e) => {
          const home = e.team_id === sheet.home.team.id;
          return (
            <li key={e.id} className={`flex items-center gap-2 px-3 py-2 text-sm ${home ? "" : "flex-row-reverse text-right"}`}>
              <span className="w-10 font-bold tabular-nums">{e.minute}&apos;</span>
              <span className="flex-1">
                <span className="font-medium">{EVENT_LABEL[e.type]}</span> — {e.person_name}
                {e.related_person_name && (
                  <span className="text-stone-500">
                    {e.type === "substitution" ? ` ↔ ${e.related_person_name}` : ` (passe : ${e.related_person_name})`}
                  </span>
                )}
              </span>
              {editable && (
                <button type="button" onClick={() => onDelete(e.id)} className="text-xs text-lds-red underline" aria-label="Supprimer l'événement">
                  Supprimer
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
