import Link from "next/link";
import { LEGAL_LINKS } from "@/components/LegalPage";
import { LeagueFacts } from "@/components/SeasonFacts";
import { Suspense } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { BottomTabs, TopNav } from "@/components/PublicNav";
import { ThemeToggle } from "@/components/ThemeToggle";
import { NAV } from "@/lib/public-nav";
import { apiGet } from "@/lib/server-api";
import { THEME_SCRIPT } from "@/lib/theme";

async function BrandSlot({ size = "md" }: { size?: "md" | "lg" }) {
  const brand = await apiGet<{ logo_url: string | null }>("/brand").catch(() => null);
  return <BrandLogo logoUrl={brand?.logo_url} size={size} />;
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3" aria-label="Ligue de la Souveraineté — accueil">
      <Suspense fallback={<BrandLogo />}>
        <BrandSlot />
      </Suspense>
      <span className="leading-tight">
        <span className="block text-[11px] font-semibold uppercase tracking-[0.2em] text-lds-gold">LDS Connect</span>
        <span className="block text-base font-black tracking-tight sm:text-lg">Ligue de la Souveraineté</span>
      </span>
    </Link>
  );
}

function StaticNav() {
  return (
    <nav aria-label="Navigation principale" className="flex gap-1 overflow-hidden text-sm">
      {NAV.map((n) => (
        <Link key={n.href} href={n.href} className="whitespace-nowrap rounded-full px-3 py-1.5 text-white/85">
          {n.label}
        </Link>
      ))}
    </nav>
  );
}

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-public min-h-screen bg-canvas text-ink">
      <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      <header className="sticky top-0 z-20 bg-pitch text-white shadow-lg print:hidden">
        <div aria-hidden className="flex h-1">
          <span className="flex-1 bg-lds-red" />
          <span className="flex-1 bg-lds-gold" />
          <span className="flex-1 bg-lds-green" />
        </div>
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex items-center justify-between gap-3 py-2.5">
            <Brand />
            <div className="flex items-center gap-1">
              <Link
                href="/billets"
                className="hidden rounded-full border border-white/25 px-3 py-1.5 text-sm font-semibold hover:bg-white/10 sm:block"
              >
                Mes billets
              </Link>
              <ThemeToggle />
            </div>
          </div>
          <div className="pb-2.5">
            <Suspense fallback={<StaticNav />}>
              <TopNav />
            </Suspense>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-6 pb-28 md:pb-10">{children}</main>

      <footer className="bg-pitch pb-24 text-green-100/80 md:pb-0 print:hidden">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-8 text-sm sm:grid-cols-3">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Suspense fallback={<BrandLogo size="lg" />}>
                <BrandSlot size="lg" />
              </Suspense>
              <p className="font-black text-white">Ligue de la Souveraineté</p>
            </div>
            <p className="text-xs leading-relaxed">
              <LeagueFacts /> du Burkina Faso. Données des joueurs limitées (nom d&apos;usage, poste, âge) : la compétition
              compte des joueurs mineurs.
            </p>
          </div>
          <ul className="grid grid-cols-2 gap-1">
            {NAV.map((n) => (
              <li key={n.href}>
                <Link href={n.href} className="hover:text-white hover:underline">
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="space-y-2 sm:text-right">
            <Link href="/billets" className="block hover:text-white hover:underline">
              Mes billets
            </Link>
            <Link href="/connexion" className="block hover:text-white hover:underline">
              Espace officiels
            </Link>
            <p className="text-xs">LDS Connect — plateforme de la Ligue de la Souveraineté.</p>
            <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs sm:justify-end">
              {LEGAL_LINKS.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="hover:text-white hover:underline">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div aria-hidden className="flex h-1">
          <span className="flex-1 bg-lds-red" />
          <span className="flex-1 bg-lds-gold" />
          <span className="flex-1 bg-lds-green" />
        </div>
      </footer>
      <Suspense>
        <BottomTabs />
      </Suspense>
    </div>
  );
}
