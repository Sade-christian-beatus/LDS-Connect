"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useOnline } from "@/lib/offline/use-sheet";
import type { User } from "@/lib/types";

/** Entrées de menu visibles selon les permissions. */
export function menuFor(user: User): { href: string; label: string }[] {
  const p = new Set(user.permissions);
  const items: { href: string; label: string }[] = [];
  if (p.has("squad:read")) {
    items.push({ href: user.team_id && !p.has("team:manage") ? `/admin/equipes/${user.team_id}` : "/admin/equipes", label: "Registre" });
  }
  if (p.has("fixture:manage")) items.push({ href: "/admin/calendrier", label: "Calendrier" });
  if (p.has("sheet:edit")) items.push({ href: "/delegue", label: "Feuilles de match" });
  if (p.has("licence:verify")) items.push({ href: "/controle", label: "Contrôle" });
  if (p.has("audit:read")) items.push({ href: "/admin/journal", label: "Journal" });
  if (p.has("user:manage")) items.push({ href: "/admin/comptes", label: "Comptes" });
  return items;
}

/** Écran d'arrivée après connexion : l'outil principal du rôle. */
export function landingFor(user: User): string {
  const p = new Set(user.permissions);
  if (p.has("team:manage")) return "/admin/equipes";
  if (p.has("squad:write") && user.team_id) return `/admin/equipes/${user.team_id}`;
  if (p.has("sheet:edit")) return "/delegue";
  if (p.has("licence:verify") && !p.has("squad:read")) return "/controle";
  return menuFor(user)[0]?.href ?? "/";
}

export function AppHeader() {
  const { user, logout } = useAuth();
  const online = useOnline();
  const router = useRouter();
  const pathname = usePathname();
  const menu = user ? menuFor(user) : [];
  return (
    <header className="sticky top-0 z-10 bg-lds-green text-white shadow">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
        <Link href="/" className="font-bold">
          LDS · Officiels
        </Link>
        {menu.length > 0 && (
          <nav aria-label="Espace officiels" className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto">
            {menu.map((m) => (
              <Link
                key={m.href}
                href={m.href}
                aria-current={pathname.startsWith(m.href) ? "page" : undefined}
                className={`whitespace-nowrap rounded px-2 py-1 ${pathname.startsWith(m.href) ? "bg-white/20 font-semibold" : "hover:bg-white/10"}`}
              >
                {m.label}
              </Link>
            ))}
          </nav>
        )}
        <div className="flex items-center gap-3">
          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${online ? "bg-green-700" : "bg-lds-red"}`} role="status">
            {online ? "En ligne" : "Hors connexion"}
          </span>
          {user && (
            <Link href="/compte" className="underline" title={user.email}>
              Mon compte
            </Link>
          )}
          {user && (
            <button
              type="button"
              className="underline"
              title={user.email}
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
