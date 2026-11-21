#!/usr/bin/env bash
# Restauration d'une sauvegarde produite par backup.sh.
# Usage : ./infra/scripts/restore.sh backups/lds-AAAAMMJJ-HHMMSS.dump
# ATTENTION : remplace le contenu actuel de la base.
set -euo pipefail

FILE="${1:?Indiquer le fichier de sauvegarde à restaurer}"
COMPOSE="${COMPOSE:-docker compose}"
[ -f "$FILE" ] || { echo "Fichier introuvable : $FILE" >&2; exit 1; }

read -r -p "Restaurer $FILE et ÉCRASER la base actuelle ? Taper OUI pour confirmer : " ok
[ "$ok" = "OUI" ] || { echo "Annulé."; exit 1; }

$COMPOSE stop api web
$COMPOSE exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$FILE"
$COMPOSE start api web
echo "Restauration terminée."
