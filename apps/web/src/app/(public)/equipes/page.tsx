import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { LeagueFacts, SeasonName } from "@/components/SeasonFacts";
import { TeamBadge } from "@/components/TeamBadge";
import { apiGet } from "@/lib/server-api";
import type { PublicTeam } from "@/lib/types";

export const metadata: Metadata = { title: "Équipes" };

export default function EquipesPage() {
  return (
    <>
      <PageHeader kicker={<SeasonName />} title="Les équipes">
        <LeagueFacts />.
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement des équipes…</p>}>
        <Teams />
      </Suspense>
    </>
  );
}

async function Teams() {
  const teams = await apiGet<PublicTeam[]>("/teams");
  return (
    <>
      {(["A", "B"] as const).map((pool) => (
        <section key={pool} className="space-y-3">
          <h2 className="flex items-center gap-2 text-xl font-black tracking-tight text-heading">
            <span className="rounded-lg bg-pitch px-2.5 py-0.5 text-lds-gold">{pool}</span>
            Poule {pool} · {pool === "A" ? "Ouagadougou" : "Bobo-Dioulasso"}
          </h2>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {teams
              .filter((t) => t.pool_code === pool)
              .map((t) => (
                <li key={t.id}>
                  <Link
                    href={`/equipes/${t.slug}`}
                    className="group relative flex items-center gap-3 overflow-hidden rounded-2xl border border-line bg-surface p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <span aria-hidden className="absolute inset-y-0 left-0 w-1.5" style={{ backgroundColor: t.primary_color }} />
                    <TeamBadge team={t} size="lg" />
                    <span className="min-w-0">
                      <span className="block font-bold leading-tight group-hover:underline">{t.name}</span>
                      <span className="text-xs font-semibold uppercase tracking-wide text-subtle">{t.region.name}</span>
                    </span>
                  </Link>
                </li>
              ))}
          </ul>
        </section>
      ))}
    </>
  );
}
