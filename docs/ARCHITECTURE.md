# Architecture de LDS Connect

## Vue d'ensemble

```
            Navigateur / PWA (mobile)                       Reverse proxy (TLS)
   ┌───────────────────────────────────────┐         ┌──────────────────────────┐
   │ Site public  · Espace officiels       │  HTTPS  │ /api/*  →  api:8000      │
   │ IndexedDB (feuilles, file d'actions,  │ ──────► │ /*      →  web:3000      │
   │ clés de licences) · Service worker    │         └────────────┬─────────────┘
   └───────────────────────────────────────┘                      │
                                     ┌────────────────────────────┼───────────────┐
                                     ▼                            ▼               │
                         ┌──────────────────────┐    ┌────────────────────────┐   │
                         │ web (Next.js)        │    │ api (FastAPI)          │   │
                         │ rendu des pages      │───►│ règles métier, RBAC,   │   │
                         │ publiques à la       │    │ audit, signature des   │   │
                         │ requête              │    │ licences, SSE          │   │
                         └──────────────────────┘    └───┬──────────┬─────────┘   │
                                                         ▼          ▼             │
                                                  PostgreSQL 16   Redis           │
                                                  (données)       (cache, débit,  │
                                                                   temps réel)    │
```

Tout tourne dans des conteneurs Docker (`docker-compose.yml`). La configuration passe
exclusivement par des variables d'environnement (`.env.example`, commenté).

## API (`apps/api`)

| Dossier | Rôle |
|---|---|
| `core/` | configuration, sécurité (argon2id, JWT), RBAC, chiffrement, limitation de débit, erreurs |
| `db/` | moteur SQLAlchemy, base déclarative, type de colonne chiffrée |
| `models/` | tables (une par domaine : registre, matchs, feuille, discipline, votes, billetterie, talents, audit) |
| `domain/` | **règles métier pures, sans base de données**, testées unitairement : calendrier (Berger), classement, phases finales, composition, événements, suspensions, éligibilité, jetons signés |
| `services/` | orchestration : base + règles + journal d'audit, dans une même transaction |
| `api/v1/` | routes HTTP (documentation OpenAPI sur `/api/v1/docs`) |
| `providers/` | interfaces SMS, paiement, stockage, avec simulateurs locaux |
| `realtime/` | publication des scores en direct (Redis pub/sub) |
| `seed/` | données de référence et de démonstration |

Choix structurants :

- **SQLAlchemy synchrone** : FastAPI exécute les routes dans un pool de threads ; plus simple
  à maintenir, largement suffisant pour 20 équipes et 99 matchs.
- **Règles paramétrables** : toutes dans `competition_rules` (une ligne par saison). Le code
  ne contient aucun seuil sportif en dur.
- **Erreurs métier** : `BusinessError` → réponse 422 `{detail, code, details}` en français.
- **Migrations Alembic** : `apps/api/migrations`. Les colonnes chiffrées y apparaissent en
  `BYTEA` (la migration ne dépend pas du code de chiffrement).

### Authentification et rôles

- Jeton d'accès JWT de 15 minutes, conservé **en mémoire** par le navigateur.
- Jeton de rafraîchissement dans un cookie `httpOnly`, `SameSite=Strict`, limité au chemin
  `/api/v1/auth` ; **rotation** à chaque usage. Réutiliser un ancien jeton révoque toute la
  session (signe de vol).
- Connexions limitées (10 tentatives / 5 min par adresse IP et compte, Redis).
- Rôles → permissions : `core/rbac.py`. Le `gestionnaire_club` est limité à son équipe
  (`ensure_team_scope`). Un délégué n'édite que les feuilles qui lui sont attribuées.

### Licences numériques

Jeton `LDS1.<données>.<signature>` :
- données : JSON canonique (clés triées) en base64url — numéro, nom, équipe, qualité,
  validité, identifiant de clé (`kid`) ; **ni date de naissance, ni CNIB**.
- signature Ed25519 sur `LDS1.<données>`.

Clés publiques exposées sur `GET /api/v1/licences/public-keys`. La page `/controle` les met en
cache, avec la liste des licences suspendues/révoquées (`/licences/status-list`) : la
vérification au stade fonctionne sans réseau. **Rotation** : nouvelle `LICENCE_SIGNING_KEY` +
nouveau `LICENCE_KEY_ID`, l'ancienne clé publique dans `LICENCE_PREVIOUS_PUBLIC_KEYS`, puis
ré-émission des licences.

