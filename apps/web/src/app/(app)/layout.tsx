import type { Metadata } from "next";
import { Suspense } from "react";
import { SkipLink } from "@/components/SkipLink";
import { AuthProvider } from "@/lib/auth";
import { AppHeader } from "./app-header";

export const metadata: Metadata = { title: "Espace officiels", robots: { index: false } };

function HeaderShell() {
  return (
    <header className="sticky top-0 z-30 bg-pitch text-white shadow print:hidden">
      <div aria-hidden className="flex h-1">
        <span className="flex-1 bg-lds-red" />
        <span className="flex-1 bg-lds-gold" />
        <span className="flex-1 bg-lds-green" />
      </div>
      <div className="px-4 py-2.5 text-sm font-black">LDS · Officiels</div>
    </header>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <SkipLink />
      {/* L'en-tête lit l'URL (menu actif) : rendu côté navigateur, coquille statique en attendant */}
      <Suspense fallback={<HeaderShell />}>
        <AppHeader />
      </Suspense>
      {/* Menu latéral (grand écran, nombreux outils) : le contenu se décale d'autant */}
      <div className="app-main">
        <main id="contenu" tabIndex={-1} className="mx-auto max-w-6xl px-4 py-5">{children}</main>
      </div>
    </AuthProvider>
  );
}
