"use client";
// Consultation du journal d'audit (en ajout seul côté base).
import { useState } from "react";
import { Button, Field, inputClass } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth";
import type { AuditEntry } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const ENTITY_LABEL: Record<string, string> = {
  player: "Joueur",
  staff: "Encadreur",
  person: "Personne",
  membership: "Effectif",
  licence: "Licence",
  team: "Équipe",
  match: "Match",
  match_sheet: "Feuille de match",
  match_event: "Événement de match",
  suspension: "Suspension",
  fixtures: "Calendrier",
  bracket: "Tableau final",
  venue: "Stade",
  user: "Compte",
  database: "Base de données",
};

const ACTION_LABEL: Record<string, string> = {
  create: "Création",
  update: "Modification",
  delete: "Suppression",
  release: "Départ de l'effectif",
  read_sensitive: "Consultation CNIB / téléphone",
  issue: "Délivrance",
  reissue: "Ré-émission",
  status_change: "Changement de statut",
  generate: "Génération",
  set_lineup: "Composition",
  submit: "Soumission",
  reopen: "Réouverture",
  validate: "Validation",
  close: "Clôture",
  login: "Connexion",
  refresh_token_reuse: "Réutilisation suspecte de session",
  export: "Export",
  export_sensitive: "Export avec données sensibles",
};

export default function JournalPage() {
  return (
    <RequireAuth permission="audit:read">
      <Journal />
    </RequireAuth>
  );
}

function Journal() {
  const { api } = useAuth();
  const [filters, setFilters] = useState({ entity_type: "", action: "" });
  const query = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString();
  const { data, error } = useApi<AuditEntry[]>(`/admin/audit?limit=50${query ? `&${query}` : ""}`);
  const [older, setOlder] = useState<{ key: string; entries: AuditEntry[] }>({ key: "", entries: [] });
  // Les pages plus anciennes ne valent que pour les filtres courants
  const extra = older.key === query ? older.entries : [];
  const entries = [...(data ?? []), ...extra];

  async function loadMore() {
    const last = entries.at(-1);
    if (!last) return;
    const more = await api<AuditEntry[]>(`/admin/audit?limit=50&before_id=${last.id}${query ? `&${query}` : ""}`);
    setOlder({ key: query, entries: [...extra, ...more] });
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-black tracking-tight text-pitch">Journal d&apos;audit</h1>
      <p className="text-sm text-stone-600">
        Qui a fait quoi, et quand. Le journal ne peut être ni modifié ni effacé, même par un administrateur de la base.
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <Field label="Type d'élément">
          <select className={inputClass} value={filters.entity_type} onChange={(e) => setFilters({ ...filters, entity_type: e.target.value })}>
            <option value="">Tous</option>
            {Object.entries(ENTITY_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Action">
          <select className={inputClass} value={filters.action} onChange={(e) => setFilters({ ...filters, action: e.target.value })}>
            <option value="">Toutes</option>
            {Object.entries(ACTION_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </Field>
      </div>
      {error && <p className="text-lds-red">{error}</p>}
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-stone-100 text-left text-xs uppercase text-stone-600">
            <tr>
              <th className="px-3 py-2">Date</th>
              <th className="px-2 py-2">Auteur</th>
              <th className="px-2 py-2">Action</th>
              <th className="px-2 py-2">Élément</th>
              <th className="px-2 py-2">Détails</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id} className="border-t border-stone-100 align-top">
                <td className="whitespace-nowrap px-3 py-1.5 tabular-nums">{new Date(e.at).toLocaleString("fr-FR")}</td>
                <td className="px-2 py-1.5">
                  {e.actor_label}
                  {e.ip_address && <span className="block text-[11px] text-stone-500">{e.ip_address}</span>}
                </td>
                <td className="px-2 py-1.5">{ACTION_LABEL[e.action] ?? e.action}</td>
                <td className="px-2 py-1.5">
                  {ENTITY_LABEL[e.entity_type] ?? e.entity_type}
                  {e.entity_id && <span className="block font-mono text-[11px] text-stone-500">{e.entity_id.slice(0, 8)}…</span>}
                </td>
                <td className="px-2 py-1.5">
                  {e.changes && (
                    <details>
                      <summary className="cursor-pointer text-xs text-lds-green">Voir</summary>
                      <pre className="mt-1 max-w-md overflow-x-auto whitespace-pre-wrap text-[11px]">{JSON.stringify(e.changes, null, 1)}</pre>
                    </details>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {entries.length > 0 && entries.length % 50 === 0 && (
        <Button variant="secondary" onClick={loadMore}>
          Entrées plus anciennes
        </Button>
      )}
    </div>
  );
}
