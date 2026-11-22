// Formatage en français (heure du Burkina Faso = UTC, sans changement d'heure).
const TZ = "Africa/Ouagadougou";

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Date à définir";
  const text = new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: TZ,
  }).format(new Date(iso));
  return text.charAt(0).toUpperCase() + text.slice(1); // « Samedi 16 janvier »
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "--:--";
  return new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: TZ,
  }).format(new Date(iso));
}

export function initials(name: string): string {
  const words = name.replace(/[^\p{L}\s]/gu, " ").split(/\s+/).filter(Boolean);
  const skip = new Set(["du", "de", "des", "la", "le", "les"]);
  const meaningful = words.filter((w) => !skip.has(w.toLowerCase()));
  return (meaningful.length >= 2 ? meaningful[0][0] + meaningful[1][0] : (meaningful[0] ?? "?").slice(0, 2))
    .toUpperCase();
}

export const PHASE_LABEL: Record<string, string> = {
  group: "Phase de poules",
  quarter_final: "Quart de finale",
  semi_final: "Demi-finale",
  third_place: "Match pour la 3e place",
  final: "Finale",
};

export const POSITION_LABEL: Record<string, string> = {
  GK: "Gardien",
  DF: "Défenseur",
  MF: "Milieu",
  FW: "Attaquant",
};

export const STAFF_LABEL: Record<string, string> = {
  head_coach: "Entraîneur principal",
  assistant_coach: "Entraîneur adjoint",
  goalkeeper_coach: "Entraîneur des gardiens",
  fitness_coach: "Préparateur physique",
  doctor: "Médecin",
  physio: "Kinésithérapeute",
  team_manager: "Team manager",
  kit_manager: "Intendant",
  other: "Encadreur",
};

export const EVENT_LABEL: Record<string, string> = {
  goal: "But",
  penalty_goal: "But sur penalty",
  own_goal: "But contre son camp",
  penalty_missed: "Penalty manqué",
  yellow_card: "Carton jaune",
  second_yellow: "Second jaune (exclusion)",
  red_card: "Carton rouge",
  substitution: "Remplacement",
};

export const SHEET_STATUS_LABEL: Record<string, string> = {
  draft: "Brouillon",
  submitted: "Soumise — match en cours",
  validated: "Validée",
  closed: "Clôturée",
};

export const ROLE_LABEL: Record<string, string> = {
  super_admin: "Super administrateur",
  admin_competition: "Administration de la compétition",
  gestionnaire_club: "Gestionnaire de club",
  delegue_match: "Délégué de match",
  cellule_technique: "Cellule technique",
  controleur_acces: "Contrôleur d'accès",
};

export const BALLOT_KIND_LABEL: Record<string, string> = {
  man_of_the_match: "Homme du match",
  goal_of_the_month: "But du mois",
  player_of_the_season: "Joueur de la saison",
  coach_of_the_season: "Entraîneur de la saison",
  team_of_the_season: "Onze idéal",
  special: "Trophée spécial",
};

export const BALLOT_STATE: Record<string, { label: string; tone: "green" | "amber" | "stone" | "blue" }> = {
  draft: { label: "Brouillon", tone: "stone" },
  upcoming: { label: "À venir", tone: "blue" },
  open: { label: "Vote ouvert", tone: "green" },
  closed: { label: "Clos", tone: "amber" },
};

/** Pastille d'un scrutin côté administration (la publication confirmée prime sur l'état). */
export function ballotBadge(b: { state: string; status: string }) {
  return b.status === "published" ? { label: "Résultats publiés", tone: "green" as const } : BALLOT_STATE[b.state];
}

/** Saisie « datetime-local » ↔ ISO : Ouagadougou est en UTC toute l'année. */
export const toLocalInput = (iso: string | null | undefined) => (iso ? iso.slice(0, 16) : "");
export const fromLocalInput = (v: string) => (v ? `${v}:00Z` : null);

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short", timeZone: TZ }).format(new Date(iso));
}
