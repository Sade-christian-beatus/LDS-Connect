"""Données de référence publiques (annonce du 20 novembre 2026).

Les couleurs sont des emplacements génériques : aucun logo ni charte officielle n'est intégré
tant que la Ligue n'a pas fourni les fichiers et donné son accord.
"""

from dataclasses import dataclass

from lds_api.models.enums import RoleCode

REGIONS = [
    "Kadiogo",
    "Oubri",
    "Koulsé",
    "Liptako",
    "Nakambé",
    "Gulmu",
    "Sirba",
    "Tapoa",
    "Guiriko",
    "Tannounyan",
    "Nando",
    "Bankui",
    "Sourou",
    "Djôrô",
    "Yaadga",
    "Soum",
    "Nazinon",
]

POOLS = [
    ("A", "Poule A", "Ouagadougou"),
    ("B", "Poule B", "Bobo-Dioulasso"),
]

# Stades : à confirmer par la Ligue (voir docs/QUESTIONS_OUVERTES.md)
VENUES = [
    ("Stade de Ouagadougou (à confirmer)", "Ouagadougou"),
    ("Stade de Bobo-Dioulasso (à confirmer)", "Bobo-Dioulasso"),
]


@dataclass(frozen=True)
class TeamSeed:
    pool: str
    region: str
    name: str
    short_name: str
    acronym: str | None
    primary_color: str
    secondary_color: str = "#ffffff"


TEAMS = [
    TeamSeed("A", "Kadiogo", "Vinnim du Kadiogo", "Vinnim", None, "#b8860b"),
    TeamSeed("A", "Kadiogo", "Nanga du Kadiogo", "Nanga", None, "#c62828"),
    TeamSeed("A", "Kadiogo", "Riimda du Kadiogo", "Riimda", None, "#2e7d32"),
    TeamSeed("A", "Oubri", "Société Kâmdé Sports", "SKS", "SKS", "#33691e", "#f9a825"),
    TeamSeed("A", "Koulsé", "Union Sportive des Koulsé", "USK", "USK", "#6d4c41", "#ffd54f"),
    TeamSeed("A", "Liptako", "GA'I Liptako FC", "GA'I Liptako", None, "#283593", "#ffca28"),
    TeamSeed("A", "Nakambé", "Royal Sport du Nakambé", "RSN", "RSN", "#0277bd"),
    TeamSeed("A", "Gulmu", "GulmuSport", "GulmuSport", None, "#1b5e20", "#ff8f00"),
    TeamSeed("A", "Sirba", "Sirba Jakondiba", "Jakondiba", None, "#8d6e63", "#fff3e0"),
    TeamSeed("A", "Tapoa", "Tapua Sport Club", "Tapua SC", None, "#00897b"),
    TeamSeed("B", "Guiriko", "Silure Sport du Guiriko", "SSG", "SSG", "#1565c0"),
    TeamSeed("B", "Guiriko", "Dozo Sport du Guiriko", "Dozo Sport", None, "#004d40"),
    TeamSeed("B", "Tannounyan", "Union Sportive des Tannounyan", "UST", "UST", "#0d47a1"),
    TeamSeed("B", "Nando", "Nando Bõn-yẽesã", "Nando", None, "#558b2f", "#ffeb3b"),
    TeamSeed("B", "Bankui", "Mouhoun Sennatantola", "Sennatantola", None, "#37474f"),
    TeamSeed("B", "Sourou", "Sounako Goua Balan Dè", "Sounako", None, "#1a237e", "#ffc107"),
    TeamSeed("B", "Djôrô", "Djôrô Société Sportive", "Djôrô 2S", "Djôrô 2S", "#d32f2f"),
    TeamSeed("B", "Yaadga", "Yaadga Pangkèta", "Yaadga", None, "#3e2723", "#ffe082"),
    TeamSeed("B", "Soum", "Soum FC", "Soum FC", None, "#bf360c", "#ffd600"),
    TeamSeed("B", "Nazinon", "Nazinon Sports Club", "Nazinon SC", "Nazinon SC", "#2e7d32"),
]

ROLE_LABELS = {
    RoleCode.SUPER_ADMIN: "Super administrateur (Secrétariat exécutif)",
    RoleCode.ADMIN_COMPETITION: "Administrateur de la compétition",
    RoleCode.GESTIONNAIRE_CLUB: "Gestionnaire de club",
    RoleCode.DELEGUE_MATCH: "Délégué de match",
    RoleCode.CELLULE_TECHNIQUE: "Cellule technique",
    RoleCode.CONTROLEUR_ACCES: "Contrôleur d'accès",
}

# Comptes de démonstration (développement uniquement — refusés en production)
DEMO_PASSWORD = "Lds2027-demo"  # noqa: S105 — mot de passe de démonstration local
DEMO_USERS = [
    ("superadmin@lds.local", "Secrétariat exécutif (démo)", RoleCode.SUPER_ADMIN, None),
    ("admin@lds.local", "Admin compétition (démo)", RoleCode.ADMIN_COMPETITION, None),
    ("club.vinnim@lds.local", "Gestionnaire Vinnim (démo)", RoleCode.GESTIONNAIRE_CLUB, "Vinnim"),
    ("delegue@lds.local", "Délégué de match (démo)", RoleCode.DELEGUE_MATCH, None),
    ("technique@lds.local", "Cellule technique (démo)", RoleCode.CELLULE_TECHNIQUE, None),
    ("controle@lds.local", "Contrôleur d'accès (démo)", RoleCode.CONTROLEUR_ACCES, None),
]
