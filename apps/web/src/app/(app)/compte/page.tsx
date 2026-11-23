"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, Field, inputClass } from "@/components/admin/ui";
import { useAuth } from "@/lib/auth";
import { ROLE_LABEL } from "@/lib/format";

const MIN_LENGTH = 12;

export default function MonComptePage() {
  const { user, ready, api, logout } = useAuth();
  const router = useRouter();
  const [f, setF] = useState({ current: "", next: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!ready) return <p className="text-stone-500">Chargement…</p>;
  if (!user) return <p>Session expirée : veuillez vous reconnecter.</p>;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (f.next.length < MIN_LENGTH) return setError(`Le nouveau mot de passe doit faire au moins ${MIN_LENGTH} caractères.`);
    if (f.next !== f.confirm) return setError("La confirmation ne correspond pas au nouveau mot de passe.");
    setBusy(true);
    try {
      await api("/auth/password", { method: "POST", body: JSON.stringify({ current_password: f.current, new_password: f.next }) });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4">
      <h1 className="text-2xl font-black tracking-tight text-pitch">Mon compte</h1>
      {user.must_change_password && !done && (
        <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          Votre mot de passe est <strong>provisoire</strong> : choisissez-en un nouveau pour accéder à votre espace.
        </p>
      )}
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-lg border border-stone-200 bg-white p-3 text-sm">
        <dt className="text-stone-500">Nom</dt>
        <dd>{user.full_name}</dd>
        <dt className="text-stone-500">E-mail</dt>
        <dd>{user.email}</dd>
        <dt className="text-stone-500">Rôle</dt>
        <dd>{user.roles.map((r) => ROLE_LABEL[r] ?? r).join(", ")}</dd>
      </dl>

      {done ? (
        <div className="space-y-3 rounded-lg bg-green-50 p-4 text-sm text-green-900" role="status">
          <p>Mot de passe modifié. Vos sessions sur les autres appareils ont été fermées.</p>
          <Button
            onClick={async () => {
              await logout();
              router.push("/connexion");
            }}
          >
            Se reconnecter
          </Button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
          <h2 className="font-semibold">Changer de mot de passe</h2>
          <Field label={user.must_change_password ? "Mot de passe provisoire reçu" : "Mot de passe actuel"}>
            <input type="password" autoComplete="current-password" required className={inputClass} value={f.current} onChange={(e) => setF({ ...f, current: e.target.value })} />
          </Field>
          <Field label="Nouveau mot de passe" hint={`${MIN_LENGTH} caractères minimum ; une phrase de plusieurs mots est idéale.`}>
            <input type="password" autoComplete="new-password" required className={inputClass} value={f.next} onChange={(e) => setF({ ...f, next: e.target.value })} />
          </Field>
          <Field label="Confirmer le nouveau mot de passe">
            <input type="password" autoComplete="new-password" required className={inputClass} value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} />
          </Field>
          {error && (
            <p role="alert" className="rounded bg-red-50 p-2 text-sm text-lds-red">
              {error}
            </p>
          )}
          <Button type="submit" disabled={busy}>
            Changer le mot de passe
          </Button>
        </form>
      )}
    </div>
  );
}
