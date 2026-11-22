"use client";
import { useCallback, useState } from "react";
import { Badge, Button, Field, inputClass, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { ApiError, useAuth } from "@/lib/auth";
import { formatDate, PHASE_LABEL } from "@/lib/format";
import type { Delegate, Match, Season, Venue } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function CalendrierAdminPage() {
  return (
    <RequireAuth permission="fixture:manage">
      <CalendarAdmin />
    </RequireAuth>
  );
}

type NoticeState = { tone: "ok" | "error"; text: string } | null;

const STATUS_LABEL: Record<string, string> = {
  scheduled: "Programmé",
  postponed: "Reporté",
  cancelled: "Annulé",
  live: "En cours",
  finished: "Terminé",
};

/** Ouagadougou = UTC toute l'année : la saisie locale est directement en UTC. */
const toInput = (iso: string | null | undefined) => (iso ? iso.slice(0, 16) : "");
const fromInput = (v: string) => (v ? `${v}:00Z` : null);

function CalendarAdmin() {
  const { data: season } = useApi<Season>("/seasons/current");
  const [poolCode, setPoolCode] = useState<"A" | "B" | "F">("A");
  const [notice, setNotice] = useState<NoticeState>(null);
  const path = poolCode === "F" ? "/bracket" : `/matches?pool=${poolCode}`;
  const { data: matches, reload } = useApi<Match[]>(path);
  const { data: venues, reload: reloadVenues } = useApi<Venue[]>("/venues");
  const { data: delegates } = useApi<Delegate[]>("/admin/delegates");
  const { data: assignments, reload: reloadAssignments } = useApi<Record<string, Delegate>>("/admin/delegate-assignments");

  const ok = useCallback(
    (text: string) => {
      setNotice({ tone: "ok", text });
      reload();
    },
    [reload],
  );
  const fail = useCallback((e: unknown) => setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) }), []);

  const pool = season?.pools.find((p) => p.code === poolCode);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-green-900">Calendrier</h1>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Phase">
        {season?.pools.map((p) => (
          <TabButton key={p.code} active={poolCode === p.code} onClick={() => setPoolCode(p.code as "A" | "B")}>
            {p.name} · {p.host_city}
          </TabButton>
        ))}
        <TabButton active={poolCode === "F"} onClick={() => setPoolCode("F")}>
          Phases finales
        </TabButton>
      </div>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      {pool && <GeneratePanel poolId={pool.id} hasMatches={!!matches?.length} onDone={ok} onError={fail} />}
      {poolCode === "F" && <BracketPanel onDone={ok} onError={fail} />}

      {matches && venues && (
        <MatchTable
          matches={matches}
          venues={venues}
          delegates={delegates ?? []}
          assignments={assignments ?? {}}
          onAssigned={(t) => {
            setNotice({ tone: "ok", text: t });
            reloadAssignments();
          }}
          onSaved={ok}
          onError={fail}
        />
      )}
      {venues && <VenuesPanel venues={venues} onDone={(t) => { setNotice({ tone: "ok", text: t }); reloadVenues(); }} onError={fail} />}
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-full px-4 py-1 text-sm font-semibold ${active ? "bg-lds-green text-white" : "bg-white ring-1 ring-stone-300"}`}
    >
      {children}
    </button>
  );
}

function GeneratePanel({
  poolId,
  hasMatches,
  onDone,
  onError,
}: {
  poolId: string;
  hasMatches: boolean;
  onDone: (t: string) => void;
  onError: (e: unknown) => void;
}) {
  const { api } = useAuth();
  const [form, setForm] = useState({ first_date: "", days_between_rounds: "7", seed: "", force: false });
  const [busy, setBusy] = useState(false);
  return (
    <details className="rounded-lg border border-stone-200 bg-white p-3" open={!hasMatches}>
      <summary className="cursor-pointer font-semibold">
        {hasMatches ? "Régénérer le calendrier de la poule" : "Générer le calendrier de la poule"}
      </summary>
      <form
        className="mt-3 grid gap-3 sm:grid-cols-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            const created = await api<Match[]>(`/admin/pools/${poolId}/fixtures`, {
              method: "POST",
              body: JSON.stringify({
                first_date: form.first_date || null,
                days_between_rounds: Number(form.days_between_rounds),
                seed: form.seed === "" ? null : Number(form.seed),
                force: form.force,
              }),
            });
            const rounds = new Set(created.map((m) => m.round_number)).size;
            onDone(`${created.length} matchs générés sur ${rounds} journées (méthode de Berger)`);
          } catch (err) {
            onError(err instanceof ApiError && err.code === "fixtures_exist" ? new Error(`${err.message}.`) : err);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="1re journée le" hint="Vide : dates à fixer match par match">
          <input type="date" className={inputClass} value={form.first_date} onChange={(e) => setForm({ ...form, first_date: e.target.value })} />
        </Field>
        <Field label="Jours entre deux journées">
          <input type="number" min={1} max={60} className={inputClass} value={form.days_between_rounds} onChange={(e) => setForm({ ...form, days_between_rounds: e.target.value })} />
        </Field>
        <Field label="Tirage (graine)" hint="Nombre : ordre reproductible. Vide : ordre d'inscription">
          <input type="number" className={inputClass} value={form.seed} onChange={(e) => setForm({ ...form, seed: e.target.value })} />
        </Field>
        <div className="flex flex-col justify-end gap-2">
          {hasMatches && (
            <label className="flex items-center gap-2 text-sm text-lds-red">
              <input type="checkbox" checked={form.force} onChange={(e) => setForm({ ...form, force: e.target.checked })} />
              Remplacer le calendrier existant
            </label>
          )}
          <Button type="submit" disabled={busy || (hasMatches && !form.force)}>
            {busy ? "Génération…" : "Générer"}
          </Button>
        </div>
      </form>
      <p className="mt-2 text-xs text-stone-500">
        La régénération est refusée dès qu&apos;un match de la poule a commencé ou qu&apos;une feuille de match existe.
      </p>
    </details>
  );
}

function BracketPanel({ onDone, onError }: { onDone: (t: string) => void; onError: (e: unknown) => void }) {
  const { api } = useAuth();
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-stone-200 bg-white p-3 text-sm">
      <p className="flex-1">
        Les équipes des quarts sont renseignées automatiquement à la fin de la phase de poules, puis celles des tours
        suivants à chaque résultat validé (croisements définis dans les règles de la saison).
      </p>
      <Button
        variant="secondary"
        onClick={async () => {
          try {
            await api("/admin/bracket", { method: "POST" });
            onDone("Tableau final créé / mis à jour");
          } catch (e) {
            onError(e);
          }
        }}
      >
        Créer / mettre à jour le tableau
      </Button>
    </div>
  );
}

type DelegateProps = {
  delegates: Delegate[];
  assignments: Record<string, Delegate>;
  onAssigned: (t: string) => void;
};

function MatchTable({
  matches,
  venues,
  delegates,
  assignments,
  onAssigned,
  onSaved,
  onError,
}: DelegateProps & {
  matches: Match[];
  venues: Venue[];
  onSaved: (t: string) => void;
  onError: (e: unknown) => void;
}) {
  if (!matches.length) return <p className="text-sm text-stone-600">Aucun match pour le moment.</p>;
  const groups = new Map<string, Match[]>();
  for (const m of matches) {
    const key = m.round_number ? `Journée ${m.round_number}` : PHASE_LABEL[m.phase];
    groups.set(key, [...(groups.get(key) ?? []), m]);
  }
  return (
    <div className="space-y-4">
      {[...groups.entries()].map(([title, list]) => (
        <section key={title} className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
          <h2 className="bg-stone-100 px-3 py-1.5 text-sm font-semibold">
            {title}
            {list[0]?.kickoff_at && <span className="ml-2 font-normal text-stone-500">{formatDate(list[0].kickoff_at)}</span>}
          </h2>
          <table className="w-full min-w-[60rem] table-fixed text-sm">
            {/* Largeurs fixes : toutes les journées s'alignent, aucun champ tronqué */}
            <colgroup>
              <col className="w-[20%]" />
              <col className="w-[22%]" />
              <col className="w-[18%]" />
              <col className="w-[12%]" />
              <col className="w-[17%]" />
              <col className="w-[11%]" />
            </colgroup>
            <tbody>
              {list.map((m) => (
                <MatchRow key={`${m.id}-${m.kickoff_at}-${m.venue?.id}-${m.status}`} match={m}
                  venues={venues}
                  delegates={delegates}
                  assignments={assignments}
                  onAssigned={onAssigned}
                  onSaved={onSaved}
                  onError={onError}
                />
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

function MatchRow({
  match,
  venues,
  delegates,
  assignments,
  onAssigned,
  onSaved,
  onError,
}: DelegateProps & {
  match: Match;
  venues: Venue[];
  onSaved: (t: string) => void;
  onError: (e: unknown) => void;
}) {
  const { api } = useAuth();
  const initial = { venue_id: match.venue?.id ?? "", kickoff: toInput(match.kickoff_at), status: match.status };
  const [f, setF] = useState(initial);
  const locked = match.status === "live" || match.status === "finished";
  const dirty = JSON.stringify(f) !== JSON.stringify(initial);
  const label = `${match.home?.short_name ?? "À déterminer"} – ${match.away?.short_name ?? "À déterminer"}`;

  return (
    <tr className="border-t border-stone-100">
      <td className="px-3 py-1.5 font-medium">
        {match.bracket_slot && <span className="mr-2 font-mono text-xs text-stone-500">{match.bracket_slot}</span>}
        {label}
        {match.home_score != null && (
          <span className="ml-2 tabular-nums text-stone-600">
            {match.home_score}–{match.away_score}
          </span>
        )}
      </td>
      <td className="px-2 py-1.5">
        <select aria-label={`Stade ${label}`} disabled={locked} className={inputClass} value={f.venue_id} onChange={(e) => setF({ ...f, venue_id: e.target.value })}>
          <option value="">Stade à définir</option>
          {venues.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
      </td>
      <td className="px-2 py-1.5">
        <input
          aria-label={`Coup d'envoi ${label}`}
          type="datetime-local"
          disabled={locked}
          className={inputClass}
          value={f.kickoff}
          onChange={(e) => setF({ ...f, kickoff: e.target.value })}
        />
      </td>
      <td className="px-2 py-1.5">
        {locked ? (
          <Badge tone={match.status === "live" ? "red" : "green"}>{STATUS_LABEL[match.status]}</Badge>
        ) : (
          <select aria-label={`Statut ${label}`} className={inputClass} value={f.status} onChange={(e) => setF({ ...f, status: e.target.value as Match["status"] })}>
            {["scheduled", "postponed", "cancelled"].map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        )}
      </td>
      <td className="px-2 py-1.5">
        <select
          aria-label={`Délégué ${label}`}
          disabled={match.status === "finished" || !match.home || !match.away}
          title={!match.home || !match.away ? "Équipes pas encore connues" : undefined}
          className={inputClass}
          value={assignments[match.id]?.id ?? ""}
          onChange={async (e) => {
            try {
              const d = await api<Delegate | null>(`/admin/matches/${match.id}/delegate`, {
                method: "PUT",
                body: JSON.stringify({ user_id: e.target.value || null }),
              });
              onAssigned(d ? `${label} : délégué ${d.full_name}` : `${label} : délégué retiré`);
            } catch (err) {
              onError(err);
            }
          }}
        >
          <option value="">Délégué non attribué</option>
          {delegates.map((d) => (
            <option key={d.id} value={d.id}>
              {d.full_name}
            </option>
          ))}
        </select>
      </td>
      <td className="px-2 py-1.5 text-right">
        {!locked && (
          <Button
            disabled={!dirty}
            onClick={async () => {
              try {
                await api(`/admin/matches/${match.id}`, {
                  method: "PATCH",
                  body: JSON.stringify({ venue_id: f.venue_id || null, kickoff_at: fromInput(f.kickoff), status: f.status }),
                });
                onSaved(`${label} : modifications enregistrées`);
              } catch (e) {
                onError(e);
              }
            }}
          >
            Enregistrer
          </Button>
        )}
      </td>
    </tr>
  );
}

