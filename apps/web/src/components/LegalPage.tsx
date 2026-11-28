// Gabarit des pages juridiques : bandeau « projet à valider » tant que la Ligue et son conseil
// n'ont pas arrêté le texte, puis sections numérotées.
import { PageHeader } from "./PageHeader";

export const LEGAL_LINKS = [
  { href: "/mentions-legales", label: "Mentions légales" },
  { href: "/confidentialite", label: "Confidentialité" },
  { href: "/conditions-de-vente", label: "Conditions de vente" },
  { href: "/accessibilite", label: "Accessibilité" },
];

export function LegalPage({ title, updated, children }: { title: string; updated: string; children: React.ReactNode }) {
  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <PageHeader kicker="Informations légales" title={title}>
        Dernière mise à jour : {updated}.
      </PageHeader>
      <p role="note" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
        <strong>Projet à valider par la Ligue et son conseil juridique.</strong> Les passages entre crochets sont à
        compléter avant l&apos;ouverture du site au public.
      </p>
      <div className="legal space-y-6 leading-relaxed text-ink [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-heading [&_li]:ml-5 [&_li]:list-disc [&_p]:mb-2 [&_ul]:space-y-1">
        {children}
      </div>
    </article>
  );
}
