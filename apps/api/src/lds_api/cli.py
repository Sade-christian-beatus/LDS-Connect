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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lds_api.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("gen-keys", help="Génère des clés neuves")
    p.add_argument("--write", metavar="FICHIER_ENV", help="Inscrit les clés vides dans ce fichier")
    p.set_defaults(func=cmd_gen_keys)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
