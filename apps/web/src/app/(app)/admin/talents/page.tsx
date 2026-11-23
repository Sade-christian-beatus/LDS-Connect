"use client";
// Tableau de bord des talents (cellule technique) : filtres, classements, suivis.
import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge, Button, inputClass, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { TeamBadge } from "@/components/TeamBadge";
import { useAuth } from "@/lib/auth";
import { POSITION_LABEL } from "@/lib/format";
import type { PublicTeam, Region, TalentDashboard } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function TalentsPage() {
  return (
    <RequireAuth permission="stats:read">
      <Talents />
    </RequireAuth>
  );
}

const SORTS: [string, string][] = [
  ["goals", "Buts"],
  ["assists", "Passes décisives"],
  ["contributions_per_90", "Buts + passes / 90 min"],
  ["goals_per_90", "Buts / 90 min"],
  ["minutes_played", "Minutes jouées"],
  ["appearances", "Matchs joués"],
  ["clean_sheets", "Clean sheets"],
  ["man_of_the_match", "Homme du match"],
  ["avg_rating", "Note moyenne (observations)"],
];

const PRESETS: { label: string; f: Record<string, string> }[] = [
  { label: "Jeunes buteurs", f: { position: "FW", age_max: "18", sort: "goals" } },
  { label: "Gardiens", f: { position: "GK", sort: "clean_sheets" } },
  { label: "Meilleurs passeurs", f: { sort: "assists" } },
  { label: "Joueurs suivis", f: { watched_only: "true", sort: "avg_rating" } },
];

type F = Record<string, string>;
const EMPTY: F = { sort: "goals", min_minutes: "0" };

