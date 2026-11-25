// Emblème d'une équipe : le logo envoyé par la Ligue s'il existe, sinon un blason dessiné
// aux couleurs et initiales du club (ce n'est pas un logo officiel).
import { initials } from "@/lib/format";

type Props = {
  team: { name: string; primary_color: string; secondary_color: string; logo_url?: string | null };
  size?: "sm" | "md" | "lg" | "xl" | "card" | "hero" | "wall";
};

// « card » et « hero » s'adaptent à l'écran : plus petits sur téléphone, où la place manque
const SIZES = {
  sm: "h-7 w-7",
  md: "h-10 w-10",
  lg: "h-16 w-16",
  xl: "h-24 w-24",
  card: "h-8 w-8 sm:h-10 sm:w-10",
  hero: "h-16 w-16 sm:h-24 sm:w-24",
  wall: "h-11 w-11 sm:h-16 sm:w-16",
};
// Coins arrondis proportionnés : un écusson garde sa forme, sans être rogné par un cercle
const TILE = { sm: "rounded-md p-[2px]", md: "rounded-lg p-[3px]", lg: "rounded-xl p-1", xl: "rounded-2xl p-1.5", card: "rounded-lg p-[3px]", hero: "rounded-2xl p-1 sm:p-1.5", wall: "rounded-xl p-[3px] sm:p-1" };

/** Couleur lisible sur le fond donné (texte clair ou foncé). */
function readable(hex: string, fallback: string) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) return fallback;
  const n = parseInt(m[1], 16);
  const lum = (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
  return lum > 0.6 ? "#1c1917" : "#ffffff";
}

export function TeamBadge({ team, size = "md" }: Props) {
  if (team.logo_url) {
    return (
      <span aria-hidden className={`inline-flex shrink-0 items-center justify-center overflow-hidden bg-white shadow-sm ring-1 ring-black/10 ${TILE[size]} ${SIZES[size]}`}>
        {/* eslint-disable-next-line @next/next/no-img-element -- logo servi par l'API, taille fixe */}
        <img src={team.logo_url} alt="" className="h-full w-full object-contain" loading="lazy" />
      </span>
    );
  }
  const ink = readable(team.primary_color, team.secondary_color);
  const band = team.secondary_color.toLowerCase() === team.primary_color.toLowerCase() ? ink : team.secondary_color;
  return (
    <svg aria-hidden viewBox="0 0 40 46" className={`shrink-0 drop-shadow-sm ${SIZES[size]}`}>
      <path d="M20 1 38 6v15c0 11-7.6 19.6-18 24C9.6 40.6 2 32 2 21V6Z" fill={team.primary_color} stroke="#ffffff" strokeWidth="2" />
      <path d="M2.9 12h34.2v5H2.9Z" fill={band} opacity="0.9" />
      <path d="m20 4.6 1 2.1 2.3.3-1.7 1.6.4 2.3L20 9.8l-2 1.1.4-2.3-1.7-1.6 2.3-.3Z" fill={band} />
      <text
        x="20"
        y="33"
        textAnchor="middle"
        fontFamily="system-ui, sans-serif"
        fontSize="12.5"
        fontWeight="800"
        fill={ink}
        letterSpacing="0.5"
      >
        {initials(team.name)}
      </text>
    </svg>
  );
}
