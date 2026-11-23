"use client";
// Navigation du site public : menu en haut (ordinateur) et barre d'onglets en bas (téléphone).
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/public-nav";

const isActive = (pathname: string, href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

export function TopNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Navigation principale" className="no-scrollbar -mx-1 flex gap-1 overflow-x-auto text-sm">
      {NAV.map((n) => {
        const on = isActive(pathname, n.href);
        return (
          <Link
            key={n.href}
            href={n.href}
            aria-current={on ? "page" : undefined}
            className={`relative whitespace-nowrap rounded-full px-3 py-1.5 font-medium transition ${
              on ? "bg-white text-pitch" : "text-white/85 hover:bg-white/10 hover:text-white"
            }`}
          >
            {n.label}
          </Link>
        );
      })}
    </nav>
  );
}

const TABS = [
  { href: "/", label: "Accueil", d: "M3 11 12 4l9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1Z" },
  { href: "/calendrier", label: "Matchs", d: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4" },
  { href: "/classements", label: "Classement", d: "M4 20V10M10 20V4M16 20v-7M22 20H2" },
  { href: "/billetterie", label: "Billets", d: "M3 8a2 2 0 0 0 0 4v4h18v-4a2 2 0 0 1 0-4V4H3Zm11-4v12" },
  { href: "/votes", label: "Votes", d: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9Z" },
];

export function BottomTabs() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Onglets"
      className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden print:hidden"
    >
      <ul className="grid grid-cols-5">
        {TABS.map((t) => {
          const on = isActive(pathname, t.href) || (t.href === "/calendrier" && pathname.startsWith("/resultats"));
          return (
            <li key={t.href}>
              <Link
                href={t.href}
                aria-current={on ? "page" : undefined}
                className={`flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium ${on ? "text-lds-green dark:text-green-300" : "text-subtle"}`}
              >
                <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={on ? 2.4 : 1.8} strokeLinejoin="round" strokeLinecap="round" aria-hidden>
                  <path d={t.d} />
                </svg>
                {t.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
