# Déploiement (guide générique pour l'équipe informatique de la Ligue)

LDS Connect ne dépend d'aucun fournisseur cloud. Il suffit d'un serveur Linux avec Docker.
Ce guide décrit une installation sur **un seul serveur**, adaptée à la phase pilote.

## 1. Serveur

| Élément | Recommandation phase pilote |
|---|---|
| Système | Ubuntu Server 24.04 LTS ou Debian 12 |
| Processeur / mémoire | 4 vCPU, 8 Go de RAM |
| Disque | 80 Go SSD (base, sauvegardes locales, journaux) |
| Réseau | adresse IP publique, ports 80 et 443 ouverts ; SSH limité aux administrateurs |
| Localisation | à décider par la Ligue (voir question ouverte n° 23) |

Installer Docker (paquet officiel `docker-ce` + plugin `docker compose`), `make` et `git`.
Créer un utilisateur dédié (ex. `lds`) membre du groupe `docker`.

## 2. Installation

```bash
git clone <adresse-du-dépôt> /opt/lds-connect && cd /opt/lds-connect
```

```bash
cp .env.example .env && make keys-into-env
```

Puis éditer `.env` :

| Variable | Valeur en production |
|---|---|
| `ENVIRONMENT` | `production` (bloque les données de démonstration) |
| `PUBLIC_BASE_URL`, `API_BASE_URL` | `https://<domaine>` |
| `CORS_ORIGINS` | `https://<domaine>` |
| `POSTGRES_PASSWORD` | mot de passe long et aléatoire |
| `REFRESH_COOKIE_SECURE` | `true` |
| `SMS_PROVIDER`, `PAYMENT_PROVIDER` | `console` / `disabled` tant que les contrats ne sont pas signés |
| `VOTE_ALLOWED_COUNTRY_CODES` | `226` (Burkina Faso) ; ajouter d'autres indicatifs pour la diaspora |
| `TICKET_ALLOWED_COUNTRY_CODES` | `226` : indicatifs acceptés pour l'achat de billets |
| `PAYMENT_CALLBACK_BASE_URL` | adresse publique de l'API vue par l'agrégateur (vide = `API_BASE_URL`) |

> **Votes du public et SMS** : seuls le simulateur et l'affichage dans les journaux
> (`console`) existent aujourd'hui. **Les votes ne doivent pas être ouverts en production**
> avant le branchement d'un connecteur SMS réel (opérateur ou agrégateur choisi par la Ligue,
> à implémenter dans `apps/api/src/lds_api/providers/sms`). Avec `console`, les codes
> n'apparaissent que dans les journaux du serveur.

> **Billetterie et paiement** : seul le simulateur existe (`PAYMENT_PROVIDER=simulator`, aucun
> argent réel). **Ne pas vendre de billets en production** avant le branchement du connecteur
> de l'agrégateur choisi par la Ligue (`apps/api/src/lds_api/providers/payment`), qui DOIT
> vérifier la signature de ses notifications. Avec `disabled`, l'achat répond « paiement pas
> encore disponible ». Une commande payée après la fin de sa réservation, sans place restante,
> est annulée et marquée « à rembourser » dans le journal d'audit.

> **Clés** (`JWT_SECRET`, `FIELD_ENCRYPTION_KEY`, `BLIND_INDEX_KEY`, `LICENCE_SIGNING_KEY`) :
> conserver une copie **hors du serveur** (coffre-fort de mots de passe, deux personnes
> habilitées). Perdre `FIELD_ENCRYPTION_KEY` rend les CNIB et téléphones illisibles ;
> perdre `LICENCE_SIGNING_KEY` oblige à ré-émettre toutes les licences. Ne jamais commiter
> le fichier `.env`.

Démarrer en **configuration production** (sans la surcouche de développement) :

```bash
docker compose -f docker-compose.yml up -d --build
```

```bash
docker compose -f docker-compose.yml exec api alembic upgrade head
```

```bash
docker compose -f docker-compose.yml exec api python -m lds_api.cli seed --no-demo
```

