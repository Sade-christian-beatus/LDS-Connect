#!/usr/bin/env bash
# Sauvegarde complète de la base PostgreSQL de LDS Connect (format custom pg_dump).
# Usage : ./infra/scripts/backup.sh [dossier_de_sortie]   (défaut : ./backups)
# À planifier quotidiennement (cron) et à copier HORS du serveur.
set -euo pipefail

OUT_DIR="${1:-./backups}"
COMPOSE="${COMPOSE:-docker compose}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"

FILE="$OUT_DIR/lds-$STAMP.dump"
$COMPOSE exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE"

# Conservation : 30 sauvegardes les plus récentes (réglable via KEEP)
KEEP="${KEEP:-30}"
ls -1t "$OUT_DIR"/lds-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm --

echo "Sauvegarde écrite : $FILE ($(du -h "$FILE" | cut -f1))"