function VenuesPanel({ venues, onDone, onError }: { venues: Venue[]; onDone: (t: string) => void; onError: (e: unknown) => void }) {
  const { api } = useAuth();
  const [f, setF] = useState({ name: "", city: "Ouagadougou", capacity: "", is_confirmed: false });
  return (
    <details className="rounded-lg border border-stone-200 bg-white p-3">
      <summary className="cursor-pointer font-semibold">Stades ({venues.length})</summary>
      <ul className="mt-2 space-y-1 text-sm">
        {venues.map((v) => (
          <li key={v.id}>
            {v.name} — {v.city} {v.is_confirmed ? <Badge tone="green">Confirmé</Badge> : <Badge tone="amber">À confirmer</Badge>}
          </li>
        ))}
      </ul>
      <form
        className="mt-3 grid gap-2 sm:grid-cols-5"
        onSubmit={async (e) => {
          e.preventDefault();
          try {
            await api("/admin/venues", {
              method: "POST",
              body: JSON.stringify({ ...f, capacity: f.capacity === "" ? null : Number(f.capacity) }),
            });
            onDone(`Stade « ${f.name} » ajouté`);
            setF({ name: "", city: f.city, capacity: "", is_confirmed: false });
          } catch (err) {
            onError(err);
          }
        }}
      >
        <Field label="Nom du stade">
          <input required minLength={2} className={inputClass} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
        </Field>
        <Field label="Ville">
          <input required className={inputClass} value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })} />
        </Field>
        <Field label="Capacité">
          <input type="number" min={0} className={inputClass} value={f.capacity} onChange={(e) => setF({ ...f, capacity: e.target.value })} />
        </Field>
        <label className="flex items-end gap-2 pb-2 text-sm">
          <input type="checkbox" checked={f.is_confirmed} onChange={(e) => setF({ ...f, is_confirmed: e.target.checked })} />
          Confirmé par la Ligue
        </label>
        <div className="flex items-end">
          <Button type="submit">Ajouter le stade</Button>
        </div>
      </form>
    </details>
  );
}
