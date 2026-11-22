"""Contrôle d'accès par rôle (RBAC) : matrice rôle → permissions.

Les routes déclarent la permission requise ; le périmètre « club » (gestionnaire limité à son
équipe) est vérifié en plus par `ensure_team_scope`.
"""

from enum import StrEnum

from lds_api.models.enums import RoleCode


class Perm(StrEnum):
    # Registre
    TEAM_MANAGE = "team:manage"  # créer/modifier les équipes et engagements
    SQUAD_READ = "squad:read"  # lire un effectif complet (données internes)
    SQUAD_WRITE = "squad:write"  # ajouter/modifier joueurs et encadreurs
    SENSITIVE_READ = "sensitive:read"  # lire CNIB / téléphone (accès journalisé)
    RESIDENCE_VERIFY = "residence:verify"  # attester la résidence (statut « local »)
    # Licences
    LICENCE_ISSUE = "licence:issue"
    LICENCE_STATUS = "licence:status"  # suspendre / révoquer
    LICENCE_VERIFY = "licence:verify"  # vérifier au stade, télécharger la liste d'état
    # Compétition
    FIXTURE_MANAGE = "fixture:manage"  # générer le calendrier, affecter stade/date
    RULES_MANAGE = "rules:manage"
    # Feuille de match
    SHEET_EDIT = "sheet:edit"
    SHEET_VALIDATE = "sheet:validate"
    SHEET_CLOSE = "sheet:close"
    # Analyse et administration
    STATS_READ = "stats:read"
    AUDIT_READ = "audit:read"
    USER_MANAGE = "user:manage"
    DATA_EXPORT = "data:export"
    VOTE_MANAGE = "vote:manage"  # scrutins du public : création, examen des votes, PV


ROLE_PERMISSIONS: dict[RoleCode, frozenset[Perm]] = {
    RoleCode.SUPER_ADMIN: frozenset(Perm),
    RoleCode.ADMIN_COMPETITION: frozenset(
        {
            Perm.TEAM_MANAGE,
            Perm.SQUAD_READ,
            Perm.SQUAD_WRITE,
            Perm.SENSITIVE_READ,
            Perm.RESIDENCE_VERIFY,
            Perm.LICENCE_ISSUE,
            Perm.LICENCE_STATUS,
            Perm.LICENCE_VERIFY,
            Perm.FIXTURE_MANAGE,
            Perm.RULES_MANAGE,
            Perm.SHEET_EDIT,
            Perm.SHEET_VALIDATE,
            Perm.SHEET_CLOSE,
            Perm.STATS_READ,
            Perm.AUDIT_READ,
            Perm.VOTE_MANAGE,
        }
    ),
    # Limité à son équipe (voir ensure_team_scope)
    RoleCode.GESTIONNAIRE_CLUB: frozenset({Perm.SQUAD_READ, Perm.SQUAD_WRITE, Perm.SENSITIVE_READ}),
    RoleCode.DELEGUE_MATCH: frozenset(
        {Perm.SQUAD_READ, Perm.LICENCE_VERIFY, Perm.SHEET_EDIT, Perm.SHEET_VALIDATE}
    ),
    RoleCode.CELLULE_TECHNIQUE: frozenset({Perm.SQUAD_READ, Perm.STATS_READ}),
    RoleCode.CONTROLEUR_ACCES: frozenset({Perm.LICENCE_VERIFY}),
}

# Rôles dont le périmètre est restreint à une seule équipe
TEAM_SCOPED_ROLES = frozenset({RoleCode.GESTIONNAIRE_CLUB})


def permissions_for(roles: set[RoleCode]) -> frozenset[Perm]:
    perms: set[Perm] = set()
    for r in roles:
        perms |= ROLE_PERMISSIONS.get(r, frozenset())
    return frozenset(perms)


def is_team_scoped(roles: set[RoleCode]) -> bool:
    """Vrai si l'utilisateur n'a QUE des rôles limités à une équipe."""
    return bool(roles) and roles <= TEAM_SCOPED_ROLES
