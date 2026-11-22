# LDS Connect

Plateforme numérique de la **Ligue de la Souveraineté** (football, Burkina Faso) : registre
des équipes et des joueurs, licences numériques à QR code, calendrier, feuille de match
numérique utilisable hors connexion, classements et site public installable (PWA).

Proposée par LUPORA Group. Le code est portable et auto-hébergeable : l'hébergement est choisi
et payé par la Ligue, sans dépendance à un service payant imposé.

## Installation locale en 5 commandes

Prérequis : Docker (avec Compose), `make` et `git`. Aucun outil Python ou Node n'est nécessaire
sur la machine.

```bash
git clone <adresse-du-dépôt> lds-connect && cd lds-connect
```

```bash
make env       # crée .env à partir de .env.example et génère des clés neuves
```

```bash
make up        # construit et lance la pile en arrière-plan
```

```bash
make migrate   # crée les tables
```

```bash
make seed      # saison 2027, 17 régions, 2 poules, 20 équipes, comptes et joueurs FICTIFS
```

| Service | Adresse |
|---|---|
| Site public et espace officiels | http://localhost:3000 |
| Documentation interactive de l'API | http://localhost:8000/api/v1/docs |
| Courriels envoyés (Mailpit) | http://localhost:8025 |
| SMS et paiements simulés | http://localhost:8090 |

### Comptes de démonstration (développement uniquement)

Mot de passe commun : `Lds2027-demo` (refusé en production : le seed de démonstration ne
s'exécute pas si `ENVIRONMENT=production`).

| Compte | Rôle | Arrivée après connexion |
|---|---|---|
| `superadmin@lds.local` | super_admin (Secrétariat exécutif) | `/admin/equipes` — tout le back-office, dont les comptes |
| `admin@lds.local` | admin_competition | `/admin/equipes` — registre, licences, calendrier, journal |
| `club.vinnim@lds.local` | gestionnaire_club (Vinnim du Kadiogo uniquement) | fiche de son équipe |
| `delegue@lds.local` | delegue_match | `/delegue` — feuilles de match |
| `technique@lds.local` | cellule_technique | `/admin/equipes` (lecture) |
| `controle@lds.local` | controleur_acces | `/controle` — contrôle des licences |

Connexion : http://localhost:3000/connexion (lien « Espace officiels » en bas du site public).

Les joueurs et encadreurs du seed sont **fictifs** (noms tirés au hasard, CNIB « X… »,
téléphones « +226 00… »). Aucun logo officiel n'est intégré : les équipes sont représentées
par leurs initiales et une couleur, en attendant les fichiers et l'accord de la Ligue.

## Ce qui est disponible (phase 1)

- **Registre** : équipes, joueurs, encadreurs, effectifs par saison, contrôle de conformité
  (30 joueurs, 7 encadreurs, âge minimum, quota de moins de 19 ans), statut « local » calculé.
- **Licences numériques** : QR signé Ed25519, vérifiable au stade **sans réseau**
  (`/controle`), suspension et révocation, rotation de clés.
- **Calendrier** : 9 journées par poule (tables de Berger), stades et horaires modifiables,
  tableau des phases finales (quarts, demies, 3e place, finale).
- **Feuille de match** (`/delegue`) : compositions avec contrôle automatique des règles
  (dont **50 % de locaux parmi les titulaires**), événements, validation, suspensions
  automatiques. Fonctionne **hors connexion** : actions mises en file et synchronisées.
- **Classements** automatiques, critères de départage paramétrables par saison.
- **Site public** : accueil avec scores en direct, calendrier, résultats, classements, pages
  équipes (données des joueurs limitées : la compétition compte des mineurs).
- **Back-office** (`/admin`) : tableau de bord des 20 équipes, fiches équipes (joueurs,
  encadreurs, vérification des résidences, données sensibles en consultation journalisée),
  licences (délivrance, carte imprimable, suspension), calendrier (génération, stades,
  horaires, délégué attribué à chaque match, tableau final), journal d'audit, gestion des
  comptes (super administrateur : création avec mot de passe provisoire affiché une seule
  fois, rôle, désactivation, réinitialisation). Chacun change son mot de passe depuis
  « Mon compte ». Chaque rôle ne voit que ce qui le concerne.

Toutes les règles sportives sont dans la table `competition_rules` (une ligne par saison).

## Commandes utiles

`make help` liste toutes les commandes. Les principales :

| Commande | Effet |
|---|---|
| `make up` / `make dev` / `make down` | Lancer (arrière-plan / premier plan) ou arrêter la pile |
| `make logs` | Suivre les journaux |
| `make test` | Tests de l'API (pytest) |
| `make lint` | ruff, eslint, TypeScript |
| `make e2e` | Test de bout en bout (Playwright) — pile lancée et seedée |
| `make backup` / `make restore FILE=…` | Sauvegarde / restauration PostgreSQL |
| `make export` | Export complet des données (JSON + CSV) |

Sans Docker (PostgreSQL 16 et Redis installés, `uv` et `pnpm`) : `make install-local`,
`make migrate-local`, `make seed-local`, `make dev-local`, `make test-local`.

## Arborescence

```
apps/api/          API FastAPI (Python 3.12, SQLAlchemy 2, Alembic)
apps/web/          Site public + PWA officiels (Next.js, TypeScript, Tailwind)
apps/simulateurs/  Passerelle SMS et paiement factices (développement)
infra/             Reverse proxy d'exemple, scripts de sauvegarde
docs/              Architecture, déploiement, données personnelles, questions ouvertes
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Déploiement](docs/DEPLOIEMENT.md) — serveur Linux + Docker, TLS, sauvegardes, mises à jour
- [Données personnelles](docs/DONNEES_PERSONNELLES.md) — mineurs, chiffrement, journalisation, CIL
- [Questions ouvertes](docs/QUESTIONS_OUVERTES.md) — points à trancher par la Ligue
