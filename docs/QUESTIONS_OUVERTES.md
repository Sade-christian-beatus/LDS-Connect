# Questions ouvertes à trancher par la Ligue

Chaque point indique la **valeur provisoire** retenue dans le code. Les règles sportives sont
toutes modifiables dans `competition_rules` sans changer le code.

## Règlement sportif

| # | Question | Valeur provisoire |
|---|---|---|
| 1 | **Barème de points** (victoire / nul / défaite) | 3 / 1 / 0 |
| 2 | **Critères de départage** et leur ordre | points, confrontations directes (points, différence, buts marqués), différence générale, buts marqués, fair-play, tirage au sort |
| 3 | **Barème de fair-play** | jaune 1 pt, second jaune 3, rouge direct 3 |
| 4 | **Âge minimum** (16 ans) et **quota de moins de 19 ans** (7 par effectif) : règle de la Ligue ou seulement observée au Guiriko ? | appliqués (paramétrables) |
| 5 | **Date de référence** pour le calcul des âges | 1er janvier 2027 (début de saison) |
| 6 | **Règle des locaux** : 50 % des titulaires, arrondi au supérieur (6 sur 11) ? Le joueur remplacé en cours de match compte-t-il ? | 6 sur 11, appréciée sur les titulaires au coup d'envoi |
| 7 | **Justificatif de résidence** (6 mois) : quel document, qui l'atteste, qui le vérifie ? | un joueur ne compte comme local qu'une fois sa résidence **vérifiée par l'administration** (permission `residence:verify`) ; toute modification de la résidence par un club annule la vérification |
| 8 | **Feuille de match** : nombre de remplaçants inscrits, nombre de remplacements et de fenêtres | 9 remplaçants, 5 remplacements (fenêtres non contrôlées) |
| 9 | **Suspensions** : seuil de cumul de jaunes, durée après un rouge, remise à zéro des jaunes avant les phases finales | 3 jaunes = 1 match ; rouge = 1 match ; second jaune = 1 match ; remise à zéro après la phase de poules |
| 10 | **Procédure de réclamation** : délai, instance, conséquences sur une feuille validée | la feuille validée peut être clôturée par l'administration ; pas encore de procédure de correction après validation |
| 11 | **Phases finales** : croisement des quarts, match pour la 3e place, lieu des rencontres | A1–B4, B2–A3, B1–A4, A2–B3 ; match pour la 3e place joué (dotation) |
| 12 | **Prolongations** en phase finale avant les tirs au but ? | non gérées : tirs au but directement en cas d'égalité |

## Organisation

| # | Question | Valeur provisoire |
|---|---|---|
| 13 | **Qui saisit la feuille de match** : délégué, arbitre, club ? Qui la valide ? | le délégué saisit et valide ; l'administration clôture |
| 14 | **Stades** exacts à Ouagadougou et Bobo-Dioulasso, horaires types | « Stade de Ouagadougou / de Bobo-Dioulasso (à confirmer) » ; créneaux 15 h et 17 h 30 |
| 15 | **Calendrier** : date de la 1re journée, rythme des journées | démonstration : 1re journée le samedi 9 janvier 2027, une journée par semaine |
| 16 | **Football féminin** et autres disciplines après la phase pilote | modèle prêt (champ genre), non activé |

## Mineurs et données personnelles

| # | Question | Valeur provisoire |
|---|---|---|
| 17 | **Autorisation parentale** pour les 16-17 ans (contrat de travail et traitement des données) | champ « autorisation parentale » prévu, non bloquant |
| 18 | **Déclaration à la CIL** : qui la dépose, quand ? Responsable du traitement : Secrétariat exécutif ? | voir [DONNEES_PERSONNELLES.md](DONNEES_PERSONNELLES.md) |
| 19 | **Durées de conservation** (licences, feuilles, journaux, votes) | non appliquées automatiquement |
| 20 | **Photos des joueurs** : publication autorisée ? (mineurs) | non publiées |

## Prestataires et hébergement

| # | Question | Valeur provisoire |
|---|---|---|
| 21 | **Opérateurs SMS** (OTP des votes) | simulateur local ; interface `SmsProvider` prête |
| 22 | **Agrégateur de paiement** mobile money (billetterie, vote payant) ; **Faso Arzeka** (plateforme nationale de paiement de l'administration, DGTCP) envisagée | simulateur local ; interface `PaymentProvider` prête ; désactivé par défaut. Faso Arzeka : à confirmer avec la DGTCP (la Ligue peut-elle encaisser par ce canal ? documentation technique officielle, environnement de test, signature des notifications) ; aucun logo ni nom affiché sans accord |
| 23 | **Hébergement** : serveur au Burkina Faso exigé ? Hébergeur retenu ? | code portable (Docker) ; voir [DEPLOIEMENT.md](DEPLOIEMENT.md) |
| 24 | **Nom de domaine officiel** (ex. lds-connect.bf) | non défini |
| 25 | **Logos officiels et charte graphique** de la Ligue et des 20 équipes, accord d'utilisation | initiales + couleurs génériques |
| 26 | **Comptes réseaux sociaux** : intégration souhaitée (liens, publications automatiques) ? | non intégrés |

## Phases 2 et 3 (à préciser avant développement)

- Votes (livrés, à paramétrer) : liste officielle des trophées et calendrier des scrutins ;
  **opérateur SMS** (indispensable en production) et coût par code envoyé ; ouverture à la
  diaspora (indicatifs autorisés) ; seuils de détection des votes en masse (actuellement :
  plus de 10 votes d'une même connexion en 10 min, 5 numéros qui se suivent) ; durée de
  conservation des numéros chiffrés ; vote payant (prix, reversement) avec la billetterie ;
  signataires du procès-verbal.
- Billetterie (livrée, à paramétrer) : **agrégateur de paiement** et frais par transaction ;
  catégories, prix et quotas par stade ; fermeture des ventes (au coup d'envoi par défaut) ;
  remboursements (hors plateforme aujourd'hui) ; forfaits supporters (transport,
  hébergement) ; zones et catégories d'accréditations ; nombre de portes et d'appareils de
  contrôle par stade.
- Talents (livrés, à paramétrer) : indicateurs supplémentaires attendus par la cellule
  technique ; étiquettes de suivi ; durée de conservation des notes d'observation ; accès
  éventuel des sélections nationales ou de recruteurs (aujourd'hui : aucun accès externe).
