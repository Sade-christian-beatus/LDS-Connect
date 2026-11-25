#!/usr/bin/env bash
# Sauvegarde complète de LDS Connect : base PostgreSQL (format custom pg_dump) et fichiers
# téléversés du volume `storage` (logos, photos de licence ; les exports régénérables sont exclus).
# Usage : ./infra/scripts/backup.sh [dossier_de_sortie]   (défaut : ./backups)
# À planifier quotidiennement (cron) et à copier HORS du serveur.
set -euo pipefail

OUT_DIR="${1:-./backups}"
COMPOSE="${COMPOSE:-docker compose}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

FILE="$OUT_DIR/lds-$STAMP.dump"
$COMPOSE exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE"

echo "Base sauvegardée : $FILE ($(du -h "$FILE" | cut -f1))"

# Fichiers : seulement avec le stockage sur disque (avec S3, le fournisseur assure la copie)
BACKEND="$($COMPOSE exec -T api sh -c 'echo "${STORAGE_BACKEND:-local}"' | tr -d '\r')"
if [ "$BACKEND" = "local" ]; then
  FILES="$OUT_DIR/lds-files-$STAMP.tar.gz"
  $COMPOSE exec -T api tar -C /app/var/storage --exclude=./exports -czf - . > "$FILES"
  echo "Fichiers sauvegardés : $FILES ($(du -h "$FILES" | cut -f1))"
else
  echo "Stockage $BACKEND : fichiers non archivés ici (copie assurée côté fournisseur)."
fi

# Conservation : 30 sauvegardes les plus récentes de chaque type (réglable via KEEP)
KEEP="${KEEP:-30}"
for pattern in "lds-*.dump" "lds-files-*.tar.gz"; do
  # shellcheck disable=SC2086
  ls -1t "$OUT_DIR"/$pattern 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm --
done
