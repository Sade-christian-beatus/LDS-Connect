import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthProvider } from "@/lib/auth";
import { AppHeader } from "./app-header";

export const metadata: Metadata = { title: "Espace officiels", robots: { index: false } };

function HeaderShell() {
  return (
    <header className="sticky top-0 z-10 bg-lds-green text-white shadow">
      <div className="mx-auto max-w-6xl px-3 py-2 text-sm font-bold">LDS · Officiels</div>
    </header>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      {/* L'en-tête lit l'URL (menu actif) : rendu côté navigateur, coquille statique en attendant */}
      <Suspense fallback={<HeaderShell />}>
        <AppHeader />
      </Suspense>
      <main className="mx-auto max-w-6xl px-3 py-4">{children}</main>
    </AuthProvider>
  );
}
