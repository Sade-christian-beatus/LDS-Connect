# Audit général de LDS Connect

> Audit du 23 novembre 2026, sur la branche `claude/identite` (tout `main` + l'identité visuelle).
> Chaque constat a été vérifié dans le code ou en exécutant la plateforme. Gravité :
> **Critique** (à corriger avant toute mise en service), **Haute** (avant l'ouverture au
> public), **Moyenne** (dans les premières semaines), **Basse** (amélioration).

## État des corrections

| # | Point | État |
|---|---|---|
| C1 | IP des visiteurs derrière le proxy | **Corrigé** : `X-Forwarded-For` lu seulement depuis `TRUSTED_PROXIES` (dernière adresse non fiable retenue), tests unitaires |
| H1 | Pages légales | **Corrigé** (contenu à valider) : mentions légales, confidentialité, CGV, liens en pied de page, case d'acceptation à l'achat |
| H2 | En-têtes de sécurité | **Corrigé** : CSP, `X-Frame-Options`, `Permissions-Policy` envoyés par le site en production ; Caddy et Nginx documentés |
| H3 | Notifications de paiement | **Corrigé** : signature HMAC-SHA256 du corps brut vérifiée (`PAYMENT_WEBHOOK_SECRET`), 401 sinon |
| H4 | Garde-fous de production | **Corrigé** : l'API refuse de démarrer avec une configuration de développement ; SMS `console` muet en production |
| H5 | Licence sans photo | **Corrigé** : photo privée (autorisation parentale exigée pour un mineur), sur la carte et à l'écran du contrôleur |
| M1 à M11, B1 à B8 | — | à traiter |

## Synthèse

| Domaine | État |
|---|---|
| Tests | 208 tests API + 7 parcours de bout en bout, CI verte sur `main` |
| Dépendances | aucune vulnérabilité connue (`pnpm audit --prod`, `pip-audit` sur les versions figées) |
| Sécurité applicative | solide (JWT court + cookie httpOnly, argon2id, chiffrement AES-GCM des données sensibles, journal append-only, QR signés Ed25519) ; **un défaut critique de configuration derrière le proxy** |
| Données personnelles | règles mineurs respectées sur toutes les pages publiques ; **pages légales absentes** |
| Fonctionnel | phases 1 à 3 livrées ; quelques écrans d'administration manquent (règles, saisons, stades) |
| Exploitation | sauvegarde de la base automatisée, **pas celle des fichiers** |

## 1. Critique

### C1. Adresse IP des visiteurs perdue derrière le reverse proxy
- **Constat** : l'API lit `request.client.host`. Uvicorn est lancé avec `--proxy-headers`, mais
  ne fait confiance à `X-Forwarded-For` que pour `127.0.0.1` (valeur par défaut de
  `FORWARDED_ALLOW_IPS`). Derrière Caddy, que ce soit dans Docker ou sur l'hôte via la
  redirection de port, la connexion vient d'une adresse du réseau Docker : **tous les visiteurs
  ont la même IP**.
- **Conséquences en production** :
  - votes : la limite « 30 codes par IP et par heure » devient globale (plus personne ne peut
    voter après 30 demandes) et la détection des votes en masse (≥ 10 votes depuis la même
    connexion en 10 min) **met de côté presque tous les votes** ;
  - billetterie : limite « 20 commandes par IP et par heure » globale ;
  - journal d'audit et empreintes d'IP sans valeur.
- **Correction retenue** : plutôt que `FORWARDED_ALLOW_IPS` d'Uvicorn, l'API lit elle-même
  `X-Forwarded-For` uniquement quand la connexion vient d'un réseau de `TRUSTED_PROXIES`
  (boucle locale et réseaux privés par défaut) et retient la dernière adresse non fiable de la
  chaîne, ce qui empêche un visiteur de choisir son adresse en ajoutant l'en-tête.

## 2. Haute

### H1. Pages légales absentes du site public
- Le site collecte des numéros de téléphone (votes, achats), vend des billets et publie des
  données de joueurs mineurs, mais n'a ni **mentions légales**, ni **politique de
  confidentialité**, ni **conditions générales de vente** (remboursement, report de match,
  billet perdu).
- `docs/DONNEES_PERSONNELLES.md` existe mais n'est pas publié aux personnes concernées (loi
  burkinabè n° 001-2021/AN sur la protection des données à caractère personnel, CIL).
