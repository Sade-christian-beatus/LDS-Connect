"use client";
// Saison et règles : règles de la compétition (barème, effectifs, discipline…) et gestion des
// saisons (préparer la suivante, basculer la saison courante). Toute modification est journalisée.
import { useState } from "react";
import { Badge, Button, Dialog, Field, inputClass, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth";
import type { RulesAdmin, SeasonAdmin } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function SaisonPage() {
  return (
    <RequireAuth permission="rules:manage">
      <Saison />
    </RequireAuth>
  );
}

type RuleKey = Exclude<keyof RulesAdmin, "season_id" | "locked_fields" | "season_started" | "tiebreakers" | "knockout_pairings" | "prize_money" | "age_reference_date">;

const GROUPS: { title: string; hint: string; fields: { key: RuleKey; label: string; unit?: string; step?: string }[] }[] = [
  {
    title: "Barème et départage",
    hint: "Figés dès le premier match : ils déterminent les classements.",
    fields: [
      { key: "points_win", label: "Points pour une victoire" },
      { key: "points_draw", label: "Points pour un nul" },
      { key: "points_loss", label: "Points pour une défaite" },
      { key: "qualifiers_per_pool", label: "Qualifiés par poule" },
      { key: "third_place_match", label: "Match pour la 3e place" },
    ],
  },
  {
    title: "Effectifs",
    hint: "Contrôlés à l'inscription des joueurs et à la délivrance des licences.",
    fields: [
      { key: "max_squad_players", label: "Joueurs au maximum" },
      { key: "max_staff", label: "Encadreurs au maximum" },
      { key: "min_age", label: "Âge minimum", unit: "ans" },
      { key: "youth_age_limit", label: "Âge limite « jeune »", unit: "ans" },
      { key: "min_youth_players", label: "Jeunes exigés au minimum" },
      { key: "residence_min_months", label: "Résidence pour être « local »", unit: "mois" },
      { key: "min_local_starters_ratio", label: "Part minimale de locaux titulaires", step: "0.05" },
    ],
  },
  {
    title: "Feuille de match",
    hint: "La durée d'un match sert au calcul des minutes jouées (figée dès le premier match).",
    fields: [
      { key: "starters_count", label: "Titulaires" },
      { key: "max_substitutes_on_sheet", label: "Remplaçants sur la feuille" },
      { key: "max_substitutions", label: "Remplacements autorisés" },
      { key: "match_duration_minutes", label: "Durée d'un match", unit: "min" },
    ],
  },
  {
    title: "Discipline",
    hint: "Figée dès le premier match : elle détermine les suspensions.",
    fields: [
      { key: "yellow_cards_threshold", label: "Jaunes avant suspension" },
      { key: "yellow_accumulation_ban_matches", label: "Suspension après cumul", unit: "match(s)" },
      { key: "red_card_ban_matches", label: "Suspension après rouge direct", unit: "match(s)" },
      { key: "second_yellow_ban_matches", label: "Suspension après deux jaunes", unit: "match(s)" },
      { key: "reset_yellows_after_group_stage", label: "Jaunes remis à zéro après les poules" },
    ],
  },
];

const PRIZES: [string, string][] = [
  ["1", "Vainqueur"],
  ["2", "Finaliste"],
  ["3", "3e"],
  ["4", "4e"],
  ["quarter_finalist", "Chaque quart-de-finaliste"],
];

function Saison() {
  const { data: rules, reload } = useApi<RulesAdmin>("/admin/rules");
  const { data: seasons, reload: reloadSeasons } = useApi<SeasonAdmin[]>("/admin/seasons");
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const fail = (e: unknown) => setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
  const current = seasons?.find((s) => s.is_current);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-pitch">Saison et règles</h1>
          <p className="text-sm text-stone-600">
            {current ? `${current.name} · ${current.teams} équipes · ${current.matches} matchs` : "Chargement…"}
          </p>
        </div>
        {rules?.season_started ? (
          <Badge tone="amber">Saison commencée : barème et discipline figés</Badge>
        ) : (
          <Badge tone="green">Avant le premier match : toutes les règles sont modifiables</Badge>
        )}
      </div>
      <Notice notice={notice} onClose={() => setNotice(null)} />
      {rules && (
        <RulesForm
          key={JSON.stringify(rules)}
          rules={rules}
          onDone={(t) => {
            setNotice({ tone: "ok", text: t });
            reload();
          }}
          onError={fail}
        />
      )}
      {seasons && (
        <Seasons
          seasons={seasons}
          onDone={(t) => {
            setNotice({ tone: "ok", text: t });
            reloadSeasons();
            reload();
          }}
          onError={fail}
        />
      )}
    </div>
  );
}

