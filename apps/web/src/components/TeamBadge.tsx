// Emplacement générique (initiales + couleurs) : aucun logo officiel tant que la Ligue
// n'a pas fourni les fichiers et donné son accord.
import { initials } from "@/lib/format";

type Props = {
  team: { name: string; primary_color: string; secondary_color: string };
  size?: "sm" | "md" | "lg";
};

const SIZES = { sm: "h-7 w-7 text-[10px]", md: "h-10 w-10 text-xs", lg: "h-16 w-16 text-lg" };

export function TeamBadge({ team, size = "md" }: Props) {
  return (
    <span
      aria-hidden
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-bold ring-2 ring-white ${SIZES[size]}`}
      style={{ backgroundColor: team.primary_color, color: team.secondary_color }}
    >
      {initials(team.name)}
    </span>
  );
}
