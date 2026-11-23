"use client";
import { useCallback, useState } from "react";
import { Badge, Button, Dialog, Field, inputClass, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth";
import { ROLE_LABEL } from "@/lib/format";
import type { Credentials, PublicTeam, RoleCode, UserAdmin } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function ComptesPage() {
  return (
    <RequireAuth permission="user:manage">
      <Accounts />
    </RequireAuth>
  );
}

type DialogState = { type: "create" } | { type: "edit"; user: UserAdmin } | { type: "credentials"; creds: Credentials; reset: boolean } | null;

function Accounts() {
  const { api, user: me } = useAuth();
  const { data: users, reload } = useApi<UserAdmin[]>("/admin/users");
  const { data: teams } = useApi<PublicTeam[]>("/teams");
  const [dialog, setDialog] = useState<DialogState>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const fail = useCallback((e: unknown) => setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) }), []);

  async function save(body: Record<string, unknown>) {
    try {
      if (dialog?.type === "create") {
        const creds = await api<Credentials>("/admin/users", { method: "POST", body: JSON.stringify(body) });
        setDialog({ type: "credentials", creds, reset: false });
      } else if (dialog?.type === "edit") {
        await api(`/admin/users/${dialog.user.id}`, { method: "PATCH", body: JSON.stringify(body) });
        setDialog(null);
        setNotice({ tone: "ok", text: "Compte mis à jour" });
      }
      reload();
    } catch (e) {
      fail(e);
    }
  }

  async function toggle(u: UserAdmin) {
    try {
      await api(`/admin/users/${u.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !u.is_active }) });
      setNotice({ tone: "ok", text: u.is_active ? `${u.full_name} : compte désactivé, sessions fermées` : `${u.full_name} : compte réactivé` });
      reload();
    } catch (e) {
      fail(e);
    }
  }

  async function reset(u: UserAdmin) {
    if (!window.confirm(`Générer un nouveau mot de passe provisoire pour ${u.full_name} ? Ses sessions en cours seront fermées.`)) return;
    try {
      const creds = await api<Credentials>(`/admin/users/${u.id}/reset-password`, { method: "POST" });
      setDialog({ type: "credentials", creds, reset: true });
    } catch (e) {
      fail(e);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-black tracking-tight text-pitch">Comptes</h1>
        <Button onClick={() => setDialog({ type: "create" })}>+ Nouveau compte</Button>
      </div>
      <Notice notice={notice} onClose={() => setNotice(null)} />
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-stone-100 text-left text-xs uppercase text-stone-600">
            <tr>
              <th className="px-3 py-2">Nom</th>
              <th className="px-2 py-2">Rôle</th>
              <th className="px-2 py-2">Dernière connexion</th>
              <th className="px-2 py-2">État</th>
              <th className="px-2 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users?.map((u) => (
              <tr key={u.id} className={`border-t border-stone-100 ${u.is_active ? "" : "opacity-60"}`}>
                <td className="px-3 py-1.5">
                  <span className="font-medium">{u.full_name}</span>
                  <span className="block text-xs text-stone-500">{u.email}</span>
                </td>
                <td className="px-2 py-1.5">
                  {u.roles.map((r) => ROLE_LABEL[r] ?? r).join(", ")}
                  {u.team && <span className="block text-xs text-stone-500">{u.team.name}</span>}
                </td>
                <td className="px-2 py-1.5 text-xs">{u.last_login_at ? new Date(u.last_login_at).toLocaleString("fr-FR") : "Jamais"}</td>
                <td className="px-2 py-1.5">
                  {u.is_active ? <Badge tone="green">Actif</Badge> : <Badge tone="stone">Désactivé</Badge>}
                  {u.must_change_password && (
                    <span className="mt-0.5 block">
                      <Badge tone="amber">Mot de passe provisoire</Badge>
                    </span>
                  )}
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex flex-wrap justify-end gap-x-3">
                    <Button variant="link" onClick={() => setDialog({ type: "edit", user: u })}>
                      Modifier
                    </Button>
                    <Button variant="link" onClick={() => reset(u)}>
                      Nouveau mot de passe
                    </Button>
                    {u.id !== me?.id && (
                      <Button variant="link" className={u.is_active ? "!text-lds-red" : ""} onClick={() => toggle(u)}>
                        {u.is_active ? "Désactiver" : "Réactiver"}
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog
        open={dialog?.type === "create" || dialog?.type === "edit"}
        title={dialog?.type === "edit" ? `Modifier — ${dialog.user.full_name}` : "Nouveau compte"}
        onClose={() => setDialog(null)}
      >
        {(dialog?.type === "create" || dialog?.type === "edit") && teams && (
          <AccountForm user={dialog.type === "edit" ? dialog.user : undefined} teams={teams} onSubmit={save} onCancel={() => setDialog(null)} />
        )}
      </Dialog>

      <Dialog open={dialog?.type === "credentials"} title="Mot de passe provisoire" onClose={() => setDialog(null)}>
        {dialog?.type === "credentials" && <CredentialsView creds={dialog.creds} reset={dialog.reset} onClose={() => setDialog(null)} />}
      </Dialog>
    </div>
  );
}

function AccountForm({
  user,
  teams,
  onSubmit,
  onCancel,
}: {
  user?: UserAdmin;
  teams: PublicTeam[];
  onSubmit: (body: Record<string, unknown>) => Promise<void>;
  onCancel: () => void;
}) {
  const [f, setF] = useState({
    email: user?.email ?? "",
    full_name: user?.full_name ?? "",
    role: (user?.roles[0] ?? "delegue_match") as RoleCode,
    team_id: user?.team?.id ?? "",
  });
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="space-y-3"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        const body: Record<string, unknown> = { full_name: f.full_name, role: f.role, team_id: f.role === "gestionnaire_club" ? f.team_id || null : null };
        if (!user) body.email = f.email;
        try {
          await onSubmit(body);
        } finally {
          setBusy(false);
        }
      }}
    >
      {!user && (
        <Field label="Adresse e-mail *">
          <input type="email" required className={inputClass} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        </Field>
      )}
      <Field label="Nom complet *">
        <input required minLength={2} className={inputClass} value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
      </Field>
      <Field label="Rôle *">
        <select className={inputClass} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value as RoleCode })}>
          {Object.entries(ROLE_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </Field>
      {f.role === "gestionnaire_club" && (
        <Field label="Équipe gérée *" hint="Le compte ne verra et ne modifiera que cette équipe">
          <select required className={inputClass} value={f.team_id} onChange={(e) => setF({ ...f, team_id: e.target.value })}>
            <option value="">— choisir —</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </Field>
      )}
      <div className="flex justify-end gap-2 border-t border-stone-200 pt-3">
        <Button variant="secondary" onClick={onCancel}>
          Annuler
        </Button>
        <Button type="submit" disabled={busy}>
          {user ? "Enregistrer" : "Créer le compte"}
        </Button>
      </div>
    </form>
  );
}

function CredentialsView({ creds, reset, onClose }: { creds: Credentials; reset: boolean; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="space-y-3 text-sm">
      <p>
        {reset ? "Nouveau mot de passe provisoire" : "Compte créé"} pour <strong>{creds.user.full_name}</strong> ({creds.user.email}) :
      </p>
      <p className="select-all rounded bg-stone-100 p-3 text-center font-mono text-lg tracking-wide" aria-label="Mot de passe provisoire">
        {creds.temporary_password}
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          onClick={async () => {
            await navigator.clipboard.writeText(creds.temporary_password);
            setCopied(true);
          }}
        >
          {copied ? "Copié ✓" : "Copier"}
        </Button>
      </div>
      <p className="rounded bg-amber-50 p-2 text-amber-900">
        Ce mot de passe ne sera <strong>plus jamais affiché</strong>. Transmettez-le par un canal sûr (en main propre, appel) et
        demandez à la personne de le changer dès sa première connexion, depuis « Mon compte ».
      </p>
      <div className="flex justify-end">
        <Button onClick={onClose}>J&apos;ai transmis le mot de passe</Button>
      </div>
    </div>
  );
}