function RulesForm({ rules, onDone, onError }: { rules: RulesAdmin; onDone: (t: string) => void; onError: (e: unknown) => void }) {
  const { api } = useAuth();
  const [f, setF] = useState<RulesAdmin>(rules);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const locked = new Set(rules.locked_fields);
  const changed = (Object.keys(f) as (keyof RulesAdmin)[]).filter((k) => JSON.stringify(f[k]) !== JSON.stringify(rules[k]));

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const body: Record<string, unknown> = { reason };
      for (const k of changed) body[k] = f[k];
      await api("/admin/rules", { method: "PATCH", body: JSON.stringify(body) });
      onDone(`Règles enregistrées (${changed.length} modification${changed.length > 1 ? "s" : ""}, inscrites au journal)`);
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        {GROUPS.map((g) => (
          <fieldset key={g.title} className="rounded-xl border border-stone-200 bg-white p-4">
            <legend className="px-1 font-bold text-pitch">{g.title}</legend>
            <p className="mb-3 text-xs text-stone-500">{g.hint}</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {g.fields.map(({ key, label, unit, step }) => {
                const isLocked = locked.has(key);
                const value = f[key];
                if (typeof value === "boolean") {
                  return (
                    <label key={key} className="flex items-center gap-2 text-sm sm:col-span-2">
                      <input
                        type="checkbox"
                        disabled={isLocked}
                        checked={value}
                        onChange={(e) => setF({ ...f, [key]: e.target.checked })}
                        className="h-4 w-4 accent-lds-green"
                      />
                      {label}
                      {isLocked && <span title="Figé pendant la saison">🔒</span>}
                    </label>
                  );
                }
                return (
                  <Field key={key} label={`${label}${isLocked ? " 🔒" : ""}`} hint={unit}>
                    <input
                      type="number"
                      step={step ?? "1"}
                      required
                      disabled={isLocked}
                      className={inputClass}
                      value={String(value)}
                      onChange={(e) => setF({ ...f, [key]: step ? e.target.value : Number(e.target.value) })}
                    />
                  </Field>
                );
              })}
            </div>
          </fieldset>
        ))}
        <fieldset className="rounded-xl border border-stone-200 bg-white p-4">
          <legend className="px-1 font-bold text-pitch">Dotations (FCFA)</legend>
          <p className="mb-3 text-xs text-stone-500">Montants versés selon le classement final.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {PRIZES.map(([k, label]) => (
              <Field key={k} label={label}>
                <input
                  type="number"
                  min={0}
                  step={100000}
                  className={inputClass}
                  value={f.prize_money[k] ?? 0}
                  onChange={(e) => setF({ ...f, prize_money: { ...f.prize_money, [k]: Number(e.target.value) } })}
                />
              </Field>
            ))}
          </div>
        </fieldset>
        <fieldset className="rounded-xl border border-stone-200 bg-white p-4">
          <legend className="px-1 font-bold text-pitch">Départage et quarts {locked.has("tiebreakers") && "🔒"}</legend>
          <p className="mb-2 text-xs text-stone-500">Critères appliqués dans l&apos;ordre en cas d&apos;égalité de points.</p>
          <ol className="mb-3 list-inside list-decimal text-sm">
            {f.tiebreakers.map((c) => (
              <li key={c}>{TIEBREAKER_LABEL[c] ?? c}</li>
            ))}
          </ol>
          <p className="text-xs text-stone-500">Croisements des quarts de finale</p>
          <p className="text-sm font-semibold">{f.knockout_pairings.map((p) => p.join(" – ")).join(" · ")}</p>
        </fieldset>
      </div>

      {/* Barre d'enregistrement collée en bas de l'écran seulement quand il y a des modifications */}
      <div
        className={`flex flex-wrap items-end gap-3 rounded-xl border bg-white/95 p-3 shadow-sm backdrop-blur ${
          changed.length ? "sticky bottom-2 z-10 border-lds-green/40 ring-2 ring-lds-green/20" : "border-stone-200"
        }`}
      >
        <div className="min-w-64 flex-1">
          <Field label="Motif de la modification (journalisé)">
            <input
              required
              minLength={3}
              placeholder="Ex. décision du bureau exécutif du 12 décembre"
              className={inputClass}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </Field>
        </div>
        <Button type="submit" disabled={busy || changed.length === 0}>
          {changed.length ? `Enregistrer (${changed.length})` : "Aucune modification"}
        </Button>
        {changed.length > 0 && (
          <Button variant="secondary" onClick={() => setF(rules)}>
            Annuler
          </Button>
        )}
      </div>
    </form>
  );
}

