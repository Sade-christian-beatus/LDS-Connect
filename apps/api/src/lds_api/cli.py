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
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