function Talents() {
  const { raw } = useAuth();
  const [f, setF] = useState<F>(EMPTY);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const query = useMemo(() => {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(f)) if (v) q.set(k, v);
    q.set("limit", "200");
    return q.toString();
  }, [f]);
  const { data, error } = useApi<TalentDashboard>(`/admin/talents?${query}`);
  const { data: teams } = useApi<PublicTeam[]>("/teams");
  const { data: regions } = useApi<Region[]>("/regions");
  const set = (k: string, v: string) => setF((prev) => ({ ...prev, [k]: v }));

  async function exportCsv() {
    try {
      const res = await raw(`/admin/talents.csv?${query}`);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(await res.blob());
      a.download = "talents.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
    }
  }

  const sortLabel = SORTS.find(([k]) => k === f.sort)?.[1] ?? "";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-pitch">Talents</h1>
          <p className="text-sm text-stone-600">
            Statistiques de tous les joueurs des effectifs, calculées à chaque validation de feuille de match
            {data ? ` (match de ${data.match_duration_minutes} min)` : ""}.
          </p>
        </div>
        <Button variant="secondary" onClick={exportCsv}>
          Exporter (CSV)
        </Button>
      </div>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      <div className="flex flex-wrap gap-2" role="group" aria-label="Recherches prêtes">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => setF({ ...EMPTY, ...p.f })}
            className="rounded-full border border-stone-300 bg-white px-3 py-1 text-sm hover:border-lds-green"
          >
            {p.label}
          </button>
        ))}
        <button type="button" onClick={() => setF(EMPTY)} className="px-2 text-sm text-stone-500 underline">
          Réinitialiser
        </button>
      </div>

      <section aria-label="Filtres" className="grid gap-3 rounded-xl border border-stone-200 bg-white p-4 sm:grid-cols-3 lg:grid-cols-6">
        <label className="text-sm">
          Poste
          <select className={inputClass} value={f.position ?? ""} onChange={(e) => set("position", e.target.value)}>
            <option value="">Tous</option>
            {Object.entries(POSITION_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Âge min.
          <input type="number" min={10} max={60} className={inputClass} value={f.age_min ?? ""} onChange={(e) => set("age_min", e.target.value)} />
        </label>
        <label className="text-sm">
          Âge max.
          <input type="number" min={10} max={60} className={inputClass} value={f.age_max ?? ""} onChange={(e) => set("age_max", e.target.value)} />
        </label>
        <label className="text-sm">
          Équipe
          <select className={inputClass} value={f.team_id ?? ""} onChange={(e) => set("team_id", e.target.value)}>
            <option value="">Toutes</option>
            {teams?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Région de l&apos;équipe
          <select className={inputClass} value={f.region_id ?? ""} onChange={(e) => set("region_id", e.target.value)}>
            <option value="">Toutes</option>
            {regions?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Minutes jouées min.
          <input type="number" min={0} step={45} className={inputClass} value={f.min_minutes ?? "0"} onChange={(e) => set("min_minutes", e.target.value)} />
        </label>
        <label className="text-sm sm:col-span-2">
          Recherche
          <input className={inputClass} placeholder="Nom ou nom d'usage" value={f.q ?? ""} onChange={(e) => set("q", e.target.value)} />
        </label>
        <label className="text-sm">
          Poule
          <select className={inputClass} value={f.pool ?? ""} onChange={(e) => set("pool", e.target.value)}>
            <option value="">Les deux</option>
            <option value="A">Poule A</option>
            <option value="B">Poule B</option>
          </select>
        </label>
        <label className="text-sm sm:col-span-2">
          Trier par
          <select aria-label="Trier par" className={inputClass} value={f.sort} onChange={(e) => set("sort", e.target.value)}>
            {SORTS.map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 self-end pb-2 text-sm">
          <input type="checkbox" checked={f.watched_only === "true"} onChange={(e) => set("watched_only", e.target.checked ? "true" : "")} />
          Suivis seulement
        </label>
      </section>

      {error && <p className="text-lds-red">{error}</p>}
      {data && (
        <p className="text-sm text-stone-600">
          {data.total} joueur(s) · classés par <strong>{sortLabel.toLowerCase()}</strong>
          {data.total > data.rows.length && ` · ${data.rows.length} premiers affichés`}
        </p>
      )}

      <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-stone-50 text-left text-[11px] uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-3 py-2">Joueur</th>
              <th className="px-2 py-2">Poste</th>
              <th className="px-2 py-2 text-right">Âge</th>
              <th className="px-2 py-2 text-right" title="Matchs joués">MJ</th>
              <th className="px-2 py-2 text-right">Min</th>
              <th className="px-2 py-2 text-right">Buts</th>
              <th className="px-2 py-2 text-right" title="Passes décisives">Passes</th>
              <th className="px-2 py-2 text-right" title="Buts + passes sur 90 minutes">B+P/90</th>
              <th className="px-2 py-2 text-right" title="Clean sheets (gardiens)">CS</th>
              <th className="px-2 py-2 text-right" title="Note moyenne des observations">Note</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {data?.rows.map((r) => (
              <tr key={r.person_id} className="hover:bg-stone-50">
                <td className="px-3 py-2">
                  <Link href={`/admin/talents/${r.person_id}`} className="flex items-center gap-2.5">
                    <TeamBadge team={r.team} size="sm" />
                    <span className="min-w-0">
                      <span className="block truncate font-semibold hover:underline">
                        {r.watched && (
                          <span className="mr-1 text-lds-gold" title="Joueur suivi">
                            ★
                          </span>
                        )}
                        {r.full_name}
                      </span>
                      <span className="block truncate text-xs text-stone-500">
                        {r.team.short_name}
                        {r.shirt_number ? ` · n° ${r.shirt_number}` : ""}
                      </span>
                    </span>
                  </Link>
                </td>
                <td className="px-2 py-2">{POSITION_LABEL[r.position]}</td>
                <td className="px-2 py-2 text-right tabular-nums">
                  {r.is_youth && (
                    <span className="mr-1">
                      <Badge tone="blue">jeune</Badge>
                    </span>
                  )}
                  {r.age}
                </td>
                <td className="px-2 py-2 text-right tabular-nums">{r.appearances}</td>
                <td className="px-2 py-2 text-right tabular-nums text-stone-600">{r.minutes_played}</td>
                <td className="px-2 py-2 text-right font-bold tabular-nums">{r.goals}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.assists}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.contributions_per_90?.toLocaleString("fr-FR") ?? "—"}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.position === "GK" ? r.clean_sheets : "—"}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.avg_rating ? `${r.avg_rating.toLocaleString("fr-FR")}/5` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.rows.length === 0 && <p className="p-6 text-center text-stone-500">Aucun joueur ne correspond à ces critères.</p>}
      </div>
      <p className="text-xs text-stone-500">
        Ratios sur 90 minutes affichés à partir de 90 minutes jouées. Les notes d&apos;observation sont internes : chaque
        consultation d&apos;une fiche est inscrite au journal.
      </p>
    </div>
  );
}
