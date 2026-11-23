"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import { LICENCE_STATUS, LicenceDialogBody } from "@/components/admin/LicenceDialog";
import { type PersonKind, PersonForm } from "@/components/admin/PersonForm";
import { Badge, Button, Dialog, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { TeamBadge } from "@/components/TeamBadge";
import { ApiError, useAuth } from "@/lib/auth";
import { POSITION_LABEL, STAFF_LABEL } from "@/lib/format";
import type { Region, SensitiveData, Squad, SquadMember } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type DialogState =
  | { type: "create"; kind: PersonKind }
  | { type: "edit"; member: SquadMember }
  | { type: "licence"; member: SquadMember }
  | { type: "sensitive"; member: SquadMember; data?: SensitiveData }
  | { type: "release"; member: SquadMember }
  | null;

export function TeamAdmin() {
  const { id } = useParams<{ id: string }>();
  return (
    <RequireAuth permission="squad:read">
      <TeamScreen teamId={id} />
    </RequireAuth>
  );
}

function describeError(e: unknown): string {
  if (e instanceof ApiError && e.details && typeof e.details === "object") {
    return `${e.message} — ${Object.values(e.details as Record<string, string[]>).flat().join(" ; ")}`;
  }
  return e instanceof Error ? e.message : String(e);
}

function TeamScreen({ teamId }: { teamId: string }) {
  const { user, api } = useAuth();
  const { data: squad, error, reload } = useApi<Squad>(`/admin/teams/${teamId}/squad`);
  const { data: regions } = useApi<Region[]>("/regions");
  const [tab, setTab] = useState<PersonKind>("player");
  const [dialog, setDialog] = useState<DialogState>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const perms = useMemo(() => new Set(user?.permissions ?? []), [user]);
  const can = (p: string) => perms.has(p);

  const ok = useCallback(
    (text: string) => {
      setNotice({ tone: "ok", text });
      setDialog(null);
      reload();
    },
    [reload],
  );
  const fail = useCallback((text: string) => setNotice({ tone: "error", text }), []);

  if (error) return <p className="text-lds-red">{error}</p>;
  if (!squad) return <p className="text-stone-500">Chargement de l&apos;effectif…</p>;

  const members = squad.members.filter((m) => m.kind === tab);
  const missing = squad.members.filter((m) => !m.licence).length;
  const pending = squad.members.filter((m) => m.residence_pending).length;

  async function save(body: Record<string, unknown>) {
    try {
      if (dialog?.type === "create") {
        await api(`/admin/teams/${teamId}/${dialog.kind === "player" ? "players" : "staff"}`, {
          method: "POST",
          body: JSON.stringify(body),
        });
        ok(`${String(body.first_name)} ${String(body.last_name)} ajouté(e) à l'effectif`);
      } else if (dialog?.type === "edit") {
        const m = dialog.member;
        await api(`/admin/${m.kind === "player" ? "players" : "staff"}/${m.person_id}`, {
          method: "PATCH",
          body: JSON.stringify(body),
        });
        ok("Modifications enregistrées");
      }
    } catch (e) {
      fail(describeError(e));
    }
  }

  async function issueAll() {
    setBusy(true);
    try {
      const r = await api<{ issued: number; errors: { person_id: string; detail: string }[] }>(
        `/admin/teams/${teamId}/licences/issue-all`,
        { method: "POST" },
      );
      if (r.errors.length) fail(`${r.issued} licence(s) délivrée(s) ; refus : ${r.errors.map((e) => e.detail).join(" ; ")}`);
      else ok(`${r.issued} licence(s) délivrée(s)`);
      reload();
    } catch (e) {
      fail(describeError(e));
    } finally {
      setBusy(false);
    }
  }

  async function revealSensitive(member: SquadMember) {
    try {
      const data = await api<SensitiveData>(`/admin/persons/${member.person_id}/sensitive`);
      setDialog({ type: "sensitive", member, data });
    } catch (e) {
      fail(describeError(e));
    }
  }

  async function release(member: SquadMember) {
    try {
      await api(`/admin/persons/${member.person_id}/release`, { method: "POST" });
      ok(`${member.first_name} ${member.last_name} retiré(e) de l'effectif (licence révoquée)`);
    } catch (e) {
      fail(describeError(e));
    }
  }

  const players = squad.members.filter((m) => m.kind === "player").length;
  const staff = squad.members.length - players;

  return (
    <div className="space-y-4">
      {can("team:manage") && (
        <Link href="/admin/equipes" className="text-sm text-lds-green underline">
          ← Toutes les équipes
        </Link>
      )}
      <header className="flex flex-wrap items-center gap-4">
        <TeamBadge team={squad.team} size="lg" />
        <div className="flex-1">
          <h1 className="text-2xl font-black tracking-tight text-pitch">{squad.team.name}</h1>
          <p className="text-sm text-stone-600">
            Région {squad.team.region.name} · Poule {squad.team.pool_code}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {can("squad:write") && (
            <>
              <Button onClick={() => setDialog({ type: "create", kind: "player" })}>+ Joueur</Button>
              <Button variant="secondary" onClick={() => setDialog({ type: "create", kind: "staff" })}>
                + Encadreur
              </Button>
            </>
          )}
          {can("licence:issue") && missing > 0 && (
            <Button variant="secondary" disabled={busy} onClick={issueAll}>
              Délivrer les {missing} licence(s) manquante(s)
            </Button>
          )}
        </div>
      </header>

      <Notice notice={notice} onClose={() => setNotice(null)} />

      <section aria-label="Conformité de l'effectif" className="flex flex-wrap gap-2">
        {squad.compliance.map((c) => (
          <span
            key={c.code}
            title={c.detail}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${c.ok ? "bg-green-100 text-green-800" : "bg-red-100 text-lds-red"}`}
          >
            {c.ok ? "✓" : "✗"} {c.label} — {c.detail}
          </span>
        ))}
        {pending > 0 && (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
            {pending} résidence(s) à vérifier
          </span>
        )}
      </section>

      <div className="flex gap-1" role="tablist" aria-label="Catégorie">
        {(
          [
            ["player", `Joueurs (${players})`],
            ["staff", `Encadrement (${staff})`],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className={`rounded-t px-4 py-2 text-sm font-semibold ${tab === k ? "bg-white text-green-900 ring-1 ring-stone-200" : "text-stone-600"}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-stone-100 text-left text-xs uppercase text-stone-600">
            <tr>
              {tab === "player" && <th className="px-2 py-2">N°</th>}
              <th className="px-2 py-2">Nom</th>
              <th className="px-2 py-2">{tab === "player" ? "Poste" : "Fonction"}</th>
              <th className="px-2 py-2">Âge</th>
              {tab === "player" && <th className="px-2 py-2">Statut local</th>}
              <th className="px-2 py-2">Licence</th>
              <th className="px-2 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.membership_id} className="border-t border-stone-100">
                {tab === "player" && <td className="px-2 py-1.5 font-bold tabular-nums">{m.shirt_number ?? "–"}</td>}
                <td className="px-2 py-1.5">
                  <span className="font-medium">
                    {m.first_name} {m.last_name}
                  </span>
                  <span className="block text-xs text-stone-500">Public : {m.display_name}</span>
                </td>
                <td className="px-2 py-1.5">
                  {m.kind === "player" ? (m.position ? POSITION_LABEL[m.position] : "") : m.function ? STAFF_LABEL[m.function] : ""}
                </td>
                <td className="px-2 py-1.5 tabular-nums">
                  {m.age} ans {m.is_minor && <Badge tone="blue">Mineur</Badge>}
                  {m.is_minor && !m.guardian_consent_on && (
                    <span className="block text-[11px] text-amber-800">Autorisation parentale non saisie</span>
                  )}
                </td>
                {tab === "player" && (
                  <td className="px-2 py-1.5">
                    {m.is_local ? (
                      <Badge tone="green">Local</Badge>
                    ) : m.residence_pending ? (
                      <Badge tone="amber">À vérifier</Badge>
                    ) : (
                      <Badge tone="stone">Non local</Badge>
                    )}
                    <span className="block text-[11px] text-stone-500">{m.residence_region ?? "Résidence non renseignée"}</span>
                  </td>
                )}
                <td className="px-2 py-1.5">
                  {m.licence ? (
                    <>
                      <span className="font-mono text-xs">{m.licence.number}</span>{" "}
                      <Badge tone={LICENCE_STATUS[m.licence.status]?.tone ?? "stone"}>
                        {LICENCE_STATUS[m.licence.status]?.label ?? m.licence.status}
                      </Badge>
                    </>
                  ) : (
                    <Badge tone="amber">À délivrer</Badge>
                  )}
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex flex-wrap justify-end gap-x-3 gap-y-1">
                    <Button variant="link" onClick={() => setDialog({ type: "licence", member: m })}>
                      Licence
                    </Button>
                    {can("squad:write") && (
                      <Button variant="link" onClick={() => setDialog({ type: "edit", member: m })}>
                        Modifier
                      </Button>
                    )}
                    {can("sensitive:read") && (m.has_cnib || m.has_phone) && (
                      <Button variant="link" onClick={() => revealSensitive(m)}>
                        CNIB / tél.
                      </Button>
                    )}
                    {can("squad:write") && (
                      <Button variant="link" className="!text-lds-red" onClick={() => setDialog({ type: "release", member: m })}>
                        Retirer
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Fenêtres */}
      <Dialog
        open={dialog?.type === "create" || dialog?.type === "edit"}
        wide
        title={
          dialog?.type === "create"
            ? dialog.kind === "player"
              ? "Nouveau joueur"
              : "Nouvel encadreur"
            : dialog?.type === "edit"
              ? `Modifier — ${dialog.member.first_name} ${dialog.member.last_name}`
              : ""
        }
        onClose={() => setDialog(null)}
      >
        {(dialog?.type === "create" || dialog?.type === "edit") && regions && (
          <PersonForm
            kind={dialog.type === "create" ? dialog.kind : dialog.member.kind}
            member={dialog.type === "edit" ? dialog.member : undefined}
            regions={regions}
            teamRegionId={squad.team.region.id}
            canVerifyResidence={can("residence:verify")}
            onSubmit={save}
            onCancel={() => setDialog(null)}
          />
        )}
      </Dialog>

      <Dialog open={dialog?.type === "licence"} title="Licence" onClose={() => setDialog(null)}>
        {dialog?.type === "licence" && (
          <LicenceDialogBody
            member={dialog.member}
            team={squad.team}
            canIssue={can("licence:issue")}
            canChangeStatus={can("licence:status")}
            onChanged={ok}
            onError={fail}
          />
        )}
      </Dialog>

      <Dialog open={dialog?.type === "sensitive"} title="Données sensibles" onClose={() => setDialog(null)}>
        {dialog?.type === "sensitive" && dialog.data && (
          <div className="space-y-3 text-sm">
            <p className="rounded bg-amber-50 p-2 text-amber-900">
              Consultation enregistrée dans le journal d&apos;audit à votre nom.
            </p>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
              <dt className="text-stone-500">Personne</dt>
              <dd className="font-medium">
                {dialog.member.first_name} {dialog.member.last_name}
              </dd>
              <dt className="text-stone-500">N° CNIB</dt>
              <dd className="font-mono">{dialog.data.cnib_number ?? "—"}</dd>
              <dt className="text-stone-500">Téléphone</dt>
              <dd className="font-mono">{dialog.data.phone ?? "—"}</dd>
            </dl>
          </div>
        )}
      </Dialog>

      <Dialog open={dialog?.type === "release"} title="Retirer de l'effectif" onClose={() => setDialog(null)}>
        {dialog?.type === "release" && (
          <div className="space-y-3 text-sm">
            <p>
              Retirer <strong>{dialog.member.first_name} {dialog.member.last_name}</strong> de l&apos;effectif ? Sa
              licence sera <strong>révoquée</strong> et son numéro libéré. L&apos;historique des matchs est conservé.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDialog(null)}>
                Annuler
              </Button>
              <Button variant="danger" onClick={() => release(dialog.member)}>
                Retirer de l&apos;effectif
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
