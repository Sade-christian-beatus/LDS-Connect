"use client";
// Formulaire joueur / encadreur (création et modification).
// En modification, CNIB et téléphone ne sont jamais pré-remplis : ils ne sont envoyés que
// s'ils sont ressaisis (les lire passe par une consultation journalisée).
import { useState } from "react";
import { POSITION_LABEL, STAFF_LABEL } from "@/lib/format";
import type { Region, SquadMember } from "@/lib/types";
import { Button, Field, inputClass } from "./ui";

export type PersonKind = "player" | "staff";

type Props = {
  kind: PersonKind;
  member?: SquadMember; // absent : création
  regions: Region[];
  teamRegionId: string;
  canVerifyResidence: boolean;
  onSubmit: (body: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
};

const FOOT_LABEL: Record<string, string> = { right: "Droit", left: "Gauche", both: "Les deux" };

export function PersonForm({ kind, member, regions, teamRegionId, canVerifyResidence, onSubmit, onCancel }: Props) {
  const creating = !member;
  const [f, setF] = useState({
    first_name: member?.first_name ?? "",
    last_name: member?.last_name ?? "",
    display_name: member?.display_name ?? "",
    birth_date: member?.birth_date ?? "",
    birth_place: member?.birth_place ?? "",
    nationality: member?.nationality ?? "BF",
    cnib_number: "",
    phone: "",
    guardian_consent_on: member?.guardian_consent_on ?? "",
    position: member?.position ?? "MF",
    preferred_foot: member?.preferred_foot ?? "",
    residence_region_id: member?.residence_region_id ?? (creating ? teamRegionId : ""),
    residence_since: member?.residence_since ?? "",
    residence_verified: member?.residence_verified ?? false,
    fbf_licence_number: member?.fbf_licence_number ?? "",
    shirt_number: member?.shirt_number?.toString() ?? "",
    function: member?.function ?? "assistant_coach",
    qualification: member?.qualification ?? "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setF({ ...f, [k]: e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value });

  function body(): Record<string, unknown> {
    const opt = (v: string) => (v === "" ? null : v);
    const b: Record<string, unknown> = {
      first_name: f.first_name.trim(),
      last_name: f.last_name.trim(),
      display_name: opt(f.display_name.trim()),
      birth_date: f.birth_date,
    };
    if (kind === "player") {
      Object.assign(b, {
        birth_place: opt(f.birth_place),
        guardian_consent_on: opt(f.guardian_consent_on),
        position: f.position,
        preferred_foot: opt(f.preferred_foot),
        residence_region_id: opt(f.residence_region_id),
        residence_since: opt(f.residence_since),
        fbf_licence_number: opt(f.fbf_licence_number),
        shirt_number: f.shirt_number === "" ? null : Number(f.shirt_number),
      });
      if (creating) b.nationality = f.nationality;
      if (!creating && canVerifyResidence) b.residence_verified = f.residence_verified;
    } else {
      Object.assign(b, { function: f.function, qualification: opt(f.qualification) });
      if (creating) b.nationality = f.nationality;
    }
    // Données sensibles : envoyées seulement si saisies
    if (f.cnib_number.trim()) b.cnib_number = f.cnib_number.trim();
    if (f.phone.trim()) b.phone = f.phone.trim();
    return b;
  }

  return (
    <form
      className="space-y-3"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
          await onSubmit(body());
        } finally {
          setBusy(false);
        }
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Prénom(s) *">
          <input required className={inputClass} value={f.first_name} onChange={set("first_name")} />
        </Field>
        <Field label="Nom *">
          <input required className={inputClass} value={f.last_name} onChange={set("last_name")} />
        </Field>
        <Field label="Nom d'usage" hint="Seul nom affiché publiquement (défaut : initiale + nom)">
          <input className={inputClass} value={f.display_name} onChange={set("display_name")} />
        </Field>
        <Field label="Date de naissance *">
          <input required type="date" className={inputClass} value={f.birth_date} onChange={set("birth_date")} />
        </Field>
        {kind === "player" && (
          <Field label="Lieu de naissance">
            <input className={inputClass} value={f.birth_place} onChange={set("birth_place")} />
          </Field>
        )}
        {creating && (
          <Field label="Nationalité (code pays)">
            <input className={inputClass} maxLength={2} value={f.nationality} onChange={set("nationality")} />
          </Field>
        )}
        <Field label="N° CNIB" hint={creating ? "Chiffré en base" : "Laisser vide pour ne pas modifier"}>
          <input className={inputClass} autoComplete="off" value={f.cnib_number} onChange={set("cnib_number")} />
        </Field>
        <Field label="Téléphone" hint={creating ? "Chiffré en base" : "Laisser vide pour ne pas modifier"}>
          <input className={inputClass} type="tel" autoComplete="off" value={f.phone} onChange={set("phone")} />
        </Field>
      </div>

      {kind === "player" ? (
        <fieldset className="grid gap-3 border-t border-stone-200 pt-3 sm:grid-cols-3">
          <legend className="sr-only">Informations sportives</legend>
          <Field label="Poste *">
            <select className={inputClass} value={f.position} onChange={set("position")}>
              {Object.entries(POSITION_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Pied">
            <select className={inputClass} value={f.preferred_foot} onChange={set("preferred_foot")}>
              <option value="">—</option>
              {Object.entries(FOOT_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
          <Field label="N° de maillot">
            <input type="number" min={1} max={99} className={inputClass} value={f.shirt_number} onChange={set("shirt_number")} />
          </Field>
          <Field label="Région de résidence" hint="Base du statut « local »">
            <select className={inputClass} value={f.residence_region_id} onChange={set("residence_region_id")}>
              <option value="">—</option>
              {regions.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Réside depuis le">
            <input type="date" className={inputClass} value={f.residence_since} onChange={set("residence_since")} />
          </Field>
          <Field label="Licence FBF">
            <input className={inputClass} value={f.fbf_licence_number} onChange={set("fbf_licence_number")} />
          </Field>
          <Field label="Autorisation parentale le" hint="Joueurs mineurs">
            <input type="date" className={inputClass} value={f.guardian_consent_on} onChange={set("guardian_consent_on")} />
          </Field>
          {!creating && canVerifyResidence && (
            <label className="flex items-center gap-2 self-end text-sm">
              <input type="checkbox" checked={f.residence_verified} onChange={set("residence_verified")} />
              Résidence vérifiée (justificatif)
            </label>
          )}
        </fieldset>
      ) : (
        <fieldset className="grid gap-3 border-t border-stone-200 pt-3 sm:grid-cols-2">
          <legend className="sr-only">Fonction</legend>
          <Field label="Fonction *">
            <select className={inputClass} value={f.function} onChange={set("function")}>
              {Object.entries(STAFF_LABEL).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Diplôme / qualification">
            <input className={inputClass} value={f.qualification} onChange={set("qualification")} />
          </Field>
        </fieldset>
      )}

      <div className="flex justify-end gap-2 border-t border-stone-200 pt-3">
        <Button variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" disabled={busy}>
          {busy ? "Enregistrement…" : creating ? "Ajouter à l'effectif" : "Enregistrer"}
        </Button>
      </div>
    </form>
  );
}
