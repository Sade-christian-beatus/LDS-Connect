"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge, Button, Field, inputClass } from "@/components/admin/ui";
import { useAuth } from "@/lib/auth";
import { ROLE_LABEL } from "@/lib/format";
import type { User } from "@/lib/types";

const MIN_LENGTH = 12;

export default function MonComptePage() {
  const { user, ready, api, logout, updateUser } = useAuth();
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

      {user.mfa_setup_required && (
        <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
          Votre rôle exige la <strong>double authentification</strong> : activez-la ci-dessous pour accéder à votre espace.
        </p>
      )}

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

      <MfaSection user={user} api={api} onUser={updateUser} />
    </div>
  );
}

type Api = <T>(path: string, init?: RequestInit) => Promise<T>;

function MfaSection({ user, api, onUser }: { user: User; api: Api; onUser: (u: User) => void }) {
  const [setup, setSetup] = useState<{ secret: string; qr_svg: string } | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3 rounded-lg border border-stone-200 bg-white p-4" aria-label="Double authentification">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">Double authentification</h2>
        {user.mfa_enabled ? <Badge tone="green">Activée</Badge> : <Badge tone="stone">Désactivée</Badge>}
      </div>
      <p className="text-sm text-stone-600">
        À chaque connexion, en plus du mot de passe, un code à 6 chiffres donné par une application d&apos;authentification
        (Google Authenticator, Microsoft Authenticator, FreeOTP…) installée sur votre téléphone. Un mot de passe volé ne
        suffit plus.
      </p>

      {!user.mfa_enabled && !setup && (
        <Button disabled={busy} onClick={() => run(async () => setSetup(await api("/auth/mfa/setup", { method: "POST" })))}>
          Activer la double authentification
        </Button>
      )}

      {!user.mfa_enabled && setup && (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              const u = await api<User>("/auth/mfa/enable", { method: "POST", body: JSON.stringify({ code }) });
              onUser(u);
              setSetup(null);
              setCode("");
              setMessage("Double authentification activée : le code vous sera demandé à chaque connexion.");
            });
          }}
        >
          <ol className="list-inside list-decimal space-y-1 text-sm">
            <li>Dans l&apos;application, choisissez « Ajouter un compte » puis « Scanner un QR code ».</li>
            <li>Scannez ce code (ou saisissez la clé affichée dessous).</li>
            <li>Tapez le code à 6 chiffres affiché par l&apos;application.</li>
          </ol>
          <div className="flex flex-wrap items-center gap-4">
            {/* eslint-disable-next-line @next/next/no-img-element -- QR SVG généré par l'API */}
            <img src={`data:image/svg+xml;utf8,${encodeURIComponent(setup.qr_svg)}`} alt="QR code d'activation" className="h-44 w-44 rounded border border-stone-200" />
            <p className="max-w-full break-all font-mono text-xs text-stone-600" aria-label="Clé de configuration">
              {setup.secret.match(/.{1,4}/g)?.join(" ")}
            </p>
          </div>
          <Field label="Code à 6 chiffres">
            <input inputMode="numeric" autoComplete="one-time-code" required className={`${inputClass} font-mono text-lg tracking-widest`} value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
          <Button type="submit" disabled={busy}>
            Confirmer l&apos;activation
          </Button>
        </form>
      )}

      {user.mfa_enabled && user.mfa_required && <p className="text-xs text-stone-500">Obligatoire pour votre rôle.</p>}
      {user.mfa_enabled && !user.mfa_required && (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              const u = await api<User>("/auth/mfa/disable", { method: "POST", body: JSON.stringify({ code }) });
              onUser(u);
              setCode("");
              setMessage("Double authentification désactivée.");
            });
          }}
        >
          <Field label="Code actuel pour désactiver">
            <input inputMode="numeric" autoComplete="one-time-code" required className={inputClass} value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
          <Button type="submit" variant="secondary" disabled={busy}>
            Désactiver
          </Button>
        </form>
      )}
      {message && (
        <p role="status" className="text-sm text-green-700">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="rounded bg-red-50 p-2 text-sm text-lds-red">
          {error}
        </p>
      )}
    </section>
  );
}
