# Données personnelles

Ce document décrit les traitements de LDS Connect et les mesures techniques en place. Il sert
de base au **dossier de déclaration auprès de la Commission de l'informatique et des libertés
(CIL) du Burkina Faso**, que le responsable de traitement (la Ligue) doit déposer. Il ne
remplace pas un avis juridique.

## 1. Responsable et finalités

- **Responsable de traitement** (à confirmer) : Secrétariat exécutif de la Ligue de la
  Souveraineté.
- **Sous-traitant technique** : LUPORA Group (développement), puis l'hébergeur choisi par la
  Ligue.
- **Finalités** : gestion des effectifs et des licences ; organisation des matchs (feuilles de
  match, discipline, classements) ; information du public ; à venir : votes du public,
  billetterie, suivi des talents.

## 2. Données traitées

| Catégorie | Données | Personnes | Accès |
|---|---|---|---|
| Identité | prénom, nom, nom d'usage, date et lieu de naissance, nationalité, genre | joueurs, encadreurs | administration, club (son équipe), délégué (noms) |
| Identifiants | **numéro CNIB** (chiffré) | joueurs, encadreurs | administration, club — **lecture journalisée** |
| Contact | **téléphone** (chiffré) | joueurs, encadreurs | administration, club — **lecture journalisée** |
| Sportif | poste, pied, numéro, région et date de début de résidence, licence FBF | joueurs | administration, club, délégué, cellule technique |
| Contrat | contrat signé, déclaration CNSS (oui/non) | joueurs, encadreurs | administration, club |
| Match | compositions, buts, cartons, suspensions | joueurs | public (noms d'usage) et officiels |
| Comptes | e-mail, nom, rôle, mot de passe **haché (argon2id)** | officiels | super administrateur |
| Traces | journal d'audit (auteur, action, date, adresse IP) | officiels | administration |
| Phase 2 | téléphone des votants (index HMAC + chiffré), acheteurs de billets | public | administration |

Aucune pièce d'identité numérisée n'est stockée à ce stade.

## 3. Mineurs (16-17 ans)

La compétition admet des joueurs dès 16 ans. Mesures appliquées :

- **Pages publiques** : uniquement le **nom d'usage** (« A. Ouédraogo »), le poste, l'équipe,
  le numéro de maillot et l'**âge en années**. Jamais la date de naissance complète, le lieu de
  naissance, le prénom complet, la CNIB, le téléphone ni la photo.
  Un test automatisé vérifie que ces champs ne figurent pas dans la réponse publique.
- **QR des licences** : nom, équipe, numéro, validité ; ni date de naissance ni CNIB (le
  contenu d'un QR est lisible par toute personne qui le scanne).
- **Autorisation parentale** : un champ est prévu ; son caractère obligatoire est à décider
  (question ouverte n° 17).

## 4. Mesures de sécurité

| Mesure | Mise en œuvre |
|---|---|
| Chiffrement au repos des champs sensibles | CNIB et téléphones chiffrés en AES-256-GCM (nonce aléatoire, intégrité vérifiée) avec une clé hors base (`FIELD_ENCRYPTION_KEY`) |
| Recherche sans déchiffrer | index aveugle HMAC-SHA256 (clé distincte `BLIND_INDEX_KEY`) : unicité des CNIB, « un vote par numéro » |
| Accès | rôles et permissions (`core/rbac.py`) ; un club ne voit que son équipe |
| Lecture des données sensibles | route dédiée, chaque lecture est inscrite au journal d'audit |
| Journal d'audit | qui / quoi / quand / IP sur licences, effectifs, feuilles de match, résultats, suspensions, connexions, exports ; valeurs sensibles masquées (`***`) dans le journal ; table **en ajout seul** (un déclencheur PostgreSQL interdit modification et suppression) |
| Authentification | mots de passe argon2id ; sessions courtes ; cookie `httpOnly` ; détection de réutilisation de jeton ; limitation des tentatives ; mots de passe provisoires générés aléatoirement, affichés une seule fois, jamais stockés en clair ni journalisés ; désactivation ou réinitialisation d'un compte = fermeture de ses sessions |
| Transport | HTTPS obligatoire en production (voir DEPLOIEMENT.md) |
| Appareils des officiels | les feuilles de match en cache sur le téléphone contiennent des noms complets et des âges, pas de CNIB ni de téléphone ; la déconnexion efface le profil et les feuilles en cache (seules les actions non encore synchronisées sont conservées) |
| Sauvegardes | chiffrées au repos pour les champs sensibles ; à stocker hors du serveur, accès restreint |
| Données de test | seed de démonstration **100 % fictif**, refusé en production |

## 5. Droits des personnes

- **Accès / rectification** : via le club ou l'administration (modification journalisée).
- **Effacement** : un joueur quittant l'effectif est retiré (licence révoquée) ; l'historique
  sportif (feuilles de match validées) est conservé pour l'intégrité des résultats. La
  procédure d'effacement complet sur demande reste à définir avec la Ligue.
- **Portabilité / propriété des données** : `make export` produit un export complet JSON + CSV.
  CNIB et téléphones y sont masqués par défaut ; l'export avec données sensibles
  (`--include-sensitive`) est journalisé et doit être protégé comme la base elle-même.

## 6. Points à décider par la Ligue

- Désignation formelle du responsable de traitement et dépôt de la déclaration CIL.
- Durées de conservation par catégorie (licences, feuilles, journaux, votes, billets).
- Autorisation parentale pour les mineurs ; publication éventuelle de photos.
- Localisation de l'hébergement (au Burkina Faso ou non) et contrat avec l'hébergeur.
- Information des joueurs (mention à intégrer au formulaire d'inscription / au contrat).
