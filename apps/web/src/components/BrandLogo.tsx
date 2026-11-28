// Logo de la Ligue : celui envoyé par le Secrétariat exécutif (stockage de la plateforme,
// jamais dans le dépôt de code), sinon une marque provisoire aux couleurs du Burkina.

const SIZES = { sm: "h-9", md: "h-12", lg: "h-20", xl: "h-32" };

/** `alt=""` quand le nom de la Ligue est écrit juste à côté (en-tête, pied de page) : le lecteur
 * d'écran ne le lit alors qu'une fois. */
export function BrandLogo({
  logoUrl,
  size = "md",
  className = "",
  alt = "Ligue de la Souveraineté",
}: {
  logoUrl?: string | null;
  size?: keyof typeof SIZES;
  className?: string;
  alt?: string;
}) {
  if (logoUrl) {
    return (
      <span className={`inline-flex shrink-0 items-center justify-center rounded-xl bg-white p-1 shadow ${SIZES[size]} ${className}`}>
        {/* eslint-disable-next-line @next/next/no-img-element -- logo servi par l'API (fichier versionné, cache long) */}
        <img src={logoUrl} alt={alt} className="h-full w-auto object-contain" />
      </span>
    );
  }
  return (
    <span aria-hidden className={`relative inline-flex aspect-square shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white shadow ${SIZES[size]} ${className}`}>
      <span className="absolute inset-x-0 top-0 h-1/2 bg-lds-red" />
      <span className="absolute inset-x-0 bottom-0 h-1/2 bg-lds-green" />
      <span className="relative text-[1.4em] leading-none text-lds-gold drop-shadow">★</span>
    </span>
  );
}
