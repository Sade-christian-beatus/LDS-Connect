"""Double authentification (TOTP) des comptes officiels (audit M9).

- Activation depuis « Mon compte » : un secret est proposé (QR code), il n'est retenu qu'après
  la saisie d'un premier code correct.
- Connexion : après le mot de passe, un jeton « mfa » de 5 minutes est remis ; la session n'est
  ouverte qu'avec un code valide. Un code ne sert qu'une fois.
- Rôles d'administration : activation obligatoire (MFA_REQUIRED_ROLES) ; tant qu'elle n'est
  pas faite, seul « Mon compte » reste accessible.
- Perte du téléphone : le super administrateur réinitialise (journalisé) ; pour lui-même,
  commande `python -m lds_api.cli reset-mfa --email …` sur le serveur.
"""

import io
import time
from datetime import UTC, datetime

import segno
from sqlalchemy.orm import Session

from lds_api.core.config import get_settings
from lds_api.core.errors import BusinessError
from lds_api.domain import totp
from lds_api.models import User
from lds_api.services import audit


def required_for(user: User) -> bool:
    roles = get_settings().mfa_roles
    return any(r.value in roles for r in user.role_codes)


def enabled(user: User) -> bool:
    return user.totp_enabled_at is not None and bool(user.totp_secret)


def setup_pending(user: User) -> bool:
    """Activation exigée mais pas encore faite : seul « Mon compte » est permis."""
    return required_for(user) and not enabled(user)


def start_setup(db: Session, actor, user: User) -> dict:
    if enabled(user):
        raise BusinessError("La double authentification est déjà activée")
    secret = totp.new_secret()
    user.totp_secret = secret
    user.totp_last_step = None
    uri = totp.provisioning_uri(secret, user.email)
    buf = io.BytesIO()
    segno.make(uri, error="m").save(buf, kind="svg", scale=5, border=2, xmldecl=False, svgns=True)
    db.flush()
    return {"secret": secret, "otpauth_uri": uri, "qr_svg": buf.getvalue().decode()}


def check_code(user: User, code: str) -> bool:
    """Vérifie un code et le consomme (il ne pourra pas être rejoué)."""
    if not user.totp_secret:
        return False
    step = totp.verify(user.totp_secret, code, time.time(), last_step=user.totp_last_step)
    if step is None:
        return False
    user.totp_last_step = step
    return True


def enable(db: Session, actor, user: User, code: str) -> None:
    if enabled(user):
        raise BusinessError("La double authentification est déjà activée")
    if not user.totp_secret:
        raise BusinessError("Commencez par afficher le QR code d'activation")
    if not check_code(user, code):
        raise BusinessError(
            "Code incorrect : vérifiez l'heure du téléphone et réessayez", code="mfa_code"
        )
    user.totp_enabled_at = datetime.now(UTC)
    audit.record(db, actor, "mfa_enable", "user", user.id)


def disable(db: Session, actor, user: User, code: str) -> None:
    if not enabled(user):
        raise BusinessError("La double authentification n'est pas activée")
    if required_for(user):
        raise BusinessError("Obligatoire pour votre rôle : elle ne peut pas être désactivée")
    if not check_code(user, code):
        raise BusinessError("Code incorrect", code="mfa_code")
    _clear(user)
    audit.record(db, actor, "mfa_disable", "user", user.id)


def reset(db: Session, actor, user: User) -> None:
    """Réinitialisation par un administrateur (téléphone perdu) : à réactiver à la connexion."""
    _clear(user)
    audit.record(db, actor, "mfa_reset", "user", user.id)


def _clear(user: User) -> None:
    user.totp_secret = None
    user.totp_enabled_at = None
    user.totp_last_step = None
