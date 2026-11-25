import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { LeagueFacts, SeasonName } from "@/components/SeasonFacts";
import { TeamBadge } from "@/components/TeamBadge";
import { apiGet } from "@/lib/server-api";
import type { PublicTeam, Season } from "@/lib/types";

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
  const [teams, season] = await Promise.all([apiGet<PublicTeam[]>("/teams"), apiGet<Season>("/seasons/current")]);
  return (
    <>
      {season.pools.map((pool) => (
        <section key={pool.code} className="space-y-3">
          <h2 className="flex items-center gap-2 text-xl font-black tracking-tight text-heading">
            <span className="rounded-lg bg-pitch px-2.5 py-0.5 text-lds-gold">{pool.code}</span>
            {pool.name} · {pool.host_city}
          </h2>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {teams
              .filter((t) => t.pool_code === pool.code)
              .map((t) => (
                <li key={t.id}>
                  <Link
                    href={`/equipes/${t.slug}`}
                    className="group flex h-full flex-col items-center overflow-hidden rounded-2xl border border-line bg-surface text-center shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                  >
                    {/* Bandeau aux couleurs du club, blason en grand par-dessus */}
                    <span
                      aria-hidden
                      className="h-12 w-full"
                      style={{ background: `linear-gradient(120deg, ${t.primary_color}, ${t.secondary_color === "#ffffff" ? t.primary_color : t.secondary_color})` }}
                    />
                    <span className="-mt-9">
                      <TeamBadge team={t} size="xl" />
                    </span>
                    <span className="flex flex-1 flex-col justify-center px-3 pb-4 pt-2">
                      <span className="block font-bold leading-tight group-hover:underline">{t.name}</span>
                      <span className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-subtle">{t.region.name}</span>
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
