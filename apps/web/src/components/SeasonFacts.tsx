// Libellés tirés de la saison courante (nom, nombre d'équipes et de régions, villes des poules)
// plutôt qu'écrits en dur : ils suivent automatiquement le changement de saison.
import { Suspense } from "react";
import { apiGet } from "@/lib/server-api";
import type { PublicTeam, Season } from "@/lib/types";

async function Name() {
  const season = await apiGet<Season>("/seasons/current");
  return <>{season.name}</>;
}

/** Nom de la saison courante (« Saison 2026-2027 »), avec « Saison » le temps du chargement. */
export function SeasonName() {
  return (
    <Suspense fallback="Saison">
      <Name />
    </Suspense>
  );
}

export function leagueFacts(teams: PublicTeam[], season?: Season): string {
  const regions = new Set(teams.map((t) => t.region.id)).size;
  const base = `${teams.length} équipes issues des ${regions} régions`;
  if (!season?.pools.length) return base;
  const pools = season.pools.map((p) => `poule ${p.code} à ${p.host_city}`).join(", ");
  return `${base}, ${season.pools.length} poules : ${pools}.`;
}

async function Facts({ withPools }: { withPools: boolean }) {
  const [teams, season] = await Promise.all([apiGet<PublicTeam[]>("/teams"), apiGet<Season>("/seasons/current")]);
  return <>{leagueFacts(teams, withPools ? season : undefined)}</>;
}

/** « 20 équipes issues des 17 régions… » calculé à partir des équipes engagées. */
export function LeagueFacts({ withPools = false }: { withPools?: boolean }) {
  return (
    <Suspense fallback="Équipes des régions du Burkina Faso">
      <Facts withPools={withPools} />
    </Suspense>
  );
}
