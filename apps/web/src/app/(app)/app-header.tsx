"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BrandLogo } from "@/components/BrandLogo";
import { useAuth } from "@/lib/auth";
import { useBrandLogo } from "@/lib/brand";
import { ROLE_LABEL } from "@/lib/format";
import { useOnline } from "@/lib/offline/use-sheet";
import type { User } from "@/lib/types";

type Item = { href: string; label: string; group: string };

const GROUPS = ["Compétition", "Au stade", "Public", "Administration"];

/** Entrées de menu visibles selon les permissions. */
export function menuFor(user: User): Item[] {
  const p = new Set(user.permissions);
  const items: Item[] = [];
  if (p.has("audit:read")) items.push({ href: "/admin/tableau-de-bord", label: "Tableau de bord", group: "Compétition" });
  if (p.has("squad:read")) {
    items.push({
      href: user.team_id && !p.has("team:manage") ? `/admin/equipes/${user.team_id}` : "/admin/equipes",
      label: "Registre",
      group: "Compétition",
    });
  }
  if (p.has("fixture:manage")) items.push({ href: "/admin/calendrier", label: "Calendrier", group: "Compétition" });
  if (p.has("rules:manage")) items.push({ href: "/admin/saison", label: "Saison et règles", group: "Compétition" });
  if (p.has("sheet:edit")) items.push({ href: "/delegue", label: "Feuilles de match", group: "Compétition" });
  if (p.has("stats:read")) items.push({ href: "/admin/talents", label: "Talents", group: "Compétition" });
  if (p.has("licence:verify")) items.push({ href: "/controle", label: "Licences", group: "Au stade" });
  if (p.has("access:scan")) items.push({ href: "/acces", label: "Entrées", group: "Au stade" });
  if (p.has("ticket:manage")) items.push({ href: "/admin/billetterie", label: "Billetterie", group: "Au stade" });
  if (p.has("accreditation:manage")) items.push({ href: "/admin/accreditations", label: "Accréditations", group: "Au stade" });
  if (p.has("vote:manage")) items.push({ href: "/admin/votes", label: "Votes", group: "Public" });
  if (p.has("audit:read")) items.push({ href: "/admin/journal", label: "Journal", group: "Administration" });
  if (p.has("user:manage")) items.push({ href: "/admin/comptes", label: "Comptes", group: "Administration" });
  if (p.has("brand:manage")) items.push({ href: "/admin/identite", label: "Identité", group: "Administration" });
  return items;
}

/** Écran d'arrivée après connexion : l'outil principal du rôle. */
export function landingFor(user: User): string {
  if (user.must_change_password || user.mfa_setup_required) return "/compte";
  const p = new Set(user.permissions);
  if (p.has("audit:read")) return "/admin/tableau-de-bord";
  if (p.has("team:manage")) return "/admin/equipes";
  if (p.has("squad:write") && user.team_id) return `/admin/equipes/${user.team_id}`;
  if (p.has("sheet:edit")) return "/delegue";
  if (p.has("stats:read") && !p.has("squad:write")) return "/admin/talents";
  if (p.has("access:scan") && !p.has("squad:read")) return "/acces";
  if (p.has("licence:verify") && !p.has("squad:read")) return "/controle";
  return menuFor(user)[0]?.href ?? "/";
}

/** Beaucoup d'outils : menu latéral sur grand écran ; sinon une rangée sous l'en-tête. */
const SIDEBAR_MIN = 5;

export function AppHeader() {
  const { user, logout } = useAuth();
  const online = useOnline();
  const router = useRouter();
  const pathname = usePathname();
  const logo = useBrandLogo();
  // Mot de passe provisoire : aucun menu tant qu'il n'est pas changé
  const menu = user && !user.must_change_password && !user.mfa_setup_required ? menuFor(user) : [];
  const sidebar = menu.length >= SIDEBAR_MIN;
  const active = (href: string) => pathname.startsWith(href);

  return (
    <>
      <header className="sticky top-0 z-30 bg-pitch text-white shadow print:hidden">
        <div aria-hidden className="flex h-1">
          <span className="flex-1 bg-lds-red" />
          <span className="flex-1 bg-lds-gold" />
          <span className="flex-1 bg-lds-green" />
        </div>
        <div className="flex items-center justify-between gap-2 px-3 py-2 text-[13px] sm:px-4 sm:text-sm">
          <Link href={user ? landingFor(user) : "/"} className="flex items-center gap-2 font-black tracking-tight">
            <BrandLogo logoUrl={logo} size="sm" />
            <span className="leading-tight">
              <span className="block text-[10px] font-semibold uppercase tracking-[0.2em] text-lds-gold">LDS Connect</span>
              <span className="block">Officiels</span>
            </span>
          </Link>
          <div className="flex items-center gap-2 sm:gap-3">
            <span
              className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${online ? "bg-white/10" : "bg-lds-red"}`}
              role="status"
            >
              <span className={`h-2 w-2 rounded-full ${online ? "bg-green-400" : "bg-white"}`} />
              {online ? "En ligne" : "Hors connexion"}
            </span>
            {user && (
              <Link href="/compte" className="hidden items-center gap-2 rounded-full py-0.5 pl-0.5 pr-3 hover:bg-white/10 sm:flex" title={user.email}>
                <span aria-hidden className="flex h-7 w-7 items-center justify-center rounded-full bg-lds-gold text-xs font-black text-pitch">
                  {user.full_name
                    .split(/\s+/)
                    .map((w) => w[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()}
                </span>
                <span className="leading-tight">
                  <span className="block font-semibold">Mon compte</span>
                  <span className="block text-[10px] text-green-100/80">{ROLE_LABEL[user.roles[0]] ?? ""}</span>
                </span>
              </Link>
            )}
            {user && (
              <Link href="/compte" className="whitespace-nowrap underline sm:hidden">
                Mon compte
              </Link>
            )}
            {user && (
              <button
                type="button"
                className="whitespace-nowrap rounded-full border border-white/25 px-2.5 py-1 hover:bg-white/10 sm:px-3"
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

      {menu.length > 0 && (
        <nav
          aria-label="Espace officiels"
          data-sidebar={sidebar ? "" : undefined}
          className={`sticky top-[3.15rem] z-20 border-b border-stone-200 bg-white/95 backdrop-blur print:hidden ${
            sidebar ? "lg:fixed lg:bottom-0 lg:left-0 lg:top-[3.15rem] lg:w-56 lg:overflow-y-auto lg:border-b-0 lg:border-r lg:bg-white" : ""
          }`}
        >
          <div className={`no-scrollbar flex gap-1 overflow-x-auto px-3 py-2 text-sm ${sidebar ? "lg:flex-col lg:gap-4 lg:overflow-visible lg:px-3 lg:py-5" : ""}`}>
            {GROUPS.map((g) => {
              const items = menu.filter((m) => m.group === g);
              if (!items.length) return null;
              return (
                <div key={g} className={`flex gap-1 ${sidebar ? "lg:flex-col" : ""}`}>
                  {sidebar && <p className="hidden px-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-stone-400 lg:block">{g}</p>}
                  {items.map((m) => (
                    <Link
                      key={m.href}
                      href={m.href}
                      aria-current={active(m.href) ? "page" : undefined}
                      className={`whitespace-nowrap rounded-lg px-3 py-1.5 font-medium transition ${
                        active(m.href) ? "bg-pitch text-white shadow-sm" : "text-stone-700 hover:bg-stone-100"
                      }`}
                    >
                      {m.label}
                    </Link>
                  ))}
                </div>
              );
            })}
          </div>
        </nav>
      )}
    </>
  );
}
