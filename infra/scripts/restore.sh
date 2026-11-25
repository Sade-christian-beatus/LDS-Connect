#!/usr/bin/env bash
# Restauration d'une sauvegarde produite par backup.sh.
# Usage : ./infra/scripts/restore.sh backups/lds-AAAAMMJJ-HHMMSS.dump [backups/lds-files-….tar.gz]
# Sans second argument, l'archive des fichiers du même horodatage est utilisée si elle existe.
# ATTENTION : remplace le contenu actuel de la base (et des fichiers restaurés).
set -euo pipefail

FILE="${1:?Indiquer le fichier de sauvegarde à restaurer}"
COMPOSE="${COMPOSE:-docker compose}"
[ -f "$FILE" ] || { echo "Fichier introuvable : $FILE" >&2; exit 1; }
STAMP="$(basename "$FILE" .dump | sed 's/^lds-//')"
FILES="${2:-$(dirname "$FILE")/lds-files-$STAMP.tar.gz}"
[ -f "$FILES" ] || FILES=""

echo "Base : $FILE"
echo "Fichiers : ${FILES:-aucune archive (les fichiers actuels sont conservés)}"
read -r -p "Restaurer et ÉCRASER les données actuelles ? Taper OUI pour confirmer : " ok
[ "$ok" = "OUI" ] || { echo "Annulé."; exit 1; }

$COMPOSE stop api web
$COMPOSE exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$FILE"
if [ -n "$FILES" ]; then
  $COMPOSE run --rm --no-deps -T --entrypoint tar api -C /app/var/storage -xzf - < "$FILES"
fi
$COMPOSE start api web
echo "Restauration terminée."
