// Proposition automatique d'une composition conforme (aide à la saisie, toujours modifiable) :
// un gardien, puis les joueurs locaux en priorité pour respecter la règle des locaux,
// avec une répartition indicative 4 défenseurs / 4 milieux / 2 attaquants.
import type { Candidate, LineupEntryIn } from "@/lib/types";

const SHAPE: Record<string, number> = { DF: 4, MF: 4, FW: 2 };

export function suggestLineup(
  candidates: Candidate[],
  startersCount: number,
  maxSubs: number,
  localsRequired: number,
): LineupEntryIn[] {
  const eligible = candidates.filter((c) => c.licence_ok && !c.is_suspended && c.shirt_number != null);
  const byLocal = (a: Candidate, b: Candidate) =>
    Number(b.is_local) - Number(a.is_local) || (a.shirt_number ?? 99) - (b.shirt_number ?? 99);

  const gk = eligible.filter((c) => c.position === "GK").sort(byLocal)[0];
  const field = eligible.filter((c) => c !== gk && c.position !== "GK").sort(byLocal);
  const starters: Candidate[] = gk ? [gk] : [];

  // 1) Locaux d'abord, en respectant la forme quand c'est possible
  const count: Record<string, number> = { DF: 0, MF: 0, FW: 0 };
  for (const c of field) {
    if (starters.length >= startersCount) break;
    const locals = starters.filter((s) => s.is_local).length;
    if (!c.is_local && locals < localsRequired) continue;
    if ((count[c.position] ?? 0) >= (SHAPE[c.position] ?? 0)) continue;
    starters.push(c);
    count[c.position] = (count[c.position] ?? 0) + 1;
  }
  // 2) Compléter si nécessaire
  for (const c of field) {
    if (starters.length >= startersCount) break;
    if (!starters.includes(c)) starters.push(c);
  }
  const bench = eligible.filter((c) => !starters.includes(c)).slice(0, maxSubs);
  const captain = starters.find((c) => c.position !== "GK") ?? starters[0];

  return [
    ...starters.map((c) => ({
      person_id: c.person_id,
      role: "starter" as const,
      shirt_number: c.shirt_number,
      is_goalkeeper: c === gk,
      is_captain: c === captain,
    })),
    ...bench.map((c) => ({
      person_id: c.person_id,
      role: "substitute" as const,
      shirt_number: c.shirt_number,
      is_goalkeeper: false,
      is_captain: false,
    })),
  ];
}
