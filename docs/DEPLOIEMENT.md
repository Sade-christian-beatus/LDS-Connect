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

> **Contrôle au démarrage** : avec `ENVIRONMENT=production`, l'API **refuse de démarrer** et
> liste les réglages à corriger si l'un de ces points n'est pas respecté : `JWT_SECRET` d'au
> moins 32 caractères, clés de chiffrement et de signature renseignées,
> `REFRESH_COOKIE_SECURE=true`, adresses publiques en `https`, aucune origine `localhost` ni
> `*` dans `CORS_ORIGINS`, aucun simulateur (`SMS_PROVIDER` / `PAYMENT_PROVIDER`).

> **Votes du public et SMS** : seuls le simulateur et l'affichage dans les journaux
> (`console`) existent aujourd'hui. **Les votes ne doivent pas être ouverts en production**
> avant le branchement d'un connecteur SMS réel (opérateur ou agrégateur choisi par la Ligue,
> à implémenter dans `apps/api/src/lds_api/providers/sms`). En production, `console`
> n'envoie rien et n'écrit pas les messages dans les journaux : la demande de code répond
> « Votes indisponibles : opérateur SMS non configuré » et le lien des billets n'est pas
> envoyé par SMS (l'acheteur le garde à l'écran après le paiement).

> **Billetterie et paiement** : seul le simulateur existe (`PAYMENT_PROVIDER=simulator`, aucun
> argent réel). **Ne pas vendre de billets en production** avant le branchement du connecteur
> de l'agrégateur choisi par la Ligue (`apps/api/src/lds_api/providers/payment`). Les
> notifications de paiement sont **signées** : l'API refuse (401) toute notification dont la
> signature ne correspond pas à `PAYMENT_WEBHOOK_SECRET` (HMAC-SHA256 du corps brut, en-tête
> `X-LDS-Signature` pour le simulateur ; le connecteur réel appliquera le schéma de signature
> de l'agrégateur dans `parse_notification`). Ce secret est obligatoire en production dès que
> le paiement est activé. Avec `disabled`, l'achat répond « paiement pas
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

- `/api/*` → `127.0.0.1:8000`, **sans mise en tampon** (flux temps réel SSE) ;
- tout le reste → `127.0.0.1:3000`.

Le proxy tourne sur le serveur (hors Docker) : `sudo apt install caddy`, copier l'exemple dans
`/etc/caddy/Caddyfile` en remplaçant le nom de domaine, puis `sudo systemctl reload caddy`.

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

**Adresse des visiteurs.** Le proxy doit transmettre `X-Forwarded-For` (Caddy le fait par
défaut). L'API ne lit cet en-tête que si la connexion vient d'un réseau listé dans
`TRUSTED_PROXIES` (par défaut : boucle locale et réseaux privés, ce qui couvre un proxy sur
l'hôte comme dans Docker) et retient la dernière adresse non fiable de la chaîne : un visiteur
ne peut pas se faire passer pour un autre en ajoutant l'en-tête lui-même. Sans cela, tous les
visiteurs auraient l'adresse du proxy et les limites anti-abus (votes, commandes) deviendraient
globales. Si le serveur est lui-même sur un réseau privé partagé avec des machines non
maîtrisées, restreindre `TRUSTED_PROXIES` à l'adresse exacte du proxy.

**En-têtes de sécurité.** Le site envoie lui-même sa politique de contenu
(`Content-Security-Policy` : ressources de la même origine seulement, aucun affichage dans le
cadre d'un autre site), `X-Frame-Options: DENY` et `Permissions-Policy` (caméra réservée au
site pour la lecture des QR, micro, géolocalisation et paiement navigateur coupés) ; voir
`apps/web/next.config.ts`. Le proxy ajoute HSTS et les mêmes protections pour les réponses de
l'API (exemple Caddy). Avec Nginx :

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(self), microphone=(), geolocation=(), payment=()" always;
```

Le HTTPS est **obligatoire** : le service worker, la caméra (lecture des QR) et le cookie
sécurisé ne fonctionnent qu'en contexte sécurisé.

## 4. Sauvegardes

```bash
make backup   # base : backups/lds-AAAAMMJJ-HHMMSS.dump ; fichiers : backups/lds-files-….tar.gz
```

À planifier chaque nuit (crontab de l'utilisateur `lds`) et **copier hors du serveur** :

```cron
30 2 * * * cd /opt/lds-connect && COMPOSE="docker compose -f docker-compose.yml" ./infra/scripts/backup.sh >> /var/log/lds-backup.log 2>&1
```

Pendant les journées de match, une sauvegarde supplémentaire après la dernière rencontre est
recommandée. Les fichiers téléversés (logos, photos de licence) sont archivés à chaque
sauvegarde avec le stockage sur disque (avec S3, activer la gestion des versions du bucket).
Le fichier `.env` se garde dans le coffre-fort, pas avec les sauvegardes. Les 30 dernières
sauvegardes de chaque type sont conservées (`KEEP=…` pour changer).

**Purge des données à durée limitée** (codes de vote, commandes non payées, numéros des
acheteurs ; durées dans `.env`, variables `RETENTION_*`) : à planifier chaque nuit après la
sauvegarde. `make purge DRY=1` affiche ce qui serait effacé sans rien toucher ; chaque passage
est inscrit au journal d'audit.

```cron
0 3 * * * cd /opt/lds-connect && docker compose -f docker-compose.yml exec -T api python -m lds_api.cli purge >> /var/log/lds-purge.log 2>&1
```

**Restauration** (remplace la base actuelle, confirmation demandée) :

```bash
make restore FILE=backups/lds-20270110-023000.dump   # + lds-files-20270110-023000.tar.gz s'il existe
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

Logos : après l'installation, le Secrétariat exécutif envoie le logo de la Ligue (menu
**Identité**) et l'administration celui de chaque équipe (fiche de l'équipe). Les fichiers sont
dans le stockage de la plateforme (volume `storage` ou S3), jamais dans le dépôt de code : la
sauvegarde de la base ne les contient pas, sauvegarder aussi ce volume (voir « Sauvegardes »).

Recalcul complet des statistiques des joueurs (elles se mettent à jour seules à chaque
validation de feuille ; utile après une reprise de données) :

```bash
docker compose exec api python -m lds_api.cli refresh-stats
```

Les fichiers sont écrits dans le volume `storage` (`/app/var/storage/exports` dans le
conteneur). CNIB et téléphones y sont **masqués** ; l'option `--include-sensitive` les inclut
en clair (action journalisée, fichier à protéger).