Le seed `--no-demo` crée la saison 2027, les règles, les 17 régions, les 2 poules et les
20 équipes, sans compte ni joueur fictif. Créer ensuite le premier compte du Secrétariat
exécutif (mot de passe demandé sans écho, 12 caractères minimum) :

```bash
docker compose -f docker-compose.yml exec api python -m lds_api.cli create-user --email secretariat@<domaine> --name "Secrétariat exécutif" --role super_admin
```

Les autres comptes (délégués, gestionnaires de club, contrôleurs…) se créent ensuite dans
l'interface, menu **Comptes** du super administrateur : un mot de passe provisoire est
généré et affiché une seule fois, à transmettre par un canal sûr ; à sa première connexion,
la personne est **obligée** de le remplacer (rien d'autre n'est accessible avant). La commande `create-user` reste disponible en secours.

PostgreSQL et Redis ne sont pas publiés par `docker-compose.yml`. L'API (8000) et le site
(3000) sont liés à `127.0.0.1` (variable `BIND_ADDRESS`) : seul le reverse proxy du serveur y
accède.

## 3. Reverse proxy et TLS

Un exemple Caddy (certificats Let's Encrypt automatiques) est fourni :
`infra/caddy/Caddyfile.example`. Routage attendu :

- `/api/*` → `api:8000`, **sans mise en tampon** (flux temps réel SSE) ;
- tout le reste → `web:3000`.

Avec Nginx, l'équivalent pour le flux en direct :

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;          # indispensable pour /api/v1/live
    proxy_read_timeout 1h;
}
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
}
```

Le HTTPS est **obligatoire** : le service worker, la caméra (lecture des QR) et le cookie
sécurisé ne fonctionnent qu'en contexte sécurisé.

## 4. Sauvegardes

```bash
make backup                 # écrit backups/lds-AAAAMMJJ-HHMMSS.dump (30 dernières conservées)
```

À planifier chaque nuit (crontab de l'utilisateur `lds`) et **copier hors du serveur** :

```cron
30 2 * * * cd /opt/lds-connect && COMPOSE="docker compose -f docker-compose.yml" ./infra/scripts/backup.sh >> /var/log/lds-backup.log 2>&1
```

Pendant les journées de match, une sauvegarde supplémentaire après la dernière rencontre est
recommandée. Sauvegarder aussi le volume `storage` (fichiers téléversés) et le fichier `.env`
(dans le coffre-fort, pas avec les sauvegardes de la base).

**Restauration** (remplace la base actuelle, confirmation demandée) :

```bash
make restore FILE=backups/lds-20270110-023000.dump
```

Tester une restauration au moins une fois avant le coup d'envoi, sur un serveur de test.

## 5. Mise à jour

```bash
make backup
```

```bash
git pull
```

```bash
docker compose -f docker-compose.yml up -d --build
```

```bash
docker compose -f docker-compose.yml exec api alembic upgrade head
```

Éviter les mises à jour pendant un match : les feuilles en cours restent sur les téléphones
des délégués et se synchronisent ensuite, mais mieux vaut ne pas tester ce scénario un jour
de match.

## 6. Surveillance

- Santé : `GET /api/v1/health` (à surveiller toutes les minutes).
- Journaux : `docker compose -f docker-compose.yml logs -f api web`.
- Journal d'audit : table `audit_logs` (en ajout seul, protégée par un déclencheur).
- Disque : vérifier l'espace libre (sauvegardes, journaux Docker).

## 7. Export des données

Les données appartiennent à la Ligue. Export complet (JSON + CSV, une table par fichier) :

```bash
make export
```

Recalcul complet des statistiques des joueurs (elles se mettent à jour seules à chaque
validation de feuille ; utile après une reprise de données) :

```bash
docker compose exec api python -m lds_api.cli refresh-stats
```

Les fichiers sont écrits dans le volume `storage` (`/app/var/storage/exports` dans le
conteneur). CNIB et téléphones y sont **masqués** ; l'option `--include-sensitive` les inclut
en clair (action journalisée, fichier à protéger).
