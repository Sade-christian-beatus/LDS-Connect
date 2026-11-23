"use client";
// Identité visuelle : logo de la Ligue et état des logos des 20 équipes.
import Link from "next/link";
import { useState } from "react";
import { LogoUploader } from "@/components/admin/LogoUploader";
import { Badge, Notice } from "@/components/admin/ui";
import { BrandLogo } from "@/components/BrandLogo";
import { RequireAuth } from "@/components/RequireAuth";
import { TeamBadge } from "@/components/TeamBadge";
import { useAuth } from "@/lib/auth";
import type { PublicTeam } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function IdentitePage() {
  return (
    <RequireAuth permission="brand:manage">
      <Identite />
    </RequireAuth>
  );
}

function Identite() {
  const { raw } = useAuth();
  const { data: brand, reload } = useApi<{ logo_url: string | null }>("/brand");
  const { data: teams } = useApi<PublicTeam[]>("/teams");
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const withLogo = teams?.filter((t) => t.logo_url).length ?? 0;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-pitch">Identité visuelle</h1>
        <p className="text-sm text-stone-600">
          Les logos sont conservés dans le stockage de la plateforme (jamais dans le code source) et affichés sur le site, les
          billets, les cartes et les documents imprimés.
        </p>
      </div>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      <section className="grid gap-5 rounded-xl border border-stone-200 bg-white p-5 lg:grid-cols-[1fr_1fr]">
        <div className="space-y-3">
          <h2 className="font-semibold">Logo de la Ligue</h2>
          <LogoUploader
            label="Logo de la Ligue"
            currentUrl={brand?.logo_url}
            upload={(body) => raw("/admin/brand/logo", { method: "PUT", body })}
            remove={() => raw("/admin/brand/logo", { method: "DELETE" })}
            onDone={(text) => {
              setNotice({ tone: "ok", text: `${text} : il apparaîtra partout au prochain chargement des pages.` });
              localStorage.removeItem("lds-brand-logo");
              reload();
            }}
            onError={(text) => setNotice({ tone: "error", text })}
          />
          <p className="text-xs text-stone-500">
            À n&apos;utiliser qu&apos;avec le fichier officiel fourni par la Ligue. Sans logo, une marque provisoire aux couleurs du
            Burkina Faso est affichée.
          </p>
        </div>
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Aperçu</p>
          <div className="flex items-center gap-3 rounded-xl bg-pitch p-3 text-white">
            <BrandLogo logoUrl={brand?.logo_url} />
            <span className="leading-tight">
              <span className="block text-[11px] font-semibold uppercase tracking-[0.2em] text-lds-gold">LDS Connect</span>
              <span className="block font-black">Ligue de la Souveraineté</span>
            </span>
          </div>
          <div className="flex items-center gap-3 rounded-xl border border-stone-200 p-3">
            <BrandLogo logoUrl={brand?.logo_url} size="lg" className="shadow-none" />
            <span className="text-sm text-stone-600">Procès-verbaux, cartes de licence et d&apos;accréditation, billets</span>
          </div>
        </div>
      </section>

      <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="font-semibold">Logos des équipes</h2>
          <span className="text-sm text-stone-600">
            {withLogo}/{teams?.length ?? 20} logo(s) envoyé(s)
          </span>
        </div>
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {teams?.map((t) => (
            <li key={t.id}>
              <Link href={`/admin/equipes/${t.id}`} className="flex items-center gap-3 rounded-lg border border-stone-200 p-2.5 hover:border-lds-green">
                <TeamBadge team={t} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold">{t.name}</span>
                  {t.logo_url ? <Badge tone="green">Logo officiel</Badge> : <Badge tone="stone">Blason provisoire</Badge>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="text-xs text-stone-500">Ouvrez une équipe pour envoyer ou remplacer son logo (rubrique « Logo de l&apos;équipe »).</p>
      </section>
    </div>
  );
}
