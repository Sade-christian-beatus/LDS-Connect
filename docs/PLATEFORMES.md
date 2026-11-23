# Les « plateformes » de LDS Connect : qui utilise quoi ?

**En une phrase :** LDS Connect est **un seul site web** (une seule adresse, par exemple
`https://lds-connect.bf`). Selon que l'on est connecté ou non, et selon son rôle, on y voit
des **espaces** différents. Il n'y a **pas d'application à télécharger** sur Play Store ou
App Store : sur téléphone, on « installe » le site depuis le navigateur (PWA), et il
s'ouvre ensuite comme une application.

```
                         https://lds-connect.bf  (une seule adresse)
                                       │
          ┌────────────────────────────┴─────────────────────────────┐
          │                                                          │
   SITE PUBLIC  (sans compte)                        ESPACE OFFICIELS  (/connexion)
   supporters, médias, clubs                         selon le rôle du compte :
   ─ accueil, scores en direct                       ─ Back-office (ordinateur)
   ─ calendrier, résultats                              registre, licences, calendrier,
   ─ classements, statistiques                          délégués, billetterie, votes,
   ─ pages des équipes, votes du public                 accréditations, journal, comptes
   ─ billetterie, mes billets (hors réseau)          ─ Feuille de match (téléphone)
                                                        délégués — fonctionne hors réseau
                                                     ─ Contrôle des licences et des entrées
                                                        (téléphone) au stade — hors réseau
          │                                                          │
          └──────────────────────────┬───────────────────────────────┘
                                     │  (invisible pour les utilisateurs)
                           API  —  /api   (le « moteur »)
                           règles, données, sécurité, journal d'audit
                                     │
                         Base de données PostgreSQL
```

## Les espaces, un par un

| Espace | Adresse | Pour qui | Appareil | Compte | Hors réseau |
|---|---|---|---|---|---|
| **Site public** | `/` (accueil, `/calendrier`, `/resultats`, `/classements`, `/statistiques`, `/equipes`, `/joueurs`, `/votes`, `/billetterie`) | Tout le monde : supporters, médias, clubs | Téléphone ou ordinateur | Non (vote : code SMS ; achat : nom + numéro mobile money) | **Mes billets** (`/billets`) : oui, les billets restent sur le téléphone |
| **Back-office** | `/admin/…` | Secrétariat exécutif, administration de la compétition, gestionnaires de club, cellule technique | Ordinateur de préférence | Oui | Non |
| **Feuille de match** | `/delegue` | Délégués de match | **Téléphone** (installé comme une application) | Oui | **Oui** : saisie au bord du terrain, envoi au retour du réseau |
| **Contrôle des licences** | `/controle` | Délégués, contrôleurs au stade | **Téléphone** | Oui | **Oui** : vérification des QR codes sans réseau |
| **Contrôle des entrées** | `/acces` | Contrôleurs d'accès aux portes du stade | **Téléphone** | Oui | **Oui** : billets et accréditations vérifiés sans réseau, passages envoyés au retour du réseau |
| **Mon compte** | `/compte` | Tout officiel | Tous | Oui | Non |
| **API** | `/api` (documentation : `/api/v1/docs`) | Personne directement : c'est le moteur ; l'équipe informatique de la Ligue | — | — | — |

## Qui voit quoi dans l'espace officiels ?

Après connexion, chacun arrive directement sur **son** outil ; le menu ne montre que ce que
son rôle permet.

| Rôle | Arrive sur | Voit dans le menu |
|---|---|---|
| Super administrateur (Secrétariat exécutif) | Registre | Registre · Calendrier · Feuilles de match · Talents · Licences · Entrées · Billetterie · Accréditations · Votes · Journal · **Comptes** |
| Administration de la compétition | Registre | Registre · Calendrier · Feuilles de match · Talents · Licences · Entrées · Billetterie · Accréditations · Votes · Journal |
| Gestionnaire de club | **Fiche de son équipe** (et rien d'autre) | Registre (son équipe) |
| Délégué de match | **Mes matchs** | Registre (lecture) · Feuilles de match · Licences |
| Cellule technique | **Talents** | Registre (lecture) · Talents |
| Contrôleur d'accès | **Contrôle des entrées** | Licences · Entrées |

## « Application » ou « site » ?

C'est **le même code et la même adresse**. La différence est seulement dans la façon de
l'ouvrir :

- **Comme un site** : on tape l'adresse dans le navigateur (Chrome, Safari…).
- **Comme une application** : sur téléphone, menu du navigateur → « Ajouter à l'écran
  d'accueil » / « Installer l'application ». Une icône LDS apparaît ; le site s'ouvre en
  plein écran et les écrans des délégués et contrôleurs fonctionnent hors réseau.

Avantages : aucune publication sur les magasins d'applications, mise à jour instantanée
pour tout le monde, un seul produit à maintenir.

## Côté technique (pour l'équipe informatique)

| Dossier du dépôt | Ce que c'est | En production |
|---|---|---|
| `apps/web` | Le site (public + espace officiels), Next.js | Conteneur `web` |
| `apps/api` | L'API, FastAPI | Conteneur `api` |
| — | Base de données et cache | Conteneurs `postgres`, `redis` |
| `apps/simulateurs` | Faux SMS et faux paiements | **Développement uniquement** |
| Mailpit | Faux serveur de courriel | **Développement uniquement** |

Le reverse proxy (voir [DEPLOIEMENT.md](DEPLOIEMENT.md)) envoie `/api/…` vers l'API et tout
le reste vers le site : pour les utilisateurs, il n'y a qu'**une seule adresse**.

## Phases suivantes

Les votes du public (phase 2) sont une page du **site public** (`/votes`), gérée depuis le
menu **Votes** de l'espace officiels. La billetterie est une page du **site public**
(`/billetterie`, `/billets`) et deux outils de l'espace officiels : **Billetterie** (prix,
ventes) et **Entrées** (contrôle aux portes, hors réseau). Toujours une seule adresse.
