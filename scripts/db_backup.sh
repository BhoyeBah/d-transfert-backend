#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SHELL_COMPOSE_FILE="${COMPOSE_FILE:-}"
SHELL_BACKUP_DIR="${BACKUP_DIR:-}"
SHELL_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.prod}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier d'environnement introuvable: $ENV_FILE" >&2
  echo "Renseigne ENV_FILE si ton fichier de prod a un autre nom." >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

COMPOSE_FILE="${SHELL_COMPOSE_FILE:-${COMPOSE_FILE:-$ROOT_DIR/docker-compose.prod.yml}}"
BACKUP_DIR="${SHELL_BACKUP_DIR:-${BACKUP_DIR:-$ROOT_DIR/backups}}"
RETENTION_COUNT="${SHELL_RETENTION_COUNT:-${BACKUP_RETENTION_COUNT:-14}}"

mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="$BACKUP_DIR/dtransfert_${timestamp}.dump.gz"

echo "Creation de la sauvegarde: $backup_file"

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres sh -lc '
  set -euo pipefail
  export PGPASSWORD="$POSTGRES_PASSWORD"
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc
' | gzip > "$backup_file"

gzip -t "$backup_file"

echo "Sauvegarde terminee."

if [[ "$RETENTION_COUNT" -gt 0 ]]; then
  mapfile -t backups < <(
    find "$BACKUP_DIR" -maxdepth 1 -type f -name 'dtransfert_*.dump.gz' | sort
  )

  if (( ${#backups[@]} > RETENTION_COUNT )); then
    delete_count=$(( ${#backups[@]} - RETENTION_COUNT ))
    for ((i = 0; i < delete_count; i++)); do
      rm -f "${backups[i]}"
    done
    echo "Rotation appliquee: ${delete_count} ancienne(s) sauvegarde(s) supprimee(s)."
  fi
fi

echo "Fichier disponible: $backup_file"
