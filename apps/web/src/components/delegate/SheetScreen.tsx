"use client";
import Link from "next/link";
import { useState } from "react";
import { TeamBadge } from "@/components/TeamBadge";
import { formatDate, formatTime, SHEET_STATUS_LABEL } from "@/lib/format";
import { useSheet } from "@/lib/offline/use-sheet";
import type { Sheet } from "@/lib/types";
import { EventsPanel } from "./EventsPanel";
import { LineupEditor } from "./LineupEditor";

type Tab = "home" | "away" | "match" | "infos";

export function SheetScreen({ matchId }: { matchId: string }) {
  const { sheet, loading, error, online, pendingCount, failed, enqueue, discardFailed } = useSheet(matchId);
  const [tab, setTab] = useState<Tab | null>(null);

  if (!sheet) {
    if (loading) return <p className="text-stone-500">Chargement de la feuille…</p>;
    return (
      <p className="text-lds-red">
        {error ?? "Feuille indisponible hors connexion : ouvrez-la une première fois avec du réseau."}
      </p>
    );
  }

  const draft = sheet.status === "draft";
  const live = sheet.status === "submitted";
  const current: Tab = tab ?? (draft ? "home" : "match");
  const ready = sheet.home.violations.length === 0 && sheet.away.violations.length === 0;

  return (
    <div className="mx-auto max-w-3xl space-y-3 pb-20">
      <Link href="/delegue" className="text-sm text-lds-green underline">
        ← Mes matchs
      </Link>
      <Scoreboard sheet={sheet} />

      {(pendingCount > 0 || failed || error) && (
        // Barre fixe en bas d'écran : son apparition ne décale jamais les boutons sous le doigt
        <div
          role="status"
          className={`fixed inset-x-0 bottom-0 z-20 border-t p-3 text-sm shadow-lg ${failed || error ? "border-red-200 bg-red-50 text-lds-red" : "border-amber-200 bg-amber-50 text-amber-900"}`}
        >
          {failed ? (
            <>
              <strong>Action refusée par le serveur :</strong> {failed.error}{" "}
              <button type="button" className="underline" onClick={discardFailed}>
                Abandonner cette action (et les suivantes)
              </button>
            </>
          ) : error ? (
            error
          ) : (
            <>
              {pendingCount} action(s) en attente de synchronisation
              {online ? "…" : " — elles seront envoyées au retour du réseau."}
            </>
          )}
        </div>
      )}

      <nav className="grid grid-cols-4 gap-1 text-sm" aria-label="Sections de la feuille">
        {(
          [
            ["home", sheet.home.team.short_name],
            ["away", sheet.away.team.short_name],
            ["match", "Match"],
            ["infos", "Infos"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-current={current === key}
            onClick={() => setTab(key)}
            className={`truncate rounded py-2 font-semibold ${current === key ? "bg-lds-green text-white" : "bg-white ring-1 ring-stone-200"}`}
          >
            {label}
          </button>
        ))}
      </nav>

      {(current === "home" || current === "away") && (
        <LineupEditor
          key={sheet[current].team.id}
          side={sheet[current]}
          startersCount={sheet.starters_count}
          maxSubs={sheet.max_substitutes}
          editable={draft}
          onSave={(entries) => enqueue({ kind: "lineup", teamId: sheet[current].team.id, body: { entries } })}
        />
      )}

      {current === "match" &&
        (draft ? (
          <p className="rounded bg-white p-3 text-sm text-stone-600">
            Saisissez et enregistrez les deux compositions, puis soumettez la feuille avant le coup
            d&apos;envoi pour ouvrir la saisie des événements.
          </p>
        ) : (
          <EventsPanel
            sheet={sheet}
            editable={live}
            onAdd={(body) => enqueue({ kind: "event", body: body as Record<string, unknown> & { client_uuid: string } })}
            onDelete={(eventId) => enqueue({ kind: "delete_event", eventId })}
          />
        ))}

      {current === "infos" && <Infos sheet={sheet} onSave={(body) => enqueue({ kind: "header", body })} />}

      <div className="space-y-2 border-t border-stone-200 pt-3">
        {draft && (
          <>
            {!ready && (
              <p className="text-sm text-stone-600">
                La soumission sera possible quand les deux compositions seront conformes.
              </p>
            )}
            <ActionButton
              disabled={!ready || pendingCount > 0}
              confirm="Soumettre la feuille ? Les compositions seront verrouillées."
              onClick={async () => {
                await enqueue({ kind: "submit" });
                setTab("match");
              }}
            >
              Soumettre la feuille (compositions verrouillées)
            </ActionButton>
          </>
        )}
        {live && (
          <>
            {sheet.events.length === 0 && (
              <button type="button" className="text-sm underline" onClick={() => enqueue({ kind: "reopen" })}>
                Corriger les compositions (retour en brouillon)
              </button>
            )}
            {sheet.event_errors.length > 0 && (
              <ul className="rounded bg-red-50 p-2 text-sm text-lds-red">
                {sheet.event_errors.map((e, i) => (
                  <li key={i}>• {e}</li>
                ))}
              </ul>
            )}
            <ActionButton
              confirm={`Valider le résultat ${sheet.match.home_score} – ${sheet.match.away_score} ? La feuille sera verrouillée.`}
              onClick={() => enqueue({ kind: "validate" })}
            >
              Fin du match : valider la feuille
            </ActionButton>
          </>
        )}
        {!draft && !live && (
          <p className="rounded bg-green-50 p-2 text-sm text-green-800">
            Feuille {SHEET_STATUS_LABEL[sheet.status].toLowerCase()}
            {sheet.validated_at && ` le ${new Date(sheet.validated_at).toLocaleString("fr-FR")}`}. Le
            résultat est officiel.
          </p>
        )}
      </div>
    </div>
  );
}

function Scoreboard({ sheet }: { sheet: Sheet }) {
  const m = sheet.match;
  return (
    <div className="rounded-xl bg-white p-3 shadow-sm">
      <p className="text-center text-xs text-stone-500">
        {formatDate(m.kickoff_at)} · {formatTime(m.kickoff_at)} · {m.venue?.name ?? "Stade à définir"}
      </p>
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex flex-1 flex-col items-center gap-1 text-center">
          <TeamBadge team={sheet.home.team} />
          <span className="text-sm font-semibold leading-tight">{sheet.home.team.name}</span>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold tabular-nums" aria-label="Score">
            {m.home_score ?? 0} – {m.away_score ?? 0}
          </div>
          {m.home_penalties != null && (
            <div className="text-xs">t.a.b. {m.home_penalties}–{m.away_penalties}</div>
          )}
          <div className="text-xs font-semibold text-lds-green">{SHEET_STATUS_LABEL[sheet.status]}</div>
        </div>
        <div className="flex flex-1 flex-col items-center gap-1 text-center">
          <TeamBadge team={sheet.away.team} />
          <span className="text-sm font-semibold leading-tight">{sheet.away.team.name}</span>
        </div>
      </div>
    </div>
  );
}

function Infos({ sheet, onSave }: { sheet: Sheet; onSave: (body: Record<string, unknown>) => Promise<void> }) {
  const editable = sheet.status === "draft" || sheet.status === "submitted";
  const knockout = sheet.match.phase !== "group";
  const [form, setForm] = useState({
    referee_name: sheet.referee_name ?? "",
    assistant_referees: sheet.assistant_referees ?? "",
    attendance: sheet.attendance?.toString() ?? "",
    notes: sheet.notes ?? "",
    home_penalties: sheet.match.home_penalties?.toString() ?? "",
    away_penalties: sheet.match.away_penalties?.toString() ?? "",
  });
  const field = (key: keyof typeof form, label: string, type = "text") => (
    <label className="block text-xs">
      {label}
      <input
        type={type}
        disabled={!editable}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        className="mt-0.5 w-full rounded border px-2 py-2 text-sm"
      />
    </label>
  );
  const num = (v: string) => (v === "" ? null : Number(v));
  return (
    <form
      className="space-y-2 rounded-lg border border-stone-200 bg-white p-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSave({
          referee_name: form.referee_name || null,
          assistant_referees: form.assistant_referees || null,
          attendance: num(form.attendance),
          notes: form.notes || null,
          ...(knockout ? { home_penalties: num(form.home_penalties), away_penalties: num(form.away_penalties) } : {}),
        });
      }}
    >
      {field("referee_name", "Arbitre central")}
      {field("assistant_referees", "Arbitres assistants")}
      {field("attendance", "Affluence", "number")}
      {knockout && (
        <div className="grid grid-cols-2 gap-2">
          {field("home_penalties", `Tirs au but ${sheet.home.team.short_name}`, "number")}
          {field("away_penalties", `Tirs au but ${sheet.away.team.short_name}`, "number")}
        </div>
      )}
      <label className="block text-xs">
        Observations du délégué
        <textarea
          disabled={!editable}
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
          className="mt-0.5 w-full rounded border px-2 py-2 text-sm"
          rows={3}
        />
      </label>
      {editable && (
        <button type="submit" className="rounded bg-lds-green px-3 py-1.5 text-sm font-semibold text-white">
          Enregistrer
        </button>
      )}
    </form>
  );
}

function ActionButton({
  children,
  onClick,
  confirm,
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => Promise<void>;
  confirm: string;
  disabled?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      disabled={disabled || busy}
      onClick={async () => {
        if (!window.confirm(confirm)) return;
        setBusy(true);
        try {
          await onClick();
        } finally {
          setBusy(false);
        }
      }}
      className="w-full rounded-lg bg-lds-red py-3 font-bold text-white disabled:opacity-50"
    >
      {children}
    </button>
  );
}
