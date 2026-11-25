"""Commandes d'administration : python -m lds_api.cli <commande>."""

import argparse
import base64
import re
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate_keys() -> dict[str, str]:
    signing_pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return {
        "JWT_SECRET": secrets.token_urlsafe(48),
        "FIELD_ENCRYPTION_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
        "BLIND_INDEX_KEY": base64.b64encode(secrets.token_bytes(32)).decode(),
        "LICENCE_SIGNING_KEY": base64.b64encode(signing_pem).decode(),
        "PAYMENT_WEBHOOK_SECRET": secrets.token_urlsafe(32),
    }


def cmd_gen_keys(args: argparse.Namespace) -> None:
    keys = generate_keys()
    if not args.write:
        for k, v in keys.items():
            print(f"{k}={v}")
        return
    path = Path(args.write)
    content = path.read_text(encoding="utf-8")
    for k, v in keys.items():
        # Seules les valeurs vides sont remplies : une clé existante n'est jamais écrasée.
        content = re.sub(rf"^{k}=[ \t]*$", f"{k}={v}", content, flags=re.MULTILINE)
    path.write_text(content, encoding="utf-8")


def cmd_seed(args: argparse.Namespace) -> None:
    from sqlalchemy import func, select

    from lds_api.db.session import SessionLocal
    from lds_api.models import Person, Team, User
    from lds_api.seed import run as seed_run
    from lds_api.seed.reference import DEMO_PASSWORD

    with SessionLocal() as db:
        season = seed_run.run(db, demo=not args.no_demo, reset=args.reset)
        teams = db.scalar(select(func.count(Team.id)))
        persons = db.scalar(select(func.count(Person.id)))
        users = db.scalar(select(func.count(User.id)))
    print(f"Saison « {season.name} » : {teams} équipes, {persons} personnes, {users} comptes.")
    if not args.no_demo:
        print(f"Comptes de démonstration : *@lds.local, mot de passe « {DEMO_PASSWORD} ».")


def cmd_export(args: argparse.Namespace) -> None:
    from lds_api.db.session import SessionLocal
    from lds_api.services.export import export_all

    with SessionLocal() as db:
        result = export_all(db, Path(args.out), include_sensitive=args.include_sensitive)
    print(f"Export écrit dans {result.pop('directory')} ({len(result)} tables).")
    if args.include_sensitive:
        print("ATTENTION : cet export contient des CNIB et téléphones en clair.")


MIN_PASSWORD_LENGTH = 12


def cmd_create_user(args: argparse.Namespace) -> None:
    import getpass
    import sys

    from sqlalchemy import select

    from lds_api.core.security import hash_password
    from lds_api.db.session import SessionLocal
    from lds_api.models import Role, Team, User
    from lds_api.models.enums import RoleCode
    from lds_api.services import audit

    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Mot de passe : ")
        if password != getpass.getpass("Confirmer : "):
            raise SystemExit("Les mots de passe ne correspondent pas.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Mot de passe trop court ({MIN_PASSWORD_LENGTH} caractères minimum).")

    with SessionLocal() as db:
        email = args.email.strip().lower()
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit(f"Le compte {email} existe déjà.")
        role = db.scalar(select(Role).where(Role.code == RoleCode(args.role)))
        if role is None:
            raise SystemExit("Rôles absents : lancer d'abord `seed`.")
        team_id = None
        if args.role == RoleCode.GESTIONNAIRE_CLUB:
            team = db.scalar(select(Team).where(Team.slug == args.team))
            if team is None:
                raise SystemExit("Un gestionnaire de club exige --team <slug de l'équipe>.")
            team_id = team.id
        user = User(
            email=email,
            full_name=args.name,
            password_hash=hash_password(password),
            roles=[role],
            team_id=team_id,
        )
        db.add(user)
        db.flush()
        audit.record(db, None, "create", "user", user.id, {"email": email, "role": args.role})
        db.commit()
    print(f"Compte créé : {email} ({args.role}).")


def cmd_refresh_stats(args: argparse.Namespace) -> None:
    from lds_api.db.session import SessionLocal
    from lds_api.services import seasons, talents

    with SessionLocal() as db:
        n = talents.refresh(db, seasons.current_season(db))
        db.commit()
    print(f"Statistiques des joueurs recalculées : {n} ligne(s).")


def cmd_purge(args: argparse.Namespace) -> None:
    from lds_api.db.session import SessionLocal
    from lds_api.services.purge import purge

    with SessionLocal() as db:
        r = purge(db, dry_run=args.dry_run)
        if not args.dry_run:
            db.commit()
    verb = "à traiter" if args.dry_run else "traités"
    print(
        f"Purge ({verb}) : {r.otp_challenges} code(s) de vote, {r.unpaid_orders} commande(s) "
        f"non payée(s), {r.paid_order_phones} numéro(s) d'acheteur."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lds_api.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("gen-keys", help="Génère des clés neuves")
    p.add_argument("--write", metavar="FICHIER_ENV", help="Inscrit les clés vides dans ce fichier")
    p.set_defaults(func=cmd_gen_keys)

    p = sub.add_parser("seed", help="Charge les données de départ (idempotent)")
    p.add_argument("--no-demo", action="store_true", help="Sans comptes ni joueurs fictifs")
    p.add_argument("--reset", action="store_true", help="Vide la base avant (hors production)")
    p.set_defaults(func=cmd_seed)

    p = sub.add_parser("export", help="Export complet des données en JSON et CSV")
    p.add_argument("--out", default="./var/exports", help="Dossier de destination")
    p.add_argument(
        "--include-sensitive",
        action="store_true",
        help="Inclut CNIB et téléphones déchiffrés (fichier sensible, action journalisée)",
    )
    p.set_defaults(func=cmd_export)

    from lds_api.models.enums import RoleCode

    p = sub.add_parser("create-user", help="Crée un compte (ex. le premier super_admin)")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True, help="Nom complet")
    p.add_argument("--role", required=True, choices=[r.value for r in RoleCode])
    p.add_argument("--team", help="Slug de l'équipe (gestionnaire de club)")
    p.add_argument(
        "--password-stdin", action="store_true", help="Lit le mot de passe sur l'entrée standard"
    )
    p.set_defaults(func=cmd_create_user)

    p = sub.add_parser("purge", help="Efface les données arrivées au terme de leur conservation")
    p.add_argument("--dry-run", action="store_true", help="Compte sans rien effacer")
    p.set_defaults(func=cmd_purge)

    p = sub.add_parser("refresh-stats", help="Recalcule les statistiques des joueurs (saison)")
    p.set_defaults(func=cmd_refresh_stats)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
