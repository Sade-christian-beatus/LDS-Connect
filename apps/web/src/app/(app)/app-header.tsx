"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useOnline } from "@/lib/offline/use-sheet";

export function AppHeader() {
  const { user, logout } = useAuth();
  const online = useOnline();
  const router = useRouter();
  return (
    <header className="sticky top-0 z-10 bg-lds-green text-white shadow">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-2 px-3 py-2 text-sm">
        <Link href="/delegue" className="font-bold">
          LDS · Officiels
        </Link>
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${online ? "bg-green-700" : "bg-lds-red"}`}
            role="status"
          >
            {online ? "En ligne" : "Hors connexion"}
          </span>
          {user && (
            <button
              type="button"
              className="underline"
              onClick={async () => {
                await logout();
                router.push("/connexion");
              }}
            >
              Déconnexion
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
