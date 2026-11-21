"use client";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function RequireAuth({ permission, children }: { permission: string; children: React.ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready) return <p className="text-stone-500">Chargement…</p>;
  if (!user) {
    return (
      <p className="text-stone-700">
        Session expirée ou hors connexion.{" "}
        <Link href="/connexion" className="font-semibold text-lds-green underline">
          Se connecter
        </Link>
      </p>
    );
  }
  if (!user.permissions.includes(permission)) {
    return <p className="text-lds-red">Votre rôle ne permet pas d&apos;accéder à cet écran.</p>;
  }
  return <>{children}</>;
}
