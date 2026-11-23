import Link from "next/link";

const NAV = [
  { href: "/", label: "Accueil" },
  { href: "/calendrier", label: "Calendrier" },
  { href: "/resultats", label: "Résultats" },
  { href: "/classements", label: "Classements" },
  { href: "/statistiques", label: "Statistiques" },
  { href: "/billetterie", label: "Billetterie" },
  { href: "/votes", label: "Votes" },
  { href: "/equipes", label: "Équipes" },
];

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="bg-lds-green text-white">
        <div className="h-1 bg-lds-red" />
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <Link href="/" className="flex items-center gap-2 font-bold">
            <span className="rounded bg-white px-1.5 py-0.5 text-sm text-lds-green">LDS</span>
            <span>Ligue de la Souveraineté</span>
          </Link>
          <nav aria-label="Navigation principale" className="flex flex-wrap gap-1 text-sm">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} className="rounded px-2 py-1 hover:bg-white/15">
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl space-y-6 px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-5xl px-4 py-8 text-xs text-stone-500">
        <p>
          LDS Connect — plateforme de la Ligue de la Souveraineté. Données des joueurs limitées
          (nom d&apos;usage, poste, âge) : la compétition compte des joueurs mineurs.
        </p>
        <p className="mt-1">
          <Link href="/connexion" className="underline">
            Espace officiels
          </Link>
        </p>
      </footer>
    </>
  );
}
