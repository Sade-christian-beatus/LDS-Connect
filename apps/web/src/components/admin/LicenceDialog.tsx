"use client";
// Licence d'un membre : carte imprimable (QR signé), délivrance, suspension / révocation.
import { useBrandLogo } from "@/lib/brand";
import { BrandLogo } from "@/components/BrandLogo";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { POSITION_LABEL, STAFF_LABEL } from "@/lib/format";
import type { SquadMember, TeamRef } from "@/lib/types";
import { usePrivateImage } from "@/lib/private-image";
import { PhotoUploader } from "./PhotoUploader";
import { Badge, Button, Field, inputClass } from "./ui";

export const LICENCE_STATUS: Record<string, { label: string; tone: "green" | "amber" | "red" | "stone" }> = {
  active: { label: "Active", tone: "green" },
  suspended: { label: "Suspendue", tone: "amber" },
  revoked: { label: "Révoquée", tone: "red" },
  expired: { label: "Expirée", tone: "stone" },
};

type Props = {
  member: SquadMember;
  team: TeamRef;
  canIssue: boolean;
  canChangeStatus: boolean;
  canEditPhoto: boolean;
  onChanged: (message: string) => void;
  onError: (message: string) => void;
};

export function LicenceDialogBody({ member, team, canIssue, canChangeStatus, canEditPhoto, onChanged, onError }: Props) {
  const { api, raw } = useAuth();
  // Version locale : la photo change sans fermer la fenêtre
  const [photoVersion, setPhotoVersion] = useState(0);
  const photo = usePrivateImage(`/admin/persons/${member.person_id}/photo`, photoVersion);
  const hasPhoto = photo.state === "ready";
  const [photoNote, setPhotoNote] = useState<string | null>(null);
  const logo = useBrandLogo();
  const lic = member.licence;
  const [qr, setQr] = useState<string | null>(null);
  const [status, setStatus] = useState(lic?.status === "active" ? "suspended" : "active");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!lic) return;
    let url: string | null = null;
    let active = true;
    raw(`/admin/licences/${lic.id}/qr.svg`)
      .then((r) => r.blob())
      .then((b) => {
        if (!active) return;
        url = URL.createObjectURL(b);
        setQr(url);
      })
      .catch((e: Error) => onError(e.message));
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [lic, raw, onError]);

  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try {
      await fn();
      onChanged(ok);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!lic) {
    return (
      <div className="space-y-3 text-sm">
        <p>Aucune licence n&apos;a encore été délivrée à {member.first_name} {member.last_name}.</p>
        {canIssue ? (
          <Button
            disabled={busy}
            onClick={() =>
              run(
                () => api("/admin/licences/issue", { method: "POST", body: JSON.stringify({ membership_id: member.membership_id }) }),
                "Licence délivrée",
              )
            }
          >
            Délivrer la licence
          </Button>
        ) : (
          <p className="text-stone-500">La délivrance relève de l&apos;administration de la Ligue.</p>
        )}
      </div>
    );
  }

  const st = LICENCE_STATUS[lic.status] ?? LICENCE_STATUS.expired;
  return (
    <div className="space-y-4">
      <div className="print-area mx-auto flex max-w-sm flex-col items-center gap-2 rounded-xl border-2 border-lds-green p-4 text-center">
        <BrandLogo logoUrl={logo} size="lg" className="shadow-none" />
        <p className="text-xs font-bold uppercase tracking-wide text-lds-green">Ligue de la Souveraineté · Licence</p>
        {photo.url ? (
          // eslint-disable-next-line @next/next/no-img-element -- photo privée (blob local, authentifié)
          <img src={photo.url} alt={`Photo de ${member.first_name} ${member.last_name}`} className="h-32 w-24 rounded border border-stone-300 object-cover" />
        ) : (
          <div className="flex h-32 w-24 items-center justify-center rounded border border-dashed border-stone-300 text-center text-[11px] text-stone-400 print:hidden">
            {photo.state === "loading" ? "…" : "Sans photo"}
          </div>
        )}
        <p className="text-lg font-bold">
          {member.first_name} {member.last_name}
        </p>
        <p className="text-sm">
          {team.name} · {member.kind === "player" ? (member.position ? POSITION_LABEL[member.position] : "Joueur") : member.function ? STAFF_LABEL[member.function] : "Encadreur"}
          {member.shirt_number ? ` · n° ${member.shirt_number}` : ""}
        </p>
        {/* eslint-disable-next-line @next/next/no-img-element -- QR SVG authentifié (blob local) */}
        {qr ? <img src={qr} alt={`QR code de la licence ${lic.number}`} className="h-52 w-52" /> : <div className="h-52 w-52 animate-pulse bg-stone-100" />}
        <p className="font-mono text-sm">{lic.number}</p>
        <p className="text-xs text-stone-600">Valable jusqu&apos;au {new Date(lic.valid_until).toLocaleDateString("fr-FR")}</p>
        <Badge tone={st.tone}>{st.label}</Badge>
      </div>
      {canEditPhoto && (
        <div className="space-y-1 border-t border-stone-200 pt-3">
          <h3 className="text-sm font-semibold">Photo de la licence</h3>
          <PhotoUploader
            hasPhoto={hasPhoto}
            needsConsent={member.is_minor && !member.guardian_consent_on}
            upload={(body) => raw(`/admin/persons/${member.person_id}/photo`, { method: "PUT", body })}
            remove={() => raw(`/admin/persons/${member.person_id}/photo`, { method: "DELETE" })}
            onDone={(text) => {
              setPhotoVersion((v) => v + 1);
              setPhotoNote(text);
            }}
            onError={onError}
          />
          {photoNote && <p role="status" className="text-xs text-green-700">{photoNote}</p>}
        </div>
      )}
      <div className="flex justify-center">
        <Button variant="secondary" onClick={() => window.print()}>
          Imprimer la licence
        </Button>
      </div>

      {canChangeStatus && lic.status !== "revoked" && (
        <form
          className="space-y-2 border-t border-stone-200 pt-3"
          onSubmit={(e) => {
            e.preventDefault();
            run(
              () => api(`/admin/licences/${lic.id}/status`, { method: "POST", body: JSON.stringify({ status, reason }) }),
              `Licence ${LICENCE_STATUS[status].label.toLowerCase()}`,
            );
          }}
        >
          <h3 className="text-sm font-semibold">Changer le statut</h3>
          <div className="grid gap-2 sm:grid-cols-[10rem_1fr]">
            <Field label="Nouveau statut">
              <select className={inputClass} value={status} onChange={(e) => setStatus(e.target.value)}>
                {lic.status !== "active" && <option value="active">Réactiver</option>}
                {lic.status !== "suspended" && <option value="suspended">Suspendre</option>}
                <option value="revoked">Révoquer (définitif)</option>
              </select>
            </Field>
            <Field label="Motif (journalisé)">
              <input required minLength={3} className={inputClass} value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
          </div>
          <Button type="submit" variant={status === "revoked" ? "danger" : "primary"} disabled={busy}>
            Appliquer
          </Button>
        </form>
      )}
    </div>
  );
}
