# Accessibilité

Objectif : le site public est utilisable par les personnes aveugles et malvoyantes, avec les
lecteurs d'écran courants (TalkBack sur Android, VoiceOver sur iPhone, NVDA ou Narrateur sur
Windows). Référence : WCAG 2.1, niveau AA. La page publique `/accessibilite` présente
l'engagement aux visiteurs et le moyen de signaler une difficulté.

## Ce qui est en place

| Sujet | Où | Comportement |
|---|---|---|
| Lien d'évitement | `components/SkipLink.tsx` | « Aller au contenu », premier élément au clavier, mène à `main#contenu` |
| Focus | `app/globals.css` | contour doré bien visible au clavier ; animations réduites si l'appareil le demande |
| Contrastes | `app/globals.css` | texte secondaire à 4,7:1 au moins sur les fonds clairs |
| Scores | `lib/a11y.ts` (`scoreSpeech`) | « 1 à 0, en direct, 66e minute » ; l'affichage compact est masqué au lecteur |
| Buts en direct | `components/LiveScores.tsx` | annonce « But ! … » quand un score change, pas à chaque minute |
| Classements | `components/StandingsTable.tsx` | colonnes nommées en entier, forme dite en mots, place qualificative signalée |
| Phases finales | `components/BracketTree.tsx` | liste des matchs dans l'ordre de la compétition |
| Compte à rebours | `components/Countdown.tsx` | phrase à la minute près |
| Logos | `BrandLogo`, `TeamBadge` | décoratifs (`alt=""`) quand le nom est écrit à côté |
| Écouter la page | `components/ListenButton.tsx`, `lib/read-aloud.ts` | lecture à voix haute du contenu principal (voix de l'appareil) |

## « Écouter la page »

Bouton dans l'en-tête du site public. Il lit `main#contenu` avec la synthèse vocale du
navigateur (`speechSynthesis`) : aucune bibliothèque, aucun service extérieur, aucun son envoyé
par Internet. Pour les personnes malvoyantes et pour celles qui lisent difficilement le
français ; les personnes aveugles gardent leur lecteur d'écran, plus complet.

- Le texte lu est celui du lecteur d'écran : les éléments `aria-hidden` sont sautés, les textes
  `sr-only` sont lus (« 1 à 0, en direct, 66e minute »).
- Un tableau se lit ligne par ligne avec le nom des colonnes (« Rang 1, Équipe…, Points 6 »).
- Passages de 220 caractères au plus (certaines voix s'arrêtent sur les phrases longues).
- Pause, passage précédent ou suivant, vitesse (normale, lente, rapide, gardée sur l'appareil),
  arrêt ; la lecture s'arrête au changement de page.
- Un élément marqué `data-read-aloud-skip` n'est jamais lu.
- Test : `e2e/ecouter.spec.ts` (voix remplacée par un enregistreur).

## Règles pour les nouveaux écrans

- Une page = un `h1`, puis des titres sans saut de niveau.
- Une abréviation ou un symbole (« J », « Pts », « 66' », « ⚽ 2 ») : afficher la version courte
  en `aria-hidden` et ajouter le texte complet en `sr-only`.
- Une information portée par la couleur (forme, carton, zone qualificative) est aussi dite en mots.
- Une mise à jour en direct passe par une petite zone `role="status"` qui ne contient que
  l'annonce, jamais par une zone `aria-live` sur toute une liste.
- Tout champ a une étiquette visible ; toute erreur est dans un `role="alert"`.
- Une image porteuse d'information a un `alt` ; une image décorative a `alt=""`.

## Contrôle automatique

`e2e/accessibilite.spec.ts` passe axe-core (règles WCAG 2.1 A et AA) sur les pages publiques,
sur téléphone et sur ordinateur, et vérifie le lien d'évitement et les en-têtes du classement :

```bash
cd apps/web && pnpm e2e e2e/accessibilite.spec.ts
```

Un contrôle automatique ne trouve qu'une partie des problèmes : avant l'ouverture au public,
faire tester les parcours principaux (résultats, classement, achat de billet, vote) par des
personnes aveugles, avec leur téléphone.

## Limites connues

- L'espace officiels (feuille de match, contrôle des entrées) n'a pas été testé au lecteur d'écran.
- Sur téléphone, les colonnes buts pour, buts contre et forme du classement sont masquées.
