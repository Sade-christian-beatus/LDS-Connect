"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Field, inputClass, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth";
import { BALLOT_KIND_LABEL, fromLocalInput } from "@/lib/format";
import type { BallotAdmin, BallotKind, BallotCandidate, Match, OptionIn, PublicTeam } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function NouveauScrutinPage() {
  return (
    <RequireAuth permission="vote:manage">
      <BallotForm />
    </RequireAuth>
  );
}

/** Source de propositions suggérée pour chaque type de scrutin. */
const SOURCE: Record<string, { kind: string; label: string }> = {
  man_of_the_match: { kind: "match", label: "Joueurs inscrits sur la feuille du match" },
  goal_of_the_month: { kind: "goals", label: "Buts marqués (matchs validés)" },
  player_of_the_season: { kind: "players", label: "Joueurs des effectifs" },
  coach_of_the_season: { kind: "coaches", label: "Entraîneurs principaux" },
  team_of_the_season: { kind: "players", label: "Joueurs des effectifs" },
  special: { kind: "teams", label: "Équipes" },
};

const DEFAULT_CHOICES: Record<string, number> = { team_of_the_season: 11 };

function BallotForm() {
  const { api } = useAuth();
  const router = useRouter();
  const { data: matches } = useApi<Match[]>("/matches?status=finished");
  const { data: teams } = useApi<PublicTeam[]>("/teams");
  const [f, setF] = useState({
    kind: "man_of_the_match" as BallotKind,
    title: "",
    description: "",
    match_id: "",
    opens_at: "",
    closes_at: "",
    max_choices: "1",
    results_visibility: "immediate" as "immediate" | "scheduled",
    results_publish_at: "",
  });
  const [teamFilter, setTeamFilter] = useState("");
  const [candidates, setCandidates] = useState<BallotCandidate[] | null>(null);
  const [options, setOptions] = useState<OptionIn[]>([]);
  const [manual, setManual] = useState("");
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const source = SOURCE[f.kind];

  async function loadCandidates() {
    const params = new URLSearchParams({ kind: source.kind });
    if (source.kind === "match") {
      if (!f.match_id) return setNotice({ tone: "error", text: "Choisissez d'abord le match" });
      params.set("match_id", f.match_id);
    }
    if (teamFilter && (source.kind === "players" || source.kind === "coaches")) params.set("team_id", teamFilter);
    try {
      setCandidates(await api<BallotCandidate[]>(`/admin/ballots/candidates?${params}`));
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
    }
  }

  const key = (o: { label: string; person_id?: string | null; match_event_id?: string | null }) =>
    o.match_event_id ?? o.person_id ?? o.label;
  const chosen = new Set(options.map(key));
  const toggle = (c: BallotCandidate) =>
    setOptions((prev) =>
      chosen.has(key(c))
        ? prev.filter((o) => key(o) !== key(c))
        : [...prev, { label: c.label, person_id: c.person_id, team_id: c.team_id, match_event_id: c.match_event_id }],
    );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const created = await api<BallotAdmin>("/admin/ballots", {
        method: "POST",
        body: JSON.stringify({
          kind: f.kind,
          title: f.title,
          description: f.description || null,
          match_id: f.match_id || null,
          opens_at: fromLocalInput(f.opens_at),
          closes_at: fromLocalInput(f.closes_at),
          max_choices: Number(f.max_choices),
          results_visibility: f.results_visibility,
          results_publish_at: f.results_visibility === "scheduled" ? fromLocalInput(f.results_publish_at) : null,
          options,
        }),
      });
      router.push(`/admin/votes/${created.id}`);
    } catch (err) {
      setNotice({ tone: "error", text: err instanceof Error ? err.message : String(err) });
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <h1 className="text-2xl font-black tracking-tight text-pitch">Nouveau scrutin</h1>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      <section className="grid gap-3 rounded-lg border border-stone-200 bg-white p-4 sm:grid-cols-2">
        <Field label="Type de scrutin *">
          <select
            className={inputClass}
            value={f.kind}
            onChange={(e) => {
              const kind = e.target.value as BallotKind;
              setF({ ...f, kind, max_choices: String(DEFAULT_CHOICES[kind] ?? 1) });
              setCandidates(null);
            }}
          >
            {Object.entries(BALLOT_KIND_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Titre *">
          <input required minLength={3} className={inputClass} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
        </Field>
        {f.kind === "man_of_the_match" && (
          <Field label="Match *">
            <select required className={inputClass} value={f.match_id} onChange={(e) => setF({ ...f, match_id: e.target.value })}>
              <option value="">— choisir un match joué —</option>
              {matches?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.home?.short_name} {m.home_score}–{m.away_score} {m.away?.short_name}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Nombre de choix par votant" hint="1 en général ; 11 pour l'onze idéal">
          <input type="number" min={1} max={11} className={inputClass} value={f.max_choices} onChange={(e) => setF({ ...f, max_choices: e.target.value })} />
        </Field>
        <Field label="Ouverture du vote *">
          <input required type="datetime-local" className={inputClass} value={f.opens_at} onChange={(e) => setF({ ...f, opens_at: e.target.value })} />
        </Field>
        <Field label="Clôture du vote *">
          <input required type="datetime-local" className={inputClass} value={f.closes_at} onChange={(e) => setF({ ...f, closes_at: e.target.value })} />
        </Field>
        <Field label="Publication des résultats">
          <select
            className={inputClass}
            value={f.results_visibility}
            onChange={(e) => setF({ ...f, results_visibility: e.target.value as "immediate" | "scheduled" })}
          >
            <option value="immediate">En continu, dès l&apos;ouverture</option>
            <option value="scheduled">À une date programmée</option>
          </select>
        </Field>
        {f.results_visibility === "scheduled" && (
          <Field label="Date de publication *">
            <input
              required
              type="datetime-local"
              className={inputClass}
              value={f.results_publish_at}
              onChange={(e) => setF({ ...f, results_publish_at: e.target.value })}
            />
          </Field>
        )}
        <div className="sm:col-span-2">
          <Field label="Présentation (facultatif)">
            <textarea rows={2} className={inputClass} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
          </Field>
        </div>
      </section>

      <section className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="font-semibold">Propositions ({options.length})</h2>
        <div className="flex flex-wrap items-end gap-2">
          {(source.kind === "players" || source.kind === "coaches") && teams && (
            <Field label="Équipe">
              <select className={inputClass} value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)}>
                <option value="">Toutes</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Button variant="secondary" onClick={loadCandidates}>
            Suggérer : {source.label}
          </Button>
        </div>
        {candidates && (
          <ul className="max-h-72 divide-y divide-stone-100 overflow-y-auto rounded border border-stone-200" aria-label="Propositions suggérées">
            {candidates.length === 0 && <li className="p-2 text-sm text-stone-500">Aucune proposition trouvée.</li>}
            {candidates.map((c) => (
              <li key={key(c)}>
                <label className="flex items-center gap-2 px-2 py-1 text-sm">
                  <input type="checkbox" checked={chosen.has(key(c))} onChange={() => toggle(c)} />
                  <span className="flex-1">{c.label}</span>
                  <span className="text-xs text-stone-500">{c.sublabel}</span>
                </label>
              </li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <input
            aria-label="Proposition libre"
            placeholder="Proposition libre (ex. trophée spécial)"
            className={inputClass}
            value={manual}
            onChange={(e) => setManual(e.target.value)}
          />
          <Button
            variant="secondary"
            onClick={() => {
              if (manual.trim()) setOptions([...options, { label: manual.trim() }]);
              setManual("");
            }}
          >
            Ajouter
          </Button>
        </div>
        {options.length > 0 && (
          <ol className="list-decimal space-y-1 pl-6 text-sm">
            {options.map((o) => (
              <li key={key(o)}>
                {o.label}{" "}
                <button type="button" className="text-xs text-lds-red underline" onClick={() => setOptions(options.filter((x) => key(x) !== key(o)))}>
                  retirer
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={() => router.push("/admin/votes")}>
          Annuler
        </Button>
        <Button type="submit" disabled={busy}>
          Enregistrer le brouillon
        </Button>
      </div>
      <p className="text-xs text-stone-500">
        Le scrutin reste un brouillon invisible du public jusqu&apos;à son ouverture. Une fois ouvert, les propositions et le
        nombre de choix sont figés. Le vote payant sera proposé avec la billetterie.
      </p>
    </form>
  );
}
