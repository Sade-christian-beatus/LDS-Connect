# Tutoriels vidéo

Sept chapitres courts, un par public, et une version complète. Ce sont des parcours réels de la
plateforme, enregistrés automatiquement : un écran qui change se met à jour en relançant les
deux commandes ci-dessous.

| # | Chapitre | Public | Support |
|---|---|---|---|
| 1 | Suivre la compétition | Supporters | téléphone |
| 2 | Acheter un billet | Supporters | téléphone |
| 3 | Voter pour son joueur | Supporters | téléphone |
| 4 | Gérer son effectif | Clubs | ordinateur |
| 5 | La feuille de match | Délégués | téléphone |
| 6 | Le contrôle au stade | Contrôleurs d'accès | téléphone |
| 7 | Piloter la compétition | Administration de la Ligue | ordinateur |

Les vidéos (MP4 1920 × 1080) ne sont pas versionnées : elles se régénèrent. Le texte de la voix
off, minuté, est dans [`SCRIPT_VOIX_OFF.md`](SCRIPT_VOIX_OFF.md) ; il est prévu pour être lu par
une vraie voix puis mixé sur les vidéos (sous-titres déjà incrustés).

## Régénérer

Pile locale lancée avec les données de démonstration (`make up` ou équivalent sans Docker),
simulateurs SMS et paiement compris, site en build de production sur le port 3000 :

```bash
cd apps/web
node tutoriels/enregistrer.mjs ../../var/tutoriels/prises          # tous les chapitres
node tutoriels/enregistrer.mjs ../../var/tutoriels/prises 02-billet  # un seul chapitre
node tutoriels/monter.mjs ../../var/tutoriels/prises ../../var/tutoriels/videos
```

- `tutoriels/chapitres.mjs` : le parcours de chaque chapitre, ses sous-titres (courts, à
  l'écran) et le texte de la voix off. Le rythme suit la voix : chaque phrase dispose du temps
  nécessaire à sa lecture (environ 2,6 mots par seconde).
- `tutoriels/lib.mjs` : capture de l'écran en pleine définition, curseur (ordinateur) ou doigt
  (téléphone) visibles, saisie au clavier visible.
- `tutoriels/monter.mjs` : habillage aux couleurs de la Ligue, cadre de téléphone ou de
  navigateur, sous-titres en fondu, carton de titre, version complète, script de voix off.

Prérequis : `ffmpeg` installé sur la machine ; le chapitre 6 (contrôle) utilise le billet
acheté au chapitre 2, à enregistrer avant. Les données affichées sont celles de la
démonstration (fictives) ; la photo de licence est une silhouette dessinée.
