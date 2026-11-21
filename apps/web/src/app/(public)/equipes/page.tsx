import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { TeamBadge } from "@/components/TeamBadge";
import { apiGet } from "@/lib/server-api";
import type { PublicTeam } from "@/lib/types";

export const metadata: Metadata = { title: "Équipes" };

export default function EquipesPage() {
  return (
    <>
      <h1 className="text-2xl font-bold text-green-900">Les 20 équipes</h1>
      <Suspense fallback={<p className="text-stone-500">Chargement des équipes…</p>}>
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
        <section key={pool} className="space-y-2">
          <h2 className="font-bold text-green-900">
            Poule {pool} · {pool === "A" ? "Ouagadougou" : "Bobo-Dioulasso"}
          </h2>
          <ul className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
            {teams
              .filter((t) => t.pool_code === pool)
              .map((t) => (
                <li key={t.id}>
                  <Link
                    href={`/equipes/${t.slug}`}
                    className="flex items-center gap-3 rounded-lg border border-stone-200 bg-white p-3 hover:border-lds-green"
                  >
                    <TeamBadge team={t} />
                    <span>
                      <span className="block font-semibold leading-tight">{t.name}</span>
                      <span className="text-xs uppercase text-stone-500">{t.region.name}</span>
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