const TIEBREAKER_LABEL: Record<string, string> = {
  points: "Points",
  head_to_head_points: "Points en confrontation directe",
  head_to_head_goal_difference: "Différence de buts en confrontation directe",
  head_to_head_goals_for: "Buts marqués en confrontation directe",
  goal_difference: "Différence de buts générale",
  goals_for: "Buts marqués",
  goals_against: "Buts encaissés (le moins)",
  wins: "Nombre de victoires",
  fair_play: "Fair-play (cartons)",
  drawing_of_lots: "Tirage au sort",
};

const STATUS: Record<string, { label: string; tone: "green" | "amber" | "stone" }> = {
  active: { label: "En cours", tone: "green" },
  draft: { label: "En préparation", tone: "amber" },
  closed: { label: "Close", tone: "stone" },
};

function Seasons({ seasons, onDone, onError }: { seasons: SeasonAdmin[]; onDone: (t: string) => void; onError: (e: unknown) => void }) {
  const { api } = useAuth();
  const latest = Math.max(...seasons.map((s) => s.year));
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState<SeasonAdmin | null>(null);
  const [f, setF] = useState({
    year: latest + 1,
    name: `Saison ${latest + 1}`,
    starts_on: `${latest + 1}-01-01`,
    ends_on: `${latest + 1}-06-30`,
    copy_from_current: true,
  });

  return (
    <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-bold text-pitch">Saisons</h2>
        <Button onClick={() => setOpen(true)}>Préparer la saison {latest + 1}</Button>
      </div>
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase text-stone-500">
          <tr>
            <th className="py-1">Saison</th>
            <th>Dates</th>
            <th className="text-right">Équipes</th>
            <th className="text-right">Matchs</th>
            <th className="pl-6">État</th>
            <th />
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100">
          {seasons.map((s) => (
            <tr key={s.id}>
              <td className="py-2 font-semibold">{s.name}</td>
              <td className="text-stone-600">
                {new Date(s.starts_on).toLocaleDateString("fr-FR")} → {new Date(s.ends_on).toLocaleDateString("fr-FR")}
              </td>
              <td className="text-right tabular-nums">{s.teams}</td>
              <td className="text-right tabular-nums">{s.matches}</td>
              <td className="pl-6">
                <Badge tone={STATUS[s.status].tone}>{STATUS[s.status].label}</Badge> {s.is_current && <Badge tone="blue">Courante</Badge>}
              </td>
              <td className="text-right">
                {!s.is_current && s.status === "draft" && (
                  <Button variant="secondary" onClick={() => setConfirm(s)}>
                    En faire la saison courante
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Dialog open={open} title={`Préparer la saison ${f.year}`} onClose={() => setOpen(false)}>
        <form
          className="space-y-3"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await api("/admin/seasons", { method: "POST", body: JSON.stringify(f) });
              setOpen(false);
              onDone(`${f.name} créée en préparation : la saison courante n'est pas modifiée`);
            } catch (err) {
              onError(err);
            }
          }}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Année">
              <input type="number" required className={inputClass} value={f.year} onChange={(e) => setF({ ...f, year: Number(e.target.value) })} />
            </Field>
            <Field label="Nom">
              <input required className={inputClass} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            </Field>
            <Field label="Début">
              <input type="date" required className={inputClass} value={f.starts_on} onChange={(e) => setF({ ...f, starts_on: e.target.value })} />
            </Field>
            <Field label="Fin">
              <input type="date" required className={inputClass} value={f.ends_on} onChange={(e) => setF({ ...f, ends_on: e.target.value })} />
            </Field>
          </div>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 accent-lds-green"
              checked={f.copy_from_current}
              onChange={(e) => setF({ ...f, copy_from_current: e.target.checked })}
            />
            <span>
              Reprendre les règles, les poules et les équipes engagées de la saison courante. Les effectifs et licences sont à
              refaire pour la nouvelle saison.
            </span>
          </label>
          <Button type="submit">Créer la saison</Button>
        </form>
      </Dialog>

      <Dialog open={confirm !== null} title="Changer de saison courante" onClose={() => setConfirm(null)}>
        {confirm && (
          <div className="space-y-3 text-sm">
            <p>
              <strong>{confirm.name}</strong> deviendra la saison affichée sur le site et utilisée partout. La saison actuelle sera
              <strong> close</strong> (consultable, mais plus modifiable) : cette action ne s&apos;annule pas.
            </p>
            <Button
              variant="danger"
              onClick={async () => {
                try {
                  await api(`/admin/seasons/${confirm.id}/activate`, { method: "POST" });
                  setConfirm(null);
                  onDone(`${confirm.name} est désormais la saison courante`);
                } catch (err) {
                  onError(err);
                }
              }}
            >
              Confirmer le changement de saison
            </Button>
          </div>
        )}
      </Dialog>
    </section>
  );
}
