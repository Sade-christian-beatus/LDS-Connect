// Lien d'évitement : premier élément atteint au clavier ou au lecteur d'écran, il mène
// directement au contenu de la page sans repasser par l'en-tête et le menu.
export function SkipLink() {
  return (
    <a
      href="#contenu"
      className="sr-only z-50 rounded-lg bg-lds-gold px-4 py-2 font-bold text-pitch focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
    >
      Aller au contenu
    </a>
  );
}