### Feuille de match

Cycle : **brouillon** (compositions) → **soumise** (compositions verrouillées après contrôle
des règles ; match en direct ; saisie des événements) → **validée** (score officiel,
classement, suspensions, tableau final) → **clôturée** (administration).

À chaque ajout ou suppression, les événements sont **rejoués dans l'ordre chronologique**
(`domain/match_events.py`) : un joueur remplacé ne peut plus marquer, un remplaçant n'entre
qu'une fois, un exclu ne joue plus, etc. Les événements portent un `client_uuid` : rejouer la
même action (synchronisation hors ligne) ne crée pas de doublon.

### Classements

Calculés par `domain/standings.py` à partir des matchs validés : barème et critères de la
saison, confrontations directes ré-appliquées aux seules équipes encore à égalité, égalités
non résolues signalées (`needs_draw`). Résultat mis en cache dans Redis avec une **clé
versionnée**, incrémentée après le commit de chaque résultat.

### Temps réel

Chaque modification d'un match publie son état sur le canal Redis `lds:live` ; l'API le
diffuse en **Server-Sent Events** (`GET /api/v1/live`). Le reverse proxy ne doit pas mettre ce
flux en tampon (voir l'exemple Caddy).

## Site web et PWA (`apps/web`)

- **Next.js (App Router)** avec Cache Components : les pages publiques sont un squelette
  statique et les données sont rendues **à la requête** (rien n'est figé au build, l'image est
  donc portable d'un serveur à l'autre).
- Types TypeScript **générés depuis l'OpenAPI** : `pnpm gen:api` → `src/lib/api-schema.ts`.
- Pages publiques : `src/app/(public)`. Espace officiels : `src/app/(app)` — back-office
  (`admin/equipes`, `admin/calendrier`, `admin/journal`), feuilles de match (`delegue`),
  contrôle des licences (`controle`). Le menu et l'écran d'arrivée dépendent des
  permissions renvoyées par `/auth/me` ; l'API reste la seule garante des droits.

### Fonctionnement hors connexion

| Élément | Mécanisme |
|---|---|
| Écrans officiels | service worker Serwist (`src/sw/sw.ts`, construit par `scripts/build-sw.mjs` après `next build`) : précache des ressources et des pages `/connexion`, `/delegue`, `/controle` ; une même coquille sert pour toutes les feuilles de match |
| Données | IndexedDB via Dexie (`src/lib/offline/db.ts`) : feuilles de match, liste des matchs, profil, clés de licences |
| Actions | file locale rejouée dans l'ordre (`use-sheet.ts`) ; affichage optimiste (`apply.ts`) ; une action refusée par le serveur est signalée et peut être abandonnée |

L'API n'est jamais mise en cache par le service worker : les données passent uniquement par
IndexedDB, ce qui évite d'afficher une donnée périmée sans le savoir.

## Phases 2 et 3

Tables déjà créées (squelette) : `ballots`, `ballot_options`, `votes`, `otp_challenges`,
`ticket_types`, `orders`, `tickets`, `accreditations`, `player_stats`. Les interfaces
`SmsProvider` et `PaymentProvider` et leurs simulateurs existent ; la logique (OTP, détection
des votes en masse, procès-verbal, billets signés `TKT1.…` sur le même modèle que les
licences, contrôle d'accès hors ligne) reste à développer.

## Tests

| Niveau | Commande | Contenu |
|---|---|---|
| Unitaires | `pytest tests/unit` | règles pures : calendrier, classement, phases finales, composition (règle des locaux), événements, suspensions, éligibilité, jetons signés, chiffrement, fournisseurs |
| Intégration | `pytest tests/integration` | API complète sur PostgreSQL réel (base de test migrée et seedée, transaction annulée par test) |
| Bout en bout | `pnpm e2e` | parcours délégué sur mobile, dont un événement saisi hors connexion puis synchronisé |

La CI GitHub Actions (`.github/workflows/ci.yml`) exécute lint, tests et build, puis le
parcours de bout en bout sur une pile complète.