- **Correction** : trois pages publiques (contenu à valider par la Ligue et son juriste),
  liens dans le pied de page, case « j'accepte les CGV » à l'achat.

### H2. En-têtes de sécurité incomplets (exemple Caddy)
- Présents : HSTS, `nosniff`, `Referrer-Policy`. Absents : **`Content-Security-Policy`**,
  **`X-Frame-Options` / `frame-ancestors`** (le back-office peut être affiché dans un cadre
  d'un autre site : risque de détournement de clic), `Permissions-Policy` (caméra limitée au
  contrôle d'accès).
- **Correction** : ajouter ces en-têtes dans `infra/caddy/Caddyfile.example` et
  `docs/DEPLOIEMENT.md`.

### H3. Notifications de paiement non authentifiées
- `POST /payments/notify` accepte toute notification de forme correcte : sans danger avec le
  simulateur (la référence de l'agrégateur doit correspondre), mais **le futur connecteur
  réel doit vérifier la signature** de l'agrégateur (ou Faso Arzeka) et, si possible,
  re-vérifier le statut auprès de son API. Documenté dans le code et le guide de déploiement :
  à rendre bloquant (refus de démarrer en production avec `PAYMENT_PROVIDER=simulator`).

### H4. Garde-fous de démarrage en production
- `JWT_SECRET` trop court est refusé en production (bien), mais rien n'empêche de démarrer
  avec `REFRESH_COOKIE_SECURE=false`, `PAYMENT_PROVIDER=simulator`, `SMS_PROVIDER=console`
  ou une liste CORS de développement.
- **Correction** : contrôle au démarrage qui refuse ces combinaisons quand
  `ENVIRONMENT=production`.

### H5. Licence sans photo
- Le modèle prévoit `photo_path` mais aucune photo n'est envoyée ni affichée : au stade, le
  contrôleur compare le nom de la licence à une pièce d'identité, sans photo sur la carte.
- **Correction** : envoi de photo (club ou administration, consentement parental pour les
  mineurs), photo sur la carte imprimée et sur l'écran de contrôle (jamais publique).

## 3. Moyenne

| # | Constat | Correction proposée |
|---|---|---|
| M1 | **Règles de compétition non modifiables** : la permission `rules:manage` existe mais aucun écran ni route ne permet de modifier `competition_rules` (barème, durée du match, seuils de cartons, quotas…) ; seul l'accès direct à la base le permet | Écran « Règles de la saison » avec journal d'audit, verrouillé une fois la saison commencée pour les règles qui changent les classements |
| M2 | **Pas de gestion des saisons** : tout repose sur « la saison courante » créée par le seed ; rien pour préparer la saison 2028 ni archiver 2027 | Création d'une saison (copie des règles et des équipes), bascule de la saison courante |
| M3 | **Stades non modifiables** : création possible (`POST /admin/venues`), mais pas de modification ; les stades « à confirmer » ne peuvent pas être confirmés | Route et écran de modification |
| M4 | **Sauvegarde incomplète** : `make backup` sauvegarde la base ; les fichiers (logos, exports) du volume `storage` sont à sauvegarder à la main | Ajouter l'archive du volume au script et au guide de restauration |
| M5 | **Aucune purge automatique** des données à durée limitée (défis SMS, numéros chiffrés des votants, commandes expirées), alors que `DONNEES_PERSONNELLES.md` prévoit des durées | Tâche planifiée `purge` une fois les durées fixées par la Ligue |
| M6 | **Logos indisponibles hors connexion** : le service worker traite tout `/api/*` en « réseau seul », y compris les images `/api/v1/media/…` ; un billet ouvert sans réseau affiche le QR mais pas le logo | Cache « d'abord le cache » pour `/api/v1/media/` (fichiers versionnés, immuables) |
| M7 | **Exemple Caddy incohérent avec le guide** : le Caddyfile vise `api:8000` / `web:3000` (noms de services Docker) alors qu'aucun service Caddy n'est dans `docker-compose.yml` et que le guide décrit un proxy sur l'hôte vers `127.0.0.1` | Ajouter un service `caddy` au compose de production, ou cibler `127.0.0.1:8000/3000` |
| M8 | **« Meilleur buteur » trompeur en cas d'égalité** : la page Statistiques met en vedette un seul joueur alors que cinq sont à égalité (2 buts) | Afficher « Meilleurs buteurs » et les ex aequo quand le rang 1 est partagé |
| M9 | **Pas de double authentification** pour les comptes à privilèges (super administrateur, administration) ; réinitialisation du mot de passe uniquement par un administrateur | TOTP optionnel puis obligatoire pour les rôles d'administration |
| M10 | **Zones des accréditations non contrôlées** : les zones sont affichées au contrôleur mais l'entrée n'est pas liée à une porte/zone | Associer chaque appareil de contrôle à une zone et refuser hors zone |
| M11 | Requêtes en boucle : la liste des commandes d'un match fait une requête par commande pour les codes des billets (500 commandes = 500 requêtes) ; le tableau de bord des talents charge tous les joueurs en mémoire (600, acceptable) | Jointure groupée pour les billets |

## 4. Basse (cohérence et finition)

| # | Constat |
|---|---|
| B1 | Libellés codés en dur : « Saison 2027 » (calendrier, résultats, classements, statistiques, fiche joueur), « 20 équipes des 17 régions » (accueil, pied de page) ; à lire depuis la saison courante |
| B2 | `README.md` : la section s'intitule encore « Ce qui est disponible (phase 1) » alors que les phases 2 et 3 sont livrées |
| B3 | Documentation de l'API (`/api/v1/docs`) publique en production : à réserver au réseau interne ou désactiver |
| B4 | Écran « Contrôle des entrées » : l'état « En ligne » apparaît deux fois (en-tête et page) |
| B5 | Super administrateur : 13 entrées de menu ; regrouper « Licences » et « Entrées » sous « Au stade » est fait, mais l'écran d'accueil pourrait devenir un tableau de bord (matchs du jour, ventes, votes ouverts) |
| B6 | Avertissement Starlette (« httpx avec TestClient déprécié ») dans les tests ; `next start` signale l'usage de `output: standalone` en local (normal en production avec `node server.js`) |
| B7 | Billets annulés : remboursement hors plateforme, sans suivi (statut `refunded` jamais utilisé) |
| B8 | Les statuts « expirée » des commandes sont calculés à la lecture : la base garde `pending` (filtrage correct, mais à savoir pour les exports directs) |

## 5. Points forts constatés

- Règles sportives entièrement paramétrées (`competition_rules`), aucune valeur codée en dur
  dans les calculs (classement, suspensions, minutes jouées, règle des locaux).
- Données des mineurs : seuls nom d'usage, poste, équipe et âge sont publics (vérifié par des
  tests), CNIB et téléphones chiffrés, accès journalisés, notes d'observation chiffrées.
- Hors connexion réel : feuille de match, contrôle des licences et des entrées, billets.
- Traçabilité : journal d'audit en ajout seul (déclencheur PostgreSQL) sur licences, feuilles,
  résultats, votes, billetterie, talents.
- Portabilité : Docker Compose, PostgreSQL, Redis, stockage disque ou S3, aucune dépendance à
  un service externe réel en développement.

## 6. Plan de correction proposé

1. **Avant la mise en service** : C1, H2, H4 (une journée de travail).
2. **Avant l'ouverture au public** : H1 (contenu juridique à fournir), H3 (avec le connecteur
   de paiement retenu), H5, M4, M6, M8, B1, B2.
3. **Premières semaines** : M1, M2, M3, M5 (durées à fixer), M7, M9, M10, M11.
