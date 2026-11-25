import Link from "next/link";

/** En-tête des pages du site public : petit surtitre, grand titre, accroche. */
export function PageHeader({ kicker, title, children }: { kicker?: React.ReactNode; title: string; children?: React.ReactNode }) {
  return (
    <header className="space-y-1">
      {kicker && <p className="text-xs font-bold uppercase tracking-[0.2em] text-lds-red">{kicker}</p>}
      <h1 className="text-3xl font-black tracking-tight text-heading sm:text-4xl">{title}</h1>
      {children && <div className="max-w-3xl text-muted">{children}</div>}
    </header>
  );
}

/** Onglets en pastilles (liens), défilables sur téléphone. */
export function Pills({
  items,
  label,
}: {
  items: { href: string; label: string; active: boolean }[];
  label: string;
}) {
  return (
    <nav aria-label={label} className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4">
      {items.map((t) => (
        <Link
          key={t.href}
          href={t.href}
          aria-current={t.active ? "page" : undefined}
          className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition ${
            t.active ? "bg-pitch text-white shadow dark:bg-lds-green" : "bg-surface text-heading ring-1 ring-line hover:ring-lds-green"
          }`}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
