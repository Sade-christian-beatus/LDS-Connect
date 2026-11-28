// Textes pour les lecteurs d'écran : ce que l'œil comprend d'un coup (« 1–0 66' », « V V N »),
// écrit en toutes lettres pour être lu à voix haute.
import type { Match } from "./types";

const minute = (n: number) => (n === 1 ? "1re minute" : `${n}e minute`);

/** Score d'un match, tel qu'il doit être lu : « 1 à 0, en direct, 66e minute ». */
export function scoreSpeech(m: Pick<Match, "status" | "home_score" | "away_score" | "home_penalties" | "away_penalties" | "live_minute">): string {
  const score = `${m.home_score ?? 0} à ${m.away_score ?? 0}`;
  if (m.status === "live") return `${score}, en direct, ${minute(m.live_minute ?? 0)}`;
  if (m.status === "finished") {
    const tab = m.home_penalties != null ? `, tirs au but ${m.home_penalties} à ${m.away_penalties}` : "";
    return `${score}, terminé${tab}`;
  }
  return "";
}

/** Annonce d'un but en direct : « But ! Équipe A 2, Équipe B 1, 67e minute. » */
export function goalSpeech(m: Match): string {
  const home = m.home?.name ?? "Équipe à domicile";
  const away = m.away?.name ?? "Équipe à l'extérieur";
  return `But ! ${home} ${m.home_score ?? 0}, ${away} ${m.away_score ?? 0}, ${minute(m.live_minute ?? 0)}.`;
}

const FORM: Record<string, string> = { V: "victoire", N: "nul", D: "défaite", W: "victoire", L: "défaite" };
/** Forme récente : « V N D » devient « victoire, nul, défaite ». */
export function formSpeech(results: string[]): string {
  return results.map((r) => FORM[r] ?? r).join(", ");
}
