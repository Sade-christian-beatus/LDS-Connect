"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { PitchLines } from "@/components/Illustrations";
import { useAuth } from "@/lib/auth";
import { useBrandLogo } from "@/lib/brand";
import { landingFor } from "../app-header";

export default function ConnexionPage() {
  const { login, loginMfa } = useAuth();
  const logo = useBrandLogo();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Deuxième étape : code de l'application d'authentification
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [code, setCode] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mfaToken) {
        const user = await loginMfa(mfaToken, code);
        router.push(landingFor(user));
        return;
      }
      const result = await login(email, password);
      if ("mfaToken" in result) {
        setMfaToken(result.mfaToken);
        setPassword("");
        return;
      }
      router.push(landingFor(result));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connexion impossible");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto mt-4 grid max-w-4xl overflow-hidden rounded-2xl bg-white shadow-xl md:grid-cols-2">
      <div className="relative hidden flex-col justify-between bg-gradient-to-br from-pitch to-lds-green p-8 text-white md:flex">
        <div aria-hidden className="pointer-events-none absolute -bottom-16 -right-16 h-64 w-64 rounded-full border-[28px] border-white/5" />
        <PitchLines className="text-white/[0.06]" />
        <div className="relative space-y-4">
          <BrandLogo logoUrl={logo} size="xl" />
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-lds-gold">LDS Connect</p>
            <p className="mt-1 text-3xl font-black leading-tight">Ligue de la Souveraineté</p>
          </div>
        </div>
        <ul className="relative space-y-2 text-sm text-green-50">
          <li>✓ Registre, licences et calendrier</li>
          <li>✓ Feuilles de match, même sans réseau</li>
          <li>✓ Contrôle des licences et des entrées au stade</li>
          <li>✓ Billetterie, votes du public</li>
        </ul>
        <div aria-hidden className="flex h-1.5 overflow-hidden rounded-full">
          <span className="flex-1 bg-lds-red" />
          <span className="flex-1 bg-lds-gold" />
          <span className="flex-1 bg-white" />
        </div>
      </div>
      <form onSubmit={onSubmit} className="space-y-4 p-6 sm:p-8">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-pitch">Espace officiels</h1>
          <p className="text-sm text-stone-600">Connexion réservée aux comptes créés par la Ligue.</p>
        </div>
        {mfaToken ? (
          <div className="space-y-3">
            <p className="rounded-lg bg-green-50 p-3 text-sm text-green-900">
              Mot de passe vérifié. Ouvrez votre application d&apos;authentification et saisissez le code à 6 chiffres
              affiché pour « LDS Connect ».
            </p>
            <label className="block text-sm font-medium">
              Code de vérification
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9 ]{6,7}"
                required
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2.5 text-center font-mono text-2xl tracking-[0.4em] focus:border-lds-green focus:outline-none focus:ring-2 focus:ring-lds-green/20"
              />
            </label>
            <button
              type="button"
              className="text-xs text-stone-500 underline"
              onClick={() => {
                setMfaToken(null);
                setCode("");
              }}
            >
              Changer de compte
            </button>
          </div>
        ) : (
          <>
            <label className="block text-sm font-medium">
              Adresse e-mail
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2.5 focus:border-lds-green focus:outline-none focus:ring-2 focus:ring-lds-green/20"
              />
            </label>
            <label className="block text-sm font-medium">
              Mot de passe
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2.5 focus:border-lds-green focus:outline-none focus:ring-2 focus:ring-lds-green/20"
              />
            </label>
          </>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-lds-red">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-pitch py-2.5 font-bold text-white shadow hover:bg-lds-green disabled:opacity-60"
        >
          {busy ? "Connexion…" : mfaToken ? "Valider le code" : "Se connecter"}
        </button>
        <p className="text-center text-xs text-stone-500">
          <Link href="/" className="underline">
            Retour au site public
          </Link>
        </p>
      </form>
    </div>
  );
}
